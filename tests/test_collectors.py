import gzip
import io
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch
from sanhedrin.store import Store
from sanhedrin.model import DataError, normalize
from sanhedrin.net import Client, Response, Deferred, FetchError, SafeRedirect
from sanhedrin.collectors import (
    StackExchange,
    WordPress,
    RSS,
    JSONFeed,
    yeshiva_page,
    wordpress_body,
    sync,
    xml_root,
    parsed_source,
)
from sanhedrin.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def response(value, headers=None):
    return Response(
        value if isinstance(value, bytes) else json.dumps(value).encode(),
        headers or {},
        "https://test.invalid",
    )


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []
        self.used = 0
        self.backoff = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        self.used += 1
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def validate(self, url):
        if not url.startswith("https://www.yeshiva.org.il/"):
            raise DataError("Rejected URL")

    def honor_backoff(self, seconds):
        self.backoff.append(seconds)


def api(items, more=False, quota=100, **extra):
    return response(
        {"items": items, "has_more": more, "quota_remaining": quota, **extra}
    )


def question(count=2):
    return {
        "question_id": 123,
        "title": "Shabbat",
        "body": "<p>Question</p>",
        "answer_count": count,
        "creation_date": 1700000000,
        "last_activity_date": 1700000100,
        "content_license": "CC BY-SA 4.0",
        "link": "https://judaism.stackexchange.com/questions/123",
        "owner": {"display_name": "Author"},
        "tags": ["shabbat"],
    }


