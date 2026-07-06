#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile migrate_qa.py migrate_production.py validate_migration.py qa_store.py add_qa_upload.py tools/qa_merge.py

if [ ! -f data/questions/manifest.json ]; then
  python3 migrate_production.py --run
else
  echo "data/questions already exists"
fi

python3 tools/qa_merge.py
python3 add_qa_upload.py --verify

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add data/questions migration_report.md
if git diff --cached --quiet; then
  echo "No changes"
  exit 0
fi

git commit -m "Auto-update chunked Q&A data"
git push
