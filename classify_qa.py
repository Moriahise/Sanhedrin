#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""classify_qa.py — fachliche Klassifizierung des Altbestands in data/questions/.

Standard: Report-Modus, keine Datenänderung.
Mit --run: Kategorien in Chunks anwenden und index/by-category/aliases neu bauen.
Originaldaten wie responsa.json, qa_db*, miyodea/ werden nicht berührt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import migrate_qa

PROTECTED_SOURCES = {"legacy", "manual"}
SCHEMA = 2


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def clean_text(text: str) -> str:
    return migrate_qa.clean_text(text)


def classify_one(title: str, question: str, tags: list[str]):
    result = migrate_qa.classify(title or "", question or "", tags or [])
    if len(result) == 4:
        cat, conf, review, source = result
    else:
        cat, conf, review = result
        source = "rules"
    return cat, conf, bool(review), source


def load_rules_from_categories_json(base: Path, report: list[str]) -> list[dict]:
    path = base / "categories.json"
    if not path.exists():
        report.append("- Regeln: categories.json nicht gefunden -> eingebaute Regeln")
        return migrate_qa.CATEGORIES
    data = read_json(path)
    cats = data.get("categories") or []
    if cats:
        migrate_qa.CATEGORIES = cats
        if hasattr(migrate_qa, "_kw_cache"):
            migrate_qa._kw_cache.clear()
        report.append(f"- Regeln: {len(cats)} Kategorien aus categories.json geladen")
    if isinstance(data.get("tag_map"), dict):
        migrate_qa.TAG_MAP = data["tag_map"]
        report.append(f"- tag_map: {len(data['tag_map'])} Zuordnungen aus categories.json")
    return cats or migrate_qa.CATEGORIES


