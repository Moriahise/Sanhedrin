import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from lxml import html
from daf_sync import extract, refresh
import run
from sanhedrin.daf_sheets import write_sheets


class PermanentSheets(unittest.TestCase):
    def test_release_retry_and_source_change(self):
        slug = "cycle-15-berakhot-2"
        markup = b'''<main><div class="source-heading"><h3><i lang="en">2a</i><i lang="he">2a</i></h3><a href="https://www.sefaria.org/Berakhot_2a"></a></div>
<div class="guiding-question"><p lang="en">Q</p><p lang="he">H</p></div><div class="paragraph-pair"><p lang="en">A</p><p lang="he">B</p></div>
<section class="discussion"><li><i lang="en">D</i><i lang="he">E</i></li></section></main>'''
        source = b'<a href="https://www.sefaria.org/Berakhot_2a">2a</a>'
        rev = hashlib.sha256(markup+b"\0"+source).hexdigest()
        entries = {"2030-01-01":[slug]}
        old = {"baseline":[], "sheets":{}}
        def get(url):
            return source if url.endswith("sources/") else markup
        state, errors = refresh(entries,old,{slug:rev},get,dt.date(2026,11,18))
        self.assertFalse(errors)
        self.assertEqual(state["sheets"][slug]["en"]["question"],"Q")
        again, errors = refresh(entries,state,{slug:rev},lambda _: self.fail("refetched unchanged source"))
        self.assertEqual(again,state)
        retained, errors = refresh(entries,state,{slug:"1"*64},get)
        self.assertTrue(errors)
        self.assertEqual(retained,state)
        with self.assertRaises(ValueError):
            extract(markup,b"<main></main>")

    def test_pilot_has_two_static_sheets_sources_and_working_local_records(self):
        state = json.loads((run.CONFIG/"daf-sheets.json").read_text())
        pilot = {f"cycle-15-berakhot-{i}" for i in range(2,9)}
        self.assertTrue(pilot <= set(state["sheets"]))
        entries = {d:r for d,r in json.loads((run.CONFIG/"daf-catalogue.json").read_text()).items() if r[0] in pilot}
        self.assertEqual(len(entries),7)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out/"sitemap.xml").write_bytes(run.render(run.CONFIG)["sitemap.xml"])
            data = out/"release"
            mappings = {}
            for slug in pilot:
                key = slug.split("-",2)[2]
                pid = "test-"+key
                digest = hashlib.sha256(pid.encode()).hexdigest()
                file = data/"content"/digest[:2]/(digest+".json")
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(json.dumps({"id":pid,"kind":"qa","title":"A saved question","provider":"test","answers":[{"html":"An answer long enough to qualify as an archived responsum."}]}))
                mappings[key] = [[pid,key,"en",True,0,""]]
            write_sheets(run.ROOT,out,data,entries,mappings,str)
            self.assertEqual(set(json.loads((out/"learn/daf-sheets.json").read_text())),pilot)
            for slug in pilot:
                for lang in ("en","he"):
                    path = f"/learn/{lang}/daf-yomi/{slug}/"
                    doc = html.fromstring((out/path[1:]/"index.html").read_text())
                    self.assertEqual(doc.get("lang"),lang)
                    self.assertEqual(doc.xpath('//link[@rel="canonical"]/@href'),[run.BASE+path])
                    self.assertIn(run.BASE+path,(out/"sitemap.xml").read_text())
                    self.assertTrue(doc.xpath('//main//blockquote/text()'))
                    self.assertTrue(doc.xpath('//a[starts-with(@href,"https://www.sefaria.org")]'))
                    self.assertTrue(doc.xpath('//a[starts-with(@href,"/qa.html?id=")]'))
