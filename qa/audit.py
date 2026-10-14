"""Oks Cars demo QA, LEAN (adapted from railroad-coffee/qa/audit.py): axe at 390 and 1440 on every page,
plus the keyboard pass that runs on the same page loads. (Railroad's 320px, carousel, hours and reduced-motion
sections are left out on purpose to keep usage low.)
Original notes:
axe-core (WCAG 2.2 AA + best practice) at 390 and 1440 on every page, sideways scroll at 320,
keyboard pass (skip link first, visible focus ring >= 3:1, menu Esc), carousel keyboard + pause,
open/closed status at fixed Toronto times, reduced-motion check (no running animations/transitions)."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8113/").rstrip("/") + "/"
PAGES = ["about", "index", "owner"]
AXE = Path("/workspace/work/tools/node_modules/axe-core/axe.min.js").read_text()
CHROME = "/usr/bin/google-chrome"
def L(c):
    c = [x / 255 for x in c[:3]]; c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
cr = lambda a, b: (max(L(a), L(b)) + 0.05) / (min(L(a), L(b)) + 0.05)
num = lambda c: [float(x) for x in re.findall(r"[\d.]+", c)][:3]
FOCUS_JS = """()=>{const e=document.activeElement;const s=getComputedStyle(e);let a=e.parentElement,bg=null;while(a){const c=getComputedStyle(a).backgroundColor;if(c&&!c.includes('rgba(0, 0, 0, 0)')&&c!=='transparent'){bg=c;break}a=a.parentElement}
return {body:e===document.body,t:(e.innerText||e.getAttribute('aria-label')||e.querySelector?.('img')?.alt||e.tagName).trim().replace(/\\s+/g,' ').slice(0,30),oc:s.outlineColor,ow:s.outlineWidth,os:s.outlineStyle,bg:bg||'rgb(251, 246, 238)'}}"""
SETTLE = """async()=>{for(let y=0;y<document.body.scrollHeight;y+=500){scrollTo(0,y);await new Promise(r=>setTimeout(r,40))}
document.querySelectorAll('.reveal,[data-stitch]').forEach(e=>e.classList.add('is-in'));scrollTo(0,0);await new Promise(r=>setTimeout(r,1500))}"""
res, fails = {}, []
def check(cond, msg):
    if not cond: fails.append(msg)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    # ---- axe + keyboard at 390 and 1440 ----
    for vp, (w, h) in {"390": (390, 844), "1440": (1440, 900)}.items():
        for n in PAGES:
            r, cons = {}, []
            pg = b.new_page(viewport={"width": w, "height": h}, has_touch=w < 900, is_mobile=w < 900)
            pg.on("console", lambda m: cons.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: cons.append(f"pageerror: {e}"))
            pg.goto(BASE + n + ".html", wait_until="networkidle"); pg.evaluate(SETTLE)
            pg.keyboard.press("Tab")
            r["first_tab"] = pg.evaluate("document.activeElement.className+'|'+(document.activeElement.getBoundingClientRect().left>=0)")
            check(r["first_tab"].startswith("skip-link|true"), f"{n}@{vp}: first Tab is not the visible skip link ({r['first_tab']})")
            pg.evaluate("document.activeElement.blur();scrollTo(0,0)")
            low, stops = [], 0
            for i in range(80):
                pg.keyboard.press("Tab"); f = pg.evaluate(FOCUS_JS); stops += 1
                if i and f["t"] == "Skip to content": break
                if f.get("body") or f["t"] == "IFRAME" or f["t"].startswith("Google Map"): continue
                if f["os"] == "none" or f["ow"] == "0px": low.append(("NO OUTLINE", f["t"])); continue
                if f["oc"].startswith("rgb"):
                    c = cr(num(f["oc"]), num(f["bg"]))
                    if c < 3: low.append((round(c, 2), f["t"], f["oc"], f["bg"]))
            r["focus_stops"], r["focus_low"] = stops, low
            check(not low, f"{n}@{vp}: weak/no focus ring {low}")
            if w < 900:
                pg.evaluate("scrollTo(0,0)"); pg.click("#menu-toggle"); pg.wait_for_timeout(400)
                op = pg.evaluate("({exp:document.getElementById('menu-toggle').getAttribute('aria-expanded'),hidden:document.getElementById('mobile-nav').hidden})")
                pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
                es = pg.evaluate("({exp:document.getElementById('menu-toggle').getAttribute('aria-expanded'),hidden:document.getElementById('mobile-nav').hidden,focus:document.activeElement.id})")
                r["menu"] = (op, es)
                check(op["exp"] == "true" and not op["hidden"] and es["exp"] == "false" and es["hidden"] and es["focus"] == "menu-toggle", f"{n}@{vp}: mobile menu {op} {es}")
            pg.add_script_tag(content=AXE)
            r["axe"] = pg.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}});return {v:r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target.join(' ')+' :: '+n.failureSummary.replace(/\\s+/g,' ').slice(0,160))})),inc:r.incomplete.map(v=>v.id+'('+v.nodes.length+')')}}")
            check(not r["axe"]["v"], f"{n}@{vp}: axe {[(v['id'], v['nodes'][:2]) for v in r['axe']['v']]}")
            r["console"] = [x for x in cons if "Search endpoint" not in x]
            check(not r["console"], f"{n}@{vp}: console errors {r['console']}")
            res[f"{n}@{vp}"] = r
            print(f"{n:8s} {vp:5s} axe={len(r['axe']['v'])} incomplete={r['axe']['inc']} focus_stops={stops} focus_low={len(low)} menu={'ok' if w < 900 else '-'} console={len(r['console'])}")
            pg.close()
    b.close()
Path(__file__).with_name("audit.json").write_text(json.dumps({"results": res, "fails": fails}, indent=1))
print("\nFAILS:" if fails else "\nALL CHECKS PASSED", *fails, sep="\n  ")
