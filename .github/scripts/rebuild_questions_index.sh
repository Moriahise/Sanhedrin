#!/usr/bin/env bash
set -euo pipefail

# Rebuild from current chunk files after chunk restore.
python3 -m py_compile migrate_qa.py qa_store.py rebuild_index.py
python3 rebuild_index.py

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add data/questions/index.json data/questions/aliases.json data/questions/manifest.json data/questions/by-category
if git diff --cached --quiet; then
  echo "No index rebuild changes"
  exit 0
fi

git commit -m "Rebuild Q&A index files"
git push
