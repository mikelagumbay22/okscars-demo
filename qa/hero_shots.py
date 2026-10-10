import os
from playwright.sync_api import sync_playwright
from PIL import Image
CHROME = "/usr/bin/google-chrome"
OUT = "/workspace/sites/okscars/screenshots/"
BASE = "http://127.0.0.1:8113/"
CLS_JS = "window.__cls=0;new PerformanceObserver(l=>{for(const e of l.getEntries()) if(!e.hadRecentInput) {window.__cls+=e.value;(window.__src=window.__src||[]).push(e.value.toFixed(4)+' '+e.sources.map(s=>s.node&&(s.node.className||s.node.nodeName)).join('/'))}}).observe({type:'layout-shift',buffered:true})"
def scroll_to(pg, p):
    pg.evaluate("""p => { const u=document.querySelector('[data-uphero]'); const span=u.offsetHeight-innerHeight;
        const top=u.getBoundingClientRect().top+scrollY; window.scrollTo(0, top+p*span); }""", p)
    pg.wait_for_timeout(900)
def save(pg, name):
    tmp = "/tmp/" + name; pg.screenshot(path=tmp)
    im = Image.open(tmp).convert("RGB"); dst = OUT + name; im.save(dst, optimize=True)
    if os.path.getsize(dst) > 1_000_000: im.quantize(256).save(dst, optimize=True)
    print(dst, os.path.getsize(dst) // 1024, "KB")
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.add_init_script(CLS_JS); pg.goto(BASE, wait_until="networkidle"); pg.wait_for_timeout(800)
    save(pg, "hero-1-desktop.png")
    for q in (0.1, 0.2, 0.3, 0.4): scroll_to(pg, q)
    scroll_to(pg, 0.47); save(pg, "hero-2-desktop.png")
    for q in (0.6, 0.7, 0.8, 0.9): scroll_to(pg, q)
    scroll_to(pg, 1.0); save(pg, "hero-3-desktop.png")
    print("desktop CLS", round(pg.evaluate("window.__cls"), 4), pg.evaluate("window.__src"), "steps", pg.evaluate("[...document.querySelectorAll('.uphero__steps [aria-current]')].map(e=>e.textContent)"))
    m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    m.add_init_script(CLS_JS); m.goto(BASE, wait_until="networkidle"); m.wait_for_timeout(800)
    for q in (0.2, 0.4, 0.6, 0.8): scroll_to(m, q)
    scroll_to(m, 1.0); save(m, "hero-mobile.png")
    print("mobile CLS", round(m.evaluate("window.__cls"), 4))
    r = b.new_page(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
    r.goto(BASE, wait_until="networkidle"); r.wait_for_timeout(500)
    print("reduced:", r.evaluate("[document.documentElement.classList.contains('scrub-ok'), getComputedStyle(document.querySelector('.uphero__car--3')).opacity, getComputedStyle(document.querySelector('.uphero__copy')).opacity, document.querySelector('[data-uphero]').offsetHeight]"))
    r.screenshot(path="/tmp/reduced.png")
    b.close()
