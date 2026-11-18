import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run


class VisibilityTests(unittest.TestCase):
    def test_committed_snapshot_matches_renderer_and_preserves_existing_files(self):
        from sanhedrin.visibility import publish
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out/"index.html").write_text("existing")
            publish(run.ROOT, out)
            self.assertEqual((out/"index.html").read_text(), "existing")
            self.assertEqual(run.render(run.CONFIG), {p.relative_to(out).as_posix():p.read_bytes()
                for p in out.rglob("*") if p.is_file() and p!=out/"index.html"})

    def test_bad_source_leaves_selection_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)
            (config/"weekly.json").write_text("{}")
            with patch.object(run,"CONFIG",config), patch.object(run,"fetch_feature",return_value=("entry",{})):
                with self.assertRaises((KeyError,ValueError)):
                    run.refresh()
            self.assertEqual((config/"weekly.json").read_text(),"{}")

    def test_notification_waits_for_deployment(self):
        with patch.object(run,"request",return_value=b'{}') as get:
            run.notify()
            self.assertEqual(get.call_count,1)

    def test_no_resubmission_when_live_bytes_match(self):
        from hashlib import sha256
        files=run.render(run.CONFIG)
        live=json.loads(files["learn/revision.json"])
        receipt=dict(live)
        for url in ("/","/about-the-name.html"):
            receipt[url]=sha256(url.encode()).hexdigest()
        def fake_request(url,*args,**kwargs):
            path=url.removeprefix(run.BASE)
            if path=="/learn/revision.json":return files["learn/revision.json"]
            if path.endswith(".txt"):return path[1:-4].encode()
            if path in ("/","/about-the-name.html"):return path.encode()
            self.fail("Unexpected request "+url)
        with patch.object(run,"request",side_effect=fake_request), patch.object(run,"read_json",return_value=receipt):
            run.notify()


if __name__=="__main__":
    unittest.main()
