"""Measure public technical availability; keep this series separate from citations."""
import concurrent.futures
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from xml.etree.ElementTree import fromstring

BASE="https://shekhina.org"


def fetch(path):
    for n in range(3):
        try:
            with urlopen(Request(BASE+path,headers={"User-Agent":"Shekhina-GEO-availability/1.0"}),timeout=20) as r:
                return r.read().decode()
        except (HTTPError,URLError,TimeoutError) as e:
            if n==2 or isinstance(e,HTTPError) and e.code not in (429,500,502,503,504):raise
            time.sleep(2**n)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonical=None;self.alts={};self.language=None;self.robots="";self.headings=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="link" and a.get("rel")=="canonical":self.canonical=a.get("href")
        if tag=="link" and a.get("rel")=="alternate" and "hreflang" in a:self.alts[a["hreflang"]]=a.get("href")
        if tag=="html":self.language=a.get("lang")
        if tag=="h1":self.headings+=1
        if tag=="meta" and a.get("name","").lower() in {"robots","oai-searchbot"}:self.robots+=" "+a.get("content","").lower()


def main():
    day=dt.date.today()
    robots=RobotFileParser();robots.parse(fetch("/robots.txt").splitlines())
    ids=sorted(json.loads(fetch("/learn/daf-sheets.json")))
    if not ids:raise ValueError("Public archive empty")
    sitemap={n.text for n in fromstring(fetch("/sitemap.xml")).iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
    sample=sorted({ids[day.toordinal()%len(ids)],"cycle-15-berakhot-6"})
    def check(pair):
        slug,lang=pair
        path=f"/learn/{lang}/daf-yomi/{slug}/"
        p=Page();p.feed(fetch(path));alt="en" if lang=="he" else "he"
        checks={"canonical":p.canonical==BASE+path,"sitemap":BASE+path in sitemap,"language":p.language==lang,
                "alternate":p.alts.get(alt)==BASE+path.replace("/"+lang+"/","/"+alt+"/"),
                "searchbot_allowed":robots.can_fetch("OAI-SearchBot",BASE+path),
                "indexable_meta":not any(x in p.robots.split() for x in ("noindex","none")) and "noindex" not in p.robots,"heading":p.headings==1}
        return {"path":path,"checks":checks}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pages=list(pool.map(check,[(s,l) for s in sample for l in ("en","he")]))
    summary={"day":str(day),"published_dafim":len(ids),"pages":pages}
    print("GEO_AVAILABILITY "+json.dumps(summary))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as f:
            f.write(f"## Öffentliche Lernblätter\n\n{len(ids)} Dafim im Archiv. Geprüft am {day}.\n\n")
            for p in pages:
                failed=[k for k,v in p["checks"].items() if not v]
                f.write("- "+BASE+p["path"]+" — "+(", ".join(failed) or "erreichbar und technisch geprüft")+"\n")
            f.write("\nDieser Test misst die Auslieferung. Zitierhäufigkeit und Besuche werden im privaten Messbericht ausgewertet.\n")
    if any(not all(p["checks"].values()) for p in pages):raise SystemExit(1)

if __name__=="__main__":main()
