#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QA_DIR = REPO / "data" / "qa"
OUT = REPO / "qa_db.json"

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    QA_DIR.mkdir(parents=True, exist_ok=True)
    all_questions = []
    seen = set()

    for f in sorted(QA_DIR.glob("*.json")):
        data = load_json(f)

        # support both formats
        items = data.get("questions")
        if items is None:
            items = data.get("items")
        if not isinstance(items, list):
            continue

        for q in items:
            qid = str(q.get("id", "")).strip()
            if not qid or qid in seen:
                continue
            seen.add(qid)
            all_questions.append(q)

    out_obj = {
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_questions": len(all_questions),
        "questions": all_questions
    }

    OUT.write_text(json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: wrote {OUT} with {len(all_questions)} questions")

if __name__ == "__main__":
    main()
