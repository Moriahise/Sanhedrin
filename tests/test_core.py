import gzip
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sanhedrin.model import normalize, DataError
from sanhedrin.store import Store
from sanhedrin.html import sanitize, plain_text, tokens
from sanhedrin.build import build, verify_export
from sanhedrin.snapshot import snapshot, restore
from sanhedrin.locking import writer_lock
from sanhedrin.migrate import import_file
from sanhedrin.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def sample(provider="yeshiva", native="123", **extra):
    hosts = {
        "yeshiva": "https://www.yeshiva.org.il/ask/",
        "miyodeya": "https://judaism.stackexchange.com/questions/",
        "chabad": "https://www.chabad.org/library/article_cdo/aid/",
    }
    return normalize(
        {
            "id": provider + "-" + native,
            "title": "Test question",
            "question": "<p>Original question</p>",
            "answers": [{"text": "Original answer"}],
            "url": hosts[provider] + native,
            **extra,
        }
    )


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.s = Store(self.root / "library.sqlite")

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def test_host_identity_overrides_wrong_legacy_source(self):
        q = sample("miyodeya", source="yeshiva")
        self.assertEqual(q["provider"], "miyodeya")
        self.assertEqual(q["native_id"], "123")

    def test_explicit_provider_conflict_rejected(self):
        with self.assertRaises(DataError):
            normalize(
                {
                    "provider": "yeshiva",
                    "title": "Q",
                    "question": "Q",
                    "url": "https://judaism.stackexchange.com/questions/123",
                }
            )

    def test_native_collision_and_ambiguous_alias(self):
        a = sample()
        b = sample("miyodeya")
        self.s.insert(a)
        self.s.insert(b)
        self.assertEqual(set(self.s.resolve("123")), {a["id"], b["id"]})
        self.s.alias("123", a["id"], "first.json")
        self.assertEqual(self.s.resolve("123", "first.json"), [a["id"]])

    def test_metadata_never_erases_body_or_category(self):
        old = sample(category="halacha", needs_review=False)
        self.s.insert(old, baseline=old)
        q = sample(question="", answers=[], kind="link", title="New title")
        self.s.upsert(q, mode="metadata")
        current = self.s.get(old["id"])
        self.assertEqual(current["question"], old["question"])
        self.assertEqual(current["answers"], old["answers"])
        self.assertEqual(current["category"], "halacha")
        self.assertFalse(self.s.verify())

    def test_verified_answer_update_retains_revision(self):
        old = sample(
            "miyodeya",
            answers=[{"answer_id": "1", "text": "Old", "is_accepted": False}],
        )
        self.s.insert(old, baseline=old)
        q = sample(
            "miyodeya", answers=[{"answer_id": "1", "text": "New", "is_accepted": True}]
        )
        self.s.upsert(q, mode="source")
        self.assertEqual(len(self.s.get(q["id"])["answers"]), 1)
        self.assertTrue(self.s.get(q["id"])["answers"][0]["accepted_verified"])
        self.assertFalse(self.s.verify())
        self.assertEqual(
            self.s.db.execute("SELECT count(*) FROM revisions").fetchone()[0], 1
        )

    def test_first_answer_not_assumed_accepted(self):
        self.assertFalse(sample()["answers"][0]["accepted_verified"])
        self.assertFalse(sample()["answers"][0]["accepted"])

    def test_transaction_rolls_back_data_and_cursor(self):
        with self.assertRaises(RuntimeError):
            with self.s.transaction():
                self.s.insert(sample())
                self.s.set_cursor("page", 2)
                raise RuntimeError()
        self.assertEqual(self.s.count(), 0)
        self.assertIsNone(self.s.cursor("page"))

    def test_import_ledger_quarantines_new_404_preserves_charge(self):
        path = self.root / "first.json"
        path.write_text(
            json.dumps(
                {
                    "exported_at": "2026-01-23T14:29:47.817Z",
                    "questions": [
                        {
                            "id": "123",
                            "title": "Question",
                            "url": "https://www.yeshiva.org.il/ask/123",
                        },
                        {
                            "id": "124",
                            "title": "ERROR 404",
                            "url": "https://www.yeshiva.org.il/ask/124",
                        },
                    ],
                }
            )
        )
        r = import_file(self.s, path, self.root)
        self.assertEqual(r["quarantined"], 1)
        q = next(self.s.records())
        self.assertIsNone(q["published_at"])
        self.assertEqual(q["kind"], "link")
        self.assertEqual(q["import_charges"][0]["path"], "first.json")
        before = self.s.logical_hash()
        import_file(self.s, path, self.root)
        self.assertEqual(before, self.s.logical_hash())

    def test_verified_wordpress_identity_keeps_public_id(self):
        old = normalize(
            {
                "id": "din-old",
                "title": "Question",
                "question": "Q",
                "answers": [{"text": "A"}],
                "url": "https://din.org.il/old/",
                "category": "halacha",
            },
            public_id="din-old",
        )
        self.s.insert(old)
        q = normalize(
            {"id": "din-12", "title": "New", "url": old["url"], "kind": "link"}
        )
        q.update(native_id="12", identity_method="verified_wordpress_api")
        self.s.upsert(q, mode="metadata")
        q["url"] = "https://din.org.il/new/"
        q["canonical_url"] = q["url"]
        self.s.upsert(q, mode="metadata")
        self.assertEqual(self.s.count(), 1)
        self.assertEqual(self.s.get("din-old")["native_id"], "12")
        self.assertEqual(self.s.get("din-old")["question"], "Q")

    def test_explicit_tags_and_conflict_review(self):
        self.assertEqual(sample(tags=["shabbat"])["category"], "halacha")
        self.assertTrue(sample(tags=["shabbat", "tanach-bible"])["needs_review"])
        self.assertEqual(
            sample(tags=["shabbat"], category="history")["category"], "history"
        )

    def test_html_xss_and_malformed_links(self):
        value = sanitize(
            '<script>alert(1)</script><svg><script>x</script></svg><a href="javascript:alert(1)" onclick="x">bad</a><a href="http://[">broken</a><iframe src="https://x"></iframe>'
        )
        self.assertNotIn("script", value)
        self.assertNotIn("onclick", value)
        self.assertNotIn("javascript:", value)
        self.assertNotIn("iframe", value)
        self.assertEqual(plain_text(value), "bad broken")

    def test_markdown_and_relative_url(self):
        value = sanitize(
            "**Hello** [answer](/a/1)",
            "markdown",
            "https://judaism.stackexchange.com/questions/1",
        )
        self.assertIn("<strong>Hello</strong>", value)
        self.assertIn("https://judaism.stackexchange.com/a/1", value)

    def test_hebrew_niqqud_normalization(self):
        self.assertEqual(tokens("שַׁבָּת"), tokens("שבת"))

    def test_snapshot_roundtrip_and_corrupt_preserves_target(self):
        q = sample()
        self.s.insert(q, baseline=q)
        self.s.alias("old", q["id"], "src.json")
        self.s.set_cursor("pages", {"page": 3})
        folder = self.root / "snap"
        snapshot(self.s, folder)
        target = self.root / "restored.sqlite"
        restore(folder, target, minimum_total=1)
        with Store(target) as restored:
            self.assertEqual(restored.logical_hash(), self.s.logical_hash())
            self.assertEqual(restored.cursor("pages"), {"page": 3})
            self.assertFalse(restored.verify())
        old = target.read_bytes()
        (folder / "library.sqlite.gz").write_bytes(b"broken")
        with self.assertRaises(DataError):
            restore(folder, target, minimum_total=1)
        self.assertEqual(target.read_bytes(), old)

    def test_snapshot_metadata_describes_the_consistent_backup(self):
        self.s.insert(sample())
        original = self.s.backup

        def concurrent_backup(path):
            original(path)
            self.s.insert(sample(native="456"))

        folder = self.root / "snap"
        with patch.object(self.s, "backup", side_effect=concurrent_backup):
            metadata = snapshot(self.s, folder)
        self.assertEqual(metadata["total"], 1)
        restore(folder, self.root / "restored.sqlite", minimum_total=1)
        with Store(self.root / "restored.sqlite") as restored:
            self.assertEqual(restored.count(), 1)

    def test_snapshot_too_small_rejected(self):
        self.s.insert(sample())
        folder = self.root / "snap"
        snapshot(self.s, folder)
        with self.assertRaises(DataError):
            restore(folder, self.root / "target.sqlite", minimum_total=2)

    def test_record_hash_mismatch_detected(self):
        q = sample()
        self.s.insert(q)
        self.s.db.execute(
            "UPDATE records SET content_hash='wrong' WHERE public_id=?", (q["id"],)
        )
        self.assertTrue(any("hash mismatch" in e for e in self.s.verify()))

    def test_backup_consistent_with_wal(self):
        self.s.insert(sample())
        target = self.root / "backup.sqlite"
        self.s.backup(target)
        with Store(target) as b:
            self.assertEqual(b.logical_hash(), self.s.logical_hash())

    def test_second_writer_rejected(self):
        with writer_lock(self.root / "lock"):
            with self.assertRaises(DataError):
                with writer_lock(self.root / "lock"):
                    pass

    def test_full_answer_search_and_raw_archive_not_public(self):
        root = self.root / "repo"
        root.mkdir()
        shutil.copytree(ROOT / "web", root / "web")
        q = sample(
            answers=[{"text": "RareAnswerToken שבת"}],
            published_at="2024-01-01",
            imported_at="2026-01-01",
        )
        self.s.insert(q)
        self.s.archive({"secret": "raw-only"}, "fixture")
        out = root / "out"
        manifest = build(self.s, root, out)
        self.assertEqual(verify_export(out)["total"], 1)
        self.assertIn("2026", manifest["facets"]["imported_year"])
        content = "".join(
            p.read_text()
            for p in (out / manifest["data_base"] / "content").rglob("*.json")
        )
        self.assertNotIn("raw-only", content)
        search = "".join(
            p.read_text()
            for p in (out / manifest["data_base"] / "search").glob("*.json")
        )
        self.assertIn("rareanswertoken", search)

    def test_failed_budget_keeps_published_site(self):
        root = self.root / "repo"
        root.mkdir()
        shutil.copytree(ROOT / "web", root / "web")
        out = root / "out"
        out.mkdir()
        (out / "sentinel").write_text("previous")
        self.s.insert(sample())
        with self.assertRaises(DataError):
            build(self.s, root, out, max_bytes=1)
        self.assertEqual((out / "sentinel").read_text(), "previous")

    def test_failed_stage_rename_restores_previous(self):
        root = self.root / "repo"
        root.mkdir()
        shutil.copytree(ROOT / "web", root / "web")
        out = root / "out"
        out.mkdir()
        (out / "sentinel").write_text("previous")
        self.s.insert(sample())
        original = Path.rename

        def rename(path, target):
            if path.name.startswith(".sanhedrin-build-"):
                raise OSError("failed publish")
            return original(path, target)

        with patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                build(self.s, root, out)
        self.assertEqual((out / "sentinel").read_text(), "previous")

    def test_context_traversal_rejected(self):
        from sanhedrin.model import legacy_context

        for value in ["../bad", "/root", "https://example.org"]:
            with self.assertRaises(DataError):
                legacy_context(value)
