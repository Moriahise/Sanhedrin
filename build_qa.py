#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Q&A pages/index from uploaded JSON files.

Behavior:
- Reads raw MiYodeya dumps from: miyodea/qa/*.json
- Produces normalized files into: data/qa/generated/<basename>.normalized.json
  Schema: {"questions":[{id,title,question,answer,metadata:{source,url,tags,score,views,date,answers}}]}
- Updates responsa.json (root) by appending entries for each question:
  - number: numeric part of id if available, else stable hash-based int
  - title_he/title_en: question title
  - summary_he/summary_en: short question excerpt
  - category: "other" (to avoid changing frontend filters)
  - file: qa.html?id=<id>&src=<normalized_path>
  - type: "html"

Run:
  python build_qa.py
"""

import json, re, hashlib
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser

REPO_ROOT = Path(__file__).resolve().parent

RAW_GLOBS = [
    REPO_ROOT / "miyodea" / "qa" / "*.json",
]

OUT_DIR = REPO_ROOT / "data" / "qa" / "generated"
RESPONSA_JSON = REPO_ROOT / "responsa.json"

class _Stripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, d):
        self.parts.append(d)
    def text(self):
        return "".join(self.parts)

def strip_html(s: str) -> str:
    st = _Stripper()
    st.feed(s or "")
    return st.text()

def extract_q_a(content: str):
    # MiYodeya export is a markdown-like string with "## Frage" and "## Antworten"
    q, a = "", ""
    parts = re.split(r"##\s*Frage", content or "", flags=re.IGNORECASE)
    if len(parts) > 1:
        after = parts[1]
        parts2 = re.split(r"##\s*Antworten", after, flags=re.IGNORECASE)
        q = parts2[0]
        rest = parts2[1] if len(parts2) > 1 else ""
        parts3 = re.split(r"\n###\s*", rest)
        if len(parts3) > 1:
            a = parts3[1]
        else:
            a = rest
    else:
        q = content or ""

    q_txt = re.sub(r"\n{3,}", "\n\n", strip_html(q)).strip()
    a_txt = re.sub(r"\n{3,}", "\n\n", strip_html(a)).strip()
    # drop leading "Antwort X ..." header
    a_txt = re.sub(r"^\s*(✅\s*)?Antwort\s*\d+.*?\n+", "", a_txt, flags=re.IGNORECASE).strip()
    return q_txt, a_txt

def stable_int(s: str) -> int:
    # 8 hex chars -> int
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]
    return int(h, 16)

def parse_year_date(iso_str: str):
    if not iso_str:
        return None, None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z",""))
        return dt.year, dt.strftime("%d/%m/%Y")
    except Exception:
        return None, None

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    normalized_files = []

    for pattern in RAW_GLOBS:
        for raw_path in sorted(raw_path for raw_path in pattern.parent.glob(pattern.name)):
            raw = load_json(raw_path)
            # raw may be list or object with 'questions'
            items = raw if isinstance(raw, list) else raw.get("questions", [])
            questions = []
            for it in items:
                q_txt, a_txt = extract_q_a(it.get("content",""))
                meta = it.get("metadata", {}) or {}
                questions.append({
                    "id": it.get("id") or it.get("qid") or it.get("question_id"),
                    "title": it.get("title") or "",
                    "question": q_txt,
                    "answer": a_txt,
                    "metadata": {
                        "source": meta.get("source") or "Mi Yodeya",
                        "url": meta.get("url") or it.get("url") or "",
                        "tags": meta.get("tags") or [],
                        "score": meta.get("score"),
                        "views": meta.get("views"),
                        "date": meta.get("date"),
                        "answers": meta.get("answers"),
                    }
                })

            out_path = OUT_DIR / f"{raw_path.stem}.normalized.json"
            out = {
                "source": "normalized",
                "generated_from": str(raw_path.as_posix()),
                "questions": questions,
            }
            out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            normalized_files.append(out_path)

    # Update responsa.json
    if RESPONSA_JSON.exists():
        responsa = load_json(RESPONSA_JSON)
        if not isinstance(responsa, list):
            raise SystemExit("responsa.json must be a JSON array")
    else:
        responsa = []

    # remove old auto Q&A entries (we mark them by category_en == 'Q&A' AND file starts with 'qa.html')
    responsa = [r for r in responsa if not (str(r.get("file","")).startswith("qa.html") and r.get("category_en") == "Q&A")]

    # append all questions
    for norm_path in normalized_files:
        norm = load_json(norm_path)
        for it in norm.get("questions", []):
            qid = str(it.get("id") or "")
            if not qid:
                continue
            # number: numeric part if present
            m = re.search(r"(\d+)$", qid)
            number = int(m.group(1)) if m else stable_int(qid) % 10000000

            meta = it.get("metadata", {}) or {}
            year, date_str = parse_year_date(meta.get("date"))
            if year is None:
                year = datetime.now().year
            if not date_str:
                date_str = datetime.now().strftime("%d/%m/%Y")

            title = it.get("title") or f"Q&A #{number}"
            question_excerpt = (it.get("question") or "").strip().replace("\n", " ")
            if len(question_excerpt) > 220:
                question_excerpt = question_excerpt[:217].rstrip() + "..."

            norm_rel = norm_path.relative_to(REPO_ROOT).as_posix()
            file_url = f"qa.html?id={qid}&src={norm_rel}"

            tags = meta.get("tags") or []
            tag_str = ", ".join(tags[:6]) if tags else ""

            responsa.append({
                "number": number,
                "title_he": title,
                "title_en": title,
                "summary_he": (question_excerpt + (f" | תגיות: {tag_str}" if tag_str else "")),
                "summary_en": (question_excerpt + (f" | Tags: {tag_str}" if tag_str else "")),
                "category": "other",
                "category_he": "שאלות ותשובות",
                "category_en": "Q&A",
                "date": date_str,
                "year": int(year),
                "file": file_url,
                "type": "html"
            })

    # stable sort: year desc then number asc
    responsa.sort(key=lambda r: (-int(r.get("year",0)), int(r.get("number",0))))

    RESPONSA_JSON.write_text(json.dumps(responsa, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: wrote {len(normalized_files)} normalized file(s) into {OUT_DIR}")
    print(f"OK: updated {RESPONSA_JSON} with {len(responsa)} total entries")

if __name__ == "__main__":
    main()
