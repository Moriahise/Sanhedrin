#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quality_check_qa.py — Qualitätsprüfung des Q&A-Bestands in data/questions/.

Findet und entfernt nur mit --run:
  LEER, NUR_TITEL, INHALTSLOS und echte DUPLIKATE.
Fragen ohne Antwort werden standardmäßig nur gemeldet.
Originaldaten wie responsa.json, qa_db*, miyodea/ und data/qa/ werden nicht berührt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from qa_store import QAStore

TAG_RE = re.compile(r"<[^>]+>")
MD_RE = re.compile(r"[#*_`>]|\[([^\]]*)\]\([^)]*\)")
WS_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\"'׳״.,;:!?()\[\]{}«»„“”\-–—/\\]")


def norm(text: str) -> str:
    text = TAG_RE.sub(" ", str(text or ""))
    text = MD_RE.sub(r"\1", text)
    text = PUNCT_RE.sub(" ", text)
    return WS_RE.sub(" ", text).strip().lower()


def content_text(q: dict) -> str:
    return norm(q.get("question", "")) or norm(q.get("title", "")) or norm(q.get("title_he", "")) or norm(q.get("title_en", ""))


def answer_texts(q: dict) -> list[str]:
    return [norm(a.get("text", "")) for a in (q.get("answers") or []) if norm(a.get("text", ""))]


def fingerprint(q: dict) -> str:
    parts = [content_text(q)] + sorted(answer_texts(q))
    return hashlib.sha256("\u0001".join(parts).encode("utf-8")).hexdigest()


def question_key(q: dict) -> str:
    return hashlib.sha256(content_text(q).encode("utf-8")).hexdigest()


def keep_score(q: dict):
    return (
        1 if q.get("category_source") in ("legacy", "manual") or q.get("category_locked") else 0,
        len(answer_texts(q)),
        1 if q.get("url") else 0,
        1 if q.get("date") else 0,
        -len(str(q.get("id", ""))),
        str(q.get("id", "")),
    )


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_chunks(base: Path):
    chunk_files = sorted((base / "chunks").glob("qa_*.json"))
    chunks = {cf: json.loads(cf.read_text(encoding="utf-8")) for cf in chunk_files}
    return chunk_files, chunks


def analyse(chunks: dict, min_question_len: int, remove_unanswered: bool):
    all_q = []
    for cf, payload in chunks.items():
        for q in payload.get("questions", []):
            all_q.append((cf, q))

    leer, nur_titel, inhaltslos, ohne_antwort = [], [], [], []
    by_fp, by_qkey = defaultdict(list), defaultdict(list)

    for cf, q in all_q:
        nq = norm(q.get("question", ""))
        title = norm(q.get("title", "")) or norm(q.get("title_he", "")) or norm(q.get("title_en", ""))
        answers = answer_texts(q)
        if not nq and len(title) < 5:
            leer.append(q["id"])
            continue
        if not nq and not answers:
            nur_titel.append(q["id"])
            continue
        if nq and len(nq) < min_question_len and not answers:
            inhaltslos.append(q["id"])
            continue
        if not answers:
            ohne_antwort.append(q["id"])
        by_fp[fingerprint(q)].append(q)
        by_qkey[question_key(q)].append(q)

    dup_remove, dup_keep = [], {}
    for fp, group in by_fp.items():
        if len(group) < 2:
            continue
        group = sorted(group, key=keep_score, reverse=True)
        survivor = group[0]
        for twin in group[1:]:
            dup_remove.append(twin["id"])
            dup_keep[twin["id"]] = survivor["id"]

    dup_set = set(dup_remove)
    same_question = []
    for k, group in by_qkey.items():
        ids = [q["id"] for q in group if q["id"] not in dup_set]
        if len(ids) > 1 and len({fingerprint(q) for q in group}) > 1:
            same_question.append(ids)

    to_remove = set(leer) | set(nur_titel) | set(inhaltslos) | dup_set
    if remove_unanswered:
        to_remove |= set(ohne_antwort)

    return {
        "all_q": all_q,
        "leer": leer,
        "nur_titel": nur_titel,
        "inhaltslos": inhaltslos,
        "ohne_antwort": ohne_antwort,
        "dup_remove": dup_remove,
        "dup_keep": dup_keep,
        "same_question": same_question,
        "to_remove": to_remove,
    }


