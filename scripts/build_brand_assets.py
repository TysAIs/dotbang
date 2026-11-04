#!/usr/bin/env python3
"""Build the dotBANG brand assets from the construction geometry.

Source of truth: DOTBANG-DESIGN-LANGUAGE-2026-11-04.md sections 2 and 4.
Everything here is integer geometry on a module grid -- no curves, no radius,
no blur, no gradient. Three colour states only.

Geometry (module m):                 box = 3m x 5m
    "."  1m x 1m  at col 1, row 5
    "!"  stem 1m x 3m at col 3, rows 1-3 ; dot 1m x 1m at col 3, row 5

    python3 scripts/build_brand_assets.py --ttf-dir /path/to/ttf

Vector output needs no dependencies. Raster output needs Pillow; the wordmark
on the social banners needs a JetBrains Mono TTF in --ttf-dir (the OFL woff2
files in assets/fonts are for the site, not for this script). Without a TTF
the banners are still written, mark-only, and the script says so.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FIELD = "#000000"
INK = "#FFFFFF"
SIGNAL = "#6CACE4"

# The only three legal colour states (design language section 4).
STATES = {
    "default": {"field": FIELD, "glyph": INK, "dot": INK},
    "signal": {"field": FIELD, "glyph": INK, "dot": SIGNAL},
    "inverse": {"field": INK, "glyph": FIELD, "dot": FIELD},
}

SOCIAL_SIZES = {
    "avatar": (400, 400),
    "banner": (1500, 500),
    "cover": (1280, 720),
}


def mark_rects(m, ox=0, oy=0, dot_color=None, glyph_color=None):
    """Return (x, y, w, h, color) rects for the mark: 3m x 5m box."""
    glyph_color = glyph_color or INK
    dot_color = dot_color or glyph_color
    return [
        (ox, oy + 4 * m, 1 * m, 1 * m, dot_color),        # period, col 1 row 5
        (ox + 2 * m, oy, 1 * m, 3 * m, glyph_color),      # bang stem, col 3 rows 1-3
        (ox + 2 * m, oy + 4 * m, 1 * m, 1 * m, glyph_color),  # bang dot, col 3 row 5
    ]


def svg_mark(state, field=None):
    """Transparent-background mark SVG on a 3x5 module viewBox."""
    s = STATES[state]
    parts = []
    if field:
        parts.append('<rect width="3" height="5" fill="%s"/>' % s["field"])
    for x, y, w, h, color in mark_rects(1, 0, 0, s["dot"], s["glyph"]):
        parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
                     % (x, y, w, h, color))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3 5" '
            'width="12" height="20" shape-rendering="crispEdges">\n  %s\n</svg>\n'
            % "\n  ".join(parts))


def svg_favicon(module=4, box=28):
    """Favicon on the module grid: black field, white mark, 2-module clearspace."""
    mark_w, mark_h = 3 * module, 5 * module
    ox = (box - mark_w) // 2
    oy = (box - mark_h) // 2
    ox -= ox % (module // 2)
    oy -= oy % (module // 2)
    parts = ['<rect width="%d" height="%d" fill="%s"/>' % (box, box, FIELD)]
    for x, y, w, h, color in mark_rects(module, ox, oy, INK, INK):
        parts.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>'
                     % (x, y, w, h, color))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
            'width="%d" height="%d" shape-rendering="crispEdges">\n  %s\n</svg>\n'
            % (box, box, box, box, "\n  ".join(parts)))


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print("wrote %s" % path.relative_to(ROOT))


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ttf-dir", default="", help="directory holding JetBrainsMono[wght].ttf")
    ap.add_argument("--no-raster", action="store_true")
    args = ap.parse_args()

    # --- vector -----------------------------------------------------------
    brand = ROOT / "assets" / "brand"
    write_text(brand / "mark.svg", svg_mark("default"))
    write_text(brand / "mark-signal.svg", svg_mark("signal"))
    write_text(brand / "mark-inverse.svg", svg_mark("inverse"))
    write_text(ROOT / "assets" / "favicon.svg", svg_favicon())

    if args.no_raster:
        return 0

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow missing: vector only, no PNG written.", file=sys.stderr)
        return 1

    def blank(w, h, color=None):
        if color:
            return Image.new("RGB", (w, h), hexrgb(color))
        return Image.new("RGBA", (w, h), (0, 0, 0, 0))

    def draw_mark(draw, m, ox, oy, dot, glyph):
        for x, y, w, h, color in mark_rects(m, ox, oy, dot, glyph):
            draw.rectangle([x, y, x + w - 1, y + h - 1], fill=hexrgb(color))

    # --- mark PNG set, 1x / 2x / 4x, three states -------------------------
    png = brand / "png"
    for state, s in STATES.items():
        for mult in (1, 2, 4):
            m = 4 * mult
            img = blank(3 * m, 5 * m)
            draw_mark(ImageDraw.Draw(img), m, 0, 0, s["dot"], s["glyph"])
            out = png / ("mark-%s-%dx.png" % (state, mult))
            out.parent.mkdir(parents=True, exist_ok=True)
            img.save(out)
            print("wrote %s (%dx%d)" % (out.relative_to(ROOT), img.width, img.height))

    for box in (16, 32):
        img = Image.new("RGB", (box, box), hexrgb(FIELD))
        m = box // 7  # 3 modules of mark + clearspace on a 7-module box
        m = max(1, m)
        ox = (box - 3 * m) // 2
        oy = (box - 5 * m) // 2
        draw_mark(ImageDraw.Draw(img), m, ox, oy, INK, INK)
        out = ROOT / "assets" / ("favicon-%d.png" % box)
        img.save(out)
        print("wrote %s (%dx%d, module %d)" % (out.relative_to(ROOT), box, box, m))

    # --- social assets ----------------------------------------------------
    font_path = None
    if args.ttf_dir:
        cand = Path(args.ttf_dir) / "JetBrainsMono[wght].ttf"
        if cand.exists():
            font_path = cand
    if not font_path:
        print("no JetBrainsMono[wght].ttf in --ttf-dir: writing mark-only social art")

    def load(size):
        if not font_path:
            return None
        f = ImageFont.truetype(str(font_path), size)
        try:
            f.set_variation_by_axes([700])
        except Exception:
            pass
        return f

    def muted(color, alpha):
        """Blend a colour onto the field at alpha -- no RGBA layer tricks."""
        fr, fg, fb = hexrgb(color)
        br, bg, bb = hexrgb(FIELD)
        return (int(fr * alpha + br * (1 - alpha)),
                int(fg * alpha + bg * (1 - alpha)),
                int(fb * alpha + bb * (1 - alpha)))

    def wordmark(draw, xy, size, color, anchor="ls"):
        f = load(size)
        if f is None:
            return 0
        draw.text(xy, "dotBANG", font=f, fill=hexrgb(color), anchor=anchor)
        return draw.textlength("dotBANG", font=f)

    def tagline(draw, xy, size, color, anchor="ls"):
        f = load(size)
        if f is None:
            return
        draw.text(xy, "Local AI, knowledge first.", font=f,
                  fill=muted(color, 0.6), anchor=anchor)

    social = ROOT / "assets" / "social"
    social.mkdir(parents=True, exist_ok=True)

    for state, s in STATES.items():
        # avatar: mark only, generous clearspace, module 24
        w, h = SOCIAL_SIZES["avatar"]
        img = blank(w, h, s["field"])
        m = 24
        draw_mark(ImageDraw.Draw(img), m, (w - 3 * m) // 2, (h - 5 * m) // 2, s["dot"], s["glyph"])
        out = social / ("dotbang-avatar-400x400-%s.png" % state)
        img.save(out)
        print("wrote %s" % out.relative_to(ROOT))

        # banner 1500x500: mark left, wordmark, tagline, module 40
        w, h = SOCIAL_SIZES["banner"]
        img = blank(w, h, s["field"])
        d = ImageDraw.Draw(img)
        m = 40
        draw_mark(d, m, 100, 150, s["dot"], s["glyph"])
        if font_path:
            wordmark(d, (260, 350), 150, s["glyph"])
            tagline(d, (264, 430), 26, s["glyph"])
        out = social / ("dotbang-banner-1500x500-%s.png" % state)
        img.save(out)
        print("wrote %s" % out.relative_to(ROOT))

        # cover 1280x720: centred stack, module 40
        w, h = SOCIAL_SIZES["cover"]
        img = blank(w, h, s["field"])
        d = ImageDraw.Draw(img)
        m = 40
        draw_mark(d, m, (w - 3 * m) // 2, 150, s["dot"], s["glyph"])
        if font_path:
            wordmark(d, (w // 2, 560), 120, s["glyph"], anchor="ms")
            tagline(d, (w // 2, 625), 26, s["glyph"], anchor="ms")
        out = social / ("dotbang-cover-1280x720-%s.png" % state)
        img.save(out)
        print("wrote %s" % out.relative_to(ROOT))

    return 0


if __name__ == "__main__":
    sys.exit(main())
