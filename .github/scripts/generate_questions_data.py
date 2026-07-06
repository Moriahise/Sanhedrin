#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate data/questions in GitHub Actions.

This script is intentionally small and uses the existing migrate_qa helpers
that are already present in the repository.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import migrate_qa

TARGET = ROOT / "data" / "questions"
REPORT = ROOT / "migration_report.md"
MAX_PER_CHUNK = 500
MAX_CHUNK_BYTES = 1_500_000


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate() -> tuple[bool, list[str]]:
    problems: list[str] = []
    index = read_json(TARGET / "index.json")
    manifest = read_json(TARGET / "manifest.json")
    categories = read_json(TARGET / "categories.json")

    entries = index.get("entries", [])
    ids = [e.get("id") for e in entries]
    if index.get("count") != len(entries):
        problems.append("index.json count passt nicht zu entries")
    if manifest.get("total") != len(entries):
        problems.append("manifest total passt nicht zu index entries")
    if len(ids) != len(set(ids)):
        problems.append("doppelte IDs im Index")

    chunk_ids = []
    for chunk_file in sorted((TARGET / "chunks").glob("qa_*.json")):
        chunk = read_json(chunk_file)
        qs = chunk.get("questions", [])
        if chunk.get("count") != len(qs):
            problems.append(f"{chunk_file}: count passt nicht")
        chunk_ids.extend(q.get("id") for q in qs)
    if sorted(chunk_ids) != sorted(ids):
        problems.append("Chunk-IDs passen nicht zum Index")

    bycat_ids = []
    for cat in categories.get("categories", []):
        p = TARGET / "by-category" / f"{cat['id']}.json"
        if p.exists():
            bycat_ids.extend(e.get("id") for e in read_json(p).get("entries", []))
    if sorted(bycat_ids) != sorted(ids):
        problems.append("by-category Dateien sind keine vollständige Partition")

    return not problems, problems


def main() -> int:
    report: list[str] = [
        f"# migration_report — GitHub Actions data/questions {datetime.utcnow().isoformat(timespec='seconds')}Z",
        "",
        "Originaldateien wurden nur gelesen. data/questions wurde neu erzeugt.",
        "",
    ]

    if TARGET.exists():
        shutil.rmtree(TARGET)

    entries = migrate_qa.collect_entries(ROOT, report)
    migrate_qa.write_new_structure(ROOT, ROOT, entries, MAX_PER_CHUNK, MAX_CHUNK_BYTES, report)

    ok, problems = validate()
    report.append("")
    report.append("## Prüfung")
    if ok:
        report.append("- [OK] data/questions konsistent erzeugt")
    else:
        for problem in problems:
            report.append(f"- [FEHLER] {problem}")

    manifest = read_json(TARGET / "manifest.json")
    index = read_json(TARGET / "index.json")
    report.append("")
    report.append("## Statistik")
    report.append(f"- Fragen: {index.get('count')}")
    report.append(f"- Chunks: {manifest.get('chunks')}")
    report.append(f"- Max pro Chunk: {manifest.get('max_per_chunk')}")
    report.append(f"- Max Chunk Bytes: {manifest.get('max_chunk_bytes')}")
    report.append("")
    report.append("**ERGEBNIS: " + ("OK" if ok else "FEHLER") + "**")

    REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
