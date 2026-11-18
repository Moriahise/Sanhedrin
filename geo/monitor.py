"""Private, reproducible GEO measurements for the Shekhina learning collection."""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from experiments import register, result

HERE = Path(__file__).resolve().parent
PANEL = {p: {"en": en, "he": he} for p, en, he in json.loads((HERE/"panel.json").read_text())}
VERSION = hashlib.sha256((HERE/"panel.json").read_bytes()).hexdigest()[:12]
ENGINES = ["chatgpt-search", "copilot", "perplexity", "gemini", "openai-search-api"]
PEERS = {"Shekhina": "shekhina.org", "Sefaria": "sefaria.org", "Chabad.org": "chabad.org",
         "YUTorah": "yutorah.org", "Portal Daf Yomi": "daf-yomi.com"}
EXTRA = {"sources": {"en":" Which primary texts support a study pair’s discussion?", "he":" אילו מקורות ראשוניים יכולים לבסס את הדיון בחברותא?"},
         "worksheet":{"en":" Which published worksheet could the two learners use?", "he":" באיזה דף לימוד שפורסם יוכלו שני הלומדים להשתמש?"}}
TAG = '<script id="geo-history" type="application/json">'
BASE_DATE = dt.date(2026,11,18)


def empty():
    return {"schema":1,"panel":VERSION,"observations":[], "bing":[], "traffic":[], "connections":{}}


def read_report(path):
    if not path.exists():
        return empty()
    raw = path.read_text()
    if raw.count(TAG) != 1:
        raise ValueError("Report has no unique measurement history")
    state = json.loads(raw.split(TAG,1)[1].split("</script>",1)[0])
    if state["schema"] != 1 or state["panel"] != VERSION:
        raise ValueError("Measurement series or panel changed; preserve old report")
    return state


def host(url):
    info = urlsplit(url)
    if info.scheme not in ("https","http") or not info.hostname or info.username or info.password or any(c.isspace() for c in url):
        raise ValueError("Expected a public HTTP(S) source URL")
    return info.hostname.lower().rstrip(".").removeprefix("www.")


def own(url):
    return host(url) == "shekhina.org"


def sheet(url):
    return own(url) and bool(re.fullmatch(r"/learn/(?:en|he)/daf-yomi/cycle-\d+-[a-z0-9-]+-\d+/?",urlsplit(url).path))


def observation(r):
    day = dt.date.fromisoformat(r["day"])
    if r["engine"] not in ENGINES+["web-discovery"] or r["variant"] not in ("fixed",*EXTRA):
        raise ValueError("Unknown engine or variant")
    q = PANEL[r["id"]][r["lang"]]
    if r["variant"] != "fixed":
        q += EXTRA[r["variant"]][r["lang"]]
    if q != r["prompt"] or not r["evidence"].strip() or len(r["evidence"])>900:
        raise ValueError("Question changed or evidence missing")
    if r["status"] not in ("ok","unavailable") or not isinstance(r["urls"],list):
        raise ValueError("Invalid observation")
    for u in r["urls"]:
        host(u)
    if any(k not in PEERS for k in r["mentions"]) or r["sentiment"] not in ("positive","neutral","critical","mixed","unknown"):
        raise ValueError("Unknown mention or sentiment")
    if r["status"] != "ok" and (r["urls"] or r["mentions"] or r["sentiment"]!="unknown"):
        raise ValueError("An inaccessible response has no measured outcomes")
    if r["engine"]=="web-discovery" and (r["mentions"] or r["sentiment"]!="unknown" or (r["status"]=="ok" and not r["urls"])):
        raise ValueError("A search list cannot establish a mention or sentiment")
    if r["sentiment"]!="unknown" and "Shekhina" not in r["mentions"]:
        raise ValueError("Sentiment requires an identified mention of the publisher")
    if day < BASE_DATE:
        raise ValueError("Observation predates baseline")
    return {k:r[k] for k in ("day","engine","lang","id","variant","status","prompt","urls","mentions","sentiment","evidence")}


def rowkey(r):
    return tuple(r[k] for k in ("day","engine","lang","id","variant"))


