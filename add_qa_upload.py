#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_qa_upload.py — neuer Upload-Weg für Fragen & Antworten.

Schreibt über qa_store.py in data/questions/ und niemals in responsa.json.
"""
import argparse
import json
import sys
from pathlib import Path

from qa_store import QAStore, ValidationError, DuplicateError


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", help="JSON-Datei mit einer Frage oder einer Liste von Fragen")
    parser.add_argument("--title")
    parser.add_argument("--question")
    parser.add_argument("--answer", action="append", default=[], help="mehrfach angebbar; erste Antwort gilt als akzeptiert")
    parser.add_argument("--tags", default="", help="kommagetrennt")
    parser.add_argument("--category", help="explizite Kategorie, sonst automatische Zuordnung")
    parser.add_argument("--date")
    parser.add_argument("--url")
    parser.add_argument("--source", default="upload", choices=["upload", "miyodea", "yeshiva"])
    parser.add_argument("--source-id", help="Pflicht bei --source miyodea/yeshiva")
    parser.add_argument("--verify", action="store_true", help="nur Konsistenzprüfung ausführen")
    args = parser.parse_args()

    store = QAStore(args.root)

    if args.verify:
        problems = store.verify()
        print("Konsistenzprüfung:", "OK — keine Probleme" if not problems else "FEHLER")
        for problem in problems:
            print("  FEHLER:", problem)
        return 0 if not problems else 1

    if args.json:
        data = json.loads(Path(args.json).read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [data]
    else:
        if not (args.title or args.question):
            parser.error("--title/--question oder --json erforderlich")
        items = [{
            "title": args.title or "",
            "question": args.question or "",
            "answers": [
                {"text": text, "accepted": i == 0, "author": None, "score": None}
                for i, text in enumerate(args.answer)
            ],
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
            "category": args.category,
            "date": args.date,
            "url": args.url,
            "source": args.source,
            "source_id": args.source_id,
        }]

    rc = 0
    for item in items:
        item.setdefault("source", args.source)
        try:
            result = store.add_question(item)
            flag = " [needs_review]" if result["needs_review"] else ""
            print(
                f"OK  {result['id']} -> {result['chunk_file']}  "
                f"Kategorie: {result['category']} ({result['confidence']}){flag}"
            )
        except DuplicateError as exc:
            print(f"ÜBERSPRUNGEN (Duplikat): {exc}")
        except ValidationError as exc:
            print(f"ABGELEHNT (Validierung): {exc}")
            rc = 1

    problems = store.verify()
    if problems:
        print("WARNUNG — Konsistenzprüfung nach Upload:")
        for problem in problems:
            print("  ", problem)
        rc = 1
    else:
        print("Konsistenzprüfung nach Upload: OK")
    return rc


if __name__ == "__main__":
    sys.exit(main())
