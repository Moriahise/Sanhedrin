#!/usr/bin/env bash
set -euo pipefail

# Generate professional report before removing empty or duplicate Q&A records.
python3 -m py_compile migrate_qa.py qa_store.py quality_check_qa.py
python3 quality_check_qa.py

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add qualitaets_report.md
if git diff --cached --quiet; then
  echo "No quality report changes"
  exit 0
fi

git commit -m "Add Q&A quality report"
git pull --rebase origin main
git push
