#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Append-only: Merge Q&A JSON files under data/qa/*.json into responsa.json.

Output entries point to: qa.html?id=<id>
No intermediate files. No HTML generation. No changes to existing entries.
"""

import json
import re
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QA_DIR = REPO / "data" / "qa"
RESPONSA_PATH = REPO / "responsa.json"

# Keep UI-compatible categories (your filter already supports "other")
CATEGORY = "other"
CATEGORY_HE = "שאלות ותשובות"
CATEGORY_EN = "Q&A"

def parse_iso(dt: str):
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except Exception:
        return None

def ddmmyyyy(dt: datetime | None) -> str:
    return dt.strftime("%d/%m/%Y") if dt else ""

def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p: Path, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    QA_DIR.mkdir(parents=True, exist_ok=True)

    # Load responsa.json
    if RESPONSA_PATH.exists():
        responsa = load_json(RESPONSA_PATH)
        if not isinstance(responsa, list):
            raise SystemExit("responsa.json must be a JSON array")
    else:
        responsa = []

    # Existing indices to avoid duplicates
    existing_files = {str(x.get("file", "")) for x in responsa if isinstance(x, dict)}
    existing_qa_ids = {str(x.get("qa_id", "")) for x in responsa if isinstance(x, dict) and x.get("qa_id") is not None}

    # Next number
    max_num = 0
    for x in responsa:
        try:
            max_num = max(max_num, int(x.get("number", 0)))
        except Exception:
            pass
    next_num = max_num + 1

    qa_files = sorted(QA_DIR.glob("*.json"))
    if not qa_files:
        print("No QA json files found in data/qa/")
        return 0

    appended = 0

    for f in qa_files:
        data = load_json(f)

        # Support BOTH formats:
        # A) { "questions": [ ... ] }  (your yeshiva export)
        # B) { "items": [ ... ] }      (optional legacy format)
        items = data.get("questions")
        if items is None:
            items = data.get("items")
        if not isinstance(items, list):
            continue

        for q in items:
            qid = str(q.get("id", "")).strip()
            if not qid:
                continue

            file_link = f"qa.html?id={qid}"
            if file_link in existing_files or qid in existing_qa_ids:
                continue

            meta = q.get("metadata") or {}
            dt = parse_iso(meta.get("date", "")) or parse_iso(q.get("saved_at", ""))

            year = dt.year if dt else datetime.utcnow().year
            date = ddmmyyyy(dt) if dt else datetime.utcnow().strftime("%d/%m/%Y")

            title = (q.get("title") or f"שאלה #{qid}").strip()
            question = (q.get("question") or "").strip()
            summary = norm_space(question)
            if len(summary) > 220:
                summary = summary[:217].rstrip() + "…"

            responsa.append({
                "number": next_num,
                "title_he": title,
                "title_en": title,
                "summary_he": summary,
                "summary_en": summary,
                "category": CATEGORY,
                "category_he": CATEGORY_HE,
                "category_en": CATEGORY_EN,
                "date": date,
                "year": year,
                "file": file_link,
                "type": "html",

                # extra fields (harmless for UI, useful for debugging)
                "qa_id": qid,
                "qa_url": q.get("url", ""),
                "qa_rabbi": meta.get("rabbi", ""),
                "qa_upvotes": meta.get("upvotes", None)
            })

            existing_files.add(file_link)
            existing_qa_ids.add(qid)
            next_num += 1
            appended += 1

    # Optional sort: newest year first, then number desc
    responsa.sort(key=lambda x: (int(x.get("year", 0)), int(x.get("number", 0))), reverse=True)

    save_json(RESPONSA_PATH, responsa)
    print(f"OK: appended {appended} Q&A items. responsa.json now has {len(responsa)} entries.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