def rebuild_indexes(base: Path, categories: list[dict]) -> tuple[int, list[str]]:
    cat_ids = [c["id"] for c in categories]
    by_category = {cid: [] for cid in cat_ids}
    index_entries = []
    aliases = {}
    problems = []

    for chunk_file in sorted((base / "chunks").glob("qa_*.json")):
        chunk = read_json(chunk_file)
        chunk_no = int(chunk.get("chunk") or chunk_file.stem.split("_")[-1])
        questions = chunk.get("questions", [])
        if chunk.get("count") != len(questions):
            chunk["count"] = len(questions)
            write_json(chunk_file, chunk)
        for q in questions:
            rec = migrate_qa.make_index_record(q, chunk_no)
            index_entries.append(rec)
            by_category.setdefault(rec.get("c") or "general", []).append(rec)
            legacy = q.get("legacy", {}) or {}
            aliases[q["id"]] = {"id": q["id"], "ch": chunk_no}
            if legacy.get("source_id"):
                sid = str(legacy["source_id"])
                aliases[sid] = {"id": q["id"], "ch": chunk_no}
                aliases[migrate_qa.source_id_number(sid)] = {"id": q["id"], "ch": chunk_no}
            if legacy.get("number") is not None:
                aliases[f"n{legacy['number']}"] = {"id": q["id"], "ch": chunk_no}
            if legacy.get("old_file"):
                aliases[str(legacy["old_file"])] = {"id": q["id"], "ch": chunk_no}

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest = read_json(base / "manifest.json")
    manifest["generated"] = now
    manifest["total"] = len(index_entries)
    manifest["chunks"] = len(list((base / "chunks").glob("qa_*.json")))
    manifest["open_chunk"] = max(1, int(manifest.get("chunks", 1)))
    manifest.setdefault("index_files", ["index.json"])

    write_json(base / "manifest.json", manifest)
    write_json(base / "index.json", {"schema": SCHEMA, "generated": now, "count": len(index_entries), "entries": index_entries})
    write_json(base / "aliases.json", {"schema": SCHEMA, "aliases": aliases})

    for cid in cat_ids:
        rows = by_category.get(cid, [])
        write_json(base / "by-category" / f"{cid}.json", {"schema": SCHEMA, "category": cid, "count": len(rows), "entries": rows})

    ids = [e.get("id") for e in index_entries]
    if len(ids) != len(set(ids)):
        problems.append("doppelte IDs im Index")
    by_total = sum(len(v) for v in by_category.values())
    if by_total != len(index_entries):
        problems.append(f"by-category-Summe {by_total} != Index {len(index_entries)}")
    return len(index_entries), problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--only-review", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    base = root / "data" / "questions"
    if not (base / "manifest.json").exists():
        print("ABBRUCH: data/questions/ nicht gefunden — erst migrieren.")
        return 2

    now = datetime.now()
    report = [
        f"# klassifizierungs_report — {now:%d.%m.%Y %H:%M:%S}",
        f"Modus: {'ANWENDEN (--run)' if args.run else 'REPORT (keine Datenänderung)'}"
        + (" | nur needs_review" if args.only_review else "")
        + (f" | Limit {args.limit}" if args.limit else ""),
        "",
    ]
    categories = load_rules_from_categories_json(base, report)
    chunk_files = sorted((base / "chunks").glob("qa_*.json"))
    if not chunk_files:
        print("ABBRUCH: keine Chunk-Dateien gefunden.")
        return 2

    if args.run:
        stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = root / "_backup_before_classification" / stamp
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
        report.append(f"- Backup: {len(chunk_files)} Chunks + Index nach _backup_before_classification/{stamp}/ (Prüfsummen verifiziert)")
        report.append("")

    before, after = Counter(), Counter()
    conf_after = Counter()
    samples = defaultdict(list)
    changed = []
    skipped_protected = 0
    seen = 0
    total = 0

    for cf in chunk_files:
        data = read_json(cf)
        dirty = False
        for q in data.get("questions", []):
            total += 1
            if args.limit and seen >= args.limit:
                continue
            old_cat = q.get("category", "general")
            before[old_cat] += 1
            if q.get("category_source") in PROTECTED_SOURCES or q.get("category_locked"):
                skipped_protected += 1
                after[old_cat] += 1
                conf_after[q.get("category_confidence", "high")] += 1
                continue
            if args.only_review and not q.get("needs_review"):
                after[old_cat] += 1
                conf_after[q.get("category_confidence", "low")] += 1
                continue
            seen += 1
            cat, conf, review, source = classify_one(q.get("title") or q.get("title_en") or q.get("title_he") or "", q.get("question", ""), q.get("tags") or [])
            after[cat] += 1
            conf_after[conf] += 1
            if len(samples[cat]) < 5:
                title = q.get("title") or q.get("title_en") or q.get("title_he") or q.get("question", "")[:70]
                samples[cat].append(f"{q.get('id')}: {str(title)[:70]}")
            if cat != old_cat or conf != q.get("category_confidence") or review != bool(q.get("needs_review")):
                if len(changed) < 20:
                    changed.append(f"{q.get('id')}: {old_cat} -> {cat} ({conf}{', review' if review else ''})")
                if args.run:
                    q["category"] = cat
                    q["category_confidence"] = conf
                    q["category_source"] = source or "rules"
                    if review:
                        q["needs_review"] = True
                    else:
                        q.pop("needs_review", None)
                    dirty = True
        if args.run and dirty:
            write_json(cf, data)
        if total % 10000 < max(1, len(data.get("questions", []))):
            print(f"  … {total} Einträge verarbeitet", file=sys.stderr)

    if args.run:
        rebuilt, problems = rebuild_indexes(base, categories)
        report.append(f"- Index neu aufgebaut: {rebuilt} Einträge | Konsistenz: {'OK' if not problems else 'FEHLER: ' + '; '.join(problems)}")
        report.append("")

    def dist(counter: Counter) -> str:
        return ", ".join(f"{k}: {v}" for k, v in sorted(counter.items(), key=lambda x: -x[1]))

    high = conf_after.get("high", 0)
    low = conf_after.get("low", 0)
    quote = 100 * high // max(1, high + low)
    report.append(f"## Ergebnis ({total} Einträge, {seen} bewertet, {skipped_protected} geschützt übersprungen)")
    report.append(f"- Verteilung vorher: {dist(before)}")
    report.append(f"- Verteilung nachher{'' if args.run else ' (Vorschau)'}: {dist(after)}")
    report.append(f"- Confidence: high {high} / low {low} (high-Quote {quote} %)")
    report.append(f"- needs_review{'' if args.run else ' (Vorschau)'}: {low}")
    report.append("")
    report.append("## Stichproben je Kategorie")
    for cat in sorted(samples):
        report.append(f"### {cat}")
        report.extend(f"- {sample}" for sample in samples[cat])
    if changed:
        report.append("")
        report.append("## Beispiele für Änderungen")
        report.extend(f"- {item}" for item in changed)
    if not args.run:
        report.append("")
        report.append("**Hinweis:** Report-Modus — keine Daten wurden geändert. Zum Anwenden: python3 classify_qa.py --run")

    out = root / "klassifizierungs_report.md"
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:20]))
    print(f"\nVollständiger Bericht: {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
