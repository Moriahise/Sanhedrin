#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_qa.py — Dry-Run-Migration für die neue Q&A-Struktur.

Dieses Skript liest bestehende Frage-Antwort-Quellen nur lesend und schreibt
alle Ergebnisse ausschließlich nach _migration_test_output/.

Es erzeugt:
  _migration_test_output/data/questions/manifest.json
  _migration_test_output/data/questions/index.json
  _migration_test_output/data/questions/categories.json
  _migration_test_output/data/questions/aliases.json
  _migration_test_output/data/questions/chunks/qa_0001.json ...
  _migration_test_output/data/questions/by-category/*.json
  _migration_test_output/migration_report.md

Originaldaten werden nicht überschrieben.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCHEMA = 2
OUT_DIR_NAME = "_migration_test_output"

CATEGORIES = [
    {"id": "halacha", "label_he": "הלכה", "label_en": "Halacha", "label_de": "Halacha", "order": 1,
     "keywords_strong": ["halacha", "halakha", "responsa", "teshuva", "psak", "din", "shulchan aruch", "rambam", "tur", "poskim", "הלכה", "פסק", "דין", "שולחן ערוך", "רמב\"ם", "טור", "פוסקים", "שו\"ת"],
     "keywords_weak": ["issur", "heter", "minhag", "אסור", "מותר", "מנהג"]},
    {"id": "tanach", "label_he": "תנ\"ך", "label_en": "Tanakh", "label_de": "Tanach", "order": 2,
     "keywords_strong": ["tanach", "tanakh", "torah", "neviim", "ketuvim", "pasuk", "parasha", "bereshit", "shemot", "vayikra", "bamidbar", "devarim", "yehoshua", "shmuel", "תנ\"ך", "תורה", "נביאים", "כתובים", "פסוק", "פרשה", "בראשית", "שמות", "ויקרא", "במדבר", "דברים", "יהושע", "שמואל"],
     "keywords_weak": ["rashi", "tehillim", "prophet", "רש\"י", "תהילים", "מקרא"]},
    {"id": "talmud", "label_he": "תלמוד", "label_en": "Talmud", "label_de": "Talmud", "order": 3,
     "keywords_strong": ["gemara", "talmud", "bavli", "yerushalmi", "daf", "sugya", "mishnah", "mishna", "baraita", "גמרא", "תלמוד", "בבלי", "ירושלמי", "דף", "סוגיה", "משנה", "ברייתא"],
     "keywords_weak": ["masechet", "amoraim", "tannaim", "מסכת", "אמוראים", "תנאים"]},
    {"id": "kabbalah", "label_he": "קבלה", "label_en": "Kabbalah", "label_de": "Kabbala", "order": 4,
     "keywords_strong": ["zohar", "kabbalah", "arizal", "rashash", "sefirot", "ramak", "etz chaim", "זוהר", "קבלה", "אריז\"ל", "רש\"ש", "ספירות", "רמ\"ק", "עץ חיים"],
     "keywords_weak": ["sod", "nistar", "chassidut", "סוד", "נסתר", "חסידות"]},
    {"id": "history", "label_he": "היסטוריה", "label_en": "History", "label_de": "Geschichte", "order": 5,
     "keywords_strong": ["history", "geschichte", "chronology", "chronologie", "persons", "places", "temple", "mikdash", "exile", "היסטוריה", "כרונולוגיה", "אישים", "מקומות", "מקדש", "בית המקדש", "גלות", "חורבן"],
     "keywords_weak": ["biography", "era", "personen", "orte", "תקופה"]},
    {"id": "general", "label_he": "כללי", "label_en": "General", "label_de": "Allgemein", "order": 6,
     "keywords_strong": [], "keywords_weak": [], "is_fallback": True},
]

TAG_MAP = {
    "halacha": "halacha", "shabbat": "halacha", "kashrut": "halacha", "brachot": "halacha", "muktzeh": "halacha",
    "parashat-hashavua": "tanach", "tanakh": "tanach", "torah-reading": "tanach", "chumash": "tanach",
    "gemara": "talmud", "talmud": "talmud", "mishna": "talmud", "daf-yomi": "talmud",
    "kabbalah": "kabbalah", "zohar": "kabbalah", "chassidut": "kabbalah",
    "jewish-history": "history", "temple": "history", "second-temple": "history",
}

LEGACY_MAP = {
    "ritual": "halacha", "civil": "halacha", "family": "halacha", "kashrut": "halacha", "shabbat": "halacha",
    "conversion": "halacha", "halacha-history": "history", "other": "general", "Q&A": "general",
}

HEBREW = re.compile(r"[\u0590-\u05ff]")


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("questions"), list):
        return data["questions"]
    return []


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def has_hebrew(text: str) -> bool:
    return bool(HEBREW.search(text or ""))


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def excerpt(text: str, limit: int = 160) -> str:
    t = clean_text(text)
    return t if len(t) <= limit else t[: limit - 1].rstrip() + "…"


def year_from_date(date_value) -> int | None:
    if not date_value:
        return None
    m = re.search(r"(19|20)\d{2}", str(date_value))
    return int(m.group(0)) if m else None


def source_id_number(raw_id: str) -> str:
    s = str(raw_id or "").strip()
    s = re.sub(r"^miyodeya[_-]", "", s, flags=re.I)
    return s or "missing"


def stable_missing_id(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8", errors="ignore")).hexdigest()[:12]
    return f"{prefix}-auto-{digest}"


def parse_miyodea_content(content: str):
    content = str(content or "")
    question = content
    answers_part = ""
    q_match = re.search(r"##\s*Frage\s*\n", question, flags=re.I)
    if q_match:
        question = question[q_match.end():]
    a_match = re.search(r"##\s*Antworten\s*\n", question, flags=re.I)
    if a_match:
        answers_part = question[a_match.end():]
        question = question[:a_match.start()]
    answers = []
    if answers_part.strip():
        parts = re.split(r"\n###\s*([^\n]*)\n", "\n" + answers_part)
        if len(parts) > 2:
            for i in range(1, len(parts) - 1, 2):
                header = parts[i]
                body = parts[i + 1].strip()
                if not body:
                    continue
                score_match = re.search(r"Score:\s*(-?\d+)", header)
                answers.append({
                    "text": body,
                    "accepted": "✅" in header,
                    "author": None,
                    "score": int(score_match.group(1)) if score_match else None,
                })
        elif answers_part.strip():
            answers.append({"text": answers_part.strip(), "accepted": True, "author": None, "score": None})
    return question.strip(), answers


def keyword_found(keyword: str, text: str) -> bool:
    if not keyword or not text:
        return False
    if has_hebrew(keyword):
        pattern = r"(?<![\u0590-\u05ff\w])[והבלמשכ]{0,2}" + re.escape(keyword) + r"(?!\w)"
    else:
        pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return bool(re.search(pattern, text, flags=re.I | re.U))


def classify(title: str, question: str, tags: list[str]):
    for tag in [str(t).strip().lower() for t in (tags or [])]:
        if tag in TAG_MAP:
            return TAG_MAP[tag], "high", False, "tag_map"

    title = title or ""
    body = (question or "")[:500]
    scores = {}
    strong_title = {}
    strong_count = {}

    for cat in CATEGORIES:
        cid = cat["id"]
        score = 0
        strongs = set()
        title_hit = False
        for kw in cat.get("keywords_strong", []):
            if keyword_found(kw, title):
                score += 5
                title_hit = True
                strongs.add(kw)
            elif keyword_found(kw, body):
                score += 3
                strongs.add(kw)
        for kw in cat.get("keywords_weak", []):
            if keyword_found(kw, title) or keyword_found(kw, body):
                score += 1
        if score:
            scores[cid] = score
            strong_title[cid] = title_hit
            strong_count[cid] = len(strongs)

    if not scores:
        return "general", "low", True, "no_match"

    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    cid, best = ordered[0]
    tie = len(ordered) > 1 and ordered[1][1] == best
    high = not tie and (strong_title.get(cid) or strong_count.get(cid, 0) >= 2)
    return cid, ("high" if high else "low"), (not high), "keywords"


def collect_responsa_meta(root: Path) -> dict:
    out = {}
    data = read_json(root / "responsa.json", [])
    if not isinstance(data, list):
        return out
    for item in data:
        if not isinstance(item, dict):
            continue
        file_value = str(item.get("file") or "")
        parsed_id = None
        if file_value.startswith("qa.html"):
            parsed = urlparse(file_value)
            parsed_id = parse_qs(parsed.query).get("id", [None])[0]
        keys = {str(item.get("source_id") or ""), str(item.get("number") or ""), str(parsed_id or "")}
        for key in [k for k in keys if k and k != "None"]:
            out[key] = item
    return out


def merge_legacy(entry: dict, meta: dict | None):
    if not meta:
        return
    entry.setdefault("legacy", {})
    if meta.get("number") is not None:
        entry["legacy"]["number"] = meta.get("number")
    if meta.get("file"):
        entry["legacy"]["old_file"] = meta.get("file")
    old_cat = meta.get("category_en") or meta.get("category")
    mapped = LEGACY_MAP.get(str(old_cat), LEGACY_MAP.get(str(meta.get("category")), None))
    if mapped and mapped != "general":
        entry["category"] = mapped
        entry["category_confidence"] = "high"
        entry["category_source"] = "legacy"
        entry.pop("needs_review", None)


def add_entry(entries: dict, raw: dict, prefix: str, source: str, source_file: Path, root: Path, fallback_seed: str):
    raw_id = raw.get("id") or raw.get("qid") or raw.get("question_id")
    sid = source_id_number(raw_id)
    qid = f"{prefix}-{sid}" if sid != "missing" else stable_missing_id(prefix, fallback_seed)
    if qid in entries:
        return False

    title = str(raw.get("title") or "")
    question = str(raw.get("question") or "")
    answers = []
    tags = []
    url = raw.get("url")
    date = raw.get("date")
    score = raw.get("score")
    views = raw.get("views")

    meta = raw.get("metadata") or {}
    if isinstance(meta, dict):
        tags = meta.get("tags") or tags
        url = meta.get("url") or url
        date = meta.get("date") or date
        score = meta.get("score", score)
        views = meta.get("views", views)

    if raw.get("content"):
        question, answers = parse_miyodea_content(raw.get("content"))
    elif raw.get("answer") is not None:
        answers = [{"text": str(raw.get("answer") or ""), "accepted": True, "author": None, "score": None}]
    elif raw.get("answers"):
        for idx, ans in enumerate(raw.get("answers") or []):
            if isinstance(ans, dict):
                text = ans.get("text") or ans.get("answer") or ""
                accepted = bool(ans.get("accepted", idx == 0))
                answers.append({"text": str(text), "accepted": accepted, "author": ans.get("author"), "score": ans.get("score")})
            else:
                answers.append({"text": str(ans), "accepted": idx == 0, "author": None, "score": None})

    category, confidence, review, category_source = classify(title, question, tags)
    title_he = title if has_hebrew(title) else ""
    title_en = "" if has_hebrew(title) else title

    entry = {
        "id": qid,
        "legacy": {"source_id": str(raw_id or sid), "src": source_file.relative_to(root).as_posix()},
        "source": source,
        "category": category,
        "category_confidence": confidence,
        "category_source": category_source,
        "title_he": title_he,
        "title_en": title_en,
        "question": question,
        "answers": [a for a in answers if clean_text(a.get("text"))],
        "url": url,
        "tags": tags or [],
        "date": date,
        "year": year_from_date(date),
    }
    if score is not None:
        entry["score"] = score
    if views is not None:
        entry["views"] = views
    if review:
        entry["needs_review"] = True
    if not entry["answers"]:
        entry["answers"] = []
    entries[qid] = entry
    return True


def collect_entries(root: Path, report: list[str]):
    entries = {}
    raw_count = 0
    source_stats = {"miyodea_raw": 0, "qa_db_years": 0, "qa_db_json": 0, "generated": 0}

    for path in sorted((root / "miyodea" / "qa").glob("*.json")):
        for raw in items(read_json(path, [])):
            raw_count += 1
            if add_entry(entries, raw, "my", "miyodea", path, root, f"{path}:{raw_count}"):
                source_stats["miyodea_raw"] += 1

    for path in sorted((root / "qa_db").glob("*.json")):
        for raw in items(read_json(path, [])):
            raw_count += 1
            if add_entry(entries, raw, "ye", "yeshiva", path, root, f"{path}:{raw_count}"):
                source_stats["qa_db_years"] += 1

    mono = root / "qa_db.json"
    if mono.exists():
        for raw in items(read_json(mono, [])):
            raw_count += 1
            if add_entry(entries, raw, "ye", "yeshiva", mono, root, f"{mono}:{raw_count}"):
                source_stats["qa_db_json"] += 1

    gen_dir = root / "data" / "qa" / "generated"
    for path in sorted(gen_dir.glob("*.json")):
        for raw in items(read_json(path, [])):
            raw_count += 1
            if add_entry(entries, raw, "my", "miyodea", path, root, f"{path}:{raw_count}"):
                source_stats["generated"] += 1

    meta = collect_responsa_meta(root)
    enriched = 0
    for e in entries.values():
        sid = str(e.get("legacy", {}).get("source_id", ""))
        stripped = source_id_number(sid)
        m = meta.get(sid) or meta.get(stripped)
        if m:
            merge_legacy(e, m)
            enriched += 1

    report.append(f"- Quellen gelesen: {raw_count}; eindeutige Fragen: {len(entries)}; pro Quelle: {source_stats}")
    report.append(f"- Aus responsa.json angereichert: {enriched} Einträge")
    return entries


def category_payload() -> dict:
    return {"schema": SCHEMA, "version": datetime.now(timezone.utc).date().isoformat(), "default_category": "general", "categories": CATEGORIES, "tag_map": TAG_MAP, "legacy_map": LEGACY_MAP}


def make_index_record(q: dict, chunk_no: int) -> dict:
    title_he = q.get("title_he") or ""
    title_en = q.get("title_en") or ""
    if not title_he and not title_en:
        title = q.get("title") or excerpt(q.get("question"), 80)
        if has_hebrew(title):
            title_he = title
        else:
            title_en = title
    accepted = next((a for a in q.get("answers", []) if a.get("accepted")), None)
    accepted = accepted or (q.get("answers") or [{}])[0]
    rec = {
        "id": q["id"], "t_he": title_he, "t_en": title_en,
        "x": excerpt(q.get("question"), 160), "ax": excerpt(accepted.get("text"), 160),
        "tg": [str(t).lower() for t in q.get("tags", [])],
        "c": q.get("category", "general"), "y": q.get("year"), "ch": chunk_no, "s": q.get("source", "")
    }
    if q.get("needs_review"):
        rec["r"] = 1
    return rec


def write_new_structure(root: Path, out_base: Path, entries: dict, max_per_chunk: int, max_chunk_bytes: int, report: list[str]):
    q_base = out_base / "data" / "questions"
    chunk_dir = q_base / "chunks"
    by_cat_dir = q_base / "by-category"
    ordered = sorted(entries.values(), key=lambda e: (e.get("year") or 0, e.get("source") or "", e.get("id") or ""))

    chunks = []
    current = []
    for entry in ordered:
        test = current + [entry]
        test_payload = {"schema": SCHEMA, "chunk": len(chunks) + 1, "count": len(test), "questions": test}
        too_many = len(test) > max_per_chunk
        too_large = len(json.dumps(test_payload, ensure_ascii=False).encode("utf-8")) > max_chunk_bytes
        if current and (too_many or too_large):
            chunks.append(current)
            current = [entry]
        else:
            current = test
    if current:
        chunks.append(current)

    index_entries = []
    aliases = {}
    for no, questions in enumerate(chunks, start=1):
        for q in questions:
            index_entries.append(make_index_record(q, no))
            legacy = q.get("legacy", {}) or {}
            aliases[q["id"]] = {"id": q["id"], "ch": no}
            if legacy.get("source_id"):
                aliases[str(legacy["source_id"])] = {"id": q["id"], "ch": no}
                aliases[source_id_number(str(legacy["source_id"]))] = {"id": q["id"], "ch": no}
            if legacy.get("number") is not None:
                aliases[f"n{legacy['number']}"] = {"id": q["id"], "ch": no}
            if legacy.get("old_file"):
                aliases[str(legacy["old_file"])] = {"id": q["id"], "ch": no}
        write_json(chunk_dir / f"qa_{no:04d}.json", {"schema": SCHEMA, "chunk": no, "count": len(questions), "questions": questions})

    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(q_base / "manifest.json", {"schema": SCHEMA, "generated": generated, "total": len(ordered), "chunks": len(chunks), "open_chunk": len(chunks) or 1, "max_per_chunk": max_per_chunk, "max_chunk_bytes": max_chunk_bytes, "index_files": ["index.json"]})
    write_json(q_base / "index.json", {"schema": SCHEMA, "generated": generated, "count": len(index_entries), "entries": index_entries})
    write_json(q_base / "categories.json", category_payload())
    write_json(q_base / "aliases.json", {"schema": SCHEMA, "aliases": aliases})

    by_category = {c["id"]: [] for c in CATEGORIES}
    for rec in index_entries:
        by_category.setdefault(rec.get("c") or "general", []).append(rec)
    for cid, rows in by_category.items():
        write_json(by_cat_dir / f"{cid}.json", {"schema": SCHEMA, "category": cid, "count": len(rows), "entries": rows})

    review_count = sum(1 for e in ordered if e.get("needs_review"))
    used_categories = sorted({e.get("category", "general") for e in ordered})
    report.append(f"- Migriert: {len(ordered)} Fragen in {len(chunks)} Chunk-Datei(en)")
    report.append(f"- Kategorien belegt: {used_categories}")
    report.append(f"- needs_review: {review_count}")


def original_files(root: Path) -> list[Path]:
    files = []
    for rel in ["responsa.json", "qa_db.json"]:
        p = root / rel
        if p.is_file():
            files.append(p)
    for rel in ["qa_db", "miyodea/qa", "data/qa/generated"]:
        p = root / rel
        if p.is_dir():
            files.extend(sorted(x for x in p.rglob("*") if x.is_file()))
    return files


def prepare_backup(root: Path, out_base: Path, do_copy: bool, report: list[str]):
    files = original_files(root)
    total = sum(p.stat().st_size for p in files)
    report.append(f"- Backup-Umfang vorbereitet: {len(files)} Dateien, {total} Bytes")
    if not do_copy:
        report.append("- Backup-Kopie nicht erstellt. Für Kopie: --backup verwenden.")
        return
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    target = out_base / "_backup_originals" / stamp
    for src in files:
        dst = target / src.relative_to(root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if sha256(src) != sha256(dst):
            raise RuntimeError(f"Backup-Prüfsumme stimmt nicht: {src}")
    report.append(f"- Backup-Kopie erstellt: {target.relative_to(root).as_posix()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-Run-Migration der Q&A-Daten.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default=OUT_DIR_NAME)
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--max-per-chunk", type=int, default=500)
    parser.add_argument("--max-chunk-bytes", type=int, default=1_500_000)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out_base = (root / args.out).resolve()
    report = [f"# migration_report — Dry Run {datetime.now():%d.%m.%Y %H:%M:%S}", "", f"Ausgabe ausschließlich nach: {out_base.relative_to(root).as_posix()}/", "Originaldaten bleiben unangetastet.", ""]

    if not (root / "index.html").exists() or not (root / "qa.html").exists():
        raise SystemExit("Bitte im Wurzelverzeichnis des Repositories ausführen.")

    prepare_backup(root, out_base, args.backup, report)
    entries = collect_entries(root, report)
    write_new_structure(root, out_base, entries, args.max_per_chunk, args.max_chunk_bytes, report)

    report.append("")
    report.append("## Ergebnis")
    report.append("Dry Run abgeschlossen. Produktive Projektdateien wurden nicht beschrieben.")
    report_path = out_base / "migration_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    print(f"\nBericht: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
