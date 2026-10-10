#!/usr/bin/env python3
"""Render the template + content file into the Oks Cars Auto Financing static multi-page demo (Business package sample).
(Forked from the Petz Kingdom / Railroad Coffee Co. builds; same pipeline, checks and export rules.)

    python3 build.py                       # uses src/content.json and ../assets
    python3 build.py --hide-placeholders   # same, without the yellow placeholder markers
    python3 build.py --export              # build, then write a clean publishable copy to ../dist
    python3 build.py --export --dist DIR   # export somewhere else (folder named dist, or under /tmp)
    python3 build.py --content other.json --assets /path/to/assets --out /path/to/out

Pages, nav, images, brand files, hours, services and quotes all come from content.json.
Build variables such as {{GOOGLE_REVIEW_COUNT}} inside content strings are filled from content.json "business".
Outputs (into --out): one .html per entry in content.json "pages", css/site.css, js/site.js,
fonts/, img/ (only the images the content references; SVGs are cleaned on copy).
Dependencies: Jinja2 (required), Pillow (optional, for responsive WebP variants).
"""
import argparse, datetime, hashlib, html as _html, json, posixpath, re, shutil, sys, urllib.parse
from html.parser import HTMLParser
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, ChainableUndefined
    from markupsafe import Markup, escape
except ImportError:
    sys.exit("Jinja2 is required:  pip install jinja2")
try:
    from PIL import Image
except ImportError:
    Image = None

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
# Shared demo-concept share-card logic (titles, descriptions, og-image, export check).
import os
TEMPLATE_DIR = Path(os.environ.get("DEMO_TEMPLATE_DIR", HERE.parents[1] / "_template"))
sys.path.insert(0, str(TEMPLATE_DIR))
try:
    import demo_share
except ImportError:
    sys.exit(f"demo_share.py not found in {TEMPLATE_DIR} (set DEMO_TEMPLATE_DIR)")
IMG_EXTS = [".avif", ".webp", ".jpg", ".jpeg", ".png"]
WIDTHS = [480, 800, 1200, 1600]
DAY_ABBR = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
            "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun"}
# Always banned in exported files; content.json export.banned_words adds more.
BANNED_DEFAULT = ["DRAFT", "TODO", "pending owner", "/workspace", "©", "All rights reserved"]


# ---------------------------------------------------------------------------
# Images and brand files
# ---------------------------------------------------------------------------
def find_asset(assets: Path, filename: str):
    """Exact filename first, then same stem with any common image extension."""
    if not filename or not assets.is_dir():
        return None
    p = assets / filename
    if p.is_file():
        return p
    stem = Path(filename).stem
    for ext in IMG_EXTS + [".svg"]:
        q = assets / f"{stem}{ext}"
        if q.is_file():
            return q
    return None


def clean_svg(text, name):
    """Drop comments, <metadata>, <desc> and editor cruft; keep an accessible <title> naming the business."""
    text = re.sub(r"<!--.*?-->\s*", "", text, flags=re.S)
    text = re.sub(r"<(metadata|desc)\b[^>]*>.*?</\1>\s*", "", text, flags=re.S)
    text = re.sub(r"<(metadata|desc)\b[^>]*/>\s*", "", text)
    text = re.sub(r"<(sodipodi|inkscape):[^>]*?(?:/>|>.*?</\1:[^>]*>)\s*", "", text, flags=re.S)
    text = re.sub(r'\s(?:sodipodi|inkscape):[\w-]+="[^"]*"', "", text)

    def title(m):
        low = m.group(2).lower()
        suffix = " monogram" if "monogram" in low else (" mark" if "mark" in low else "")
        return f"<title{m.group(1)}>{escape(name)}{suffix}</title>"
    return re.sub(r"<title([^>]*)>(.*?)</title>", title, text, flags=re.S)


IMAGE_MAX_KB = 0      # set from content.json meta.image_max_kb (0 = no budget)
IMAGE_LOG = []        # (name, bytes, quality) for the build summary


def save_webp(im, path: Path, quality=80, smooth_first=False):
    """Save WebP within meta.image_max_kb: lower quality to 60 first; if a grainy image still doesn't fit,
    add a very light smoothing pass (0.5 px) and continue down to quality 50."""
    from PIL import ImageFilter
    budget = IMAGE_MAX_KB * 1000          # decimal KB, the stricter reading
    attempts = [(q, False) for q in range(quality, 59, -5)] + [(q, True) for q in range(70, 49, -5)]
    if smooth_first:                      # images.<x>.smooth: grainy stock photo, smooth at every size
        attempts = [(q, True) for q in range(quality, 49, -3)]
    smoothed = None
    for q, smooth in attempts:
        src = im
        if smooth:
            smoothed = smoothed or im.filter(ImageFilter.GaussianBlur(0.5))
            src = smoothed
        src.save(path, "WEBP", quality=q, method=6)
        size = path.stat().st_size
        if not budget or size <= budget:
            break
    IMAGE_LOG.append((path.name, size, q, smooth))
    return size