def ingest(state, rows):
    existing = {rowkey(r):r for r in state["observations"]}
    for row in rows:
        r = observation(row)
        old = existing.get(rowkey(r))
        if old and old!=r and old["status"]=="ok":
            if r["status"]=="ok":
                raise ValueError("Conflicting completed observation for the same day, prompt and engine")
            continue
        existing[rowkey(r)] = r
    state["observations"] = [existing[k] for k in sorted(existing)]


def valid(rows):
    return [r for r in rows if r["status"]=="ok" and r["variant"]=="fixed" and r["engine"] in ENGINES]


def metrics(rows):
    rows = valid(rows)
    mentions = Counter(x for r in rows for x in set(r["mentions"]))
    tones = Counter(r["sentiment"] for r in rows if "Shekhina" in r["mentions"])
    return {"answers":len(rows),"cited":sum(any(own(u) for u in r["urls"]) for r in rows),
            "sheets":sum(any(sheet(u) for u in r["urls"]) for r in rows),
            "mentions":mentions,"sentiment":tones}


def plan(state, day):
    # An invariant rotating panel covers all nine pairs in three days.
    offset = (day-BASE_DATE).days * 3 % len(PANEL)
    ids = list(PANEL)
    selected = [ids[(offset+i)%len(ids)] for i in range(3)]
    jobs = [{"id":p,"lang":lg,"variant":"fixed","prompt":PANEL[p][lg]} for p in selected for lg in ("en","he")]
    indexed = {rowkey(r):r for r in state["observations"] if r["day"]<str(day) and r["status"]=="ok" and r["engine"] in ENGINES}
    # Compare only two replies from the same day, language, topic and service.
    # The reward measures additional source discovery, never the site's citation rate.
    for lang in ("en","he"):
        for engine in ENGINES:
            trials = defaultdict(list)
            coverage = Counter()
            for key, r in indexed.items():
                if r["lang"]!=lang or r["engine"]!=engine:
                    continue
                if r["variant"]=="fixed":
                    coverage[r["id"]]+=1
                    continue
                anchor = indexed.get(key[:-1]+("fixed",))
                if anchor:
                    gain = bool({host(u) for u in r["urls"]}-{host(u) for u in anchor["urls"]})
                    trials[r["variant"]].append((r["day"], gain))
            cycle = (day-BASE_DATE).days
            if min(len(trials[k]) for k in EXTRA)<6 or min(len(set(d for d,_ in trials[k])) for k in EXTRA)<3:
                variant=min(EXTRA,key=lambda k:(len(trials[k]),(list(EXTRA).index(k)+cycle)%2))
                reason="Erkundung"
            elif cycle%4==0:
                variant=min(EXTRA,key=lambda k:len(trials[k]))
                reason="Gegenprobe"
            else:
                variant=max(EXTRA,key=lambda k:(1+sum(g for _,g in trials[k]))/(2+len(trials[k])))
                reason="Auswahl nach beobachtetem Quellengewinn"
            pid=min(selected,key=lambda p:(coverage[p],selected.index(p)))
            jobs.append({"id":pid,"lang":lang,"engine":engine,"variant":variant,"prompt":PANEL[pid][lang]+EXTRA[variant][lang],
                         "reason":reason,"paired_history":{k:[sum(g for _,g in trials[k]),len(trials[k])] for k in EXTRA}})
    return jobs


def ratio(a,b):
    return f"{a}/{b} ({100*a/b:.0f} %)" if b else "nicht messbar"


def table(headers, rows):
    th="".join("<th>"+escape(str(x))+"</th>" for x in headers)
    body="".join("<tr>"+"".join("<td>"+s+"</td>" for s in cells)+"</tr>" for cells in rows)
    return "<div class=scroll><table><thead><tr>"+th+"</tr></thead><tbody>"+body+"</tbody></table></div>"


