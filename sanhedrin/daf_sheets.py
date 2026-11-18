"""Publish printable bilingual Daf sheets alongside the existing interactive reader."""
import hashlib
import json
import re
from html import escape
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree as ET

from .visibility import BASE, LANGS, link, page, sheet_path

DAF = "https://moriahise.github.io/Daf-Yomi/shiur/"
ARCHIVE = "daf-yomi/archive"


def excerpt(text, anchor, size=280):
    text = " ".join(text.split())
    if len(text) <= size:
        return text
    at = text.casefold().find(anchor.casefold()) if anchor else -1
    start = max(0, at - size // 3)
    if start:
        start = text.rfind(" ", 0, start) + 1
    end = min(start + size, len(text))
    if end < len(text):
        boundary = text.rfind(" ", start, end)
        if boundary > start:
            end = boundary
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def library_section(hits, dataout, lang, plain):
    en = lang == "en"
    title = "From the library" if en else "מתוך הספרייה"
    sections = []
    for pid, reason, language, cited, idx, anchor in sorted(hits, key=lambda h:(not h[3], h[2] != lang)):
        key = hashlib.sha256(pid.encode()).hexdigest()
        record = json.loads((dataout / "content" / key[:2] / (key+".json")).read_text())
        if record["id"] != pid or record["kind"] != "qa":
            raise ValueError("Mismatched responsum: " + pid)
        answer = record["answers"][idx]
        body = plain(answer["html"])
        if len(body.strip()) < 25:
            continue
        url = "/qa.html?id=" + quote(pid, safe="")
        label = ("Cites this daf" if en else "מראה מקום לדף") if cited else ("Related topic" if en else "נושא משותף")
        author = answer.get("author") or answer.get("owner") or ""
        if isinstance(author, dict):
            author = author.get("display_name") or author.get("name") or ""
        credit = " · ".join(str(v) for v in (author,record["provider"],answer.get("license") or record.get("license")) if v)
        original = record.get("url") or ""
        original_link = ""
        if urlsplit(original).scheme in ("http","https"):
            original_link = " · "+link(original,"Original source" if en else "המקור המקורי")
        sections.append('<article class="qa-entry"><small>'+escape(label+" · "+reason)+'</small><h3 dir="auto">'+
                        link(url,record["title"])+'</h3><blockquote dir="auto">'+escape(excerpt(body,anchor))+
                        '</blockquote><small dir="auto">'+escape(credit)+'</small><p>'+
                        link(url,"Full question and answer" if en else "השאלה והתשובה המלאות")+original_link+'</p></article>')
        break
    if not sections:
        sections.append("<p>"+("No related answered record has been identified yet." if en else "טרם נמצאה בספרייה תשובה הקשורה לדף זה.")+"</p>")
    return "<section><h2>"+title+"</h2>"+"".join(sections)+"</section>"


def write_sheets(root, out, dataout, entries, matches, plain):
    source = root/"visibility/daf-sheets.json"
    if not source.is_file():
        return
    selected = json.loads(source.read_text())["sheets"]
    archive = {lang:[] for lang in LANGS}
    pages = []
    def write(lang, slug, title, desc, body):
        path = sheet_path(lang, slug)
        folder = out/path.lstrip("/")
        folder.mkdir(parents=True, exist_ok=True)
        (folder/"index.html").write_text(page(lang, slug, title, desc, body))
        pages.append(BASE+path)

    published = []
    for date, (slug, daf_en, daf_he, title_en, title_he) in sorted(entries.items()):
        if slug not in selected:
            continue
        if not re.fullmatch(r"cycle-\d+-[a-z0-9-]+-\d+",slug):
            raise ValueError("Invalid edition identifier")
        row = selected[slug]
        published.append(slug)
        for lang in LANGS:
            en = lang == "en"
            title = title_en if en else daf_he+" · "+title_he
            item = row[lang]
            path = "daf-yomi/"+slug
            sources = "".join("<li>"+link(s["url"],s[lang])+"</li>" for s in row["sources"])
            related = library_section(matches.get(slug.split("-",2)[2], []), dataout, lang, plain)
            body = ("<p>"+escape(daf_en if en else daf_he)+' · <time>'+escape(date)+'</time></p><h2>'+
                    escape(item["question"])+'</h2><p>'+escape(item["reading"])+'</p><h2>'+
                    ("Discuss together" if en else "שאלה לחברותא")+'</h2><p>'+escape(item["discuss"])+'</p><h2>'+
                    ("Read the sources" if en else "עיון במקורות")+'</h2><ul>'+sources+'</ul><p>'+
                    link(DAF+slug+"/","Full shiur" if en else "השיעור המלא")+" · "+
                    link(DAF+slug+"/sources/","Shiur source sheet" if en else "דף המקורות לשיעור")+"</p>"+related+
                    "<p>"+link(sheet_path(lang,ARCHIVE),"Chavruta archive" if en else "ארכיון דפי החברותא")+"</p>")
            write(lang,path,title,item["question"],body)
            archive[lang].append("<li>"+link(sheet_path(lang,path),title)+"</li>")
    for lang in LANGS:
        title = "Daf Yomi chavruta archive" if lang=="en" else "ארכיון חברותא לדף היומי"
        write(lang,ARCHIVE,title,title,"<ul>"+"".join(archive[lang])+"</ul>")
    (out/"learn/daf-sheets.json").write_text(json.dumps(sorted(published)))
    sitemap = out/"sitemap.xml"
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("",ns)
    xml = ET.parse(sitemap)
    for url in pages:
        ET.SubElement(ET.SubElement(xml.getroot(),f"{{{ns}}}url"),f"{{{ns}}}loc").text=url
    xml.write(sitemap, encoding="utf-8", xml_declaration=True)
