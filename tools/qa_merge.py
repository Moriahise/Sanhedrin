#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge Q&A JSON files under data/qa/*.json into the new chunked store.

Old behavior appended to responsa.json. That is intentionally stopped for Q&A.
New behavior writes only through qa_store.QAStore into data/questions/:
chunks, index.json, by-category, aliases.json and manifest.json.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from qa_store import QAStore, DuplicateError, ValidationError

QA_DIR = REPO / "data" / "qa"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_item(q: dict) -> dict:
    qid = str(q.get("id", "")).strip()
    meta = q.get("metadata") or {}
    answer = q.get("answer") or q.get("response") or ""
    answers = q.get("answers")

    if answers is None:
        answers = [{"text": answer, "accepted": True, "author": None, "score": None}] if answer else []
    else:
        norm = []
        for i, a in enumerate(answers):
            if isinstance(a, str):
                norm.append({"text": a, "accepted": i == 0, "author": None, "score": None})
            elif isinstance(a, dict):
                norm.append({
                    "text": a.get("text") or a.get("answer") or "",
                    "accepted": bool(a.get("accepted", i == 0)),
                    "author": a.get("author"),
                    "score": a.get("score"),
                })
        answers = norm

    date = q.get("date") or meta.get("date") or q.get("saved_at") or ""
    if "T" in str(date):
        date = str(date).split("T", 1)[0]
    if not date:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    return {
        "source": q.get("source") or "yeshiva",
        "source_id": qid,
        "title": (q.get("title") or q.get("question") or f"שאלה #{qid}").strip(),
        "question": (q.get("question") or "").strip(),
        "answers": answers,
        "tags": q.get("tags") or meta.get("tags") or [],
        "category": q.get("category"),
        "date": date,
        "url": q.get("url") or meta.get("url") or (f"https://www.yeshiva.org.il/ask/{qid}" if qid else None),
    }


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    qa_files = sorted(QA_DIR.glob("*.json"))
    if not qa_files:
        print("No QA json files found in data/qa/")
        return 0

    store = QAStore(REPO)
    added = skipped = rejected = 0

    for path in qa_files:
        data = load_json(path)
        items = data.get("questions") if isinstance(data, dict) else None
        if items is None and isinstance(data, dict):
            items = data.get("items")
        if items is None and isinstance(data, list):
            items = data
        if not isinstance(items, list):
            continue

        for raw in items:
            item = normalize_item(raw)
            if not item["source_id"]:
                rejected += 1
                print(f"ABGELEHNT ({path.name}): fehlende id")
                continue
            try:
                res = store.add_question(item, require_answer=True)
                added += 1
                flag = " [needs_review]" if res["needs_review"] else ""
                print(f"OK {res['id']} -> {res['chunk_file']} {res['category']} ({res['confidence']}){flag}")
            except DuplicateError as exc:
                skipped += 1
                print(f"ÜBERSPRUNGEN: {exc}")
            except ValidationError as exc:
                rejected += 1
                print(f"ABGELEHNT ({item['source_id']}): {exc}")

    problems = store.verify()
    if problems:
        print("Konsistenzprüfung FEHLER:")
        for problem in problems:
            print("  ", problem)
        return 1

    print(f"OK: added={added}, skipped_duplicates={skipped}, rejected={rejected}")
    print("OK: data/questions/ konsistent. responsa.json wurde nicht verändert.")
    return 0 if rejected == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
