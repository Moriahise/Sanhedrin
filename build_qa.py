#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build/import Q&A from Mi Yodeya JSON files.

Legacy behavior wrote Q&A cards into responsa.json. That is intentionally stopped.
This script still produces normalized helper files in data/qa/generated/, but new
Q&A entries are written through QAStore into the chunked data/questions/ store.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from html.parser import HTMLParser

from qa_store import QAStore, DuplicateError, ValidationError

REPO_ROOT = Path(__file__).resolve().parent
RAW_GLOBS = [REPO_ROOT / "miyodea" / "qa" / "*.json"]
OUT_DIR = REPO_ROOT / "data" / "qa" / "generated"


class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def text(self):
        return "".join(self.parts)


def strip_html(text: str) -> str:
    stripper = _Stripper()
    stripper.feed(text or "")
    return stripper.text()


def extract_q_a(content: str):
    q, a = "", ""
    parts = re.split(r"##\s*Frage", content or "", flags=re.IGNORECASE)
    if len(parts) > 1:
        after = parts[1]
        parts2 = re.split(r"##\s*Antworten", after, flags=re.IGNORECASE)
        q = parts2[0]
        rest = parts2[1] if len(parts2) > 1 else ""
        parts3 = re.split(r"\n###\s*", rest)
        a = parts3[1] if len(parts3) > 1 else rest
    else:
        q = content or ""

    q_txt = re.sub(r"\n{3,}", "\n\n", strip_html(q)).strip()
    a_txt = re.sub(r"\n{3,}", "\n\n", strip_html(a)).strip()
    a_txt = re.sub(r"^\s*(✅\s*)?Antwort\s*\d+.*?\n+", "", a_txt, flags=re.IGNORECASE).strip()
    return q_txt, a_txt


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_id(raw_id) -> str:
    # Nicht kürzen: migrate_qa.py verwendet die Roh-ID stabil als legacy.source_id.
    return str(raw_id or "").strip()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    store = QAStore(REPO_ROOT)
    normalized_files = []
    added = skipped = rejected = 0

    for pattern in RAW_GLOBS:
        for raw_path in sorted(raw_path for raw_path in pattern.parent.glob(pattern.name)):
            raw = load_json(raw_path)
            items = raw if isinstance(raw, list) else raw.get("questions", [])
            questions = []

            for item in items:
                q_txt, a_txt = extract_q_a(item.get("content", ""))
                meta = item.get("metadata", {}) or {}
                raw_id = item.get("id") or item.get("qid") or item.get("question_id")
                sid = source_id(raw_id)
                answers = [{"text": a_txt, "accepted": True, "author": None, "score": None}] if a_txt else []

                normalized = {
                    "id": raw_id,
                    "title": item.get("title") or "",
                    "question": q_txt,
                    "answer": a_txt,
                    "metadata": {
                        "source": meta.get("source") or "Mi Yodeya",
                        "url": meta.get("url") or item.get("url") or "",
                        "tags": meta.get("tags") or [],
                        "score": meta.get("score"),
                        "views": meta.get("views"),
                        "date": meta.get("date"),
                        "answers": meta.get("answers"),
                    },
                }
                questions.append(normalized)

                try:
                    store.add_question({
                        "source": "miyodea",
                        "source_id": sid,
                        "title": item.get("title") or "",
                        "question": q_txt,
                        "answers": answers,
                        "tags": meta.get("tags") or [],
                        "date": str(meta.get("date") or "").split("T", 1)[0] or None,
                        "url": meta.get("url") or item.get("url") or None,
                    }, require_answer=False)
                    added += 1
                except DuplicateError:
                    skipped += 1
                except ValidationError as exc:
                    rejected += 1
                    print(f"ABGELEHNT {raw_path.name}/{raw_id}: {exc}")

            out_path = OUT_DIR / f"{raw_path.stem}.normalized.json"
            out = {
                "source": "normalized",
                "generated_from": str(raw_path.as_posix()),
                "questions": questions,
            }
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            normalized_files.append(out_path)

    problems = store.verify()
    if problems:
        print("Konsistenzprüfung FEHLER:")
        for problem in problems:
            print("  ", problem)
        return 1

    print(f"OK: wrote {len(normalized_files)} normalized file(s) into {OUT_DIR}")
    print(f"OK: added={added}, skipped_duplicates={skipped}, rejected={rejected}")
    print("OK: Q&A index written to data/questions/. responsa.json wurde nicht verändert.")
    return 0 if rejected == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
