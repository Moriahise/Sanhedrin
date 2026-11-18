"""Render the public learning supplement offline from versioned bilingual source records."""
import hashlib
import json
import re
from html import escape
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree as ET

BASE = "https://shekhina.org"
LANGS = ("he", "en")
COPY = {
    "en": ("Source sheets for chavruta study", "Read the sources", "Discuss together", "Responsa library", "Hebrew", "Printable source sheets with primary texts and questions for paired study.", "Shiurim · published weekly study", "Learning feed", "Study with a partner"),
    "he": ("דפי מקורות ללימוד בחברותא", "עיון במקורות", "שאלות לחברותא", "ספריית השו״ת", "English", "דפי מקורות להדפסה עם הפניות לטקסטים ושאלות ללימוד בחברותא.", "שיעורים · הלימוד השבועי שפורסם", "עדכונים ללימוד", "לימוד בחברותא"),
}
CSS = """*{box-sizing:border-box}html{background:#f7f6ee;color:#193b35;font:17px/1.65 system-ui,sans-serif}body{margin:auto;max-width:52rem;padding:1.3rem}nav{display:flex;gap:1rem;justify-content:space-between;flex-wrap:wrap;border-bottom:1px solid #acb5a7;padding-bottom:1rem}main{padding:1rem 0}h1,h2{font-family:Georgia,serif;line-height:1.22}h1{font-size:clamp(2rem,6vw,3.25rem)}a{color:#175949;text-underline-offset:.18em}li{margin:.65rem 0}section{margin-block:1.8rem}a:focus-visible{outline:3px solid #ab7132}footer{border-top:1px solid #acb5a7;padding-top:1rem}@media print{nav,footer,.feedback{display:none}html{background:white;color:black;font-size:11pt}body{max-width:none;padding:0}a{color:black}li{break-inside:avoid}}"""
CSS += """ .tracks{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,17rem),1fr));gap:1rem}.track,.daily-call{border-block-start:2px solid #a78952;padding-block:.6rem}.track{margin:0}.daily-call{background:#e8efe5;padding:1rem 1.25rem}.track h2,.daily-call h2{margin:.4rem 0}h3{line-height:1.35}.day-controls{display:flex;gap:.45rem;flex-wrap:wrap;margin:.4rem 0 1.2rem}.day-controls button,.day-controls input{background:#fffdf7;color:inherit;font:inherit;border:1px solid #8b9f91;border-radius:.3rem;padding:.35rem .6rem}.day-controls button{cursor:pointer}.day-controls :disabled{opacity:.5}.qa-entry{border-block-start:1px solid #acb5a7;padding-block:.8rem}.qa-entry h3{margin:.25rem 0}.qa-entry small{color:#435d4e}.qa-entry summary{cursor:pointer}.reader-fallback{margin-block:2rem}@media print{.day-controls,#dates,.reader-fallback{display:none}}"""
HOSTS = {"www.sefaria.org", "www.sefaria.org.il", "shekhina.org", "moriahise.github.io"}


def sheet_path(lang, slug=""):
    return f"/learn/{lang}/" + (slug + "/" if slug else "")


def link(url, label, **attrs):
    attributes = "".join(f' {key}="{escape(val, quote=True)}"' for key, val in attrs.items())
    return f'<a href="{escape(url, quote=True)}"{attributes}>{escape(label)}</a>'


def check_record(slug, row):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or len(slug) > 90:
        raise ValueError(f"Invalid study slug: {slug}")
    for lang in LANGS:
        fields = row[lang]
        for value in [fields["title"], fields["body"], fields["question"], *fields["questions"]]:
            if not isinstance(value, str) or not value.strip() or len(value) > 5000:
                raise ValueError(f"Incomplete {lang} content: {slug}")
        if not fields["questions"]:
            raise ValueError(f"No discussion questions: {slug}")
    if not row["sources"]:
        raise ValueError(f"No sources: {slug}")
    for source in row["sources"]:
        url = urlsplit(source["url"])
        if (url.scheme != "https" or url.netloc not in HOSTS or not url.path.strip("/")
                or not all(source[lang].strip() for lang in LANGS)):
            raise ValueError(f"Invalid source: {slug}")


def page(lang, slug, title, description, inner):
    other = "en" if lang == "he" else "he"
    labels = COPY[lang]
    path = sheet_path(lang, slug)
    alternates = "".join(f'<link rel="alternate" hreflang="{code}" href="{BASE}{sheet_path(code, slug)}">' for code in LANGS)
    head = (f'<title>{escape(title)} · Shekhina</title><meta name="description" content="{escape(description)}">'
            f'<link rel="canonical" href="{BASE}{path}">{alternates}<link rel="stylesheet" href="/learn/study.css">'
            f'<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(description)}">'
            f'<meta property="og:url" content="{BASE}{path}"><link rel="alternate" type="application/rss+xml" href="/learn/{lang}/feed.xml">')
    navigation = link("/", labels[3]) + link(sheet_path(other, slug), labels[4], lang=other, hreflang=other)
    foot = link(sheet_path(lang), labels[0]) + " · " + link(f"/learn/{lang}/feed.xml", labels[7])
    direction = "rtl" if lang == "he" else "ltr"
    return (f'<!doctype html><html lang="{lang}" dir="{direction}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">{head}</head>'
            f'<body><nav>{navigation}</nav><main><h1>{escape(title)}</h1>{inner}</main><footer>{foot}</footer></body></html>')


