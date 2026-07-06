#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_production.py — produktiver Parallelaufbau der neuen Q&A-Struktur.

Wichtig:
- Originaldaten werden gesichert.
- Originaldaten werden nicht gelöscht.
- Die Anwendung wird nicht auf die neue Struktur umgestellt.
- Neue Struktur wird parallel unter data/questions/ erzeugt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import migrate_qa

BACKUP_ROOT = Path("_backup_before_question_migration")
TARGET = Path("data") / "questions"
SOURCE_PATHS = ["responsa.json", "qa_db.json", "qa_db", "miyodea/qa", "data/qa"]
REQUIRED_CATEGORIES = {"halacha", "tanach", "talmud", "kabbalah", "history", "general"}


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in SOURCE_PATHS:
        path = root / rel
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and TARGET.as_posix() not in f.relative_to(root).as_posix():
                    files.append(f)
    return files


def checksums(root: Path) -> dict[str, str]:
    return {f.relative_to(root).as_posix(): sha256_of(f) for f in source_files(root)}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def backup_sources(root: Path, stamp: str, report: list[str]) -> Path:
    srcs = source_files(root)
    backup_dir = root / BACKUP_ROOT / stamp
    report.append("## 1. Backup der Originaldaten")
    report.append(f"- Backup-Ziel: `{BACKUP_ROOT.as_posix()}/{stamp}/`")
    report.append(f"- Dateien: {len(srcs)}")
    report.append(f"- Gesamtgröße: {sum(f.stat().st_size for f in srcs)} Bytes")
    for src in srcs:
        dst = backup_dir / src.relative_to(root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if sha256_of(src) != sha256_of(dst):
            raise RuntimeError(f"Backup-Prüfsumme weicht ab: {src}")
    report.append("- Ergebnis: Backup kopiert und per SHA-256 geprüft.")
    report.append("")
    return backup_dir


def validate_output(root: Path, source_count: int, source_answers: int, report: list[str]) -> tuple[bool, dict[str, int]]:
    base = root / TARGET
    index = read_json(base / "index.json")
    cats = read_json(base / "categories.json")
    chunk_files = sorted((base / "chunks").glob("qa_*.json"))

    questions = {}
    answer_count = 0
    for cf in chunk_files:
        payload = read_json(cf)
        for q in payload.get("questions", []):
            questions[q.get("id")] = q
            answer_count += len(q.get("answers", []))

    index_entries = index.get("entries", [])
    index_ids = [e.get("id") for e in index_entries]
    cat_ids = {c.get("id") for c in cats.get("categories", [])}

    bycat_ids = []
    for cid in cat_ids:
        path = base / "by-category" / f"{cid}.json"
        if path.exists():
            data = read_json(path)
            bycat_ids.extend([e.get("id") for e in data.get("entries", [])])

    needs_review = sum(1 for q in questions.values() if q.get("needs_review"))
    raw_first_chunk = (base / "chunks" / "qa_0001.json").read_text(encoding="utf-8") if chunk_files else ""
    hebrew_not_escaped = "\\u05" not in raw_first_chunk
    has_utf8 = any("\u0590" <= ch <= "\u05ff" for ch in raw_first_chunk)

    checks = [
        ("Originalfragen = migrierte Fragen", source_count == len(questions)),
        ("Antworten vollständig", source_answers == answer_count),
        ("IDs eindeutig", len(index_ids) == len(set(index_ids)) == len(questions)),
        ("index.json count korrekt", index.get("count") == len(index_entries) == len(questions)),
        ("categories.json korrekt", REQUIRED_CATEGORIES <= cat_ids),
        ("by-category vollständig", sorted(bycat_ids) == sorted(index_ids)),
        ("Sonderzeichen UTF-8, Hebrew nicht escaped", hebrew_not_escaped),
    ]

    report.append("## 3. Prüfung")
    ok = True
    for name, passed in checks:
        ok = ok and passed
        report.append(f"- [{'OK' if passed else 'FEHLER'}] {name}")
    report.append(f"- Hinweis: Hebrew vorhanden im ersten Chunk: {'ja' if has_utf8 else 'nicht in erster Stichprobe'}")
    report.append("")

    stats = {
        "source_questions": source_count,
        "migrated_questions": len(questions),
        "source_answers": source_answers,
        "migrated_answers": answer_count,
        "categories": len(cat_ids),
        "needs_review": needs_review,
        "chunks": len(chunk_files),
    }
    return ok, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Migration wirklich ausführen")
    parser.add_argument("--root", default=".")
    parser.add_argument("--max-per-chunk", type=int, default=500)
    parser.add_argument("--max-chunk-bytes", type=int, default=1_500_000)
    parser.add_argument("--force-rebuild", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report: list[str] = [
        f"# migration_report — produktive Migration im Parallelaufbau {stamp}",
        "",
        "Die Anwendung wurde nicht umgestellt. Alte Daten bleiben erhalten.",
        "",
    ]

    if not args.run:
        report.append("Planmodus. Ausführung mit `python3 migrate_production.py --run`.")
        (root / "migration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        print("\n".join(report))
        return 0

    for required in ["index.html", "qa.html", "responsa.json", "migrate_qa.py"]:
        if not (root / required).exists():
            raise SystemExit(f"ABBRUCH: `{required}` nicht gefunden. Bitte im Repo-Root ausführen.")

    before = checksums(root)
    backup_dir = backup_sources(root, stamp, report)

    target = root / TARGET
    if target.exists() and any(target.iterdir()):
        if not args.force_rebuild:
            raise SystemExit("ABBRUCH: data/questions/ existiert bereits. Für Neuaufbau --force-rebuild nutzen.")
        shutil.rmtree(target)

    source_entries = migrate_qa.collect_sources(root, [])
    source_count = len(source_entries)
    source_answers = sum(len(e.get("answers", [])) for e in source_entries.values())

    report.append("## 2. Neue produktive Datenstruktur")
    total, chunks, review = migrate_qa.build(root, target, args.max_per_chunk, args.max_chunk_bytes, report)
    report.append(f"- Ziel: `{TARGET.as_posix()}/`")
    report.append(f"- Migrierte Fragen: {total}")
    report.append(f"- Chunk-Dateien: {chunks}")
    report.append(f"- needs_review: {review}")
    report.append("")

    after = checksums(root)
    originals_ok = before == after
    validation_ok, stats = validate_output(root, source_count, source_answers, report)

    report.append("## 4. Gesamtstatus")
    report.append(f"- Ursprüngliche Fragen: {stats['source_questions']}")
    report.append(f"- Migrierte Fragen: {stats['migrated_questions']}")
    report.append(f"- Ursprüngliche Antworten: {stats['source_answers']}")
    report.append(f"- Migrierte Antworten: {stats['migrated_answers']}")
    report.append(f"- Kategorien: {stats['categories']}")
    report.append(f"- needs_review: {stats['needs_review']}")
    report.append(f"- Chunk-Dateien: {stats['chunks']}")
    report.append(f"- Backup: `{backup_dir.relative_to(root).as_posix()}/`")
    report.append(f"- Originaldaten per SHA-256 unverändert: {'ja' if originals_ok else 'nein'}")
    report.append("- Anwendung liest weiterhin die alte Struktur.")
    report.append("")
    success = originals_ok and validation_ok
    report.append("**ERGEBNIS: " + ("PRODUKTIVE PARALLELSTRUKTUR BEREIT" if success else "FEHLER — NICHT BEREIT") + "**")

    (root / "migration_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