def answer(native):
    return {
        "answer_id": native,
        "question_id": 123,
        "body": "<p>Answer " + str(native) + "</p>",
        "is_accepted": native == 2,
        "content_license": "CC BY-SA 4.0",
        "owner": {"display_name": "Writer"},
    }


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = Store(Path(self.tmp.name) / "state.sqlite")

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def test_all_native_answers_and_verified_acceptance(self):
        c = FakeClient([api([answer(1)], True), api([answer(2)])])
        a = StackExchange(self.s, c, {})
        a.apply([question()], "page", {"page": 2})
        q = self.s.get("my-123")
        self.assertEqual(len(q["answers"]), 2)
        self.assertTrue(q["answers"][1]["accepted_verified"])
        self.assertTrue(q["answers"][1]["accepted"])
        self.assertEqual(q["format"], "html")
        self.assertEqual(self.s.cursor("page"), {"page": 2})
        self.assertEqual(q["license"], "CC BY-SA 4.0")

    def test_answer_mismatch_does_not_advance(self):
        self.s.set_cursor("page", {"page": 1})
        a = StackExchange(self.s, FakeClient([api([answer(1)])]), {})
        with self.assertRaises(DataError):
            a.apply([question()], "page", {"page": 2})
        self.assertEqual(self.s.count(), 0)
        self.assertEqual(self.s.cursor("page"), {"page": 1})

    def test_partial_answer_pagination_preserves_page(self):
        a = StackExchange(
            self.s, FakeClient([api([answer(1)], True), Deferred("budget")]), {}
        )
        with self.assertRaises(Deferred):
            a.apply([question()], "page", 2)
        self.assertEqual(self.s.count(), 0)
        self.assertIsNone(self.s.cursor("page"))

    def test_data_and_cursor_rollback_on_write_failure(self):
        a = StackExchange(self.s, FakeClient([api([])]), {})
        with patch.object(
            self.s, "set_cursor", side_effect=RuntimeError("write failure")
        ):
            with self.assertRaises(RuntimeError):
                a.apply([question(0)], "page", 2)
        self.assertEqual(self.s.count(), 0)
        self.assertFalse(self.s.db.execute("SELECT * FROM source_state").fetchall())

    def test_api_quota_and_backoff(self):
        c = FakeClient([api([], quota=3, backoff=5)])
        a = StackExchange(self.s, c, {})
        with self.assertRaises(Deferred):
            a.api("questions")
        self.assertEqual(c.backoff, [5])

    def test_remote_missing_retains_existing_body(self):
        q = normalize(
            {
                "title": "Q",
                "question": "Old",
                "url": "https://judaism.stackexchange.com/questions/123",
            }
        )
        self.s.insert(q)
        a = StackExchange(self.s, FakeClient([]), {})
        a.apply([], requested=["123"])
        self.assertEqual(self.s.get(q["id"])["question"], "Old")
        self.assertEqual(
            self.s.db.execute("SELECT state FROM source_state").fetchone()[0],
            "remote_missing",
        )

    def test_wordpress_ignored_window_fails(self):
        self.s.set_cursor(
            "din:wordpress", {"min": 1700000000, "max": 1700001000, "page": 1}
        )
        c = FakeClient(
            [
                response(
                    [{"id": 1, "modified_gmt": "2020-01-01T00:00:00"}],
                    {"X-WP-Total": "1", "X-WP-TotalPages": "1"},
                )
            ]
        )
        a = WordPress(
            self.s,
            c,
            {"mode": "metadata", "endpoint": "https://din.org.il/wp-json/wp/v2/posts"},
            "din",
        )
        with self.assertRaises(DataError):
            a.run()
        self.assertEqual(self.s.count(), 0)
        self.assertEqual(self.s.cursor("din:wordpress")["page"], 1)

    def test_wordpress_repeat_page_fails_without_skipping(self):
        self.s.set_cursor(
            "din:wordpress", {"min": 1700000000, "max": 1700001000, "page": 1}
        )
        item = {
            "id": 1,
            "modified_gmt": "2023-11-14T22:15:00",
            "date_gmt": "2023-11-14T22:15:00",
            "link": "https://din.org.il/question-one/",
            "title": {"rendered": "One"},
        }
        r = response([item], {"X-WP-Total": "2", "X-WP-TotalPages": "2"})
        a = WordPress(
            self.s,
            FakeClient([r, r]),
            {"mode": "metadata", "endpoint": "https://din.org.il/wp-json/wp/v2/posts"},
            "din",
        )
        with self.assertRaises(DataError):
            a.run()
        self.assertEqual(self.s.count(), 1)
        self.assertEqual(self.s.cursor("din:wordpress")["page"], 2)

    def test_source_markers_fail_closed(self):
        for provider in ("din", "aish"):
            with self.assertRaises(DataError):
                wordpress_body("<div>Generic article text</div>", provider)
        q, a = wordpress_body("<p>שאלה: מתי?</p><p>תשובה: ביום שני</p>", "din")
        self.assertIn("מתי", q)
        self.assertIn("ביום שני", a[0]["text"])

    def test_rss_chabad_query_native_dedup_and_preserves_body(self):
        q = normalize(
            {
                "title": "Old title",
                "question": "Original text",
                "url": "https://www.chabad.org/library/article_cdo/aid/7516692/jewish/Old.htm",
            }
        )
        self.s.insert(q)
        xml = b"<rss><channel><item><title>New title</title><link>https://www.chabad.org/article.asp?aid=7516692</link><pubDate>Sun, 27 Sep 2026 12:00:00 -0500</pubDate><description>Summary not full text</description></item></channel></rss>"
        a = RSS(
            self.s,
            FakeClient([response(xml)]),
            {"endpoint": "https://www.chabad.org/tools/rss/magazine_rss.xml"},
            "chabad",
        )
        a.run()
        self.assertEqual(self.s.count(), 1)
        current = self.s.get(q["id"])
        self.assertEqual(current["question"], "Original text")
        self.assertEqual(current["title"], "New title")
        self.assertEqual(current["native_id"], "7516692")
        self.assertTrue(current["published_at"].startswith("2026-09-27"))

    def test_xml_entities_rejected(self):
        with self.assertRaises(DataError):
            xml_root(b'<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss/>')

    def test_utf16_xml_entities_rejected(self):
        with self.assertRaises(DataError):
            xml_root('<!DOCTYPE rss [<!ENTITY x "entity">]><rss/>'.encode("utf-16"))

    def test_jsonld_graph_and_fallback(self):
        body = b'<script type="application/ld+json">{"@graph":[{"@type":"QAPage","mainEntity":{"name":"Title","text":"Question","acceptedAnswer":{"text":"Answer"},"dateCreated":"2026-01-01"}}]}</script>'
        q = yeshiva_page(body, "https://www.yeshiva.org.il/ask/123", "full")
        self.assertEqual(q["title"], "Title")
        self.assertEqual(q["answers"][0]["text"], "Answer")
        self.assertNotIn("is_accepted", q["answers"][0])
        self.assertEqual(
            yeshiva_page(
                b'<h1>Fallback</h1><div id="questionText">Q</div><div id="answerText">A</div>',
                "https://www.yeshiva.org.il/ask/123",
                "full",
            )["title"],
            "Fallback",
        )

    def test_publisher_feed_resume_and_metadata_strips_bodies(self):
        base = "https://www.yeshiva.org.il/feed"
        item = {
            "title": "One",
            "question": "Do not import full text",
            "answers": [{"text": "Do not import"}],
            "url": "https://www.yeshiva.org.il/ask/1",
        }
        c = FakeClient(
            [
                response(
                    {
                        "schema": 1,
                        "items": [item],
                        "cursor": "one",
                        "next": base + "?page=2",
                    }
                ),
                Deferred("budget"),
            ]
        )
        a = JSONFeed(self.s, c, {"mode": "metadata", "endpoint": base}, "yeshiva")
        with self.assertRaises(Deferred):
            a.run()
        self.assertEqual(
            self.s.cursor("yeshiva:publisher_feed")["next"], base + "?page=2"
        )
        self.assertEqual(self.s.get("yeshiva-1")["question"], "")
        self.assertEqual(self.s.get("yeshiva-1")["answers"], [])
        c = FakeClient(
            [response({"schema": 1, "items": [], "cursor": "done", "next": None})]
        )
        JSONFeed(self.s, c, {"mode": "metadata", "endpoint": base}, "yeshiva").run()
        self.assertEqual(c.urls[0], base + "?page=2")

    def test_feed_off_host_next_rejected_before_commit(self):
        c = FakeClient(
            [
                response(
                    {
                        "schema": 1,
                        "items": [
                            {"title": "One", "url": "https://www.yeshiva.org.il/ask/1"}
                        ],
                        "cursor": "one",
                        "next": "https://evil.example/",
                    }
                )
            ]
        )
        with self.assertRaises(DataError):
            JSONFeed(
                self.s,
                c,
                {"mode": "metadata", "endpoint": "https://www.yeshiva.org.il/feed"},
                "yeshiva",
            ).run()
        self.assertEqual(self.s.count(), 0)

    def test_one_source_failure_does_not_stop_others(self):
        config = {
            "sources": {
                "chabad": {
                    "adapter": "rss",
                    "mode": "metadata",
                    "enabled": True,
                    "hosts": ["www.chabad.org"],
                    "endpoint": "https://www.chabad.org/feed",
                    "budget": 3,
                },
                "din": {"enabled": False},
            }
        }
        r = sync(
            self.s,
            config,
            client_factory=lambda *a, **k: FakeClient([FetchError("HTTP 403")]),
        )
        self.assertEqual(r["status"], "partial")
        self.assertEqual(r["sources"]["din"]["status"], "disabled")
        self.assertEqual(r["sources"]["chabad"]["status"], "error")
        self.assertEqual(
            self.s.db.execute("SELECT status FROM runs").fetchone()[0], "partial"
        )

    def test_source_url_must_belong_to_publisher(self):
        with self.assertRaises(DataError):
            parsed_source(
                {
                    "title": "Injected",
                    "url": "https://evil.example/123",
                    "kind": "link",
                },
                "yeshiva",
                "metadata",
            )

    def test_api_native_url_mismatch_rejected(self):
        raw = question(0)
        raw["link"] = "https://judaism.stackexchange.com/questions/456"
        with self.assertRaises(DataError):
            StackExchange(self.s, FakeClient([api([])]), {}).apply([raw], "page", 2)
        self.assertEqual(self.s.count(), 0)
        self.assertIsNone(self.s.cursor("page"))

    def test_only_miyodeya_collected_in_production_config(self):
        config = load_config(ROOT / "config/sources.json")
        enabled = {p for p, c in config["sources"].items() if c["enabled"]}
        self.assertEqual(enabled, {"miyodeya"})
        self.assertEqual(config["sources"]["miyodeya"]["mode"], "full")
        for provider in {"din", "aish", "chabad", "yeshiva"}:
            self.assertIn("Manual browser-extension imports", config["sources"][provider]["disabled_reason"])


