"""
Updated Yeshiva Q&A ingest script with support for splitting qa_db into
yearly files.

This script reads Yeshiva Q&A dumps from the `data/qa` directory and
merges them into JSON files organised by year within the `qa_db/` folder.
Each file under `qa_db/` contains a list of questions for a specific year,
so that no single file exceeds GitHub's 100 MB limit.  It also maintains
`responsa.json` without overwriting existing entries from other sources.
Each question's original URL is surfaced as a top‑level `url` field (pulled
from `metadata.url` or the top‑level `url` when present) so that the
front‑end can display a proper source link.  New responsa entries are
appended to `responsa.json` for indexing.

To use this script, run it from the repository root. It will read any
existing files under `qa_db/`, merge in new Yeshiva items from
`data/qa/*.json`, and write the updated files back to disk.
"""

import json
import glob
import os
from datetime import datetime

# Paths relative to this script's directory
ROOT = os.path.dirname(os.path.dirname(__file__))  # repository root
RESPONSA_PATH = os.path.join(ROOT, "responsa.json")
# Glob pattern for Yeshiva dumps
YESHIVA_GLOB = os.path.join(ROOT, "data", "qa", "*.json")
QA_DB_DIR = os.path.join(ROOT, "qa_db")


def load_json(path, default):
    """Load a JSON file and return a default value on failure."""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"⚠️  Failed to parse {path}: {exc}")
        return default


def save_json(path, data):
    """Save a Python object as JSON with UTF‑8 encoding."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_summary_from_content(content: str) -> str:
    """
    Create a concise summary from the provided Q&A content.

    Yeshiva exports provide separate `question` and `answer` fields.  This
    function receives the concatenated question and answer text.  It removes
    markdown headings (lines starting with '#') and common section labels
    like 'Frage', 'Question', 'Answer', 'Antworten', etc.  The remaining
    lines are joined with spaces and truncated to approximately 220
    characters with an ellipsis appended if the original sanitized text
    exceeds this length.
    """
    if not content:
        return ""
    sanitized_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        low = stripped.lower()
        if (
            low.startswith('frage')
            or low.startswith('answers')
            or low.startswith('antworten')
            or low.startswith('answer')
            or low.startswith('question')
        ):
            continue
        sanitized_lines.append(stripped)
    sanitized_text = " ".join(sanitized_lines).strip()
    if len(sanitized_text) > 220:
        return sanitized_text[:220] + "…"
    return sanitized_text


def extract_year(meta_date: str) -> int:
    """Extract the year component from an ISO date string."""
    if not meta_date:
        return datetime.utcnow().year
    try:
        return int(meta_date[:4])
    except Exception:
        return datetime.utcnow().year


def to_responsa_entry(item, src_relpath: str):
    """Build a responsa entry from a Yeshiva question item."""
    meta = item.get("metadata", {}) or {}
    qid = str(item.get("id", "")).strip()
    digits = "".join(ch for ch in qid if ch.isdigit())
    number = int(digits) if digits else 0
    year = extract_year(meta.get("date"))
    date_str = meta.get("date", f"{year}-01-01")[:10]
    title = item.get("title") or f"Q&A {qid}"
    # Concatenate question and answer content for summary
    combined = "\n".join([
        item.get("question", ""),
        item.get("answer", ""),
    ]).strip()
    summary = normalize_summary_from_content(combined)
    return {
        "number": number,
        "title_he": title,
        "title_en": title,
        "summary_he": summary,
        "summary_en": summary,
        "category": "other",
        "category_he": "שאלות ותשובות",
        "category_en": "Q&A",
        "date": date_str,
        "year": year,
        "file": f"qa.html?id={qid}&src={src_relpath}",
        "type": "html",
        "source": meta.get("source", "Yeshiva"),
        "source_url": item.get("url") or meta.get("url"),
        "tags": meta.get("tags", []),
        "source_id": qid,
        "src": src_relpath,
    }


def main():
    # Ensure the QA_DB_DIR exists
    os.makedirs(QA_DB_DIR, exist_ok=True)
    # Load existing responsa entries
    responsa = load_json(RESPONSA_PATH, [])
    if not isinstance(responsa, list):
        raise SystemExit("responsa.json must be a JSON array")
    existing_keys = set()
    for r in responsa:
        k = (str(r.get("src", "")), str(r.get("source_id", "")))
        if k != ("", ""):
            existing_keys.add(k)
    # Load existing QA DB entries from all yearly files
    existing_map = {}
    if os.path.isdir(QA_DB_DIR):
        for fpath in glob.glob(os.path.join(QA_DB_DIR, "*.json")):
            data = load_json(fpath, {"questions": []})
            if isinstance(data, dict):
                questions = data.get("questions", [])
                for q in questions:
                    if isinstance(q, dict):
                        qid = str(q.get("id"))
                        if qid:
                            existing_map[qid] = q
    new_entries = []
    # Process each Yeshiva file
    for path in sorted(glob.glob(YESHIVA_GLOB)):
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        data = load_json(path, None)
        # Yeshiva dumps are expected to be a dict with top-level keys or a list of questions
        if isinstance(data, dict):
            # The questions list may be under 'questions'
            if isinstance(data.get("questions"), list):
                records = data["questions"]
            else:
                records = [data]
        elif isinstance(data, list):
            records = data
        else:
            continue
        for item in records:
            if not isinstance(item, dict):
                continue
            qid = str(item.get("id", "")).strip()
            if not qid:
                continue
            meta = item.get("metadata") or {}
            # ensure top-level 'url' field
            if meta.get("url") and not item.get("url"):
                item["url"] = meta["url"]
            # ensure a combined `content` field exists for the site to display
            question_text = item.get("question", "")
            answer_text = item.get("answer", "")
            combined_content = (question_text + "\n\n" + answer_text).strip()
            # Only set content if missing or empty
            if not item.get("content") and combined_content:
                item["content"] = combined_content
            existing_map[qid] = item
            key = (rel, qid)
            if key not in existing_keys:
                entry = to_responsa_entry(item, rel)
                new_entries.append(entry)
                existing_keys.add(key)
    # Append new responsa entries
    if new_entries:
        responsa.extend(new_entries)
    # Group all questions by year and write per-year JSON files
    groups = {}
    for q in existing_map.values():
        meta = q.get("metadata") or {}
        year = extract_year(meta.get("date"))
        groups.setdefault(year, []).append(q)
    for year, items in groups.items():
        save_json(os.path.join(QA_DB_DIR, f"{year}.json"), {"questions": items})
    # Save updated responsa
    save_json(RESPONSA_PATH, responsa)


if __name__ == "__main__":
    main()
