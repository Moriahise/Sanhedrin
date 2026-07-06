#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_unused_files.py — sichere Bereinigung für Moriahise/Sanhedrin

Verschiebt ausschließlich Dateien, die in BEREINIGUNGS_ANALYSE.md als sicher
oder — nur mit --include-probable — sehr wahrscheinlich unnötig markiert wurden.
Es wird nie gelöscht, nur nach _archiv_unused/ verschoben. Relative Pfade bleiben
erhalten, Ziele werden nie überschrieben, und vor jedem Verschieben wird ein
Protokoll mit SHA-256-Prüfsummen geschrieben.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ARCHIVE_DIR = "_archiv_unused"

# BEREINIGUNGS_ANALYSE.md, Abschnitt "Sicher archivierbar".
SAFE_FILES = [
    "update_responsa-OLD.py",
    "test.txt",
]

# BEREINIGUNGS_ANALYSE.md, Abschnitt "Wahrscheinlich archivierbar".
# Standardmäßig unangetastet. Nur mit --include-probable und bestandenem
# Referenz-Check einbeziehen.
PROBABLE_FILES = [
    "test_local.py",
    "SETUP-ANLEITUNG.html",
    "qa_db.json",
]

PROTECTED_FILES = {
    "index.html",
    "qa.html",
    "script.js",
    "styles.css",
    "responsa.json",
    "build_qa.py",
    "update_responsa.py",
    "README.md",
    "SCHNELLSTART.md",
    "cleanup_unused_files.py",
}

PROTECTED_DIRS = {
    ".git",
    ".github",
    ARCHIVE_DIR,
    "data",
    "miyodea",
    "qa_db",
    "responsa",
    "scripts",
    "tools",
}

CORE_FILES = [
    "index.html",
    "qa.html",
    "script.js",
    "styles.css",
    "responsa.json",
    "build_qa.py",
    "update_responsa.py",
    ".github/workflows/update-responsa.yml",
]

SCAN_SUFFIXES = {".html", ".js", ".py", ".yml", ".yaml", ".md", ".css"}
STREAM_SCAN_FILES = ["responsa.json"]
MAX_FULL_READ = 2 * 1024 * 1024
IGNORE_SCAN_NAMES = {
    "BEREINIGUNGS_ANALYSE.md",
    "ARCHITEKTUR_ANALYSE.md",
    "cleanup_report.md",
    "cleanup_unused_files.py",
}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def human(size: int) -> str:
    n = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{int(n)} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{size} B"


def run_git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=30
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def repo_root_ok(root: Path) -> bool:
    return all((root / p).is_file() for p in ("index.html", "qa.html", "responsa.json"))


def is_protected(rel: str) -> bool:
    p = Path(rel)
    return p.name in PROTECTED_FILES or (p.parts and p.parts[0] in PROTECTED_DIRS)


def scan_references(root: Path, candidates: list[str]) -> dict[str, list[str]]:
    hits = {c: [] for c in candidates}
    candidate_names = {Path(c).name: c for c in candidates}

    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if rel.parts and rel.parts[0] in {".git", ARCHIVE_DIR}:
            continue
        if p.name in IGNORE_SCAN_NAMES or p.name.startswith("cleanup_protokoll_"):
            continue
        if p.suffix.lower() not in SCAN_SUFFIXES or p.stat().st_size > MAX_FULL_READ:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, cand in candidate_names.items():
            if p.name == name:
                continue
            if name in text:
                hits[cand].append(str(rel).replace("\\", "/"))

    for stream_name in STREAM_SCAN_FILES:
        stream_path = root / stream_name
        if not stream_path.is_file():
            continue
        encoded = {
            Path(c).name.encode("utf-8"): c
            for c in candidates
            if Path(c).name != stream_name
        }
        if not encoded:
            continue
        overlap = max(len(k) for k in encoded) + 1
        tail = b""
        with stream_path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                buf = tail + chunk
                for needle, cand in encoded.items():
                    if needle in buf and stream_name not in hits[cand]:
                        hits[cand].append(stream_name)
                tail = buf[-overlap:]

    return hits