def process_image(src: Path, out_img: Path, business_name: str, opts=None):
    opts = opts or {}
    """Copy an image and (if Pillow is available) emit WebP width variants for srcset."""
    out_img.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".svg":
        (out_img / src.name).write_text(clean_svg(src.read_text(encoding="utf-8"), business_name), encoding="utf-8")
        size = image_size(src)
        return {"src": f"img/{src.name}", "srcset": f"img/{src.name}",
                "width": size["width"] or 800, "height": size["height"] or 600}
    if Image is None:
        shutil.copy2(src, out_img / src.name)
        return {"src": f"img/{src.name}", "srcset": f"img/{src.name}", "width": 800, "height": 600}
    with Image.open(src) as im:
        im = im.convert("RGB") if im.mode not in ("RGB", "RGBA") else im
        ow, oh = im.size
        cap = int(opts.get("max_width") or WIDTHS[-1])   # images.<x>.max_width: largest variant (detailed, small-on-page images)
        widths = sorted(set([w for w in WIDTHS if w < min(ow, cap)] + [min(ow, cap)]))
        # Skip a near-duplicate top size (e.g. 1280 right after 1200): it adds bytes, not detail.
        if len(widths) > 1 and widths[-1] < widths[-2] * 1.15:
            widths.pop()
        entries = []
        for w in widths:
            h = round(oh * w / ow)
            name = f"{src.stem}-{w}.webp"
            save_webp(im.resize((w, h), Image.LANCZOS), out_img / name,
                      quality=int(opts.get("webp_quality", 80)), smooth_first=bool(opts.get("smooth")))
            entries.append((w, name))
    default = next((n for w, n in entries if w >= 800), entries[-1][1])
    return {"src": f"img/{default}", "srcset": ", ".join(f"img/{n} {w}w" for w, n in entries),
            "width": ow, "height": oh}


def image_size(path: Path):
    """Intrinsic width/height (SVG via width/height or viewBox) for CLS-free <img> tags."""
    try:
        if path.suffix.lower() == ".svg":
            head = path.read_text(encoding="utf-8", errors="ignore")[:2000]
            w = re.search(r'<svg[^>]*\swidth="([\d.]+)', head)
            h = re.search(r'<svg[^>]*\sheight="([\d.]+)', head)
            if w and h:
                return {"width": round(float(w.group(1))), "height": round(float(h.group(1)))}
            vb = re.search(r'viewBox="[\d.\-]+[ ,]+[\d.\-]+[ ,]+([\d.]+)[ ,]+([\d.]+)"', head)
            if vb:
                return {"width": round(float(vb.group(1))), "height": round(float(vb.group(2)))}
        elif Image is not None and path.suffix.lower() != ".ico":
            with Image.open(path) as im:
                return {"width": im.size[0], "height": im.size[1]}
    except Exception:
        pass
    return {"width": None, "height": None}


def css_var(css: str, name: str, fallback: str, _depth=0):
    """Value of a CSS custom property, following var(--x) chains (meta tags can't resolve variables)."""
    m = re.search(rf"--{name}\s*:\s*([^;]+);", css)
    if not m:
        return fallback
    val = m.group(1).strip()
    ref = re.fullmatch(r"var\(\s*--([\w-]+)\s*(?:,\s*([^)]+))?\)", val)
    if ref and _depth < 10:
        return css_var(css, ref.group(1), (ref.group(2) or fallback).strip(), _depth + 1)
    return val


def walk_images(node, fn):
    """Find every image object ({"file": ..., "alt": ...}) anywhere in the content tree."""
    if isinstance(node, dict):
        if "file" in node and "alt" in node:
            fn(node)
        for k, v in node.items():
            if not k.startswith("_"):
                walk_images(v, fn)
    elif isinstance(node, list):
        for v in node:
            walk_images(v, fn)


# ---------------------------------------------------------------------------
# Hours, schema, placeholders
# ---------------------------------------------------------------------------
def group_hours(hours):
    groups = []
    for h in hours:
        disp = "Closed" if h.get("closed") else h["display"]
        if groups and groups[-1]["display"] == disp:
            groups[-1]["days"].append(h["day"])
        else:
            groups.append({"display": disp, "days": [h["day"]]})
    for g in groups:
        d = g["days"]
        g["label"] = DAY_ABBR.get(d[0], d[0]) if len(d) == 1 else f"{DAY_ABBR.get(d[0], d[0])}–{DAY_ABBR.get(d[-1], d[-1])}"
        g["closed"] = g["display"] == "Closed"
    return groups


