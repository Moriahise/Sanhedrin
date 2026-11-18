"""Refresh published weekly sheets, optionally measure search demand, and notify IndexNow."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from lxml import html

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sanhedrin.visibility import BASE, LANGS, check_record, render

CONFIG = ROOT / "visibility"
SHIURIM = "https://moriahise.github.io/Shiurim/"
MAX_READ = 5_000_000


def request(url, data=None, headers=None, method=None):
    headers = {"User-Agent": "Shekhina-visibility/1.0", **(headers or {})}
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=25) as response:
        body = response.read(MAX_READ+1)
        if len(body) > MAX_READ:
            raise ValueError(f"Response exceeds limit for {urlsplit(url).hostname}")
        return body


def read_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, obj):
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)+"\n"
    if path.exists() and path.read_text() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        f.write(data)
    Path(f.name).replace(path)


def text_at(node, xpath):
    matches = node.xpath(xpath)
    if not matches:
        raise ValueError("Upstream bilingual component missing: "+xpath)
    return " ".join(matches[0].text_content().split())


def fetch_feature():
    home = html.fromstring(request(SHIURIM).decode("utf-8"))
    hrefs = home.xpath('//section[contains(concat(" ",@class," ")," hero ")]//a[contains(@href,"shiur/")]/@href')
    if not hrefs:
        raise ValueError("No published featured shiur")
    url = urljoin(SHIURIM, hrefs[0])
    match = re.fullmatch(re.escape(SHIURIM)+r"shiur/([a-z0-9]+(?:-[a-z0-9]+)*)/", url)
    if not match:
        raise ValueError("Unexpected featured address")
    slug = match[1]
    doc = html.fromstring(request(url).decode("utf-8"))
    row = {"sources":[]}
    for block in doc.xpath('//*[contains(concat(" ",@class," ")," source-heading ")]')[:3]:
        href = block.xpath("a/@href")
        if href and urlsplit(href[0]).netloc in ("www.sefaria.org","www.sefaria.org.il"):
            row["sources"].append({"url": href[0], **{s:text_at(block,f'h3//*[@lang="{s}"]') for s in LANGS}})
    if not row["sources"]:
        raise ValueError("No verifiable primary source")
    row["sources"].append({"url":url,"en":"Full weekly study at Shiurim","he":"השיעור המלא באתר שיעורים"})
    for lang in LANGS:
        questions=doc.xpath(f'//section[@class="discussion"]//li/*[@lang="{lang}"]')
        row[lang] = {"title":text_at(doc,f'//p[@class="lesson-subtitle"]/*[@lang="{lang}"]'),
                     "question":text_at(doc,f'//div[@class="guiding-question"]/p[@lang="{lang}"]'),
                     "body":text_at(doc,f'//div[@class="paragraph-pair"]/p[@lang="{lang}"]'),
                     "questions":[" ".join(q.text_content().split()) for q in questions[:3]]}
    return slug,row


def refresh():
    path=CONFIG/"weekly.json"
    rows=read_json(path,{})
    slug,row=fetch_feature()
    match=re.search(r"(\d{4}-\d\d-\d\d)$",slug)
    row["date"]=dt.date.fromisoformat(match[1]).isoformat() if match else rows.get(slug,{}).get("date",dt.date.today().isoformat())
    check_record(slug,row)
    rows[slug]=row
    # Generate the entire candidate before touching the working selection.
    with tempfile.TemporaryDirectory() as tmp:
        stage=Path(tmp)
        for name in ("sheets.json","indexnow-key.txt","priority.json"):
            if (CONFIG/name).exists(): (stage/name).write_bytes((CONFIG/name).read_bytes())
        save(stage/"weekly.json",rows)
        files=render(stage)
        if sum(map(len,files.values()))>2_000_000:
            raise ValueError("Candidate exceeds allocation; retain previous release")
    save(path,rows)
    print("Verified published study:",slug)


def notify():
    key=(CONFIG/"indexnow-key.txt").read_text().strip()
    desired=json.loads(render(CONFIG)["learn/revision.json"])
    live=json.loads(request(BASE+"/learn/revision.json"))
    if live!=desired:
        print("Waiting for the public release. Retry on the next run.")
        return
    if request(BASE+"/"+key+".txt").decode().strip()!=key:
        raise ValueError("Live IndexNow key mismatch")
    receipt=CONFIG/"state/indexnow.json"
    previous=read_json(receipt,{})
    if not isinstance(previous,dict):raise ValueError("Invalid notification ledger")
    changed={p for p in set(previous)|set(live) if previous.get(p)!=live.get(p)}
    # Inspect the actual deployed bytes, including top-level entry points.
    for path in ("/","/about-the-name.html"):
        live[path]=hashlib.sha256(request(BASE+path)).hexdigest()
        if previous.get(path)==live[path]:changed.discard(path)
        else:changed.add(path)
    if not changed:
        print("IndexNow: no changes")
        return
    for path in changed & desired.keys():
        if hashlib.sha256(request(BASE+path)).hexdigest()!=desired[path]:
            raise ValueError("Public page differs from the selected revision: "+path)
    packet={"host":"shekhina.org","key":key,"keyLocation":BASE+"/"+key+".txt","urlList":[BASE+p for p in sorted(changed)]}
    request("https://api.indexnow.org/indexnow",json.dumps(packet).encode(),{"Content-Type":"application/json"})
    save(receipt,live)
    print("IndexNow accepted the notification for",len(changed),"URLs")


def google():
    names=("GSC_CLIENT_ID","GSC_CLIENT_SECRET","GSC_REFRESH_TOKEN")
    if not all(os.getenv(n) for n in names):
        print("Google Search Console: verified property credentials unavailable; no measurements recorded.")
        return
    client,secret,refresh_token=(os.environ[n] for n in names)
    body=urlencode(dict(client_id=client,client_secret=secret,refresh_token=refresh_token,grant_type="refresh_token")).encode()
    token=json.loads(request("https://oauth2.googleapis.com/token",body))["access_token"]
    headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"}
    prop=quote(os.getenv("GSC_PROPERTY") or "sc-domain:shekhina.org",safe="")
    api="https://www.googleapis.com/webmasters/v3/sites/"+prop
    sitemap=BASE+"/sitemap.xml"
    entries=json.loads(request(api+"/sitemaps",headers=headers)).get("sitemap",[])
    if not any(r.get("path")==sitemap for r in entries):
        request(api+"/sitemaps/"+quote(sitemap,safe=""),headers=headers,method="PUT")
    end=dt.date.today()-dt.timedelta(days=3)
    payload={"startDate":str(end-dt.timedelta(days=27)),"endDate":str(end),"dimensions":["page"],"rowLimit":2000,
             "dimensionFilterGroups":[{"filters":[{"dimension":"page","operator":"contains","expression":"/learn/"}]}]}
    result=json.loads(request(api+"/searchAnalytics/query",json.dumps(payload).encode(),headers))
    fixed=read_json(CONFIG/"sheets.json",{})
    stats={}
    for row in result.get("rows",[]):
        url=row["keys"][0]
        for slug in fixed:
            if url in (BASE+"/learn/en/"+slug+"/",BASE+"/learn/he/"+slug+"/"):
                observed=stats.setdefault(slug,[0,0])
                observed[0]+=row["impressions"]
                observed[1]+=row["clicks"]
    # Require an equal opportunity to be measured and rank only evergreen sheets.
    order=[]
    if len(stats)==len(fixed) and all(i>=30 for i,c in stats.values()) and any(c for i,c in stats.values()):
        order=sorted(fixed,key=lambda k:(-(stats[k][1]+1)/(stats[k][0]+10),k))
    save(CONFIG/"priority.json",order)
    print("28-day Search Console sample:",len(result.get("rows",[])),"pages; evergreen priority:",order or "baseline")


def materialize():
    files=render(CONFIG)
    if sum(map(len,files.values()))>2_000_000:
        raise ValueError("Supplement exceeds allocation")
    destination=CONFIG/"published"
    with tempfile.TemporaryDirectory(dir=CONFIG) as temp:
        staged=Path(temp)/"next"
        for name,data in files.items():
            target=staged/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
        if destination.exists():
            destination.rename(Path(temp)/"previous")
        try:
            staged.rename(destination)
        except OSError:
            if (Path(temp)/"previous").exists():
                (Path(temp)/"previous").rename(destination)
            raise


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation",choices=("refresh","notify","google","check","materialize"))
    op=parser.parse_args().operation
    if op=="check":
        files=render(CONFIG)
        for name,body in files.items():
            if name.endswith(".xml"): ET.fromstring(body)
            if name.endswith(".html"):
                page=html.fromstring(body.decode())
                if not page.xpath('//main/h1/text()') or not page.xpath('//link[@rel="canonical"]/@href'):
                    raise ValueError(name)
        published=CONFIG/"published"
        actual={p.relative_to(published).as_posix():p.read_bytes() for p in published.rglob("*") if p.is_file()}
        if files!=actual: raise ValueError("Published snapshot is stale or incomplete")
        print("Verified",len(files),"files,",sum(map(len,files.values())),"bytes")
    else:
        {"refresh":refresh,"notify":notify,"google":google,"materialize":materialize}[op]()
