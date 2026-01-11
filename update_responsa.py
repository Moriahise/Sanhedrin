#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility script to automatically update the ``responsa.json`` file based on
the HTML and PDF documents located under the ``responsa`` directory.  When
new files are added to a year subdirectory (e.g. ``responsa/2025``), this
script scans the folder structure, extracts minimal metadata from each
document and appends entries for unknown files to the JSON archive.  It
avoids duplicating existing entries by checking the ``file`` field.

Key points:

* Supported document types are HTML/HTM and PDF.  Unknown file types are
  ignored.
* Titles are ALWAYS taken from the filename (without extension).
* Summaries are generated from the first roughly 50 words of the document's
  text when possible.  If BeautifulSoup (from the ``bs4`` package) is
  unavailable or parsing fails, summaries default to an empty string.
* Categories default to ``other`` with multilingual labels (``אחר`` and
  ``Other``).  You can adjust this logic as needed.
* Dates are based on the file's last modification time on disk and are
  formatted as ``dd/mm/YYYY``.  The year field is extracted from this date.
* Entry numbers are assigned sequentially starting from the largest number
  present in the existing JSON.  New entries increment this counter.

Usage:

    python3 update_responsa.py

Run this script from the project root (the directory containing
``responsa.json``).  It will update ``responsa.json`` in place and report
how many new entries were added.  If the ``responsa`` directory does not
exist, the script exits silently.
"""

import os
import json
import datetime
import sys
from pathlib import Path
from typing import Tuple, Dict, List

# Attempt to import BeautifulSoup for extracting summaries from HTML.
# If unavailable, summaries will be left empty.
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


def extract_summary_from_html(path: Path) -> str:
    """Extract a summary (first ~50 words) from an HTML file.
    
    Returns empty string if BeautifulSoup is unavailable or parsing fails.
    """
    summary = ""
    
    if BeautifulSoup is None:
        return summary
    
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove scripts, styles, and other non-content tags
        for tag in soup(["script", "style", "meta", "link", "head"]):
            tag.decompose()
        
        # Extract text
        text = soup.get_text(separator=" ", strip=True)
        words = text.split()
        
        if words:
            summary = " ".join(words[:50])
            if len(words) > 50:
                summary += "..."
    
    except Exception:
        # In case of any parsing error, return empty summary
        summary = ""
    
    return summary


def extract_metadata(path: Path) -> Dict:
    """Build a metadata dictionary for a given document file.

    The title is ALWAYS the filename (without extension).
    For HTML files, a summary is extracted from the text.
    For PDFs, the summary is left empty.
    The date and year are derived from the file's modification time.
    """
    ext = path.suffix.lower()
    file_type = "html" if ext in {".html", ".htm"} else "pdf"
    
    # ALWAYS use filename (without extension) as title
    title = path.stem
    
    # Use modification time for date
    mtime = path.stat().st_mtime
    dt = datetime.datetime.fromtimestamp(mtime)
    date_str = dt.strftime("%d/%m/%Y")
    year = dt.year
    
    # Extract summary only for HTML files
    if file_type == "html":
        summary = extract_summary_from_html(path)
    else:
        summary = ""
    
    # Assemble entry
    entry = {
        "title_he": title,
        "title_en": title,
        "summary_he": summary,
        "summary_en": summary,
        "category": "other",
        "category_he": "אחר",
        "category_en": "Other",
        "date": date_str,
        "year": year,
        "file": str(path.as_posix()),
        "type": file_type,
    }
    return entry


def main() -> int:
    print("🔄 Starting responsa.json update...")
    print("=" * 60)
    
    # Determine project root based on this script's location
    root = Path(__file__).resolve().parent
    responsa_dir = root / "responsa"
    json_path = root / "responsa.json"
    
    # Bail out if there is no responsa directory
    if not responsa_dir.is_dir():
        print("❌ No 'responsa' directory found. Nothing to update.")
        return 0
    
    # Load existing JSON data
    existing_data: List[Dict] = []
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"✓ Loaded {len(existing_data)} existing entries")
        except Exception as e:
            # If JSON is malformed, start with an empty list
            print(f"⚠️  Error loading JSON: {e}")
            print("  Starting with empty list...")
            existing_data = []
    else:
        print("✓ No existing responsa.json, will create new one")
    
    # Build a mapping of known files to their entries for quick lookup
    existing_map = {entry.get("file"): entry for entry in existing_data if isinstance(entry, dict)}
    
    # Determine the next available number
    existing_numbers = [entry.get("number", 0) for entry in existing_data if isinstance(entry.get("number"), int)]
    next_number = max(existing_numbers, default=0) + 1
    
    new_entries: List[Dict] = []
    
    print(f"\n🔍 Scanning for HTML/PDF files in {responsa_dir}...")
    print("-" * 60)
    
    # Walk through the responsa directory
    for file_path in sorted(responsa_dir.rglob("*")):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in {".html", ".htm", ".pdf"}:
            continue
        rel_path = file_path.relative_to(root).as_posix()
        
        if rel_path in existing_map:
            continue  # skip files already present in the JSON
        
        # Extract metadata and assign a new number
        metadata = extract_metadata(file_path)
        # Override the file field with a POSIX-style relative path
        metadata["file"] = rel_path
        metadata["number"] = next_number
        next_number += 1
        
        new_entries.append(metadata)
        
        # Show what was found
        print(f"  ✓ {file_path.name} → Title: {metadata['title_he']}")
    
    # If no new entries were found, report and exit
    print("\n" + "=" * 60)
    if not new_entries:
        print("✅ No new responsa found. 'responsa.json' is up to date.")
        return 0
    
    # Append and sort combined data by number
    updated_data = existing_data + new_entries
    updated_data.sort(key=lambda x: x.get("number", 0))
    
    # Write back to JSON file
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Added {len(new_entries)} new entr{'y' if len(new_entries) == 1 else 'ies'} to 'responsa.json'")
    print(f"📊 Total entries: {len(updated_data)}")
    print(f"💾 Saved to: {json_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