def schema_org(c, image_url=None):
    """LocalBusiness JSON-LD from real data only: no url until there is a domain, no e-mail,
    aggregateRating only if meta.schema_include_rating (kept false; the export also bans it)."""
    b = c["business"]
    a = b["address"]
    spec = []
    for h in c["hours"]:
        if h.get("closed") or h.get("tbc") or not h.get("opens"):
            continue                      # unconfirmed days stay out of the schema until confirmed
        if spec and spec[-1]["opens"] == h["opens"] and spec[-1]["closes"] == h["closes"]:
            spec[-1]["dayOfWeek"].append(h["day"])
        else:
            spec.append({"@type": "OpeningHoursSpecification", "dayOfWeek": [h["day"]],
                         "opens": h["opens"], "closes": h["closes"]})
    data = {"@context": "https://schema.org", "@type": b.get("schema_type", "Restaurant"), "name": b["name"]}
    if b.get("alternate_name"):
        data["alternateName"] = b["alternate_name"]
    if b.get("cuisine"):
        data["servesCuisine"] = b["cuisine"]
    if b.get("price_range"):
        data["priceRange"] = b["price_range"]
    data["telephone"] = b.get("phone_schema") or b["phone_e164"]
    if b.get("fax_schema"):
        data["faxNumber"] = b["fax_schema"]
    if b.get("email"):
        data["email"] = b["email"]
    data["address"] = {"@type": "PostalAddress",
                       "streetAddress": ", ".join(x for x in (a["street"], a.get("unit")) if x),
                       "addressLocality": a["city"], "addressRegion": a["region"],
                       "postalCode": a["postal_code"], "addressCountry": a["country"]}
    data["address"] = {k: v for k, v in data["address"].items() if v}      # no street/postcode until confirmed
    if b.get("area_served"):
        data["areaServed"] = b["area_served"]
    if spec:
        data["openingHoursSpecification"] = spec
    if b.get("has_map"):
        data["hasMap"] = b["has_map"]
    elif b.get("google_place_id"):
        data["hasMap"] = "https://www.google.com/maps/place/?q=place_id:" + b["google_place_id"]
    geo = b.get("geo") or {}
    if geo.get("latitude") is not None and geo.get("longitude") is not None:
        data["geo"] = {"@type": "GeoCoordinates", "latitude": geo["latitude"], "longitude": geo["longitude"]}
    if image_url:
        data["image"] = image_url
    if b.get("same_as"):
        data["sameAs"] = b["same_as"]          # confirmed public profiles only (Facebook)         # the logo (meta.schema_image), never the og-image
    # Confirmed facts only. offers / payment_accepted / amenities are left unset in content.json for this
    # site until the owner confirms them (export.banned_patterns blocks them); the code stays for reuse.
    if b.get("offers"):                   # names only, no prices (copy.md A8)
        data["makesOffer"] = [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": n}} for n in b["offers"]]
    if b.get("payment_accepted"):          # only once confirmed by the business
        data["paymentAccepted"] = b["payment_accepted"]
    if b.get("amenities"):
        data["amenityFeature"] = [{"@type": "LocationFeatureSpecification", "name": n, "value": True} for n in b["amenities"]]
    if c["meta"].get("schema_include_rating") and b.get("rating"):
        data["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": b["rating"],
                                   "reviewCount": b["review_count"]}
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


# [PLACEHOLDER: x], [OWNER PLACEHOLDER: x], [OWNER APPROVAL NEEDED: x], [CONFIRM HOURS WITH OWNER] ...
PH_RE = re.compile(r"\[((?:OWNER )?PLACEHOLDER|OWNER APPROVAL NEEDED|CONFIRM[A-Z ]*)(?::\s*([^\]]*))?\]")


def ph_label(m):
    kind, text = m.group(1), (m.group(2) or "").strip()
    if kind == "PLACEHOLDER":
        text = re.sub(r"^confirm\s+", "", text, flags=re.I)
        return f"To confirm: {text}" if text else "To confirm"
    if kind == "OWNER PLACEHOLDER":
        return f"To come: {text}" if text else "To come"
    if kind == "OWNER APPROVAL NEEDED":
        # Shown publicly: the text itself (e.g. "Owner story to come"), never an internal instruction.
        return (text[:1].upper() + text[1:]) if text else "Details to come"
    rest = kind[len("CONFIRM"):].strip().lower()           # [CONFIRM HOURS] -> "Hours to be confirmed"
    label = (rest[:1].upper() + rest[1:] + " to be confirmed") if rest else "To be confirmed"
    return label + (f": {text}" if text else "")


def make_ph_filter(show: bool):
    """Escape text; turn placeholder tokens into visible markers, or drop them when hidden."""
    def ph(value):
        if value is None:
            return Markup("")
        text = str(escape(value))
        if show:
            text = PH_RE.sub(lambda m: f'<mark class="ph-inline">{ph_label(m)}</mark>', text)
        else:
            text = re.sub(r"\s{2,}", " ", PH_RE.sub("", text)).strip()
        return Markup(text)
    return ph


def has_text(value):
    """True if a string still has content once placeholders are removed."""
    return bool(value) and bool(PH_RE.sub("", str(value)).strip())


def phone_link(html, business):
    """Turn the display phone number inside a sentence into a tel: link."""
    disp = str(escape(business["phone_display"]))
    return Markup(str(html).replace(disp, f'<a href="tel:{business["phone_e164"]}">{disp}</a>', 1))


def strip_placeholder_menu(c):
    """With --hide-placeholders, drop menu rows whose name is only a placeholder."""
    for cat in c.get("menu", {}).get("categories", []):
        cat["items"] = [i for i in cat.get("items", []) if has_text(i.get("name", ""))]


def find_placeholders(node, path=""):
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k.startswith("_"):
                continue
            if k == "placeholder" and v is True and not node.get("resolved"):
                hits.append(f"{path}: image {node.get('file')} not in assets yet")
            hits += find_placeholders(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits += find_placeholders(v, f"{path}[{i}]")
    elif isinstance(node, str):
        for m in PH_RE.finditer(node):
            hits.append(f"{path}: [{m.group(1)}{': ' + m.group(2) if m.group(2) else ''}]")
    return hits


# ---------------------------------------------------------------------------
# Export: a clean, publishable copy of the built site (nothing from src/).
# ---------------------------------------------------------------------------
SOCIAL_IMAGE_META = ("og:image", "og:image:url", "og:image:secure_url", "twitter:image")


class _RefParser(HTMLParser):
    """Collect every href/src/srcset in an HTML document."""
    def __init__(self, html):
        super().__init__()
        self.refs = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            if (a.get("property") or a.get("name") or "") in SOCIAL_IMAGE_META and a.get("content"):
                self.refs.append(a["content"])
        for k, v in attrs:
            if not v:
                continue
            if k in ("href", "src"):
                self.refs.append(v)
            elif k in ("srcset", "imagesrcset"):
                self.refs.extend(p.strip().split()[0] for p in v.split(",") if p.strip())


def _is_local(ref):
    return not re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", ref, re.I)


def _strip_code_comments(text, js=False):
    """Remove /* */ (and, for JS, //) comments while leaving string literals alone."""
    out, i, n = [], 0, len(text)
    quotes = "'\"`" if js else "'\""
    while i < n:
        ch = text[i]
        if ch in quotes:
            j = i + 1
            while j < n and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1]); i = j + 1
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif js and text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(ch); i += 1
    cleaned = re.sub(r"[ \t]+$", "", "".join(out), flags=re.M)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"


