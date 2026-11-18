import datetime as dt
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from lxml import html
import observe
import run


class ObservationTests(unittest.TestCase):
    def test_reader_must_explicitly_confirm_and_duplicate_is_counted_once(self):
        files = run.render(run.CONFIG)
        for lang in run.LANGS:
            doc = html.fromstring(files[f"learn/{lang}/bet-el/index.html"].decode())
            url, = doc.xpath('//aside//a/@href')
            form = parse_qs(urlsplit(url).query)
            issue = {"number": 3, "created_at": "2026-11-18T00:00:00Z",
                     "title": form["title"][0], "body": form["body"][0]}
            confirmed = {**issue, "body": issue["body"].replace("[ ]", "[x]")}
            reports = [issue, confirmed, confirmed, {**confirmed, "number": 4, "pull_request": {}}]
            day = dt.date(2026, 11, 18)
            self.assertEqual(observe.session_reports(lambda url: json.dumps(reports), day, day, {"bet-el"}),
                             {"session_reports": 1, "repeat_session_reports": 1})

    def test_audit_checks_both_languages_and_detects_broken_canonical(self):
        files = run.render(run.CONFIG)
        files["learn/daf-related.json"] = b'{"bekhorot-61":[["example","Bekhorot 61","en",true]]}'
        channel = b'<a href="https://shekhina.org/learn/en/">EN</a><a href="https://shekhina.org/learn/he/">HE</a>'
        def read(url):
            if url in observe.CHANNELS.values():
                return channel
            path = url.removeprefix(run.BASE + "/")
            return files[path + "index.html" if path.endswith("/") else path]
        day = dt.date(2026, 11, 18)
        current = observe.audit(read, day)
        self.assertTrue(all(current["public_links"]["moriah"].values()))
        path = "learn/he/index.html"
        files[path] = files[path].replace(b'rel="canonical"', b'rel="broken"')
        with self.assertRaisesRegex(ValueError, "/learn/he/"):
            observe.audit(read, day)