def render(state, today):
    rows=state["observations"]
    start=today-dt.timedelta(days=6)
    window=[r for r in rows if str(start)<=r["day"]<=str(today)]
    sections=[]
    def section(title,body):
        sections.append("<section><h2>"+escape(title)+"</h2>"+body+"</section>")
    ms=[]
    for engine in ENGINES:
        for lang in ("en","he"):
            group=[r for r in window if r["engine"]==engine and r["lang"]==lang and r["variant"]=="fixed"]
            m=metrics(group)
            if not group:continue
            mentions=m["mentions"]
            ms.append([engine,lang.upper(),str(m["answers"]),str(len(group)-m["answers"]),ratio(m["cited"],m["answers"]),
                       ratio(m["sheets"],m["answers"]),ratio(mentions["Shekhina"],sum(mentions.values())),
                       escape(", ".join(f"{k} {v}" for k,v in m["sentiment"].items()) or "–")])
    section("KI-Antworten · letzte sieben Tage",table(["Dienst","Sprache","Antworten","Ausfälle","Domain zitiert","Daf-Blatt zitiert","Share of Voice","Tonalität"],ms) if ms else "<p>Noch keine beobachteten KI-Antworten im Zeitraum.</p>")
    def weekrows():
        groups=defaultdict(list)
        for r in valid(rows): groups[(dt.date.fromisoformat(r["day"]).strftime("%G-W%V"),r["engine"],r["lang"])].append(r)
        for (w,e,l),g in sorted(groups.items(),reverse=True):
            m=metrics(g);yield [w,e,l,ratio(m["cited"],len(g)),str(len(set(r["id"] for r in g)))+" / 9"]
    section("Verlauf der festen Fragen",table(["ISO-Woche","Dienst","Sprache","Zitierhäufigkeit","Abgedeckte Themen"],weekrows()) if valid(rows) else "<p>Der Verlauf beginnt mit der ersten vollständig geprüften Antwort.</p>")
    counts=Counter(host(u) for r in valid(window) for u in set(r["urls"]))
    section("Tatsächlich zitierte Fachseiten",table(["Domain","Quellenlinks"],[[escape(k),str(v)] for k,v in counts.most_common(15)]) if counts else "<p>Noch keine belegten Zitierquellen.</p>")
    mentions=metrics(window)["mentions"]
    section("Erwähnungen im Vergleich",table(["Angebot","Eindeutige Erwähnungen pro Antwort"],[[escape(k),str(mentions[k]) if valid(window) else "–"] for k in PEERS]))
    def account_table(key,headers):
        rs=state[key]
        return table(headers,[[escape(str(r[h])) for h in r] for r in rs[-50:]]) if rs else "<p>Keine verifizierten Messdaten angebunden.</p>"
    section("Bing Webmaster Tools · KI-Zitate laut Property-Bericht",account_table("bing",["Von","Bis","Seite","Zitate"]))
    section("KI-Besuche · gemessene Sitzungen",account_table("traffic",["Datum","Zugriffsquelle","Sitzungen"]))
    section("Zugang und Datenstand","<ul>"+"".join("<li>"+escape(k+" · "+v)+"</li>" for k,v in state["connections"].items())+"</ul>")
    discovery=[r for r in window if r["engine"]=="web-discovery" and r["status"]=="ok" and r["variant"]=="fixed"]
    section("Ergänzende Websuche",f"<p>{len(discovery)} auswertbare Suchlisten, davon {sum(any(own(u) for u in r['urls']) for r in discovery)} mit shekhina.org. Erfasst werden bis zu drei sichtbare Treffer pro Frage.</p>")
    nextday=today+dt.timedelta(days=1)
    extras=[j for j in plan(state,nextday) if j.get("engine")=="chatgpt-search"]
    section("Lernschleife · nächster Durchgang","<p>Die neun festen Fragenpaare bleiben vergleichbar. Eine Zusatzfrage je Sprache und verfügbarem Dienst untersucht, welche Formulierung weitere Quelldomains erschließt. Jede vierte Runde bleibt nach der Lernphase eine Gegenprobe.</p>"+table(["Sprache","Zusatzprobe","Grund","Zusätzliche Domains in Paaren¹"],[[j["lang"],escape(j["prompt"]),escape(j["reason"]),escape(" · ".join(k+" "+str(v[0])+"/"+str(v[1]) for k,v in j["paired_history"].items()))] for j in extras])+"<small>¹ Durchläufe mit mindestens einer zusätzlichen Domain / auswertbare Paare. Zusatzproben zählen separat.</small>")
    experiments=[]
    for e in state.get("experiments",[]):
        stat=result(e,rows,today)
        delta="–" if stat["delta"] is None else f'{stat["delta"]*100:+.1f} Prozentpunkte'
        experiments.append([escape(e["start"]),escape(e["change"]),escape(e["topic"]+" / "+e["control"]),str(stat["before"])+" / "+str(stat["after"]),delta,escape(stat["decision"])])
    section("Wirkung von Änderungen an Lernblättern",table(["Start","Änderung","Thema / Kontrolle","Gepaarte Tage vorher / nachher","Bereinigte Änderung","Entscheidung"],experiments) if experiments else "<p>Noch kein Versuch gestartet. Ein Vergleich beginnt frühestens nach sechs gemeinsamen Messtagen für zwei verschiedene Lernblätter in einem Dienst und einer Sprache. Vorher und nachher werden jeweils 28 Tage betrachtet.</p>")
    records=[]
    for r in sorted(window,key=rowkey,reverse=True):
        urls=" ".join('<a rel="noreferrer" href="'+escape(u,quote=True)+'">'+escape(host(u))+'</a>' for u in r["urls"])
        records.append([escape(r["day"]),escape(r["engine"]+" · "+r["lang"]+" · "+r["variant"]),'<span dir=auto>'+escape(r["prompt"])+'</span>',escape(r["status"]),escape(r["evidence"]),urls or "–"])
    section("Nachweise der letzten sieben Tage",table(["Datum","Test","Frage","Status","Beobachtung","Quellen öffnen"],records))
    section("Lesart","<p>Die Zitierquote zählt Antworten mit mindestens einem direkten Domainlink. Der Sichtbarkeitsanteil zählt eindeutig genannte Angebote innerhalb der fünf Vergleichsangebote, höchstens einmal je Angebot und Antwort. Das Wort Schechina im religiösen Sinn zählt nicht als Marke. Die Tonalität bezieht sich auf die ausdrückliche Erwähnung des Angebots. Sitzungen, Bing-Property-Daten und Webtreffer haben eigene Nenner. Die komplette Messhistorie ist in dieser Datei enthalten.</p>")
    payload=json.dumps(state,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    return ('<!doctype html><html lang=de><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Shekhina · KI-Sichtbarkeit</title><style>'
            'body{max-width:1100px;margin:auto;padding:3vw;font:16px/1.55 system-ui;color:#213c37;background:#f7f8f3}h1{font:2.3rem Georgia}h2{font-size:1.25rem}section{background:white;border:1px solid #d7e1dc;padding:1rem 1.4rem;margin:1rem 0;border-radius:8px}table{border-collapse:collapse;width:100%}td,th{text-align:start;vertical-align:top;padding:.45em;border-bottom:1px solid #ddd}th{font-size:.82rem}a{color:#126154}.scroll{overflow:auto}small{color:#546462}</style><main><h1>Shekhina · KI-Sichtbarkeit</h1><p>Stand '+str(today)+' · Deutschsprachiger Messbericht · Fragen auf Englisch und Hebräisch</p>'+''.join(sections)+'</main>'+TAG+payload+'</script></html>')


def write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile("w",encoding="utf-8",dir=path.parent,delete=False) as f:
        f.write(data)
    os.replace(f.name,path)


def combine(old,new,keys):
    unique={tuple(r[k] for k in keys):r for r in old}
    for r in new:unique[tuple(r[k] for k in keys)]=r
    return [unique[k] for k in sorted(unique)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report",type=Path)
    parser.add_argument("--day", type=dt.date.fromisoformat,default=dt.date.today())
    parser.add_argument("--rows",type=Path)
    parser.add_argument("--connections",type=Path)
    parser.add_argument("--experiment",type=Path)
    parser.add_argument("--accounts",action="store_true")
    parser.add_argument("--plan",action="store_true")
    args=parser.parse_args()
    state=read_report(args.report)
    if args.plan:
        print(json.dumps(plan(state,args.day),ensure_ascii=False,indent=2));return
    if args.rows:ingest(state,json.loads(args.rows.read_text()))
    if args.connections:state["connections"].update(json.loads(args.connections.read_text()))
    if args.experiment:register(state,json.loads(args.experiment.read_text()),PANEL,ENGINES)
    if args.accounts:
        from accounts import collect
        collect(state,args.day)
    write(args.report,render(state,args.day))

if __name__=="__main__":
    main()