def hours_sentence(hours):
    """Plain-English week summary, e.g. 'Closed Monday. Tuesday to Friday 10 a.m. to 3 p.m.'"""
    parts = []
    for g in group_hours(hours):
        d = g["days"]
        days = d[0] if len(d) == 1 else (f"{d[0]} and {d[1]}" if len(d) == 2 else f"{d[0]} to {d[-1]}")
        if g["closed"]:
            parts.append(f"Closed {days}.")
        else:
            t = g["display"].replace(" – ", " to ").replace("–", " to ")
            parts.append(f"{days} {t}" + ("" if t.endswith(".") else "."))
    return " ".join(parts)


def menu_area_css(menu):
    """Desktop grid-template-areas for the menu cards, generated from content.json menu.desktop_areas."""
    rows = menu.get("desktop_areas") or []
    if not rows:
        return ""
    ids = {cat["id"] for cat in menu.get("categories", [])} | {"pantry"}
    for row in rows:
        for name in row.split():
            if name not in ids and name != ".":
                sys.exit(f"menu.desktop_areas: unknown id {name!r}")
    areas = " ".join(f'"{r}"' for r in rows)
    rules = " ".join(f"#{i} {{ grid-area: {i}; }}" for i in sorted(ids) if any(i in r.split() for r in rows))
    return ("\n/* Generated from content.json menu.desktop_areas */\n@media (min-width: 900px) {\n"
            f"  .menu-cols--areas {{ display: grid; columns: auto; gap: 1.5rem; grid-template-columns: repeat({len(rows[0].split())}, 1fr); "
            f"grid-template-areas: {areas}; align-items: start; }}\n"
            f"  .menu-cols--areas > .menu-cat {{ margin: 0; display: block; }}\n  {rules}\n}}\n")


forbidden_hits = demo_share.forbidden_hits   # shared never-publish matcher (see _template/demo_share.py)


