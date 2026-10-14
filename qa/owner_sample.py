"""Render one owner-mode social post (upload a photo, Reserved) and save it.  Usage: owner_sample.py BASE OUT PHOTO"""
import base64, sys
from playwright.sync_api import sync_playwright
BASE, OUT, PHOTO = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome"); pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(BASE + "owner.html", wait_until="networkidle")
    pg.fill("#o-year", "2022"); pg.fill("#o-make", "Toyota"); pg.fill("#o-model", "Vios 1.3 XLE CVT"); pg.select_option("#o-status", "Reserved")
    pg.set_input_files("#o-photo", PHOTO); pg.click("button[type=submit]"); pg.wait_for_selector("[data-preview]:not([hidden])", timeout=15000); pg.wait_for_timeout(300)
    raw = base64.b64decode(pg.get_attribute("[data-preview]", "src").split(",", 1)[1]); open(OUT, "wb").write(raw); print(OUT, len(raw) // 1024, "KB")
    b.close()
