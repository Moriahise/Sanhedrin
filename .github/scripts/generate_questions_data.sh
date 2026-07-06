#!/usr/bin/env bash
set -euo pipefail

# Triggered via GitHub Actions to generate data/questions from current main.
python3 -m py_compile migrate_qa.py .github/scripts/generate_questions_data.py
python3 .github/scripts/generate_questions_data.py

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add data/questions migration_report.md
if git diff --cached --quiet; then
  echo "No changes"
  exit 0
fi

git commit -m "Auto-update chunked Q&A data"
git push
