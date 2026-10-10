#!/usr/bin/env python3
"""Screenshots for the Oks Cars demo (local preview only).

    python3 screenshot.py [BASE_URL]     # default http://127.0.0.1:8113

Desktop (1440, full page) and mobile (390, full page) for every page, plus nav-mobile-open.png.
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8113").rstrip("/")
OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)
CHROME = "/usr/bin/google-chrome"


def settle(page, full=True):
    """Scroll through the page, force lazy images to load, wait for them and for fonts."""
    page.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) {
        window.scrollTo(0, y); await new Promise(r => setTimeout(r, 70)); } }""")
    try:
        if page.locator("iframe#map").count():
            page.locator("iframe#map").first.scroll_into_view_if_needed(timeout=2000)
            page.wait_for_timeout(6000)  # let the keyless embed render its tiles
    except Exception:
        pass
    page.evaluate("""async () => {
        document.querySelectorAll('img[loading="lazy"]').forEach(i => i.loading = 'eager');
        await Promise.all([...document.images].map(i => i.complete ? null :
            new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); })));
        await document.fonts.ready;
        document.querySelectorAll('.reveal,[data-stitch]').forEach(e => e.classList.add('is-in')); }""")
    page.wait_for_timeout(4200)  # let reveals, track draw-in and the train run finish
    if full:
        # Full-page captures freeze sticky-bottom bars at the first viewport edge; show it at the page end.
        page.add_style_tag(content=".mobile-callbar{position:static !important}")
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    return page.evaluate("[...document.images].filter(i => !i.complete || i.naturalWidth === 0).map(i => i.currentSrc || i.src)")


def shot(page, path, full=True):
    broken = settle(page, full)
    if full and page.locator("iframe").count():
        # Cross-origin map iframes are not repainted off-screen in a full_page capture:
        # grow the viewport to the page height instead so the map tiles are actually drawn.
        vp = page.viewport_size
        page.set_viewport_size({"width": vp["width"], "height": page.evaluate("document.documentElement.scrollHeight")})
        page.wait_for_timeout(5000)
        page.screenshot(path=str(path), full_page=False)
        page.set_viewport_size(vp)
    else:
        page.screenshot(path=str(path), full_page=full)
    print("saved", path, f"({page.evaluate('document.images.length')} images, not loaded: {broken or 'none'})")


PAGES = [("home", "/")]   # lean run: home only
ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    desk = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    for name, path in PAGES:
        if ONLY and name not in ONLY:
            continue
        desk.goto(BASE + path, wait_until="networkidle")
        shot(desk, OUT / f"{name}-desktop.png")
    desk.close()

    mob = browser.new_page(
        viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
        user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"))
    for name, path in PAGES:
        if ONLY and name not in ONLY:
            continue
        mob.goto(BASE + path, wait_until="networkidle")
        shot(mob, OUT / f"{name}-mobile.png")
    if ONLY and "nav" in ONLY:
        mob.goto(BASE + "/services.html", wait_until="networkidle")
        settle(mob, full=False)
        mob.click("#menu-toggle")
        mob.wait_for_timeout(400)
        assert mob.locator("#mobile-nav").is_visible()
        mob.screenshot(path=str(OUT / "nav-mobile-open.png"), full_page=False)
        print("saved", OUT / "nav-mobile-open.png")
    mob.close()
    browser.close()
