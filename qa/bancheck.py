"""Static ban/rule checks over dist/ for the Oks Cars demo (complements build.py's export checks)."""
import json, re, html as H
from pathlib import Path
D = Path("/workspace/sites/okscars/dist")
BANNER = "Business package demo concept"
FOOTER = "Demo concept, not affiliated with or approved by Oks Cars Auto Financing."
BADGE = "Illustrative image, not a photo of Oks Cars' units"
FB = "https://www.facebook.com/profile.php?id=100063768174483"
fails, lines = [], []
def ok(c, m): lines.append(("PASS " if c else "FAIL ") + m); c or fails.append(m)
pages = sorted(D.glob("*.html"))
texts = {f: f.read_text() for f in D.rglob("*") if f.suffix in (".html", ".css", ".js", ".svg", ".json", ".txt", ".xml")}
alltext = "\n".join(texts.values()); low = alltext.lower()
ok(not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", alltext, re.I), "no e-mail address anywhere in dist")
for w in ["mailto", "kennyboooo", "yahoo", "gmail", "aggregaterating", "oliver", "kenneth", "santos", "dennis", "m.me/"]:
    ok(w not in low, f"no '{w}' anywhere")
vis = H.unescape(" ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", texts[f], flags=re.S)) for f in texts if f.suffix == ".html"))
for pat, why in [(r"\b(BDO|BPI|PNB|RCBC|AUB|PSBank)\b|metrobank|security bank|china ?bank|union ?bank|eastwest|maybank|landbank", "real bank names"),
                 (r"guarantee|warrant", "guarantees/warranties"), (r"\b0% interest|zero interest|lowest rate|\binterest rate of", "rate claims"),
                 (r"since (19|20)\d\d|award|\bcertified", "years/awards"), (r"\bstock\b", "'stock' wording"), (r"\$\s?\d", "$ prices")]:
    ok(not re.search(pat, vis, re.I), f"no {why} in visible text")
ok(not re.search(r"₱\s?\d[\d,]*\s*(?:–|-|to)\s*₱", vis), "no invented price ranges")
ok(all('href="tel:+639457743386"' in p.read_text() for p in pages), "tap-to-call on every page")
ok(all(FB in p.read_text() for p in pages), "Facebook link on every page")
ok(all("Message us on Facebook" in p.read_text() for p in pages), "'Message us on Facebook' on every page")
idx = H.unescape((D / "index.html").read_text())
for s in ["Where approval stories", "1000+", "happy clients", "10+ bank partners", "287K", "Promo to confirm · Terms apply", "₱9K or ₱19K", "Tara, apply na!", "Sulit"]:
    ok(s in idx, f"Home has '{s}'")
ok('class="stamp"' in idx and "Approved" in idx, "APPROVED stamp on Home")
cars = H.unescape((D / "cars-for-sale.html").read_text())
ok(cars.count('class="badge-sample">Sample listing') == 6, "6 listings badged 'Sample listing'")
ok(cars.count("Ask for price") == 6, "each listing 'Ask for price'")
ok("2023 Nissan Almera 1.0 Turbo AT" in cars, "Almera sample listing")
ok(cars.count('class="chip"') == 9 and 'aria-pressed="true"' in cars, "filter chips (condition + body) with aria-pressed")
fin = H.unescape((D / "financing.html").read_text())
ok("Estimate only. Actual terms depend on the bank." in fin and 'aria-live="polite"' in fin, "calculator disclaimer + live region")
ok(all(f'<label for="{i}"' in fin for i in ["c-price", "c-term", "c-rate"]) and "Example rate only" in fin, "calculator labelled + example rate marked")
for fid in ["a-name", "a-mobile", "a-car", "a-dp", "a-emp", "a-msg"]:
    ok(f'<label for="{fid}"' in fin, f"apply form field {fid} labelled")
for f in ["financing.html", "sell-your-car.html", "contact.html"]:
    t = (D / f).read_text(); ok("<fieldset disabled>" in t and "This form is disabled in this demo" in t, f"{f}: form disabled with note")
