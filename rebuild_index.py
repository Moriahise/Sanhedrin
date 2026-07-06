#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rebuild_index.py — index.json, by-category/ und aliases.json neu aufbauen.

Regeneriert alle abgeleiteten Dateien aus den Chunk-Dateien. Die Chunks selbst
und alle Originaldaten werden nur gelesen.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from qa_store import QAStore


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not (root / "data" / "questions" / "manifest.json").exists():
        print("ABBRUCH: data/questions/ nicht gefunden — im Repo-Root ausführen.")
        return 2

    store = QAStore(root)
    n = store.rebuild_index()
    problems = store.verify()
    dist = Counter(e["c"] for e in store.index["entries"])

    print(f"Index neu aufgebaut: {n} Einträge")
    print("Verteilung:", ", ".join(f"{k}: {v}" for k, v in sorted(dist.items(), key=lambda x: -x[1])))
    print("Konsistenzprüfung:", "OK — keine Probleme" if not problems else "FEHLER")
    for problem in problems:
        print("  FEHLER:", problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