def write_text(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sichere Archivierung unnötiger Dateien.")
    parser.add_argument("--root", default=".", help="Repo-Wurzelverzeichnis")
    parser.add_argument("--execute", action="store_true", help="wirklich verschieben")
    parser.add_argument(
        "--include-probable",
        action="store_true",
        help="auch wahrscheinlich unnötige Dateien nach Referenz-Check einbeziehen",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    report: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        report.append(line)

    say(f"# cleanup_unused_files — Lauf vom {now:%d.%m.%Y %H:%M:%S}")
    say(f"Modus: {'AUSFÜHRUNG (verschieben)' if args.execute else 'PROBELAUF (nichts wird verändert)'}")
    say("")

    if not repo_root_ok(root):
        say("ABBRUCH: index.html / qa.html / responsa.json nicht gefunden.")
        write_text(root / "cleanup_report.md", report)
        return 2

    git_status = run_git(root, "status", "--porcelain")
    if git_status is None:
        say("Hinweis: git ist nicht verfügbar; bitte vorher extern sichern.")
    elif git_status.stdout.strip() and args.execute:
        say("ABBRUCH: Git-Arbeitsverzeichnis ist nicht sauber. Erst committen oder sichern.")
        write_text(root / "cleanup_report.md", report)
        return 2
    elif not git_status.stdout.strip():
        say("Git-Arbeitsverzeichnis ist sauber.")
    say("")

    candidates: list[tuple[str, str]] = [(p, "SICHER") for p in SAFE_FILES]
    if args.include_probable:
        candidates += [(p, "WAHRSCHEINLICH") for p in PROBABLE_FILES]

    for rel, _ in candidates:
        if is_protected(rel):
            say(f"ABBRUCH: {rel} steht auf der Schutzliste.")
            write_text(root / "cleanup_report.md", report)
            return 2

    plan: list[tuple[str, str, int]] = []
    missing: list[tuple[str, str]] = []
    for rel, level in candidates:
        path = root / rel
        if path.is_file():
            plan.append((rel, level, path.stat().st_size))
        else:
            missing.append((rel, level))

    say("## Kandidatenliste")
    for rel, level, size in plan:
        say(f"  [{level}] {rel} ({human(size)})")
    for rel, level in missing:
        say(f"  [{level}] {rel} — nicht vorhanden, wird übersprungen")
    if not args.include_probable:
        say("  (WAHRSCHEINLICH-Dateien nicht einbezogen: " + ", ".join(PROBABLE_FILES) + ")")
    say("")

    if not plan:
        say("Nichts zu archivieren.")
        write_text(root / "cleanup_report.md", report)
        return 0

    say("## Referenz-Check")
    refs = scan_references(root, [rel for rel, _, _ in plan])
    cleared: list[tuple[str, str, int]] = []
    blocked: list[tuple[str, str, list[str]]] = []
    for rel, level, size in plan:
        found = refs.get(rel, [])
        if found:
            blocked.append((rel, level, found))
            say(f"  BLOCKIERT: {rel} wird referenziert in: {', '.join(found)}")
        else:
            cleared.append((rel, level, size))
            say(f"  ok: {rel} — keine Referenzen gefunden")
    say("")

    proto_name = f"cleanup_protokoll_{stamp}.md"
    proto = [
        f"# Bereinigungs-Protokoll — {now:%d.%m.%Y %H:%M:%S}",
        f"Modus: {'EXECUTE' if args.execute else 'DRY-RUN'}",
        "",
        "| Datei | Stufe | Größe | SHA-256 | Ziel |",
        "|---|---|---|---|---|",
    ]
    for rel, level, size in cleared:
        proto.append(
            f"| {rel} | {level} | {human(size)} | `{sha256_of(root / rel)}` | {ARCHIVE_DIR}/{rel} |"
        )
    if blocked:
        proto.append("")
        proto.append("Blockiert / nicht verschoben:")
        proto += [f"- {rel}: {', '.join(found)}" for rel, _, found in blocked]
    write_text(root / proto_name, proto)
    say(f"Protokoll geschrieben: {proto_name}")
    say("")

    moved: list[str] = []
    errors: list[str] = []
    say("## Verschieben")
    for rel, _, _ in cleared:
        src = root / rel
        dst = root / ARCHIVE_DIR / rel
        if not args.execute:
            say(f"  [Probelauf] würde verschieben: {rel} -> {ARCHIVE_DIR}/{rel}")
            continue
        if dst.exists():
            msg = f"{rel}: Ziel existiert bereits — nicht überschrieben"
            errors.append(msg)
            say(f"  FEHLER: {msg}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        before = sha256_of(src)
        gm = run_git(root, "mv", rel, str(dst.relative_to(root)).replace("\\", "/"))
        if gm is None or gm.returncode != 0:
            shutil.move(str(src), str(dst))
        after = sha256_of(dst)
        if before != after:
            msg = f"{rel}: Prüfsumme nach Verschieben abweichend"
            errors.append(msg)
            say(f"  FEHLER: {msg}")
        else:
            moved.append(rel)
            say(f"  verschoben: {rel} -> {ARCHIVE_DIR}/{rel}")
    say("")

    say("## Integritätstest nach dem Lauf")
    intact = True
    for rel in CORE_FILES:
        ok = (root / rel).is_file()
        intact = intact and ok
        say(f"  {'ok    ' if ok else 'FEHLT '} {rel}")
    say("")
    say("Projektstatus: " + ("INTAKT — alle Kerndateien vorhanden." if intact else "PROBLEM — Kerndatei fehlt."))
    say("Startbarkeit lokal testen mit: python3 -m http.server")
    say("")

    report.append("## Zusammenfassung")
    report.append(f"- Verschoben: {len(moved)}" + (" (" + ", ".join(moved) + ")" if moved else ""))
    report.append(f"- Nicht vorhanden / übersprungen: {len(missing)}" + (" (" + ", ".join(p for p, _ in missing) + ")" if missing else ""))
    report.append(f"- Blockiert durch Referenzen: {len(blocked)}")
    report.append(f"- Fehler: {len(errors)}")
    for msg in errors:
        report.append(f"  - {msg}")
    report.append("- Unangetastet: alle geschützten Kerndateien, alle unklaren Ordner und alle nur wahrscheinlich unnötigen Dateien ohne --include-probable.")
    write_text(root / "cleanup_report.md", report)
    print("Bericht geschrieben: cleanup_report.md")

    return 0 if intact and not errors else 1


if __name__ == "__main__":
    sys.exit(main())
