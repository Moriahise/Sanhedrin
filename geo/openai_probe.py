"""Explicitly opt-in API comparison channel, distinct from consumer ChatGPT Search."""
import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen
from monitor import ingest, plan, read_report, render, write


def extract(data):
    if data.get("status")!="completed" or not any(o.get("type")=="web_search_call" and o.get("status")=="completed" for o in data["output"]):
        raise ValueError("Web-grounded answer not completed")
    blocks=[c for o in data["output"] if o.get("type")=="message" for c in o.get("content",[]) if c.get("type")=="output_text"]
    if not blocks or not any(b["text"].strip() for b in blocks):raise ValueError("No readable answer")
    urls=list(dict.fromkeys(a["url"] for b in blocks for a in b.get("annotations",[]) if a.get("type")=="url_citation"))
    text=" ".join(b["text"] for b in blocks)
    # Count prose only. Markers and textual URLs must not turn a citation into a brand mention.
    prose=re.sub(r"【[^】]*】|.*?|\[([^\]]*)\]\(https?://[^)]*\)|https?://\S+",lambda m:m.group(1) or "",text)
    aliases={"Shekhina":r"\bshekhina\.org\b|Sanhedrin Responsa Library|ספריית השו[״\"׳']?ת סנהדרין",
             "Sefaria":r"\bsefaria\b|ספריא","Chabad.org":r"chabad\.org|חב[״\"]ד אורג",
             "YUTorah":r"\byu\s?torah\b","Portal Daf Yomi":r"Portal Daf Yomi|פורטל הדף היומי"}
    mentions=[k for k,pat in aliases.items() if re.search(pat,prose,re.I)]
    return urls,mentions


def main():
    p=argparse.ArgumentParser();p.add_argument("report",type=Path);p.add_argument("--day",type=dt.date.fromisoformat,default=dt.date.today());args=p.parse_args()
    if os.getenv("GEO_ALLOW_BILLABLE")!="yes":p.error("Requires explicit API-budget opt-in")
    key=os.environ["GEO_OPENAI_KEY"];model=os.environ["GEO_OPENAI_MODEL"]
    state=read_report(args.report)
    jobs=[j for j in plan(state,args.day) if j.get("engine","openai-search-api")=="openai-search-api"]
    for j in jobs:
        row={k:j[k] for k in ("id","lang","prompt","variant")}
        row.update(day=str(args.day),engine="openai-search-api",sentiment="unknown")
        if any(all(r[k]==row[k] for k in ("id","lang","day","engine","variant")) and r["status"]=="ok" for r in state["observations"]):continue
        data={"model":model,"input":j["prompt"],"tools":[{"type":"web_search"}],"tool_choice":"required","store":False,"max_tool_calls":1,"max_output_tokens":1500}
        try:
            req=Request("https://api.openai.com/v1/responses",data=json.dumps(data).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
            with urlopen(req,timeout=100) as response:result=json.load(response)
            urls,mentions=extract(result)
            row.update(status="ok",urls=urls,mentions=mentions,evidence=f"OpenAI Responses · {model} · {result['id']} · url_citation")
        except (OSError,ValueError,KeyError) as err:
            row.update(status="unavailable",urls=[],mentions=[],evidence=type(err).__name__)
        ingest(state,[row])
        write(args.report,render(state,args.day))
        if row["status"]=="unavailable":break

if __name__=="__main__":
    main()