sell = (D / "sell-your-car.html").read_text()
ok(all(f'id="{i}"' in sell for i in ["s-make", "s-model", "s-year", "s-km", "s-photos"]) and 'type="file" accept="image/*" multiple' in sell, "sell form make/model/year/mileage/photos")
con = H.unescape((D / "contact.html").read_text())
ok(not re.search(r"instagram|tiktok", low), "no instagram/tiktok text, links, icons or data anywhere in dist")
ok("Handle to confirm" not in alltext and not re.search(r'href="#"', alltext), "no social placeholder links or 'Handle to confirm' notes")
ok("Antipolo, Rizal" in con and "<iframe" not in con, "location city only, no map embed")
ok(not re.search(r"\b\d+(\.\d+)?\s?% (?:interest|add-on)", vis, re.I), "no rate presented as theirs")
ok((D / ".nojekyll").exists(), ".nojekyll present")
ok(not (D / "img/logo.svg").exists() and not (D / "img/logo.png").exists() and not (D / "img/favicon-512.png").exists(), "old made-up logo files gone")
ok(all('class="brand__logo" src="img/logo-96.png"' in p.read_text() and 'width="56" height="56"' in p.read_text() for p in pages), "real logo in header on every page (sized)")
ok(all('rel="manifest" href="img/site.webmanifest"' in p.read_text() for p in pages), "manifest linked on every page")
ok("Illustrative" not in re.sub(r'<div class="(media|listing__art).*?</div>', "", idx, flags=re.S).split('class="site-header"')[1].split("</header>")[0], "logo not badged as illustrative")
for f in pages:
    s = f.read_text(); u = H.unescape(s); n = f.name
    ok('<meta name="robots" content="noindex, nofollow">' in s, f"{n}: noindex")
    ok(BANNER in u and s.index('class="demo-banner"') < s.index('class="skip-link"'), f"{n}: demo banner")
    ok(FOOTER in u, f"{n}: footer disclaimer")
    for k in ("og:title", "twitter:title", "og:site_name"):
        m = re.search(rf'(?:property|name)="{k}" content="([^"]+)"', s)
        ok(m and "(demo concept)" in m.group(1), f"{n}: {k} has '(demo concept)'")
    ok("(demo concept)" in re.search(r"<title>(.*?)</title>", s).group(1), f"{n}: <title> has '(demo concept)'")
    refs = re.findall(r'(?:href|src|poster)="([^"]+)"', s) + [u2.split()[0] for ss in re.findall(r'srcset="([^"]+)"', s) for u2 in ss.split(",")]
    bad = [r for r in refs if r.startswith("/") or (not re.match(r"^(https?:|tel:|#)", r) and not (D / r.split("#")[0].split("?")[0]).exists())]
    ok(not bad, f"{n}: all refs relative and resolvable {bad[:3]}")
    for img in re.findall(r"<img\b[^>]*>", s):
        ok(re.search(r'\swidth="\d+"', img) and re.search(r'\sheight="\d+"', img), f"{n}: img has width/height")
    for m in re.finditer(r'<div class="(media|listing__art)[^"]*"[^>]*>(.*?)</div>', s, re.S):
        ok(BADGE in H.unescape(m.group(2)), f"{n}: image badged")
    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        d = json.loads(ld)
        ok(d["@type"] == ["AutoDealer"] and set(d) <= {"@context", "@type", "name", "address", "telephone", "image", "sameAs"} and d["sameAs"] == [FB] and d["image"].endswith("img/logo-512.png"), f"{n}: JSON-LD keys {sorted(d)}")
big = [(f.name, f.stat().st_size) for f in D.rglob("*") if f.suffix in (".webp", ".jpg", ".png") and f.stat().st_size >= 150_000]
ok(not big, f"all images under 150 KB {big}")
print("\n".join(lines)); print(f"\n{len(lines) - len(fails)} passed, {len(fails)} failed")
