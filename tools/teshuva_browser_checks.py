"""Exercise the question editor against the complete publication in Chromium."""
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


def run(directory, reports):
    reports.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(directory)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}/"
    errors, result = [], {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("SANHEDRIN_CHROMIUM") or None,
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page(viewport={"width": 1440, "height": 1050})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "teshuva.html")
            page.wait_for_function('() => Boolean(document.querySelector("#rav-image").dataset.profileId)')
            profile_count = page.evaluate("async()=> (await (await fetch('rav-profiles.json')).json()).length")
            assert profile_count >= 71
            assert page.locator("#rav-select").count() == 0
            for removed in ['Choose a rabbi portrait', 'The profile accompanies the draft.', 'Only Moriahise can use OpenAI.']:
                assert removed not in page.locator('body').inner_text()
            page.wait_for_function('() => document.querySelector("#rav-image").naturalWidth > 0')
            assert not page.locator("#use-openai").is_checked()
            assert page.locator("#generate").is_disabled()
            page.locator("#question-editor").fill("How should Shabbat candles be lit?")
            page.locator("#keywords").fill("shabbat candles")
            page.locator("#generate").click()
            page.wait_for_selector("#answer-sources .source", timeout=90000)
            first_portrait = page.locator("#rav-image").get_attribute("data-profile-id")
            page.locator("#generate").click()
            page.wait_for_selector("#answer-sources .source", timeout=90000)
            assert page.locator("#rav-image").get_attribute("data-profile-id") == first_portrait
            page.locator("#question-editor").fill("What sources explain lighting Shabbat candles?")
            page.locator("#generate").click()
            page.wait_for_selector("#answer-sources .source", timeout=90000)
            selected = page.locator("#rav-image").get_attribute("data-profile-id")
            assert selected != first_portrait
            assert page.locator("#answer-sources .source").count() == 6
            assert page.locator("#answer-image").get_attribute("src") == page.locator("#rav-image").get_attribute("src")
            assert all(len(q) >= 25 for q in page.locator("#answer-sources blockquote").all_inner_texts())
            data = page.evaluate("""async()=>{const {Catalogue,retrieve}=await import('./teshuva-data.js');const c=new Catalogue();await c.init();const config=await(await fetch('teshuva-search.json')).json();const a=await retrieve(c,'שבת נרות',config,8);return {total:c.manifest.total,ids:a.sources.map(s=>s.id),languages:a.sources.map(s=>s.language),sources:a.sources.length};}""")
            assert data["sources"] == 8
            assert set(data["languages"]) == {"en", "he"}
            assert data["total"] >= 64000
            result["retrieval"] = data
            # Keyboard formatting and HTML sanitation are checked in the real editor.
            page.evaluate("""()=>{const e=document.querySelector('#question-editor'),r=document.createRange();r.selectNodeContents(e);const s=getSelection();s.removeAllRanges();s.addRange(r);}""")
            page.locator('[data-command="bold"]').click()
            assert page.locator("#question-editor b, #question-editor strong").count() >= 1
            page.locator('[data-dir="rtl"]').click()
            assert page.locator("#question-editor").get_attribute("dir") == "rtl"
            page.reload()
            page.wait_for_function('() => Boolean(document.querySelector("#rav-image").dataset.profileId)')
            assert page.locator("#rav-image").get_attribute("data-profile-id") == selected
            assert "Shabbat" in page.locator("#question-editor").inner_text()
            page.locator("#generate").click()
            page.wait_for_selector("#answer-sources .source", timeout=90000)
            # Do not post a fictitious question: inspect the prepared issue only.
            page.context.route("https://github.com/**", lambda route: route.fulfill(status=200, content_type="text/html", body="Prepared submission preview"))
            with page.expect_popup() as popup:
                page.locator("#save").click()
            tab = popup.value
            tab.wait_for_url("https://github.com/Moriahise/Sanhedrin/issues/new?**")
            assert tab.url.startswith("https://github.com/Moriahise/Sanhedrin/issues/new")
            tab.close()
            request_body = page.locator("#submission-body").input_value()
            assert "sanhedrin-teshuva:v1" in request_body
            assert '"use_openai": false' in request_body
            assert '"source_ids"' in request_body
            assert '"profile_id": "auto"' in request_body
            # A long request gets an explicit copy/paste route instead of URL truncation.
            long = page.evaluate("""async()=>{const {submission}=await import('./teshuva-data.js');return submission({schema:1,question_html:'<p>'+('ש'.repeat(7000))+'</p>'}).long;}""")
            assert long
            page.evaluate("() => window.scrollTo(0,0)")
            page.screenshot(path=str(reports / "teshuva-desktop.png"), full_page=False)
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#language").click()
            assert page.locator("html").get_attribute("dir") == "rtl"
            assert page.locator("html").get_attribute("lang") == "he"
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(reports / "teshuva-mobile-rtl.png"), full_page=False)
            page.locator("#question-editor").fill("האם אפשר להדליק נרות בשבת?")
            page.locator("#keywords").fill("שבת נרות")
            page.locator("#generate").click()
            page.wait_for_selector("#answer-sources .source", timeout=90000)
            assert page.locator("#answer-sources .source").count() == 6
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            result["mobile_rtl"] = True
            page.locator("#keywords").fill("zzzznomatchxyz")
            page.locator("#generate").click()
            page.wait_for_function('() => document.querySelector("#status").textContent.includes("לא נמצא")')
            assert page.locator("#answer-panel").is_hidden()
            # Start at the final portrait and verify that the next question wraps.
            cycle = page.evaluate("""async()=>{const profiles=await(await fetch('rav-profiles.json')).json();const rotation=await(await fetch('rav-rotation.json')).json();const draft=JSON.parse(localStorage.getItem('sanhedrin-teshuva-draft'));draft.portrait={nextIndex:Math.ceil(rotation.next_index/profiles.length)*profiles.length+profiles.length-1,questionText:'',profileId:''};localStorage.setItem('sanhedrin-teshuva-draft',JSON.stringify(draft));return {last:profiles.at(-1).id,first:profiles[0].id};}""")
            page.reload()
            page.wait_for_function('() => Boolean(document.querySelector("#rav-image").dataset.profileId)')
            page.locator("#keywords").fill("שבת נרות")
            page.locator("#generate").click()
            page.wait_for_selector("#answer-sources .source", timeout=90000)
            assert page.locator("#rav-image").get_attribute("data-profile-id") == cycle['last']
            page.locator("#clear").click()
            page.locator("#question-editor").fill("How are Shabbat candles lit before sunset?")
            page.locator("#keywords").fill("shabbat candles")
            page.locator("#generate").click()
            page.wait_for_selector("#answer-sources .source", timeout=90000)
            assert page.locator("#rav-image").get_attribute("data-profile-id") == cycle['first']
            # Explicit failure handling rather than claiming an empty successful answer.
            failed = browser.new_page()
            failed.route("**/catalog/manifest.json", lambda route: route.fulfill(status=503, body="unavailable"))
            failed.goto(base + "teshuva.html")
            failed.wait_for_function('() => document.querySelector("#status").textContent.includes("could not")')
            assert failed.locator("#generate").is_disabled()
            failed.close()
            assert not errors, errors
            result.update(profiles=profile_count, automatic_portraits=True, portrait_wraparound=True, editor_formatting=True, draft_restoration=True,
                prepared_github_submission=True, no_api_required=True, errors=errors)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (reports / "teshuva-browser.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("dist"))
    parser.add_argument("--reports", type=Path, default=Path("test-results"))
    args = parser.parse_args()
    print(json.dumps(run(args.directory, args.reports), ensure_ascii=False, indent=2))