class TransportTests(unittest.TestCase):
    def test_https_allowlist_and_request_budget(self):
        c = Client(["allowed.example"], budget=1)
        for u in [
            "http://allowed.example/",
            "https://allowed.example:444/",
            "https://user:secret@allowed.example/",
            "https://evil.example/",
        ]:
            with self.assertRaises(DataError):
                c.validate(u)
        c.consume()
        with self.assertRaises(Deferred):
            c.consume()

    def test_redirect_strips_auth_when_host_changes(self):
        c = Client(["one.example", "two.example"])
        request = urllib.request.Request(
            "https://one.example/", headers={"Authorization": "Bearer secret"}
        )
        redirect = SafeRedirect(c).redirect_request(
            request, None, 302, "", {}, "https://two.example/"
        )
        self.assertFalse(redirect.has_header("Authorization"))
        with self.assertRaises(DataError):
            SafeRedirect(c).redirect_request(
                request, None, 302, "", {}, "https://evil.example/"
            )

    def test_gzip_bomb_bounded(self):
        class Raw(io.BytesIO):
            headers = {"Content-Encoding": "gzip"}
            url = "https://allowed.example/"

        c = Client(["allowed.example"], max_bytes=1000, delay=0)
        with patch.object(
            c.opener, "open", return_value=Raw(gzip.compress(b"x" * 5000))
        ):
            with self.assertRaises(FetchError):
                c.get("https://allowed.example/")

    def test_429_retry_after_honored(self):
        error = urllib.error.HTTPError(
            "https://allowed.example/",
            429,
            "Too many",
            {"Retry-After": "5"},
            io.BytesIO(),
        )

        class Raw(io.BytesIO):
            headers = {}
            url = "https://allowed.example/"

        c = Client(["allowed.example"], delay=0)
        with patch.object(
            c.opener, "open", side_effect=[error, Raw(b"{}")]
        ), patch.object(c, "wait") as wait:
            c.get("https://allowed.example/")
            self.assertIn(unittest.mock.call(5), wait.call_args_list)

    def test_long_retry_deferred(self):
        error = urllib.error.HTTPError(
            "https://allowed.example/",
            429,
            "Too many",
            {"Retry-After": "3600"},
            io.BytesIO(),
        )
        c = Client(["allowed.example"], delay=0)
        with patch.object(c.opener, "open", side_effect=error):
            with self.assertRaises(Deferred):
                c.get("https://allowed.example/")
