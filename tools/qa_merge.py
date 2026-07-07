#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge Q&A JSON files under data/qa/*.json into the new chunked store.

This workflow is deliberately tolerant for GitHub upload folders:
valid new questions are added, duplicates are skipped, invalid rows are reported
but do not break the whole ingestion run. responsa.json is never modified.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from qa_store import QAStore, DuplicateError, ValidationError

QA_DIR = REPO / "data" / "qa"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_answers(raw: dict) -> list[dict]:
    answer = raw.get("answer") or raw.get("response") or raw.get("answer_text") or ""
    answers = raw.get("answers")
    if answers is None:
        return [{"text": str(answer), "accepted": True, "author": None, "score": None}] if str(answer).strip() else []

    normalized = []
    for i, item in enumerate(answers or []):
        if isinstance(item, str):
            text = item
            accepted = i == 0
            author = None
            score = None
        elif isinstance(item, dict):
            text = item.get("text") or item.get("answer") or item.get("body") or ""
            accepted = bool(item.get("accepted", i == 0))
            author = item.get("author")
            score = item.get("score")
        else:
            continue
        if str(text).strip():
            normalized.append({"text": str(text), "accepted": accepted, "author": author, "score": score})
    return normalized


def clean_date(raw_value) -> str:
    """Use only a real source/upload date. Never invent the current year."""
    value = str(raw_value or "").strip()
    if not value:
        return ""
    if "T" in value:
        value = value.split("T", 1)[0]
    return value


def normalize_item(raw: dict, path: Path, fallback_no: int, default_date: str = "") -> dict:
    meta = raw.get("metadata") or {}
    source = raw.get("source") or meta.get("source") or "yeshiva"
    qid = str(raw.get("id") or raw.get("source_id") or meta.get("id") or "").strip()
    if not qid:
        qid = f"{path.stem}-{fallback_no}"
        source = "upload"

    date = clean_date(
        raw.get("saved_at")
        or meta.get("saved_at")
        or default_date
        or raw.get("date")
        or meta.get("date")
    )
    question = str(raw.get("question") or raw.get("body") or raw.get("content") or "").strip()
    title = str(raw.get("title") or question or f"שאלה #{qid}").strip()

    tags = raw.get("tags") or meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return {
        "source": source,
        "source_id": qid,
        "title": title,
        "question": question,
        "answers": normalize_answers(raw),
        "tags": tags,
        "category": raw.get("category") or meta.get("category"),
        "date": date,
        "url": raw.get("url") or meta.get("url") or (f"https://www.yeshiva.org.il/ask/{qid}" if source == "yeshiva" and qid else None),
    }


def extract_items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("questions", "items", "data", "qa", "records"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        if data.get("question") or data.get("title") or data.get("answer") or data.get("answers"):
            return [data]
    return []


def main() -> int:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    qa_files = sorted(QA_DIR.glob("*.json"))
    if not qa_files:
        print("No QA json files found in data/qa/")
        return 0

    store = QAStore(REPO)
    added = skipped = rejected = files_seen = 0

    for path in qa_files:
        files_seen += 1
        try:
            data = load_json(path)
        except Exception as exc:
            rejected += 1
            print(f"ABGELEHNT ({path.name}): JSON kann nicht gelesen werden: {exc}")
            continue

        default_date = clean_date(data.get("exported_at")) if isinstance(data, dict) else ""
        items = extract_items(data)
        if not items:
            print(f"ÜBERSPRUNGEN ({path.name}): keine Fragenliste gefunden")
            continue

        for no, raw in enumerate(items, start=1):
            if not isinstance(raw, dict):
                rejected += 1
                print(f"ABGELEHNT ({path.name} #{no}): Eintrag ist kein Objekt")
                continue
            item = normalize_item(raw, path, no, default_date)
            try:
                res = store.add_question(item, require_answer=False)
                added += 1
                flag = " [needs_review]" if res["needs_review"] else ""
                print(f"OK {res['id']} -> {res['chunk_file']} {res['category']} ({res['confidence']}){flag}")
            except DuplicateError as exc:
                skipped += 1
                print(f"ÜBERSPRUNGEN: {exc}")
            except ValidationError as exc:
                rejected += 1
                print(f"ABGELEHNT ({item.get('source_id')}): {exc}")

    rebuilt = store.rebuild_index()
    problems = store.verify()
    if problems:
        print("Konsistenzprüfung FEHLER:")
        for problem in problems:
            print("  ", problem)
        return 1

    print(f"OK: files={files_seen}, added={added}, skipped_duplicates={skipped}, rejected={rejected}, index={rebuilt}")
    print("OK: data/questions/ konsistent. responsa.json wurde nicht verändert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