def feedback(lang, slug):
    if lang == "he":
        intro = "למדתם יחד? אפשר לדווח מרצון ב־GitHub. הדיווח ושם המשתמש יוצגו לציבור. סמנו x בתוך הסוגריים המרובעים ליד ההצהרה המתאימה. אין לציין שמות או פרטי קבוצה."
        action = "דיווח על לימוד בחברותא"
        first, repeat = "למדנו את הדף יחד.", "כבר למדנו יחד דף קודם מהסדרה."
    else:
        intro = "Studied this together? You can report a session on GitHub. The report and your username will be public. Mark each applicable box with an x. Please omit names and group details."
        action = "Report a study session"
        first, repeat = "We studied this sheet together.", "We previously studied another sheet in this series together."
    body = (f"Sheet: {slug}\nLanguage: {lang}\n\n"
            f"- [ ] {first} <!-- studied -->\n- [ ] {repeat} <!-- returning -->")
    url = "https://github.com/Moriahise/Sanhedrin/issues/new?" + urlencode(
        {"title": f"[Chavruta] {slug}", "body": body})
    return f'<aside class="feedback"><p>{escape(intro)} {link(url, action, rel="nofollow")}</p></aside>'


def xml(root):
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def collection_intro(lang, weekly):
    en = lang == "en"
    groups = [
        ("Torah shiur" if en else "שיעור תורה", "https://moriahise.github.io/Shiurim/", False),
        ("Zohar shiur" if en else "שיעור בזוהר", "https://moriahise.github.io/Zohar/", True),
    ]
    cards = []
    for title, source, zohar in groups:
        keys = [k for k in weekly if k.startswith("zohar-") == zohar]
        body = ""
        if keys:
            recent = max(keys, key=lambda k: weekly[k]["date"])
            item = weekly[recent][lang]
            body = "<h3>" + link(sheet_path(lang,recent),item["title"]) + "</h3><p>" + escape(item["question"]) + "</p>"
        cards.append('<section class="track"><h2>'+title+'</h2>'+body+link(source, "All shiurim" if en else "לכל השיעורים")+'</section>')
    return ('<section class="daily-call"><h2>'+link(sheet_path(lang,"daf-yomi"),"Daf Yomi chavruta collection" if en else "אוסף חברותא לדף היומי")+'</h2><p>'
            + ("Study the day’s daf with a partner, then explore related questions and answers from the Sanhedrin library." if en else "למדו את הדף היומי בחברותא ועיינו בשאלות ובתשובות הקשורות לסוגיה מתוך ספריית סנהדרין.")+'</p></section><div class="tracks">'
            +"".join(cards)+"</div>")


def daf_reader(lang):
    en = lang == "en"
    path = sheet_path(lang,"daf-yomi")
    title = "Daf Yomi chavruta" if en else "חברותא לדף היומי"
    desc = ("Study the daf with its sources, discussion questions and related responsa." if en else
            "לימוד הדף היומי עם מקורות, שאלות לחברותא ושאלות ותשובות מן הספרייה.")
    controls = ('<form id="dates"><label for="day">'+("Study date · Jerusalem" if en else "תאריך הלימוד · ירושלים")+'</label>'
                '<div class="day-controls"><button id="previous" type="button">'+("Previous daf" if en else "הדף הקודם")+'</button>'
                '<input id="day" type="date" required><button type="submit">'+("Open" if en else "פתיחה")+'</button>'
                '<button id="next" type="button">'+("Next daf" if en else "הדף הבא")+'</button>'
                '<button id="today" type="button">'+("Today" if en else "היום")+'</button></div></form>')
    inner = ('<p>'+desc+'</p>'+controls+'<div id="study" aria-live="polite"></div><p class="reader-fallback">'+
             link(path+"today.html","Printable daily edition" if en else "מהדורת היום להדפסה")+" · "+
             link("https://moriahise.github.io/Daf-Yomi/","Daf Yomi library" if en else "ספריית הדף היומי")+'</p>'
             '<script type="module" src="/learn/daf-reader.js"></script>')
    return page(lang,"daf-yomi",title,desc,inner)