def fill_vars(node, values):
    """Replace {{VAR}} build variables in every content string (e.g. {{GOOGLE_REVIEW_COUNT}})."""
    if isinstance(node, dict):
        return {k: fill_vars(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [fill_vars(v, values) for v in node]
    if isinstance(node, str):
        for k, v in values.items():
            node = node.replace("{{" + k + "}}", str(v))
    return node


def check_jsonld(dist: Path, pages, c, site_url):
    """Structured data holds confirmed facts only: every JSON-LD block parses, it appears on the home page only,
    none of export.schema_forbidden_keys appear at any depth, and `image` is the logo file (absolute under
    site_url, present in dist), never the og-image."""
    problems = []
    forbidden = set(c.get("export", {}).get("schema_forbidden_keys", []))
    logo_key = c["meta"].get("schema_image")
    logo_file = (c.get("brand_files") or {}).get(logo_key, "") if logo_key else ""

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in forbidden:
                    problems.append(f"JSON-LD: forbidden key {path}{k}")
                walk(v, f"{path}{k}.")
        elif isinstance(node, list):
            for v in node:
                walk(v, path)
    found = 0
    for page in pages:
        html = (dist / page).read_text(encoding="utf-8")
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        if blocks and page != "index.html":
            problems.append(f"{page}: JSON-LD outside the home page")
        for raw in blocks:
            found += 1
            try:
                data = json.loads(raw)
            except ValueError as e:
                problems.append(f"{page}: JSON-LD does not parse ({e})")
                continue
            walk(data, "")
            img = data.get("image") if isinstance(data, dict) else None
            if not logo_file:
                problems.append(f"{page}: meta.schema_image must name the logo in brand_files (JSON-LD image = logo)")
            else:
                if not isinstance(img, str) or not img.startswith(site_url):
                    problems.append(f"{page}: JSON-LD image must be an absolute URL under {site_url}: {img!r}")
                else:
                    rel = img[len(site_url):]
                    if Path(rel).name != Path(logo_file).name:
                        problems.append(f"{page}: JSON-LD image must be the logo {logo_file}, not {rel}")
                    if not (dist / rel).is_file():
                        problems.append(f"{page}: JSON-LD image file missing from dist: {rel}")
            if isinstance(img, str) and "og-image" in img:
                problems.append(f"{page}: JSON-LD image points at the og-image")
    if not found:
        problems.append("index.html: no JSON-LD block")
    return problems


def export_site(built: Path, dist: Path, c):
    """Wipe `dist`, copy only the pages + the files they reference, strip comments, run safety checks."""
    project = HERE.parent.resolve()
    dist = dist.resolve()
    if dist in (project, HERE.resolve(), built.resolve(), Path(dist.anchor)) or not (
            dist.name == "dist" or str(dist).startswith("/tmp/")):
        sys.exit(f"Refusing to wipe {dist}: use a folder named 'dist' (or one under /tmp).")
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)

    exp = c.get("export", {})
    banned = list(dict.fromkeys(BANNED_DEFAULT + exp.get("banned_words", [])))
    never = c["_never_publish_all"]
    pages = [p["file"] for p in c["pages"]]
    site_url = (c["meta"].get("site_url") or "").strip()
    site_url = site_url + ("/" if site_url and not site_url.endswith("/") else "")
    needed, problems = set(), []
    for page in pages:
        html = (built / page).read_text(encoding="utf-8")
        if not re.search(r'<meta name="robots" content="noindex[^"]*">', html):
            problems.append(f"{page}: missing noindex meta")
        html = re.sub(r"<!--(?!\[if).*?-->", "", html, flags=re.S)
        lazy = re.findall(r'\bdata-src="([^"]+)"', html) + [u.split()[0] for ss in re.findall(r'\bdata-srcset="([^"]+)"', html) for u in ss.split(",")]
        for ref in _RefParser(html).refs + re.findall(r'\bposter="([^"]+)"', html) + lazy:
            if site_url and ref.startswith(site_url):
                ref = ref[len(site_url):]           # absolute og:image/og:url on our own site -> local file
            if ref.startswith("/") and not ref.startswith("//"):
                problems.append(f"{page}: root-absolute reference {ref}")
            elif _is_local(ref):
                path = ref.split("#")[0].split("?")[0]
                if path:
                    needed.add(path)
        # JSON-LD URLs on our own site (the logo image) must ship in dist too.
        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            for u in re.findall(r'"(https?://[^"]+)"', block):
                if site_url and u.startswith(site_url) and u[len(site_url):]:
                    needed.add(u[len(site_url):].split("#")[0].split("?")[0])
        (dist / page).write_text(html, encoding="utf-8")

    for ref in sorted(p for p in needed if p.endswith(".css")):
        css = (built / ref).read_text(encoding="utf-8")
        for u in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", css):
            if u.startswith("/"):
                problems.append(f"{ref}: root-absolute url({u})")
            elif _is_local(u) and not u.startswith("data:"):
                needed.add(posixpath.normpath(posixpath.join(posixpath.dirname(ref), u.split("?")[0].split("#")[0])))

    for ref in sorted(needed):
        rel = posixpath.normpath(ref)
        if rel in pages:
            continue
        if rel.startswith("..") or rel.split("/")[0] not in ("css", "js", "img", "fonts"):
            problems.append(f"reference outside css/js/img/fonts: {ref}")
            continue
        src = built / rel
        if not src.is_file():
            problems.append(f"missing file for reference: {ref}")
            continue
        dest = dist / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        if ext == ".css":
            dest.write_text(_strip_code_comments(src.read_text(encoding="utf-8")), encoding="utf-8")
        elif ext in (".js", ".mjs"):
            dest.write_text(_strip_code_comments(src.read_text(encoding="utf-8"), js=True), encoding="utf-8")
        elif ext == ".svg":
            dest.write_text(clean_svg(src.read_text(encoding="utf-8"), c["business"]["name"]), encoding="utf-8")
        else:
            shutil.copy2(src, dest)
    (dist / ".nojekyll").write_bytes(b"")
    if (dist / "robots.txt").exists():
        problems.append("robots.txt present")

    hits = []
    files = sorted(f for f in dist.rglob("*") if f.is_file())
    for f in files:
        rel = str(f.relative_to(dist))
        if f.suffix.lower() in (".html", ".css", ".js", ".svg", ".txt", ".json", ".xml"):
            text = f.read_text(encoding="utf-8", errors="ignore")
            for word in banned:
                if word in text:
                    hits.append(f"{rel}: {word}")
            for m in re.findall(r"\{\{\s*[A-Za-z_][\w.]*\s*\}\}|\{%", text):
                problems.append(f"{rel}: unfilled template/build variable {m}")
    # Never-publish files (whole reference folder + named files): shared check.
    np_dirs = tuple(exp.get("never_publish_dirs") or demo_share.NEVER_PUBLISH_DIRS)
    np_problems = demo_share.check_never_publish(dist, never, np_dirs)
    print(f"Never-publish check ({len(never)} files, folder {', '.join(np_dirs)}): {len(np_problems)} problem(s)")
    problems += np_problems
    # Private data patterns (e.g. the owner's personal e-mail domain), case-insensitive.
    pat_problems = demo_share.check_banned_patterns(dist, exp.get("banned_patterns", []))
    print(f"Banned-pattern check ({len(exp.get('banned_patterns', []))} patterns, case-insensitive): {len(pat_problems)} hit(s)")
    problems += pat_problems
    # Demo banner and footer disclaimer must appear, exactly, on every page.
    required = [c["meta"].get(r[1:], "") if r.startswith("@") else r for r in exp.get("required_text", [])]
    req_problems = []
    for page in pages:
        req_problems += demo_share.check_required_text((dist / page).read_text(encoding="utf-8"), page, required)
    print(f"Required-text check ({len(required)} strings x {len(pages)} pages): {len(req_problems)} problem(s)")
    problems += req_problems
    # AI-honest image wording: no leftover "stock image/photo" wording anywhere (shared check).
    stock_problems = demo_share.check_stock_wording(dist)
    print(f"Image-wording check (no 'stock image/photo' wording): {len(stock_problems)} problem(s)")
    problems += stock_problems
    # Share cards must always say "demo concept" (shared check, see _template/demo_share.py).
    share_problems = []
    for page in pages:
        share_problems += demo_share.check_share_tags((dist / page).read_text(encoding="utf-8"), page, site_url, dist)
    print(f"Share-card check ({len(pages)} pages, site_url {site_url or '(empty, relative)'}): {len(share_problems)} problem(s)")
    problems += share_problems

    # JSON-LD: parses, Home only, no forbidden keys, image = the logo under site_url (in dist), not the og-image.
    ld_problems = check_jsonld(dist, pages, c, site_url)
    print(f"JSON-LD check ({len(exp.get('schema_forbidden_keys', []))} forbidden keys, image = logo): {len(ld_problems)} problem(s)")
    problems += ld_problems

    # Visible placeholder markers must read as neutral public text: no personal names or internal notes.
    ph_banned = exp.get("placeholder_banned_words", [])
    ph_count = 0
    for page in pages:
        html = (dist / page).read_text(encoding="utf-8")
        markers = re.findall(r'<mark class="ph-inline">(.*?)</mark>', html, re.S)
        markers += re.findall(r'class="ph-badge(?! image-badge)[^"]*"[^>]*>(.*?)</', html, re.S)
        markers += re.findall(r'<div class="ph-label"[^>]*>(.*?)</div>', html, re.S)
        ph_count += len(markers)
        for mk in markers:
            plain = _html.unescape(re.sub("<[^>]+>", "", mk))
            for word in ph_banned:
                if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", plain, re.I):
                    problems.append(f"{page}: placeholder contains {word!r}: {re.sub('<[^>]+>', '', mk).strip()}")
    print(f"Placeholder wording check ({len(ph_banned)} terms over {ph_count} visible markers): "
          f"{sum(1 for p in problems if 'placeholder contains' in p)} hit(s)")
    max_kb = int(c["meta"].get("image_max_kb") or 0)
    if max_kb:
        for f in files:
            if f.suffix.lower() in (".webp", ".jpg", ".jpeg", ".png", ".avif") and f.stat().st_size > max_kb * 1000:
                problems.append(f"image over {max_kb} KB budget: {f.relative_to(dist)} ({f.stat().st_size // 1000} KB)")
    total = sum(f.stat().st_size for f in files)
    print(f"Exported {len(files)} files ({total / 1024:.1f} KiB) → {dist}")
    print(f"Banned-word check ({len(banned)} terms): {len(hits)} hit(s)")
    for h in hits:
        print("  BANNED:", h)
    for p in problems:
        print("  PROBLEM:", p)
    if problems or hits:
        sys.exit("Export check FAILED")
    print("Export check passed: noindex on every page, relative paths only, no never-publish files, 0 banned words.")


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", default=str(SRC / "content.json"))
    ap.add_argument("--theme", default=str(SRC / "theme.css"))
    ap.add_argument("--assets", default=str(HERE.parent / "assets"),
                    help="folder with logo/photos (default: ../assets next to this site folder)")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--hide-placeholders", action="store_true", help="hide yellow placeholder markers")
    ap.add_argument("--export", action="store_true",
                    help="after building, write only the publishable files (comment-free) to --dist")
    ap.add_argument("--dist", default=str(HERE.parent / "dist"), help="export folder (wiped first)")
    args = ap.parse_args()

    content_path, assets, out = Path(args.content), Path(args.assets), Path(args.out)
    c = json.loads(content_path.read_text(encoding="utf-8"))
    c = fill_vars(c, {"GOOGLE_REVIEW_COUNT": c["business"].get("review_count", "")})
    if args.hide_placeholders:
        c["meta"]["show_placeholder_badges"] = False
        strip_placeholder_menu(c)
    show_ph = bool(c["meta"].get("show_placeholder_badges", True))
    b = c["business"]
    exp = c.get("export", {})
    np_dirs = tuple(exp.get("never_publish_dirs") or demo_share.NEVER_PUBLISH_DIRS)
    globbed = sorted({f.name for g in exp.get("never_publish_globs", []) for f in assets.glob(g) if f.is_file()})
    never = demo_share.never_publish_files(assets, exp.get("never_publish", []) + globbed, np_dirs)
    never_globs = exp.get("never_publish_globs", [])
    c["_never_publish_all"] = never
    global IMAGE_MAX_KB
    IMAGE_MAX_KB = int(c["meta"].get("image_max_kb") or 0)

    # --- images (only what content references); never-publish files are refused outright
    out_img = out / "img"
    if out_img.exists():
        shutil.rmtree(out_img)
    found, missing = [], []

    def guard(name):
        if any(Path(str(name)).match(g) for g in never_globs):
            sys.exit(f"Refusing to use never-publish file {name} (matches {never_globs})")
        bad = forbidden_hits(str(name), never)
        if bad or demo_share.is_never_publish_path(name, np_dirs):
            sys.exit(f"Refusing to use never-publish file {name} ({bad or 'never-publish folder'})")

    def resolve(img):
        guard(img["file"])
        p = find_asset(assets, img["file"])
        if p:
            guard(p.name)
            guard(p)
            img["resolved"] = process_image(p, out_img, b["name"], img)
            found.append(p.name)
        else:
            img["resolved"] = None
            missing.append(img["file"])
    walk_images(c, resolve)

    # --- brand files (logo, footer logo, icons) named in content.json "brand_files"
    files = {}
    for key, fname in (c.get("brand_files") or {}).items():
        if not fname or key.startswith("_"):
            continue
        guard(fname)
        f = find_asset(assets, fname)
        if not f:
            missing.append(fname)
            continue
        out_img.mkdir(parents=True, exist_ok=True)
        if f.suffix.lower() == ".svg":
            (out_img / f.name).write_text(clean_svg(f.read_text(encoding="utf-8"), b["name"]), encoding="utf-8")
        else:
            shutil.copy2(f, out_img / f.name)
        files[key] = {"src": f"img/{f.name}", **image_size(f)}
        found.append(f.name)

    # --- social share image (og:image / twitter:image / JSON-LD image)
    social = None
    sspec = c["meta"].get("social_image") or {}
    simg = (c.get("images") or {}).get(sspec.get("source_image", ""))
    if sspec and simg and Image is not None:
        sp = find_asset(assets, simg["file"])
        if sp:
            guard(sp.name)
            spec = {"badge": c["meta"].get("image_badge", ""), "alt": simg.get("alt", ""), **sspec}
            if spec.get("font") and not Path(spec["font"]).is_absolute():
                spec["font"] = str((HERE / spec["font"]).resolve())
            social = demo_share.make_og_image(sp, out_img, spec, focus=simg.get("focus", ""),
                                              stock=bool(simg.get("illustrative")))
    site_url = demo_share.site_url_of(c)

    def abs_url(path):
        """Absolute when meta.site_url is set, otherwise the relative path (fine for a noindex preview)."""
        return demo_share.abs_url(site_url, path)
    if social:
        social["url"] = abs_url(social["src"])

    # --- css + js + fonts
    (out / "css").mkdir(parents=True, exist_ok=True)
    css = Path(args.theme).read_text(encoding="utf-8") + "\n" + (SRC / "styles.css").read_text(encoding="utf-8")
    (out / "css" / "site.css").write_text(css, encoding="utf-8")
    (out / "js").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / "js" / "site.js", out / "js" / "site.js")
    if (out / "fonts").exists():
        shutil.rmtree(out / "fonts")
    shutil.copytree(SRC / "fonts", out / "fonts")
    for sub in ("hero", "listings"):               # hero stage/part WebPs + sample-listing photos (pre-sized)
        if (assets / sub).is_dir():
            if (out / "img" / sub).exists():
                shutil.rmtree(out / "img" / sub)
            shutil.copytree(assets / sub, out / "img" / sub)
    hv = (c.get("hero_video") or {}).get("file")
    if hv and (assets / Path(hv).name).is_file():   # hero loop (already ffmpeg-compressed in ../assets)
        (out / "img").mkdir(parents=True, exist_ok=True)
        shutil.copy2(assets / Path(hv).name, out / hv)

    # --- derived
    map_q = b.get("map_query") or b["address"]["full"]
    q = urllib.parse.quote_plus(map_q)
    directions_url = "https://www.google.com/maps/dir/?api=1&destination=" + urllib.parse.quote(b.get("directions_query") or map_q)
    if b.get("google_place_id"):
        directions_url += "&query_place_id=" + urllib.parse.quote(b["google_place_id"])
    map_embed_url = f"https://maps.google.com/maps?q={q}&output=embed"
    if b.get("google_cid"):
        # Keyless, pinned to the exact listing (CID = decimal form of the place's feature ID).
        cid = urllib.parse.quote(str(b["google_cid"]))
        map_embed_url = f"https://maps.google.com/maps?cid={cid}&output=embed"
        directions_url = f"https://maps.google.com/?cid={cid}"
    if b.get("directions_url"):
        directions_url = b["directions_url"]       # explicit directions link to the verified listing
    hours_grouped = group_hours(c["hours"])
    def plain(text):
        """Placeholder tokens as neutral words for places that can't show markup (JS 'hours today')."""
        return PH_RE.sub(lambda m: ph_label(m), text or "")
    hours_json = json.dumps(
        [{"day": h["day"], "display": plain(h.get("display", "")), "closed": bool(h.get("closed")),
          "opens": h.get("opens", ""), "closes": h.get("closes", "")} for h in c["hours"]],
        ensure_ascii=False)
    quotes = {t["id"]: t for t in c.get("testimonials", {}).get("items", [])}
    build_id = hashlib.sha1((css + (SRC / "js" / "site.js").read_text()).encode()).hexdigest()[:8]
    pages = c["pages"]
    base_ctx = {
        "c": c, "b": b, "show_ph": show_ph,
        "year": datetime.date.today().year,
        "build_id": build_id,
        "nav": [p for p in pages if p.get("nav_label")],
        "page_href": {p["id"]: p["file"] for p in pages},
        "map_embed_url": map_embed_url,
        "directions_url": directions_url,
        "reviews_url": b.get("reviews_url") or "",
        "hours_grouped": hours_grouped,
        "hours_week_summary": " · ".join(f'{g["label"]} {g["display"]}' for g in hours_grouped),
        "hours_json": hours_json.replace("</", "<\\/"),
        "quotes": quotes,
        "files": files,
        "theme_color": c["meta"].get("theme_color") or css_var(css, "color-bg", "#ffffff"),
        "schema_json": schema_org(c, abs_url(files[c["meta"]["schema_image"]]["src"])
                                  if c["meta"].get("schema_image") in files else None),
        "hours_sentence": hours_sentence(c["hours"]),
        "social": social,
        "site_url": site_url,
        "page_url": (lambda f: abs_url("" if f == "index.html" else f) if site_url else ""),
    }

    env = Environment(loader=FileSystemLoader([str(SRC / "templates"), str(demo_share.TEMPLATES_DIR)]), autoescape=True,
                      undefined=ChainableUndefined, trim_blocks=False, lstrip_blocks=False)
    env.globals.update(show_ph=show_ph, has_text=has_text)
    env.filters["ph"] = make_ph_filter(show_ph)
    env.filters["phone_link"] = phone_link

    built = []
    for page in pages:
        share = demo_share.page_share(c, page, page["file"], social)
        html = env.get_template(page["template"]).render(**base_ctx, page=page, share=share)
        (out / page["file"]).write_text(html, encoding="utf-8")
        built.append(f'{page["file"]} ({len(html):,} bytes)')

    print(f"Built {len(built)} pages → {out}")
    for line in built:
        print(f"  - {line}")
    print(f"Assets dir: {assets}  ({'found' if assets.is_dir() else 'NOT FOUND'})")
    print(f"  used:    {', '.join(dict.fromkeys(found)) or '-'}")
    print(f"  missing: {', '.join(dict.fromkeys(missing)) or '-'}")
    if IMAGE_LOG:
        big = max(IMAGE_LOG, key=lambda x: x[1])
        print(f"WebP variants: {len(IMAGE_LOG)}, largest {big[0]} {big[1] / 1024:.1f} KiB"
              + (f" (budget {IMAGE_MAX_KB} KB)" if IMAGE_MAX_KB else ""))
        for n, size, q, smooth in IMAGE_LOG:
            if q < 80 or smooth:
                print(f"  re-encoded to fit budget: {n} {size / 1024:.1f} KiB at q{q}" + (" + 0.5px smoothing" if smooth else ""))
            if IMAGE_MAX_KB and size > IMAGE_MAX_KB * 1000:
                print(f"  WARNING over budget: {n} {size / 1024:.1f} KiB")
    if social:
        print(f"Social image: {social['src']} {social['width']}x{social['height']} ({social['bytes'] / 1024:.1f} KiB)"
              f" -> og:image {social['url']}")
    ph = find_placeholders(c)
    print(f"Placeholders remaining in content: {len(ph)}")
    for h in ph:
        print("  -", h)
    if args.export:
        export_site(out, Path(args.dist), c)


if __name__ == "__main__":
    main()
