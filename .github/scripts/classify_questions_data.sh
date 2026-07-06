#!/usr/bin/env bash
set -euo pipefail

# Trigger classification workflow for current data/questions.
python3 -m py_compile migrate_qa.py classify_qa.py
python3 classify_qa.py --run

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add data/questions klassifizierungs_report.md
if git diff --cached --quiet; then
  echo "No classification changes"
  exit 0
fi

git commit -m "Classify chunked Q&A data"
git push
