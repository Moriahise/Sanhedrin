#!/usr/bin/env bash
set -euo pipefail

# Repair after legacy ingest changed responsa/qa_db and the chunked store lost entries.
# This run uses the fixed chunk rollover and upload date handling.
CLEAN_SHA="b7a63522b79fab64766faee271bb3af8665f2d67"

python3 -m py_compile migrate_qa.py qa_store.py add_qa_upload.py tools/qa_merge.py

echo "Restore data/questions and legacy generated files from clean baseline: ${CLEAN_SHA}"
git checkout "${CLEAN_SHA}" -- data/questions responsa.json qa_db

echo "Merge current data/qa uploads into restored chunked store"
python3 tools/qa_merge.py
python3 add_qa_upload.py --verify

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git add data/questions responsa.json qa_db
if git diff --cached --quiet; then
  echo "No repair changes"
  exit 0
fi

git commit -m "Repair chunked Q&A data after upload"
git pull --rebase origin main
git push
