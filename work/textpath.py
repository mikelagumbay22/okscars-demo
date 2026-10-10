import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
import cairosvg, os

F = '/workspace/sites/okscars/work/fonts/'
OUT = '/workspace/sites/sadaf-cleaners/assets/'
_cache = {}
def font(name):
    if name not in _cache:
        path = F + name
        blob = hb.Blob.from_file_path(path)
        _cache[name] = (TTFont(path), hb.Font(hb.Face(blob)))
    return _cache[name]

def shape(name, text, size, tracking_em=0.0):
    """return list of (glyphname, x_units) and total advance in px"""
    tt, hf = font(name)
    upem = tt['head'].unitsPerEm
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(hf, buf, {"kern": True, "liga": True, "lnum": True})
    order = tt.getGlyphOrder()
    x = 0; out = []
    track = tracking_em * upem
    n = len(buf.glyph_infos)
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        out.append((order[info.codepoint], x + pos.x_offset))
        x += pos.x_advance + (track if i < n - 1 else 0)
    return out, x * size / upem

def path(name, text, size, x0, baseline, tracking_em=0.0):
    tt, _ = font(name)
    upem = tt['head'].unitsPerEm; s = size / upem
    gs = tt.getGlyphSet()
    glyphs, adv = shape(name, text, size, tracking_em)
    pen = SVGPathPen(gs, ntos=lambda v: ('%.2f' % v).rstrip('0').rstrip('.'))
    bp = BoundsPen(gs)
    for g, gx in glyphs:
        t = (s, 0, 0, -s, x0 + gx * s, baseline)
        gs[g].draw(TransformPen(pen, t)); gs[g].draw(TransformPen(bp, t))
    return pen.getCommands(), adv, bp.bounds

