#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile migrate_qa.py qa_store.py quality_check_qa.py
python3 quality_check_qa.py --run
python3 rebuild_index.py

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add data/questions qualitaets_report.md
if git diff --cached --quiet; then
  echo "No quality cleanup changes"
  exit 0
fi

git commit -m "Clean empty and duplicate Q&A records"
git push
