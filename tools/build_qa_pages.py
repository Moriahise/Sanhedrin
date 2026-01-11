#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_QA_DIR = REPO_ROOT / "data" / "qa"
OUTPUT_QA_DIR = REPO_ROOT / "qa"
RESPONSA_JSON = REPO_ROOT / "responsa.json"

DEFAULT_CATEGORY = "other"
DEFAULT_CATEGORY_HE = "שאלות ותשובות"
DEFAULT_CATEGORY_EN = "Q&A"

def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\u0590-\u05FF\- ]+", "", text)  # keep hebrew + word chars
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text[:120] if text else "qa"

def safe_read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def safe_write_json(path: Path, obj):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def parse_year(date_str: str) -> int:
    # example: "2025-04-09T14:29:16Z"
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).year
    except Exception:
        return datetime.utcnow().year

def format_date_for_card(date_str: str) -> str:
    # frontend expects "dd/mm/yyyy" like existing responsa.json
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return datetime.utcnow().strftime("%d/%m/%Y")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <link rel="stylesheet" href="{css_path}">
  <style>
    .qa-wrap {{
      max-width: 1000px;
      margin: 0 auto;
      padding: 2rem 1rem 4rem;
    }}
    .qa-card {{
      background: rgba(26, 44, 66, 0.92);
      border: 2px solid var(--primary-gold);
      border-radius: 16px;
      padding: 2rem;
      box-shadow: 0 8px 25px rgba(0,0,0,0.35);
    }}
    .qa-title {{
      font-size: 1.8rem;
      color: var(--light-gold);
      margin-bottom: 1rem;
      font-weight: 700;
    }}
    .qa-meta {{
      color: var(--text-gold);
      margin-bottom: 1.5rem;
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      font-size: 0.95rem;
    }}
    .qa-section h2 {{
      color: var(--primary-gold);
      font-size: 1.25rem;
      margin: 1.6rem 0 0.6rem;
    }}
    .qa-text {{
      white-space: pre-wrap;
      line-height: 1.9;
      color: var(--text-light);
      font-size: 1.08rem;
    }}
    .qa-link a {{
      color: var(--primary-gold);
      font-weight: 700;
      text-decoration: none;
    }}
    .qa-link a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <header class="main-header">
    <div class="header-content">
      <div class="title-section">
        <h1 class="site-title">
          <span class="hebrew-title">בית דין גדול סנהדרין</span>
          <span class="english-title">Beit Din Gadol Sanhedrin</span>
        </h1>
        <p class="subtitle">
          <span class="hebrew-subtitle">ארכיון שאלות ותשובות</span>
          <span class="english-subtitle">Responsa Archive</span>
        </p>
      </div>
    </div>
  </header>

  <main class="qa-wrap">
    <div class="qa-card">
      <div class="qa-title">{title}</div>

      <div class="qa-meta">
        <span>📅 {date_card}</span>
        <span>👤 {author}</span>
        <span>🧑‍⚖️ {rabbi}</span>
        <span>👍 {upvotes}</span>
      </div>

      <div class="qa-section">
        <h2>שאלה</h2>
        <div class="qa-text">{question}</div>
      </div>

      <div class="qa-section">
        <h2>תשובה</h2>
        <div class="qa-text">{answer}</div>
      </div>

      <div class="qa-section qa-link">
        <h2>מקור</h2>
        <div class="qa-text"><a href="{source_url}" target="_blank" rel="noopener noreferrer">{source_url}</a></div>
      </div>
    </div>
  </main>
</body>
</html>
"""

def main():
    ensure_dir(DATA_QA_DIR)
    ensure_dir(OUTPUT_QA_DIR)

    # load existing responsa.json (list)
    if RESPONSA_JSON.exists():
        responsa = safe_read_json(RESPONSA_JSON)
        if not isinstance(responsa, list):
            raise SystemExit("responsa.json must be a JSON array")
    else:
        responsa = []

    # build an index of already imported QA ids to avoid duplicates
    seen_qa_ids = set()
    for item in responsa:
        if isinstance(item, dict) and "qa_id" in item:
            seen_qa_ids.add(str(item["qa_id"]))

    # find next number
    max_number = 0
    for item in responsa:
        try:
            max_number = max(max_number, int(item.get("number", 0)))
        except Exception:
            pass
    next_number = max_number + 1

    # collect qa json files
    qa_files = sorted(DATA_QA_DIR.glob("*.json"))
    if not qa_files:
        print("No QA files found in data/qa/")
        return

    added = 0

    for qa_path in qa_files:
        data = safe_read_json(qa_path)

        # expected structure: { "items": [ ... ] }
        items = data.get("items", [])
        if not isinstance(items, list):
            continue

        for qa in items:
            qa_id = str(qa.get("id", "")).strip()
            if not qa_id or qa_id in seen_qa_ids:
                continue

            title = (qa.get("title") or "").strip() or f"Q&A {qa_id}"
            question = (qa.get("question") or "").strip()
            answer = (qa.get("answer") or "").strip()
            source_url = (qa.get("url") or "").strip()

            md = qa.get("metadata") or {}
            author = (md.get("author") or "—").strip()
            rabbi = (md.get("rabbi") or "—").strip()
            upvotes = md.get("upvotes", 0)
            date_iso = (md.get("date") or "").strip()
            year = parse_year(date_iso) if date_iso else datetime.utcnow().year
            date_card = format_date_for_card(date_iso) if date_iso else datetime.utcnow().strftime("%d/%m/%Y")

            year_dir = OUTPUT_QA_DIR / str(year)
            ensure_dir(year_dir)

            slug = slugify(title)
            filename = f"{year}-{slug}.{qa_id}.html"
            out_path = year_dir / filename

            # css path from /qa/<year>/ to repo root styles.css
            css_path = "../../styles.css"

            html = HTML_TEMPLATE.format(
                title=escape_html(title),
                css_path=css_path,
                date_card=escape_html(date_card),
                author=escape_html(author),
                rabbi=escape_html(rabbi),
                upvotes=escape_html(str(upvotes)),
                question=escape_html(question),
                answer=escape_html(answer),
                source_url=escape_html(source_url),
            )

            out_path.write_text(html, encoding="utf-8")

            # add to responsa.json so existing UI shows it
            responsa.append({
                "number": next_number,
                "title_he": title,
                "title_en": title,  # optional: same for now
                "summary_he": (question[:180] + "…") if len(question) > 180 else question,
                "summary_en": (question[:180] + "…") if len(question) > 180 else question,
                "category": DEFAULT_CATEGORY,
                "category_he": DEFAULT_CATEGORY_HE,
                "category_en": DEFAULT_CATEGORY_EN,
                "date": date_card,
                "year": year,
                "file": f"qa/{year}/{filename}",
                "type": "html",
                "qa_id": qa_id,
                "source_url": source_url
            })

            seen_qa_ids.add(qa_id)
            next_number += 1
            added += 1

    # sort responsa by year desc then number desc (optional)
    responsa.sort(key=lambda x: (int(x.get("year", 0)), int(x.get("number", 0))), reverse=True)

    safe_write_json(RESPONSA_JSON, responsa)
    print(f"Added {added} new QA entries.")

def escape_html(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))

if __name__ == "__main__":
    main()
