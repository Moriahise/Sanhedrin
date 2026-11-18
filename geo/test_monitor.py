import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
import monitor as m
from accounts import bing
from experiments import result
from openai_probe import extract


def row(day="2026-11-18",id="berakhot6",engine="chatgpt-search",variant="fixed",urls=(),status="ok"):
    return dict(day=day,id=id,lang="en",engine=engine,variant=variant,
                prompt=m.PANEL[id]["en"]+(m.EXTRA[variant]["en"] if variant!="fixed" else ""),
                urls=list(urls),status=status,mentions=[],sentiment="unknown",evidence="Visible sources checked")


class MonitorTests(unittest.TestCase):
    def test_denominators_and_host_boundaries(self):
        url="https://shekhina.org/learn/en/daf-yomi/cycle-15-berakhot-6/"
        rows=[row(urls=[url,url]),row(id="daily",urls=["https://shekhina.org.example.org/"]),row(id="zohar",status="unavailable"),row(engine="web-discovery",urls=[url]),row(variant="sources",urls=[url])]
        s=m.empty();m.ingest(s,rows);m.ingest(s,rows)
        self.assertEqual(len(s["observations"]),5)
        k=m.metrics(s["observations"]);self.assertEqual((k["answers"],k["sheets"],k["cited"]),(2,1,1))
        with self.assertRaises(ValueError):m.ingest(s,[row(urls=["https://other.example/"])])
        with self.assertRaises(ValueError):m.observation(dict(row(),sentiment="critical"))
        with self.assertRaises(ValueError):m.observation(dict(row(),prompt="visit shekhina.org"))
    def test_rotation_learning_and_control(self):
        state=m.empty();day=m.BASE_DATE
        ids={j["prompt"] for i in range(3) for j in m.plan(state,day+dt.timedelta(days=i)) if j["variant"]=="fixed"}
        self.assertEqual(len(ids),18)
        for i in range(12):
            d=str(day+dt.timedelta(days=i));v="sources" if i%2==0 else "worksheet"
            m.ingest(state,[row(d),row(d,variant=v,urls=["https://www.sefaria.org/"] if v=="sources" else [])])
        j=next(j for j in m.plan(state,day+dt.timedelta(days=13)) if j.get("engine")=="chatgpt-search" and j["lang"]=="en")
        self.assertEqual(j["variant"],"sources");self.assertEqual(j["paired_history"]["sources"],[6,6])
    def test_only_emitted_api_annotations_count(self):
        data={"status":"completed","output":[{"type":"web_search_call","status":"completed","action":{"sources":[{"url":"https://shekhina.org"}]}},{"type":"message","content":[{"type":"output_text","text":"The Shekhinah in the text.","annotations":[]}]}]}
        self.assertEqual(extract(data),([],[]))
    def test_private_dashboard_roundtrip_and_import(self):
        st=m.empty();m.ingest(st,[dict(row(),evidence="</script><img>")])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"report.html";m.write(p,m.render(st,m.BASE_DATE))
            self.assertEqual(m.read_report(p),st);self.assertNotIn("</script><img>",p.read_text())
            p.write_text("URL,Citations\nhttps://shekhina.org/learn/,7\n")
            self.assertEqual(bing(p,["2026-11-01","2026-11-18"])[0]["citations"],7)
    def test_experiment_requires_measured_control(self):
        item={"start":"2026-12-01","engine":"chatgpt-search","lang":"en","topic":"berakhot6","control":"berakhot2","url":"https://shekhina.org/learn/en/a/","control_url":"https://shekhina.org/learn/en/b/"}
        rows=[row("2026-12-03",urls=[item["url"]])]
        self.assertEqual(result(item,rows,dt.date(2026,12,30))["after"],0)

if __name__=="__main__":unittest.main()
