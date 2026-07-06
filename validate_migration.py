#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_migration.py — prüft den Dry-Run-Output der Q&A-Migration.

Nur lesend. Das Skript prüft _migration_test_output/data/questions/ und hängt das
Ergebnis an _migration_test_output/migration_report.md an.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_CATEGORIES = {"halacha", "tanach", "talmud", "kabbalah", "history", "general"}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def check(lines: list[str], ok_ref: dict, name: str, cond: bool, detail: str = ""):
    if not cond:
        ok_ref["ok"] = False
    state = "OK" if cond else "FEHLER"
    lines.append(f"- [{state}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validiert den Q&A-Migrations-Dry-Run.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default="_migration_test_output")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = root / args.out
    qbase = out / "data" / "questions"
    report_path = out / "migration_report.md"

    lines = ["", "## Verifikation (automatisch)"]
    ok_ref = {"ok": True}

    required_files = [
        qbase / "manifest.json",
        qbase / "index.json",
        qbase / "categories.json",
        qbase / "aliases.json",
    ]
    for path in required_files:
        check(lines, ok_ref, f"Datei vorhanden: {path.relative_to(out)}", path.exists())
    if not ok_ref["ok"]:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        return 1

    manifest = read_json(qbase / "manifest.json")
    index = read_json(qbase / "index.json")
    categories = read_json(qbase / "categories.json")
    aliases = read_json(qbase / "aliases.json")

    chunk_dir = qbase / "chunks"
    by_cat_dir = qbase / "by-category"
    chunk_files = sorted(chunk_dir.glob("qa_*.json"))
    all_questions = {}
    chunk_by_id = {}

    for chunk_file in chunk_files:
        payload = read_json(chunk_file)
        chunk_no = payload.get("chunk")
        questions = payload.get("questions", [])
        check(lines, ok_ref, f"Chunk count korrekt: {chunk_file.name}", payload.get("count") == len(questions), f"count={payload.get('count')}, real={len(questions)}")
        check(lines, ok_ref, f"Chunk-Limit Anzahl: {chunk_file.name}", len(questions) <= manifest.get("max_per_chunk", 500))
        check(lines, ok_ref, f"Chunk-Limit Größe: {chunk_file.name}", chunk_file.stat().st_size <= manifest.get("max_chunk_bytes", 1_500_000), f"{chunk_file.stat().st_size} Bytes")
        for q in questions:
            qid = q.get("id")
            if qid in all_questions:
                ok_ref["ok"] = False
            all_questions[qid] = q
            chunk_by_id[qid] = chunk_no

    index_entries = index.get("entries", [])
    index_ids = [e.get("id") for e in index_entries]
    question_ids = set(all_questions)

    check(lines, ok_ref, "Manifest-Gesamtzahl stimmt", manifest.get("total") == len(all_questions), f"manifest={manifest.get('total')}, chunks={len(all_questions)}")
    check(lines, ok_ref, "Index-count stimmt", index.get("count") == len(index_entries) == len(all_questions), f"index={index.get('count')}, entries={len(index_entries)}, chunks={len(all_questions)}")
    check(lines, ok_ref, "IDs eindeutig", len(index_ids) == len(set(index_ids)) == len(all_questions))
    check(lines, ok_ref, "Index und Chunks enthalten dieselben IDs", set(index_ids) == question_ids)

    ptr_ok = True
    required_index_fields = True
    for e in index_entries:
        qid = e.get("id")
        if chunk_by_id.get(qid) != e.get("ch"):
            ptr_ok = False
        for field in ["id", "x", "c", "ch", "s"]:
            if field not in e:
                required_index_fields = False
    check(lines, ok_ref, "Index zeigt auf richtige Chunks", ptr_ok)
    check(lines, ok_ref, "Index-Pflichtfelder vorhanden", required_index_fields)

    cat_ids = {c.get("id") for c in categories.get("categories", [])}
    check(lines, ok_ref, "Sechs Zielkategorien vorhanden", REQUIRED_CATEGORIES <= cat_ids, f"{sorted(cat_ids)}")
    check(lines, ok_ref, "Default-Kategorie vorhanden", categories.get("default_category") in cat_ids)
    check(lines, ok_ref, "Tag-Map zeigt nur auf gültige Kategorien", set(categories.get("tag_map", {}).values()) <= cat_ids)
    check(lines, ok_ref, "Legacy-Map zeigt nur auf gültige Kategorien", set(categories.get("legacy_map", {}).values()) <= cat_ids)

    by_category_ids = []
    by_cat_ok = True
    for cid in REQUIRED_CATEGORIES:
        path = by_cat_dir / f"{cid}.json"
        if not path.exists():
            by_cat_ok = False
            continue
        data = read_json(path)
        rows = data.get("entries", [])
        if data.get("category") != cid or data.get("count") != len(rows):
            by_cat_ok = False
        for row in rows:
            by_category_ids.append(row.get("id"))
            if row.get("c") != cid:
                by_cat_ok = False
    check(lines, ok_ref, "by-category-Dateien korrekt", by_cat_ok)
    check(lines, ok_ref, "by-category ist vollständige Partition", sorted(by_category_ids) == sorted(index_ids))

    q_fields_ok = True
    review_ok = True
    for qid, q in all_questions.items():
        if not q.get("id") or "answers" not in q or not isinstance(q.get("answers"), list):
            q_fields_ok = False
        if q.get("category") not in cat_ids:
            q_fields_ok = False
        if q.get("category_confidence") == "low" and not q.get("needs_review"):
            review_ok = False
        if q.get("category_confidence") == "high" and q.get("needs_review"):
            review_ok = False
    check(lines, ok_ref, "Chunk-Fragen haben Pflichtfelder", q_fields_ok)
    check(lines, ok_ref, "Unsichere Kategorien sind review-pflichtig", review_ok)

    alias_targets_ok = True
    for alias, target in aliases.get("aliases", {}).items():
        if target.get("id") not in all_questions:
            alias_targets_ok = False
        if chunk_by_id.get(target.get("id")) != target.get("ch"):
            alias_targets_ok = False
    check(lines, ok_ref, "Aliases zeigen auf vorhandene IDs", alias_targets_ok)

    lines.append("")
    lines.append("**Gesamtergebnis: " + ("ALLE PRÜFUNGEN BESTANDEN" if ok_ref["ok"] else "FEHLER GEFUNDEN") + "**")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    return 0 if ok_ref["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
