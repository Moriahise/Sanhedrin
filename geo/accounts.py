"""Optional read-only imports. Keep account measurements in the private report."""
import csv
import datetime as dt
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from monitor import combine, host, own


def post(url, data, headers):
    with urlopen(Request(url,data=data,headers=headers),timeout=35) as response:
        return json.load(response)


def bing(path, period=None):
    data=path.read_text(encoding="utf-8-sig")
    dialect=csv.Sniffer().sniff(data[:8192],delimiters=",;\t")
    rows=csv.DictReader(data.splitlines(),dialect=dialect)
    # The cited-pages export may have only Page and Citations, with the period in the UI.
    parsed=[]
    for item in rows:
        row={k.strip().lower():str(v).strip() for k,v in item.items() if k}
        url=next((row[k] for k in ("url","page","page url","cited page","cited url","seite") if k in row),None)
        if not url or not own(url):raise ValueError("Expected cited pages for shekhina.org")
        amount=next((row[k] for k in ("citations","total citations","zitate","zitierungen") if k in row),None)
        if amount is None or not amount.isdecimal():raise ValueError("Expected integer citation count")
        start=row.get("start date") or row.get("date") or (period or ["",""])[0]
        end=row.get("end date") or row.get("date") or (period or ["",""])[1]
        if dt.date.fromisoformat(start)>dt.date.fromisoformat(end):raise ValueError("Bad Bing period")
        parsed.append({"from":start,"to":end,"url":url,"citations":int(amount)})
    if not parsed:raise ValueError("Empty export cannot establish a domain-wide zero")
    if len({(r["from"],r["to"],r["url"]) for r in parsed})!=len(parsed):raise ValueError("Ambiguous duplicate page in export")
    return parsed


def ga4(day):
    prop=os.environ["GEO_GA4_PROPERTY"]
    if not prop.isdecimal():raise ValueError("GA4 property must be numeric")
    token=os.getenv("GEO_GA4_ACCESS_TOKEN")
    if not token:
        form={"client_id":os.environ["GEO_GA4_CLIENT_ID"],"client_secret":os.environ["GEO_GA4_CLIENT_SECRET"],
              "refresh_token":os.environ["GEO_GA4_REFRESH_TOKEN"],"grant_type":"refresh_token"}
        token=post("https://oauth2.googleapis.com/token",urlencode(form).encode(),{"Content-Type":"application/x-www-form-urlencoded"})["access_token"]
    # Use completed property days and group sessions by initiating source. No visitor IDs.
    end=day-dt.timedelta(days=2)
    start=end-dt.timedelta(days=6)
    groups={"ChatGPT":["chatgpt.com","chat.openai.com","chatgpt"],
            "Perplexity":["perplexity.ai","www.perplexity.ai","perplexity"],
            "Gemini":["gemini.google.com","gemini"],"Copilot":["copilot.com","copilot.microsoft.com","copilot"]}
    sources={v:k for k,values in groups.items() for v in values}
    def criterion(name,values):
        return {"filter":{"fieldName":name,"inListFilter":{"values":values,"caseSensitive":False}}}
    body={"dateRanges":[{"startDate":str(start),"endDate":str(end)}],"dimensions":[{"name":"date"},{"name":"sessionSource"}],
          "metrics":[{"name":"sessions"}],"dimensionFilter":{"andGroup":{"expressions":[criterion("hostName",["shekhina.org","www.shekhina.org"]),criterion("sessionSource",list(sources))]}},"limit":"1000"}
    data=post("https://analyticsdata.googleapis.com/v1beta/properties/"+prop+":runReport",json.dumps(body).encode(),{"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    if data.get("metadata",{}).get("subjectToThresholding") or data.get("metadata",{}).get("dataLossFromOtherRow"):
        raise ValueError("Report subject to thresholding or data loss")
    if int(data.get("rowCount",0))!=len(data.get("rows",[])):raise ValueError("Partial GA4 result")
    counts={(str(start+dt.timedelta(days=i)),name):0 for i in range(7) for name in groups}
    for r in data.get("rows",[]):
        date,src=[v["value"] for v in r["dimensionValues"]]
        key=(str(dt.datetime.strptime(date,"%Y%m%d").date()),sources[src.lower()])
        n=int(r["metricValues"][0]["value"])
        if n<0:raise ValueError("Negative session count")
        counts[key]+=n
    return [{"day":d,"source":s,"sessions":n} for (d,s),n in counts.items()]


def collect(state,day):
    for name in ("Bing AI Performance","GA4"):
        try:
            if name=="GA4":
                if not os.getenv("GEO_GA4_PROPERTY"):continue
                rows=ga4(day);key="traffic";ids=("day","source")
            else:
                if not os.getenv("GEO_BING_CSV"):continue
                period=(os.getenv("GEO_BING_PERIOD") or "/").split("/")
                if len(period)!=2:raise ValueError("Expected FROM/TO")
                rows=bing(Path(os.environ["GEO_BING_CSV"]),period);key="bing";ids=("from","to","url")
            state[key]=combine(state[key],rows,ids)
            state["connections"][name]=f"Import am {day} · {len(rows)} belegte Zeilen"
        except (OSError,ValueError,KeyError) as err:
            state["connections"][name]=f"{day} · Abruf unvollständig ({type(err).__name__}); letzter verfügbarer Datenstand erhalten"
