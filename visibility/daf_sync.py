"""Extract bilingual study sheets only from the public Daf Yomi publication."""
import datetime as dt
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from lxml import html

DAF = "https://moriahise.github.io/Daf-Yomi/"
START = "2026-11-18"


def extract(markup, sources_markup):
    doc = html.fromstring(markup.decode("utf-8"))
    source_doc = html.fromstring(sources_markup.decode("utf-8"))
    source_urls = set(source_doc.xpath('//a/@href'))
    def lines(node, xpath):
        return [" ".join(el.text_content().split()) for el in node.xpath(xpath) if el.text_content().strip()]
    row = {"sources": []}
    for heading in doc.xpath('//div[@class="source-heading"]'):
        hrefs = heading.xpath('./a/@href')
        if not hrefs or hrefs[0] not in source_urls:
            continue
        url = urlsplit(hrefs[0])
        if url.scheme != "https" or url.netloc not in {"www.sefaria.org", "www.sefaria.org.il"} or not url.path.strip("/"):
            continue
        row["sources"].append({"url": hrefs[0], **{lang:lines(heading, f'h3//*[@lang="{lang}"]')[0] for lang in ("en", "he")}})
    if not row["sources"]:
        raise ValueError("No primary source shared by the edition and its source sheet")
    for lang in ("en", "he"):
        def first(selector):
            return lines(doc, selector + f'[@lang="{lang}"]')[0]
        row[lang] = {"question":first('//div[@class="guiding-question"]/p'),
                     "reading":first('//div[@class="paragraph-pair"]/p'),
                     "discuss":first('//section[@class="discussion"]//li/*')}
    return row


def refresh(entries, previous, revisions, get, today=None):
    """Prioritize today's daf and new approvals. Retain verified copies on partial failure."""
    today = today or dt.datetime.now(ZoneInfo("Asia/Jerusalem")).date()
    upcoming = (today + dt.timedelta(days=2)).isoformat()
    by_slug = {row[0]: day for day, row in entries.items()}
    if set(by_slug) != set(revisions) or not all(isinstance(v, str) and re.fullmatch("[0-9a-f]{64}", v) for v in revisions.values()):
        raise ValueError("Daf catalogue and revision list are from different releases")
    deferred = set(previous["baseline"])
    sheets = {s:v for s,v in previous["sheets"].items() if s in by_slug}
    due = [s for s,d in by_slug.items() if (s in sheets or s not in deferred or START <= d <= upcoming)
           and sheets.get(s, {}).get("revision") != revisions[s]]
    due.sort(key=lambda s:(not START <= by_slug[s] <= upcoming, abs((dt.date.fromisoformat(by_slug[s])-today).days), s))
    def fetch(slug):
        base = DAF + "shiur/" + slug + "/"
        try:
            lesson = get(base)
            sources = get(base+"sources/")
            original = re.sub(rb'<p class="chavruta-links">[^<]*(?:<a [^>]*>[^<]*</a>[^<]*){2}</p>(?=</main>)', b"", lesson)
            if hashlib.sha256(original + b"\0" + sources).hexdigest() != revisions[slug]:
                raise ValueError("Publication changed during retrieval")
            row = extract(lesson, sources)
            return slug, dict(row, revision=revisions[slug]), None
        except (OSError, ValueError, IndexError) as error:
            return slug, None, str(error)
    failures = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        for slug, row, error in pool.map(fetch, due[:64]):
            if row is None:
                failures.append((slug,error))
            else:
                sheets[slug] = row
    return {"baseline": sorted(deferred.intersection(by_slug)), "sheets":sheets}, failures
