import copy
import io
import json
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from sanhedrin.model import normalize, DataError, digest
from sanhedrin.store import Store
from sanhedrin.teshuva import profiles, search_groups, evidence_text, compose, api_draft, render, validate_request, publish_assets, PORTRAIT_ROTATION_PATH
from tools.save_teshuva import save, atomic_save, parse_body, authorized, openai_access

ROOT = Path(__file__).resolve().parents[1]


def mock_response(draft, status="completed"):
    return io.BytesIO(json.dumps({"status": status, "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(draft)}]}]}).encode())


class FakeGitHub:
    def __init__(self):
        self.files = {}
        self.head = "old"
        self.tree = None
        self.conflict = False
        self.commits = 0
        self.concurrent_files = {}

    def content(self, path, ref="main"):
        return self.files.get(path)

    def request(self, method, path, value=None, optional=False):
        if path == "/git/ref/heads/main":
            return {"object": {"sha": self.head}}
        if path.startswith("/git/commits/"):
            return {"tree": {"sha": "tree-" + self.head}}
        if path == "/git/trees":
            self.tree = value
            return {"sha": "newtree"}
        if path == "/git/commits":
            self.commits += 1
            return {"sha": "commit-" + str(self.commits)}
        if path == "/git/refs/heads/main":
            if self.conflict:
                self.conflict = False
                self.head = "concurrent-commit"
                self.files["unrelated.txt"] = "preserved"
                self.files.update(self.concurrent_files)
                raise urllib.error.HTTPError("https://api.github.com/", 422, "Conflict", {}, None)
            self.head = value["sha"]
            self.files.update({e["path"]: e["content"] for e in self.tree["tree"]})
            return {"object": {"sha": self.head}}
        raise AssertionError((method, path))


class TeshuvaTests(unittest.TestCase):
    def setUp(self):
        self.rerank_patch = patch("sanhedrin.research.rerank_sources", side_effect=lambda question, sources, **kwargs: sources[:16])
        self.rerank_patch.start(); self.addCleanup(self.rerank_patch.stop)
        # Existing fixtures isolate drafting; research stages have separate regression tests.
        self.plan_patch = patch('sanhedrin.research.plan_question', return_value={'queries_en':['shabbat candles'],'queries_he':['שבת נרות'],'subquestions':['What do the sources say?']})
        self.review_patch = patch('sanhedrin.research.review_draft', return_value={'status':'ready','issues':[],'clarification_questions':[],'citation_audit_version':1})
        self.plan_patch.start();self.review_patch.start()
        self.addCleanup(self.plan_patch.stop);self.addCleanup(self.review_patch.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "config", self.root / "config")
        (self.root / "Rav").mkdir()
        (self.root / "Rav/Rav Test שם.png").write_bytes(b"image-fixture")
        self.store = Store(self.root / "db.sqlite")
        self.record = normalize({"id": "yeshiva-42", "title": "שבת candles", "question": "A question alone must not become an answer.",
            "answers": [{"text": "<p>Shabbat candles are discussed in this original saved source text.</p>"}], "url": "https://www.yeshiva.org.il/ask/42"})
        self.store.insert(self.record)
        self.request = {"schema": 1, "question_html": "<p>How are shabbat candles used?</p>", "keywords": "shabbat candles", "language": "en",
            "profile_id": profiles(self.root)[0]["id"], "use_openai": False, "source_ids": [self.record["id"]]}

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_bilingual_groups_strip_niqqud_and_hebrew_prefix(self):
        config = json.loads((self.root / "config/teshuva-search.json").read_text())
        self.assertEqual(search_groups("שַׁבָּת", config), search_groups("shabbat", config))
        self.assertEqual(search_groups("בשבת", config), search_groups("shabbat", config))

    def test_portrait_name_and_url_preserved(self):
        p = profiles(self.root)[0]
        self.assertEqual(p["name"], "Rav Test שם")
        self.assertTrue(p["image"].startswith("Rav/Rav%20Test%20"))

    def test_question_and_link_only_are_not_evidence(self):
        q = copy.deepcopy(self.record)
        q["answers"] = []
        self.assertFalse(evidence_text(q))
        q["kind"] = "link"
        self.assertFalse(evidence_text(q))

    def test_articles_and_documents_are_evidence(self):
        for kind in ["article", "document"]:
            q = {**self.record, "answers": [], "kind": kind}
            self.assertEqual(len(evidence_text(q)), 1)

    def test_plain_comparison_not_parsed_as_html(self):
        q = {**self.record, "answers": [{"text": "This is a saved answer where A < B and B > C remain visible.", "format": "plain"}]}
        self.assertIn("A < B", evidence_text(q)[0][0])

    def test_api_off_makes_no_network_call(self):
        with patch("sanhedrin.teshuva.api_draft") as api:
            result = compose(self.store, self.root, self.request, identity="teshuva-1-123456789abc", api_key="test-only")
        api.assert_not_called()
        self.assertEqual(result["mode"], "library")
        self.assertEqual(result["sources"][0]["id"], self.record["id"])

    def test_api_missing_preserves_library_answer(self):
        result = compose(self.store, self.root, {**self.request, "use_openai": True}, identity="teshuva-1-123456789abc")
        self.assertEqual(result["openai_status"], "unconfigured")
        self.assertEqual(result["mode"], "library")

    def test_valid_api_uses_numbered_saved_sources(self):
        seen = []
        def opener(req, timeout):
            seen.append(json.loads(req.data))
            return mock_response({"status": "draft", "paragraphs": [{"text": "The saved source discusses Shabbat candles.", "citations": [1]}]})
        result = compose(self.store, self.root, {**self.request, "use_openai": True}, identity="teshuva-1-123456789abc", api_key="test-only", opener=opener)
        self.assertEqual(result["mode"], "openai")
        self.assertFalse(seen[0]["store"])
        self.assertEqual(seen[0]["text"]["format"]["type"], "json_schema")
        self.assertEqual(json.loads(seen[0]["input"])["sources"][0]["number"], 1)

    def test_invalid_api_reference_falls_back(self):
        for citations in [[0], [2], [True], []]:
            result = compose(self.store, self.root, {**self.request, "use_openai": True}, identity="teshuva-1-123456789abc", api_key="test-only",
                opener=lambda *a, **k: mock_response({"status": "draft", "paragraphs": [{"text": "Unsupported answer", "citations": citations}]}))
            self.assertEqual(result["mode"], "library")
            self.assertEqual(result["openai_status"], "failed")

    def test_api_timeout_falls_back(self):
        def fail(*args, **kwargs):
            raise TimeoutError()
        result = compose(self.store, self.root, {**self.request, "use_openai": True}, identity="teshuva-1-123456789abc", api_key="test-only", opener=fail)
        self.assertEqual(result["mode"], "library")

    def test_real_api_metadata_is_recorded_without_credentials(self):
        draft = {"status": "draft", "paragraphs": [{"text": "Saved source.", "citations": [1]}]}
        body = {"id": "resp_test_fixture", "status": "completed",
                "usage": {"input_tokens": 90, "output_tokens": 40, "total_tokens": 130},
                "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(draft)}]}]}
        result = compose(self.store, self.root, {**self.request, "use_openai": True},
                         identity="teshuva-1-123456789abc", api_key="test-only-secret",
                         opener=lambda *a, **k: io.BytesIO(json.dumps(body).encode()))
        self.assertEqual(result["openai_response_id"], "resp_test_fixture")
        self.assertEqual(result["openai_usage"]["total_tokens"], 130)
        self.assertNotIn("test-only-secret", json.dumps(result))

    def test_http_error_records_only_status_and_keeps_sources(self):
        def fail(*args, **kwargs):
            raise urllib.error.HTTPError("https://api.openai.com/", 429, "Quota", {}, None)
        result = compose(self.store, self.root, {**self.request, "use_openai": True},
                         identity="teshuva-1-123456789abc", api_key="test-only", opener=fail)
        self.assertEqual(result["openai_http_status"], 429)
        self.assertEqual(result["mode"], "library")

    def test_api_insufficient_keeps_excerpts(self):
        result = compose(self.store, self.root, {**self.request, "use_openai": True}, identity="teshuva-1-123456789abc", api_key="test-only",
            opener=lambda *a, **k: mock_response({"status": "insufficient", "paragraphs": []}))
        self.assertEqual(result["openai_status"], "insufficient")
        self.assertEqual(len(result["sources"]), 1)

    def test_html_is_sanitized_at_input_and_output(self):
        request = {**self.request, "question_html": '<p onclick="alert(1)">How are candles used?</p><script>evil()</script>'}
        with patch('sanhedrin.teshuva.api_draft', return_value={'status':'draft','paragraphs':[{'text':'Saved sources.','citations':[1]}]}):
            result = compose(self.store, self.root, {**request,'use_openai':True}, identity="teshuva-1-123456789abc",api_key='test-only')
        page = render(result)
        self.assertNotIn("onclick", page)
        self.assertNotIn("evil()", page)
        self.assertIn("Rav%20Test", page)
        self.assertIn("https://www.yeshiva.org.il/ask/42", page)

    def test_invalid_sources_and_profiles_rejected(self):
        for changes in [{"source_ids": []}, {"source_ids": [self.record["id"]]*2}, {"source_ids": ["missing"]}, {"profile_id": "../../malicious"}, {"question_html": "a"*8001}]:
            with self.assertRaises(DataError):
                compose(self.store, self.root, {**self.request, **changes}, identity="teshuva-1-123456789abc")

    def test_saved_citations_cannot_inject_html(self):
        result = compose(self.store, self.root, self.request, identity="teshuva-1-123456789abc")
        result["paragraphs"] = [{"text": "bad", "citations": ['1\"><img src=x>']}]
        with self.assertRaises(DataError):
            render(result)

    def test_request_parser_accepts_one_block(self):
        body = '<!-- sanhedrin-teshuva:v1 -->\n```json\n' + json.dumps(self.request) + '\n```'
        self.assertEqual(parse_body(body), self.request)
        with self.assertRaises(DataError):
            parse_body(body + '\n```json\n{}\n```')

    def test_atomic_save_retries_without_losing_concurrent_changes(self):
        api = FakeGitHub()
        api.conflict = True
        result = save(api, self.root, self.store, 27, self.request)
        self.assertTrue(result["saved"])
        self.assertEqual(api.commits, 2)
        self.assertEqual(api.files["unrelated.txt"], "preserved")
        self.assertEqual(api.tree["base_tree"], "tree-concurrent-commit")
        self.assertEqual(len([p for p in api.files if p.startswith("Sanhedrin/")]), 2)

    def test_retry_is_idempotent_and_does_not_call_api_again(self):
        api = FakeGitHub()
        first = save(api, self.root, self.store, 27, self.request)
        with patch("tools.save_teshuva.compose", side_effect=AssertionError("Must reuse saved response")):
            second = save(api, self.root, self.store, 27, self.request)
        self.assertEqual(first["id"], second["id"])
        self.assertFalse(second["changed"])
        self.assertEqual(api.commits, 1)

    def test_partial_saved_pair_is_repaired_from_json(self):
        api = FakeGitHub()
        first = save(api, self.root, self.store, 27, self.request)
        del api.files["Sanhedrin/" + first["id"] + ".html"]
        with patch("tools.save_teshuva.compose", side_effect=AssertionError("Must reuse JSON")):
            second = save(api, self.root, self.store, 27, self.request)
        self.assertTrue(second["changed"])
        self.assertIn("Sanhedrin/" + first["id"] + ".html", api.files)

    def test_changed_question_gets_distinct_file(self):
        api = FakeGitHub()
        a = save(api, self.root, self.store, 27, self.request)
        b = save(api, self.root, self.store, 27, {**self.request, "question_html": "What is the source for Shabbat candles?"})
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(len(api.files), 4)

    def test_automatic_portraits_cycle_and_retry_keeps_counter(self):
        for name in ['A.png', 'B.png']:
            (self.root / 'Rav' / name).write_bytes(b'image-fixture')
        choices = profiles(self.root)
        api = FakeGitHub()
        request = {**self.request, 'profile_id': 'auto'}
        for index in range(5):
            result = save(api, self.root, self.store, 40 + index, request)
            saved = json.loads(api.files['Sanhedrin/' + result['id'] + '.json'])
            self.assertEqual(saved['profile'], choices[index % len(choices)])
            self.assertEqual(saved['portrait_sequence'], index)
        before = api.files[PORTRAIT_ROTATION_PATH]
        retry = save(api, self.root, self.store, 44, request)
        self.assertFalse(retry['changed'])
        self.assertEqual(api.files[PORTRAIT_ROTATION_PATH], before)
        self.assertEqual(json.loads(before)['next_index'], 5)

    def test_automatic_portrait_rechecks_counter_after_conflict(self):
        (self.root / 'Rav/A.png').write_bytes(b'image-fixture')
        api = FakeGitHub()
        api.conflict = True
        api.concurrent_files = {PORTRAIT_ROTATION_PATH: json.dumps({'schema': 1, 'next_index': 1})}
        result = save(api, self.root, self.store, 40, {**self.request, 'profile_id': 'auto'})
        saved = json.loads(api.files['Sanhedrin/' + result['id'] + '.json'])
        self.assertEqual(saved['profile'], profiles(self.root)[1])
        self.assertEqual(saved['portrait_sequence'], 1)
        self.assertEqual(json.loads(api.files[PORTRAIT_ROTATION_PATH])['next_index'], 2)
        self.assertEqual(api.files['unrelated.txt'], 'preserved')

    def test_api_upgrade_preserves_automatic_portrait_without_advancing(self):
        (self.root / 'Rav/A.png').write_bytes(b'image-fixture')
        api = FakeGitHub()
        request = {**self.request, 'profile_id': 'auto', 'use_openai': True}
        first = save(api, self.root, self.store, 40, request, api_block_reason='disabled')
        initial = json.loads(api.files['Sanhedrin/' + first['id'] + '.json'])
        save(api, self.root, self.store, 41, {**self.request, 'profile_id': 'auto'})
        counter = api.files[PORTRAIT_ROTATION_PATH]
        draft = {'status': 'draft', 'paragraphs': [{'text': 'Saved candles source.', 'citations': [1]}]}
        with patch('sanhedrin.teshuva.api_draft', return_value=draft):
            upgraded = save(api, self.root, self.store, 40, request, api_key='test-only')
        saved = json.loads(api.files['Sanhedrin/' + upgraded['id'] + '.json'])
        self.assertEqual(saved['profile'], initial['profile'])
        self.assertEqual(saved['portrait_sequence'], initial['portrait_sequence'])
        self.assertEqual(api.files[PORTRAIT_ROTATION_PATH], counter)
        self.assertEqual(saved['mode'], 'openai')

    def test_corrupt_counter_does_not_save_or_reset_rotation(self):
        api = FakeGitHub()
        api.files[PORTRAIT_ROTATION_PATH] = json.dumps({'schema': 1, 'next_index': -1})
        with self.assertRaises(DataError):
            save(api, self.root, self.store, 40, {**self.request, 'profile_id': 'auto'})
        self.assertEqual(api.commits, 0)
        self.assertEqual(len(api.files), 1)

    def test_published_rotation_uses_durable_counter(self):
        api = FakeGitHub()
        save(api, self.root, self.store, 40, {**self.request, 'profile_id': 'auto'})
        (self.root / 'Sanhedrin').mkdir()
        for path, data in api.files.items():
            (self.root / path).write_text(data)
        out = self.root / 'dist'
        out.mkdir()
        publish_assets(self.root, out)
        self.assertEqual(json.loads((out / 'rav-rotation.json').read_text()), {'schema': 1, 'next_index': 1})
        self.assertEqual(len(json.loads((out / 'teshuvot.json').read_text())), 1)

    def test_saved_archive_is_published_without_old_placeholders(self):
        api = FakeGitHub()
        with patch('sanhedrin.teshuva.api_draft',return_value={'status':'draft','paragraphs':[{'text':'Saved sources.','citations':[1]}]}):
            result = save(api, self.root, self.store, 27, {**self.request,'use_openai':True},api_key='test-only')
        (self.root / "Sanhedrin").mkdir()
        for path, data in api.files.items():
            (self.root / path).write_text(data)
        (self.root / "Sanhedrin/old-placeholder.html").write_text("placeholder")
        out = self.root / "dist"
        out.mkdir()
        assets = publish_assets(self.root, out)
        self.assertEqual(assets["saved_teshuvot"], 1)
        self.assertFalse((out / "Sanhedrin/old-placeholder.html").exists())
        self.assertEqual(json.loads((out / "teshuvot.json").read_text())[0]["id"], result["id"])

    def test_untrusted_actor_cannot_use_secrets(self):
        class Permissions:
            def request(self, *args, **kwargs):
                return {"permission": "read"}
        self.assertFalse(authorized(Permissions(), {}, "outsider", "owner/repo"))
        self.assertTrue(authorized(Permissions(), {}, "owner", "owner/repo"))

    def test_only_owner_can_use_openai_even_after_maintainer_approval(self):
        request = {**self.request, "use_openai": True}
        issue = {"user": {"login": "Moriahise"}}
        self.assertEqual(openai_access(request, issue, "Moriahise", "Moriahise", "Moriahise/Sanhedrin", "true"), "")
        for author, actor, rerunner in [("visitor", "Moriahise", "Moriahise"),
                                       ("Moriahise", "maintainer", "maintainer"),
                                       ("Moriahise", "Moriahise", "maintainer"),
                                       ("Moriahise", "Moriahise", "")]:
            with self.subTest(author=author, actor=actor, rerunner=rerunner):
                reason = openai_access(request, {"user": {"login": author}}, actor, rerunner,
                                       "Moriahise/Sanhedrin", "true")
                self.assertEqual(reason, "owner_only")
                with patch("sanhedrin.teshuva.api_draft") as api:
                    result = compose(self.store, self.root, request, identity="teshuva-1-123456789abc",
                                     api_key="test-only", api_block_reason=reason)
                api.assert_not_called()
                self.assertEqual(result["mode"], "library")
                self.assertEqual(result["openai_status"], "owner_only")

    def test_master_switch_defaults_off_and_preserves_library(self):
        request = {**self.request, "use_openai": True}
        for enabled in ["", "false", "1", "TRUE"]:
            reason = openai_access(request, {"user": {"login": "Moriahise"}}, "Moriahise",
                                   "Moriahise", "Moriahise/Sanhedrin", enabled)
            self.assertEqual(reason, "disabled")
            with patch("sanhedrin.teshuva.api_draft") as api:
                result = compose(self.store, self.root, request, identity="teshuva-1-123456789abc",
                                 api_key="test-only", api_block_reason=reason)
            api.assert_not_called()
            self.assertEqual(result["sources"][0]["id"], self.record["id"])
            self.assertIn("Shabbat candles are discussed", render(result))
        self.assertNotIn("The saved source passages are shown", render(result))

    def test_authorized_retry_upgrades_fallback_and_then_reuses_api_result(self):
        api = FakeGitHub()
        request = {**self.request, "use_openai": True}
        first = save(api, self.root, self.store, 27, request, api_block_reason="disabled")
        self.assertEqual(first["openai_status"], "disabled")
        draft = {"status": "draft", "paragraphs": [{"text": "Saved candles source.", "citations": [1]}]}
        with patch("sanhedrin.teshuva.api_draft", return_value=draft) as draft_call:
            second = save(api, self.root, self.store, 27, request, api_key="test-only")
            third = save(api, self.root, self.store, 27, request, api_key="test-only")
        draft_call.assert_called_once()
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["mode"], "openai")
        self.assertTrue(second["changed"])
        self.assertFalse(third["changed"])
        self.assertEqual(json.loads(api.files["Sanhedrin/" + second["id"] + ".json"])["mode"], "openai")

    def test_blocked_retry_never_calls_api(self):
        api = FakeGitHub()
        request = {**self.request, "use_openai": True}
        save(api, self.root, self.store, 27, request, api_block_reason="disabled")
        with patch("sanhedrin.teshuva.api_draft") as draft_call:
            result = save(api, self.root, self.store, 27, request, api_key="test-only", api_block_reason="owner_only")
        draft_call.assert_not_called()
        self.assertEqual(result["mode"], "library")


if __name__ == "__main__":
    unittest.main()
