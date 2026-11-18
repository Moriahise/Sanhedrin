"""Exercise both chavruta readers against the complete offline site export."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright


def main():
    root = Path("dist")
    items = json.loads((root/"learn/daf-catalogue.json").read_text())
    matches = json.loads((root/"learn/daf-related.json").read_text())
    date = next(d for d,row in sorted(items.items()) if matches.get(row[0].split("-",2)[2]))
    server = ThreadingHTTPServer(("127.0.0.1",0),functools.partial(SimpleHTTPRequestHandler,directory=root))
    Thread(target=server.serve_forever,daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=["--no-sandbox"])
            tab = browser.new_page(viewport={"width":390,"height":844})
            errors=[]
            tab.on("pageerror",lambda exc:errors.append(str(exc)))
            # The catalogue, Q&A detail and language links use real local production files.
            tab.route("https://moriahise.github.io/Daf-Yomi/**",lambda req:req.fulfill(
                content_type="text/html",headers={"Access-Control-Allow-Origin":"*"},
                body='<div class="guiding-question"><p lang="en">A study question</p><p lang="he">שאלה לעיון</p></div><div class="paragraph-pair"><p lang="en">Source reading</p><p lang="he">עיון במקור</p></div>'))
            tab.goto(base+"/learn/en/daf-yomi/?date="+date)
            tab.locator("h3",has_text="A study question").wait_for()
            tab.locator(".qa-entry h4").first.wait_for()
            tab.locator('nav a[hreflang="he"]').click()
            tab.locator("h3",has_text="שאלה לעיון").wait_for()
            tab.locator(".qa-entry h4").first.wait_for()
            assert tab.locator("#day").input_value()==date
            assert tab.evaluate("document.documentElement.scrollWidth <= innerWidth")
            tab.locator("#day").fill("2000-01-01")
            tab.locator('#dates [type="submit"]').click()
            tab.get_by_text("אין באוסף שיעור שפורסם לתאריך זה.").wait_for()
            tab.go_back()
            tab.locator(".qa-entry h4").first.wait_for()
            assert not errors,errors
            print("Verified date selection, archived answers, Hebrew, mobile width and browser history")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__=="__main__":
    main()
