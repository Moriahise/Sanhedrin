import json
import tempfile
import unittest
from pathlib import Path
from lxml import html
import run
from sanhedrin.daf_chavruta import DafMatches


class DafCollectionTests(unittest.TestCase):
    def test_match_excludes_unanswered_and_distinguishes_topic_from_citation(self):
        entries = {"2026-11-18":["cycle-14-bekhorot-61","Bekhorot 61","בכורות דף 61",
                                 "Bekhorot 61 — Exchange of tithe","תמורת מעשר"]}
        matcher = DafMatches(entries)
        card = {"id":"topic","language":"en","kind":"qa","has_evidence":True,"answers":1,
                "title":"How does the animal tithe work?","provider":"miyodeya"}
        answer = ["A sufficiently long saved answer for this test."]
        matcher.consider(card,"",answer)
        matcher.consider({**card,"id":"folio","title":"עניין אחר","language":"he"},"",["נושא אחר לגמרי עם מראה מקום מפורש בבכורות ס״א."])
        matcher.consider({**card,"id":"different","title":"Wrong folio"},"Bekhorot 62a",answer)
        matcher.consider({**card,"id":"codex","title":"A different text"},"Hilchot Bechorot 61:2",answer)
        matcher.consider({**card,"id":"no-answer"},"Bekhorot 61a",[""])
        result=matcher.top["bekhorot-61"]
        self.assertEqual([v[1] for v in result["en"]],["topic"])
        self.assertEqual(result["he"][0][:4],(22,"folio","Bekhorot 61",0))

    def test_collections_reachable_in_both_languages(self):
        public = run.render(run.CONFIG)
        for lang in run.LANGS:
            hub = html.fromstring(public[f"learn/{lang}/index.html"].decode())
            for target in ["https://moriahise.github.io/Zohar/",run.SHIURIM,f"/learn/{lang}/daf-yomi/"]:
                self.assertIn(target,hub.xpath('//a/@href'))
            self.assertIn(f"learn/{lang}/daf-yomi/index.html",public)
        self.assertIn("learn/index.html",public)
        self.assertIn("learn/daf-reader.js",public)
        self.assertEqual(json.loads(public["learn/daf-catalogue.json"]),run.read_json(run.CONFIG/"daf-catalogue.json",{}))