def render(config):
    fixed = json.loads((config / "sheets.json").read_text())
    weekly = json.loads((config / "weekly.json").read_text())
    if fixed.keys() & weekly.keys():
        raise ValueError("Duplicate study URLs")
    rows = {**fixed, **weekly}
    for slug, row in rows.items():
        check_record(slug, row)
    preference = config / "priority.json"
    preferred = json.loads(preference.read_text()) if preference.exists() else []
    evergreen = list(dict.fromkeys([s for s in preferred if s in fixed] + list(fixed)))
    order = list(reversed(sorted(weekly, key=lambda k: (weekly[k]["date"], k)))) + evergreen
    result = {"learn/study.css": CSS.encode()}
    collection = (config / "daf-catalogue.json").is_file()
    if collection:
        result["learn/daf-catalogue.json"] = json.dumps(json.loads((config/"daf-catalogue.json").read_text()), ensure_ascii=False,separators=(",",":")).encode()
        result["learn/daf-reader.js"] = (config/"daf-reader.js").read_bytes()
        result["learn/index.html"] = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Chavruta · חברותא | Shekhina</title><link rel="canonical" href="https://shekhina.org/learn/"><link rel="stylesheet" href="study.css"></head><body><main>'
            '<h1>Chavruta · <bdi lang="he">חברותא</bdi></h1><p>Torah and Zohar shiurim · Daf Yomi with questions and answers</p><p lang="he" dir="rtl">שיעורי תורה וזוהר · הדף היומי עם שאלות ותשובות</p>'
            '<nav><a href="en/" lang="en">Study in English</a><a href="he/" lang="he" dir="rtl">לימוד בעברית</a></nav></main></body></html>').encode()
    urls = {"/", "/about-the-name.html"}
    for lang in LANGS:
        labels = COPY[lang]
        if collection:
            daily_path = sheet_path(lang,"daf-yomi")
            result[daily_path.lstrip("/")+"index.html"] = daf_reader(lang).encode()
            urls.update(("/learn/",daily_path))
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")
        for key, value in (("title", labels[0]+" · Shekhina"), ("link", BASE+sheet_path(lang)), ("description", labels[5]), ("language", lang)):
            ET.SubElement(channel, key).text = value
        index = []
        for slug in order:
            row = rows[slug]
            item = row[lang]
            sources = "".join("<li>"+link(s["url"], s[lang])+"</li>" for s in row["sources"])
            questions = "".join("<li>"+escape(q)+"</li>" for q in item["questions"])
            body = (f'<p><strong>{escape(item["question"])}</strong></p><p>{escape(item["body"])}</p>'
                    f'<section><h2>{labels[1]}</h2><ul>{sources}</ul></section>'
                    f'<section><h2>{labels[2]}</h2><ol>{questions}</ol></section>')
            path = sheet_path(lang, slug)
            urls.add(path)
            result[path.lstrip("/")+"index.html"] = page(lang, slug, item["title"], item["question"], body + feedback(lang, slug)).encode()
            index.append("<li>"+link(path, item["title"])+f'<br>{escape(item["question"])}</li>')
            if len(index) <= 20:
                entry = ET.SubElement(channel, "item")
                for key,val in (("title",item["title"]),("description",item["question"]),("link",BASE+path),("guid",BASE+path)):
                    ET.SubElement(entry,key).text=val
        path = sheet_path(lang)
        urls.add(path)
        result[path.lstrip("/")+"index.html"] = page(lang, "", labels[0], labels[5], f'<p>{labels[5]}</p>'+ (collection_intro(lang,weekly) if collection else "") + ('<h2>'+("Source sheet archive" if lang=="en" else "ארכיון דפי המקורות")+'</h2>') + f'<ul>{"".join(index)}</ul>' ).encode()
        result[path.lstrip("/")+"feed.xml"] = xml(rss)
    key = (config / "indexnow-key.txt").read_text().strip()
    if not re.fullmatch("[a-f0-9]{32}", key):
        raise ValueError("Invalid IndexNow key")
    result[key+".txt"] = key.encode()
    result["robots.txt"] = f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n".encode()
    sitemap = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in sorted(urls):
        ET.SubElement(ET.SubElement(sitemap,"url"),"loc").text=BASE+url
    result["sitemap.xml"] = xml(sitemap)
    # Public fingerprints let the independent notifier wait for the actual Pages rollout.
    fingerprints = {"/"+k[:-len("index.html")]: hashlib.sha256(v).hexdigest()
                    for k,v in result.items() if k.endswith("/index.html") and k!="learn/index.html"}
    result["learn/revision.json"] = json.dumps(fingerprints,sort_keys=True).encode()
    return result


def publish(root: Path, out: Path):
    config = root / "visibility"
    if not config.exists():  # Older library-only fixtures and checkouts.
        return
    # Only verified, committed bytes enter the library build. Source fetching and
    # ranking run independently; neither network outages nor drafts affect Pages.
    public = config / "published"
    files = {}
    for source in public.rglob("*"):
        if source.is_file():
            name = source.relative_to(public).as_posix()
            if not (name.startswith("learn/") or name in ("robots.txt", "sitemap.xml")
                    or re.fullmatch(r"[a-f0-9]{32}\.txt", name)):
                raise ValueError("Unexpected supplement file: "+name)
            files[name] = source.read_bytes()
    if sum(map(len, files.values())) > 2_000_000:
        raise ValueError("Study supplement exceeds its 2 MB allocation")
    for name, data in files.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as file:
            file.write(data)