def write_report(root: Path, report: list[str]) -> None:
    (root / "qualitaets_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--min-frage-laenge", type=int, default=15)
    parser.add_argument("--remove-unanswered", action="store_true")
    parser.add_argument("--yes-i-checked-the-report", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    base = root / "data" / "questions"
    if not (base / "manifest.json").exists():
        print("ABBRUCH: data/questions/ nicht gefunden.")
        return 2

    now = datetime.now()
    report = [
        f"# qualitaets_report — {now:%d.%m.%Y %H:%M:%S}",
        f"Modus: {'ENTFERNEN (--run)' if args.run else 'REPORT (keine Datenänderung)'}",
        "",
    ]

    chunk_files, chunks = load_chunks(base)
    result = analyse(chunks, args.min_frage_laenge, args.remove_unanswered)
    total = len(result["all_q"])
    to_remove = result["to_remove"]

    report.append(f"## Analyse ({total} Einträge geprüft)")
    report.append(f"- LEER (kein Fragetext, kein Titel): {len(result['leer'])}" + (f" — {result['leer'][:10]}" if result['leer'] else ""))
    report.append(f"- NUR_TITEL (Überschrift vorhanden, aber weder Fragetext noch Antwort): {len(result['nur_titel'])}" + (f" — {result['nur_titel'][:10]}" if result['nur_titel'] else ""))
    report.append(f"- INHALTSLOS (Fragment < {args.min_frage_laenge} Zeichen, keine Antwort): {len(result['inhaltslos'])}" + (f" — {result['inhaltslos'][:10]}" if result['inhaltslos'] else ""))
    report.append(f"- DUPLIKATE (identischer Inhalt): {len(result['dup_remove'])} zu entfernen, {len(set(result['dup_keep'].values()))} Überlebende" + (f" — z. B. {list(result['dup_keep'].items())[:8]}" if result['dup_keep'] else ""))
    report.append(f"- OHNE_ANTWORT (nur {'ENTFERNT' if args.remove_unanswered else 'gemeldet'}): {len(result['ohne_antwort'])}" + (f" — {result['ohne_antwort'][:10]}" if result['ohne_antwort'] else ""))
    report.append(f"- GLEICHE_FRAGE, andere Antworten (manuell prüfen, NICHT entfernt): {len(result['same_question'])}" + (f" — {result['same_question'][:5]}" if result['same_question'] else ""))
    report.append(f"- **Zu entfernen gesamt: {len(to_remove)} von {total} ({100 * len(to_remove) // max(1, total)} %)**")
    report.append("")

    if not args.run:
        report.append("**Report-Modus — nichts wurde geändert.** Wenn die Funde plausibel sind: mit --run ausführen.")
        write_report(root, report)
        print("\n".join(report))
        return 0

    if not to_remove:
        report.append("Nichts zu entfernen — Bestand ist sauber.")
        write_report(root, report)
        print("\n".join(report))
        return 0

    if len(to_remove) > total * 0.30 and not args.yes_i_checked_the_report:
        report.append("ABBRUCH: Über 30 % des Bestands würden entfernt. Erst Bericht prüfen; dann bewusst bestätigen.")
        write_report(root, report)
        print("\n".join(report))
        return 2

    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = root / "_backup_before_quality" / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    for cf in chunk_files:
        dst = backup_dir / cf.name
        shutil.copy2(cf, dst)
        if sha256_of(dst) != sha256_of(cf):
            print(f"ABBRUCH: Backup-Prüfsumme weicht ab: {cf.name}")
            return 2
    for extra in ("index.json", "aliases.json", "manifest.json"):
        src = base / extra
        if src.exists():
            shutil.copy2(src, backup_dir / extra)

    quarantine = [q for _, q in result["all_q"] if q["id"] in to_remove]
    (backup_dir / "entfernte_eintraege.json").write_text(json.dumps({
        "schema": 2,
        "removed_at": now.isoformat(timespec="seconds"),
        "count": len(quarantine),
        "duplicate_of": result["dup_keep"],
        "questions": quarantine,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    for cf, payload in chunks.items():
        keep = [q for q in payload.get("questions", []) if q["id"] not in to_remove]
        if len(keep) != len(payload.get("questions", [])):
            payload["questions"] = keep
            payload["count"] = len(keep)
            cf.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    store = QAStore(root)
    n = store.rebuild_index()
    survivors = {e["id"]: e["ch"] for e in store.index["entries"]}
    remapped = 0
    for gone, alive in result["dup_keep"].items():
        if alive not in survivors:
            continue
        for old_q in quarantine:
            if old_q["id"] != gone:
                continue
            sid = old_q.get("legacy", {}).get("source_id")
            if sid:
                store.aliases["aliases"][sid] = {"id": alive, "ch": survivors[alive]}
                remapped += 1
            num = old_q.get("legacy", {}).get("number")
            if num is not None:
                store.aliases["aliases"][f"n{num}"] = {"id": alive, "ch": survivors[alive]}
    if remapped:
        from qa_store import _atomic_write
        _atomic_write(base / "aliases.json", store.aliases)

    problems = store.verify()
    report.append("## Ausführung")
    report.append(f"- Backup: {len(chunk_files)} Chunks + Index nach _backup_before_quality/{stamp}/ (Prüfsummen verifiziert)")
    report.append(f"- Quarantäne: {len(quarantine)} vollständige Einträge in entfernte_eintraege.json")
    report.append(f"- Entfernt: {len(to_remove)} | Bestand jetzt: {n}")
    report.append(f"- Aliase entfernter Duplikate auf Überlebende umgeleitet: {remapped}")
    report.append(f"- Index neu aufgebaut | Konsistenz: {'OK' if not problems else 'FEHLER: ' + '; '.join(problems)}")
    report.append("")
    report.append("Rückweg: Chunks + Index aus dem lokalen Backup-Ordner zurückkopieren; entfernte Einträge stehen vollständig in entfernte_eintraege.json.")

    write_report(root, report)
    print("\n".join(report))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
