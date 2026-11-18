"""Track a single reversible editorial change and an unchanged comparison sheet."""
import datetime as dt
import statistics
from urllib.parse import urlsplit


def page_key(url):
    p=urlsplit(url)
    return (p.hostname or "").lower().removeprefix("www."),p.path.rstrip("/")


def register(state, item, panel, engines):
    start=dt.date.fromisoformat(item["start"])
    if item["engine"] not in engines or item["lang"] not in {"en","he"}:
        raise ValueError("Unknown experiment channel")
    keys=list(panel)
    if item["topic"]==item["control"] or keys.index(item["topic"])//3!=keys.index(item["control"])//3:
        raise ValueError("Choose a distinct control from the same sampling group")
    for field in ("url","control_url"):
        if page_key(item[field])[0]!="shekhina.org" or not page_key(item[field])[1].startswith("/learn/"+item["lang"]+"/"):
            raise ValueError("Expected a same-language Shekhina learning page")
    if page_key(item["url"])==page_key(item["control_url"]) or not item["change"].strip() or not item["revision"].strip():
        raise ValueError("Need distinct sheets and a reversible revision")
    experiments=state.setdefault("experiments",[])
    if item in experiments:return
    if any(abs((start-dt.date.fromisoformat(e["start"])).days)<28 for e in experiments):
        raise ValueError("One change per observation window")
    if result(item,state["observations"],start)["before"]<6:
        raise ValueError("At least six paired baseline days required")
    experiments.append({k:item[k] for k in ("start","engine","lang","topic","control","url","control_url","change","revision")})


def result(item, rows, today):
    start=dt.date.fromisoformat(item["start"])
    paired={}
    for r in rows:
        if r["engine"]!=item["engine"] or r["lang"]!=item["lang"] or r["status"]!="ok" or r["variant"]!="fixed":continue
        d=dt.date.fromisoformat(r["day"])
        if d>today or not -28<=(d-start).days<28 or r["id"] not in (item["topic"],item["control"]):continue
        key="url" if r["id"]==item["topic"] else "control_url"
        paired.setdefault(d,{})[key]=int(any(page_key(u)==page_key(item[key]) for u in r["urls"]))
    before=[];after=[]
    for day, pair in paired.items():
        if len(pair)==2:(before if day<start else after).append(pair["url"]-pair["control_url"])
    delta=statistics.mean(after)-statistics.mean(before) if after and before else None
    decision="weiter messen"
    if today>=start+dt.timedelta(days=27):
        if min(len(before),len(after))<6:decision="unzureichende Abdeckung"
        elif delta>=0.25:decision="positives Signal · in Folgerunde wiederholen"
        elif delta<=-0.25:decision="negatives Signal · Rücknahme prüfen"
        else:decision="kein klares Signal"
    return dict(before=len(before),after=len(after),delta=delta,decision=decision)
