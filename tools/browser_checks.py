"""Exercise the complete generated site in a real browser, including failures."""

import argparse
import functools
import http.server
import json
import os
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run(directory, report_dir):
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((directory / "catalog/manifest.json").read_text())
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(directory))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/"
    errors = []
    results = {}
    try:
        with sync_playwright() as p:
            executable = os.environ.get("SANHEDRIN_CHROMIUM")
            browser = p.chromium.launch(
                executable_path=executable or None,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(base)
            page.wait_for_function(
                '() => document.querySelector("#cards").getAttribute("aria-busy")==="false"'
            )
            assert page.locator(".card").count() == 48
            assert page.locator("#next").is_enabled()
            resources = page.evaluate(
                'performance.getEntriesByType("resource").reduce((s,r)=>s+r.decodedBodySize,0)'
            )
            assert resources < 250000, resources
            results["initial_resource_bytes"] = resources
            page.locator("#language").click()
            page.wait_for_function('() => document.documentElement.lang==="en"')
            page.screenshot(
                path=str(report_dir / "catalogue-desktop.png"), full_page=False
            )
            lookup = page.evaluate(
                """async()=>{const {Catalogue}=await import('./catalog-data.js');const c=new Catalogue();await c.init();const a=await c.search('shabbat'),b=await c.search('שבת'),d=await c.search('שַׁבָּת');const docs=await c.search('',{kind:'document'}),imp=await c.search('',{provider:'yeshiva',imported_year:'2026'}),pub=await c.search('',{provider:'yeshiva',published_year:'2026'});const ids=await c.resolve('137101'),context=await c.detail('137101','data/qa/12yeshiva-qa-database-2026-01-23.json');return {shabbat:a.total,hebrew:b.total,niqqud:d.total,documents:docs.total,imported2026:imp.total,published2026:pub.total,ambiguous:ids.length,contextProvider:context.provider};}"""
            )
            assert lookup["shabbat"] > 1000
            assert lookup["hebrew"] == lookup["niqqud"]
            assert lookup["documents"] == 17
            assert lookup["imported2026"] > lookup["published2026"]
            assert lookup["ambiguous"] == 2
            assert lookup["contextProvider"] == "yeshiva"
            results["search"] = lookup
            page.locator("#next").click()
            page.wait_for_function(
                '() => document.querySelector("#page-number").textContent.startsWith("2 /")'
            )
            assert page.locator(".card").count() == 48
            for pid, host in [
                ("ye-137101", "judaism.stackexchange.com"),
                ("yeshiva-137101", "yeshiva.org.il"),
            ]:
                page.goto(base + "qa.html?id=" + pid)
                page.wait_for_function(
                    '() => document.querySelector("#reader").getAttribute("aria-busy")==="false"'
                )
                assert host in page.locator("#reader>a").first.get_attribute("href")
                assert page.locator(".body-text").count() > 0
            page.goto(base + "qa.html?id=137101")
            page.wait_for_function(
                '() => document.querySelector("#reader").getAttribute("aria-busy")==="false"'
            )
            assert page.locator("#reader p a").count() == 2
            page.goto(base + "qa.html?id=does-not-exist")
            page.wait_for_function(
                '() => document.querySelector("#reader").getAttribute("aria-busy")==="false"'
            )
            assert page.locator("#notice").inner_text()
            docs = [
                q
                for f in (directory / manifest["data_base"] / "catalog/pages").glob(
                    "*.json"
                )
                for q in json.loads(f.read_text())
                if q["kind"] == "document"
            ]
            page.goto(base + docs[0]["document_path"])
            assert page.locator("script").count() == 0
            assert page.locator("article").inner_text()
            page.wait_for_load_state("networkidle")
            assert page.evaluate(
                "[...document.images].every(i=>i.complete&&i.naturalWidth>0)"
            )
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(base)
            page.wait_for_function(
                '() => document.querySelector("#cards").getAttribute("aria-busy")==="false"'
            )
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.screenshot(
                path=str(report_dir / "catalogue-mobile.png"), full_page=False
            )
            page.goto(base + "qa.html?id=yeshiva-137101")
            page.wait_for_function(
                '() => document.querySelector("#reader").getAttribute("aria-busy")==="false"'
            )
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.screenshot(path=str(report_dir / "reader-mobile.png"), full_page=False)
            page.goto(base + "status.html")
            page.wait_for_selector(".health-item")
            assert page.locator(".health-item").count() == 6
            failed = browser.new_page()
            failed.on("pageerror", lambda e: errors.append(str(e)))
            failed.route(
                "**/catalog/manifest.json",
                lambda route: route.fulfill(status=503, body="unavailable"),
            )
            failed.goto(base)
            failed.wait_for_function(
                '() => document.querySelector("#cards").getAttribute("aria-busy")==="false"'
            )
            assert failed.locator("#notice").inner_text()
            failed.close()
            changed = browser.new_page()
            changed.on("pageerror", lambda e: errors.append(str(e)))
            changed.goto(base)
            changed.wait_for_function(
                '() => document.querySelector("#cards").getAttribute("aria-busy")==="false"'
            )
            new = {
                **manifest,
                "release": "v1-" + "a" * 24,
                "data_base": "releases/v1-" + "a" * 24 + "/",
            }
            changed.route(
                "**/catalog/manifest.json", lambda route: route.fulfill(json=new)
            )
            changed.route(
                "**/catalog/locator/*.json",
                lambda route: route.fulfill(status=404, body="missing"),
            )
            # Force an old release to disappear while a reader is open.
            caught = changed.evaluate(
                """async (old)=>{const {Catalogue,SnapshotChanged}=await import('./catalog-data.js');const c=new Catalogue();c.manifest=old;try{await c.locate('yeshiva-137101');return false;}catch(e){return e instanceof SnapshotChanged;}}""",
                manifest,
            )
            assert caught
            changed.close()
            browser.close()
        assert not errors, errors
        results.update(
            total=manifest["total"],
            javascript_errors=errors,
            status="ok",
            checks=[
                "pagination",
                "full text",
                "Hebrew niqqud",
                "separate date filters",
                "source collisions",
                "legacy src links",
                "documents",
                "mobile layout",
                "HTTP failure",
                "changed snapshot",
            ],
        )
        (report_dir / "browser.json").write_text(json.dumps(results, indent=2))
        return results
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    parser.add_argument("--report-dir", type=Path, default=Path("test-results"))
    a = parser.parse_args()
    print(json.dumps(run(a.directory.resolve(), a.report_dir.resolve()), indent=2))
