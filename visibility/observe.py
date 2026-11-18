"""Check the public reading paths and preserve one technical observation per ISO week."""
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
import os
import re
from urllib.parse import urlencode, urljoin
from xml.etree import ElementTree as ET

from lxml import html
import run

CHANNELS = {"moriah": "https://moriahise.github.io/Moriah/", "shiurim": run.SHIURIM}
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def audit(fetch, observed_on):
    base = run.BASE
    revision = json.loads(fetch(base + "/learn/revision.json"))
    sitemap = {el.text for el in ET.fromstring(fetch(base + "/sitemap.xml")).iter(NS + "loc")}
    if not revision or not all(base + path in sitemap for path in revision):
        raise ValueError("Sitemap and current learning pages disagree")
    if f"Sitemap: {base}/sitemap.xml" not in fetch(base + "/robots.txt").decode():
        raise ValueError("robots.txt does not advertise the live sitemap")
    counts = {}
    leads = set()
    for lang in run.LANGS:
        hub = f"/learn/{lang}/"
        root = ET.fromstring(fetch(base + hub + "feed.xml"))
        items = [item.findtext("link") for item in root.findall("./channel/item")]
        if not items or any(not link or not link.startswith(base + hub) or link not in sitemap for link in items):
            raise ValueError(f"Invalid {lang} feed")
        counts[lang] = len(items)
        leads.add(items[0].removeprefix(base + hub))

    def verify(path):
        raw = fetch(base + path)
        page = html.fromstring(raw.decode("utf-8"))
        parts = path.split("/")
        lang = parts[2]
        alt = "en" if lang == "he" else "he"
        other_path = "/".join([*parts[:2], alt, *parts[3:]])
        if (hashlib.sha256(raw).hexdigest() != revision[path]
                or page.get("lang") != lang or page.get("dir") != ("rtl" if lang == "he" else "ltr")
                or page.xpath('//link[@rel="canonical"]/@href') != [base + path]
                or page.xpath('//link[@hreflang=$alt]/@href', alt=alt) != [base + other_path]
                or other_path not in revision or not page.xpath("//main/h1")):
            raise ValueError(f"Invalid published learning page: {path}")

    # Inspect both hubs and a rotating historical pair in addition to the latest sheet.
    hubs = [f"/learn/{lang}/" for lang in run.LANGS]
    slugs = sorted(p.removeprefix("/learn/en/") for p in revision if p.startswith("/learn/en/") and p != "/learn/en/")
    if not slugs:
        raise ValueError("No published study sheets")
    if len(leads) != 1:
        raise ValueError("The two language feeds lead with different studies")
    leads.add(slugs[observed_on.toordinal() % len(slugs)])
    sample = set(hubs + [h + slug for h in hubs for slug in leads])
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(verify, sorted(sample)))

    channels = {}
    for name, url in CHANNELS.items():
        doc = html.fromstring(fetch(url).decode("utf-8"))
        urls = {urljoin(url, href) for href in doc.xpath("//a/@href")}
        channels[name] = {lang: base + f"/learn/{lang}/" in urls for lang in run.LANGS}
    daf = {}
    if "/learn/en/daf-yomi/" in revision:
        editions = json.loads(fetch(base + "/learn/daf-catalogue.json"))
        matches = json.loads(fetch(base + "/learn/daf-related.json"))
        if not editions or not isinstance(matches,dict) or not matches:
            raise ValueError("Published daily chavruta data missing")
        row = editions.get(observed_on.isoformat())
        daf = {"daf_editions":len(editions), "daf_with_related_qa":len(matches),
               "observed_date_has_daf":bool(row)}
    return {**daf, "observed_on": observed_on.isoformat(), "learning_pages": len(revision),
            "sitemap_urls": len(sitemap), "feed_entries": counts, "public_links": channels}


def session_reports(fetch, start, end, slugs):
    """Count checked public self-reports in the date range. Never store account details."""
    seen = set()
    returning = 0
    for page in range(1, 11):
        params = urlencode({"state": "all", "sort": "created", "direction": "desc",
                            "since": start.isoformat() + "T00:00:00Z", "per_page": 100, "page": page})
        issues = json.loads(fetch("https://api.github.com/repos/Moriahise/Sanhedrin/issues?" + params))
        if not isinstance(issues, list):
            raise ValueError("Invalid response from the public feedback channel")
        for issue in issues:
            number = issue["number"]
            if "pull_request" in issue or number in seen or not (str(start) <= issue["created_at"][:10] <= str(end)):
                continue
            title = issue["title"]
            body = issue.get("body") or ""
            slug = title.removeprefix("[Chavruta] ")
            if title == slug or slug not in slugs or f"Sheet: {slug}" not in body.splitlines():
                continue
            if not re.search(r"(?mi)^- \[x\] [^\n]*<!-- studied -->\s*$", body):
                continue
            seen.add(number)
            if re.search(r"(?mi)^- \[x\] [^\n]*<!-- returning -->\s*$", body):
                returning += 1
        if len(issues) < 100 or issues[-1]["created_at"][:10] < str(start):
            return {"session_reports": len(seen), "repeat_session_reports": returning}
    raise ValueError("Feedback volume exceeded the bounded public sample")


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    result = audit(run.request, today)
    slugs = set(run.read_json(run.CONFIG / "weekly.json", {})) | set(run.read_json(run.CONFIG / "sheets.json", {}))
    start = today - dt.timedelta(days=today.weekday())
    def read_feedback(url):
        token = os.environ.get("GH_TOKEN")
        headers = {"Authorization": "Bearer "+token} if token else {}
        return run.request(url, headers=headers)
    result["voluntary_reports_week_to_date"] = session_reports(read_feedback, start, today, slugs)
    key = today.strftime("%G-W%V")
    output = run.CONFIG / "state/observations.json"
    history = run.read_json(output, {})
    last_sunday = start - dt.timedelta(days=1)
    previous_key = last_sunday.strftime("%G-W%V")
    previous = history.get(previous_key)
    if previous and "voluntary_reports_full_week" not in previous:
        previous["voluntary_reports_full_week"] = session_reports(
            run.request, start - dt.timedelta(days=7), last_sunday, slugs)
    history[key] = result
    run.save(output, {k: history[k] for k in sorted(history)[-53:]})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all(ok for channel in result["public_links"].values() for ok in channel.values()):
        raise SystemExit("An inbound link is missing from a published study channel.")


if __name__ == "__main__":
    main()
