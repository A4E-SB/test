"""
Himaya icon set (v1.7) — ONE consistent stroke-icon family, drawn with PIL.

Why drawn instead of downloaded: Himaya is 100% offline and the build
sandbox has no access to icon CDNs — but PIL is already bundled, and a
Feather-style set is just strokes on a 24px grid. Every icon shares the
same geometry rules (24-grid, 3px padding, 2px stroke, round forms), so
the family is consistent by construction. Rendered at 4x and downscaled
for antialiasing.

This module imports PIL only (no tkinter) — unit-testable headless.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

GRID = 24          # design grid
PAD = 3.5          # padding inside the grid
STROKE = 2

# name -> draw function(d, p) where d = ImageDraw, p = PAD-adjusted coords
def _shield(d, p):
    pts = [(12, p), (20 - p / 2, 3 + p), (20 - p / 2, 10.5),
           (12, 21 - p / 2 + 1), (4 + p / 2, 10.5), (4 + p / 2, 3 + p)]
    d.line(pts + [pts[0]], fill=d._ink, width=STROKE, joint="curve")


def _users(d, p):
    d.ellipse((5.5, 5, 12.5, 12), outline=d._ink, width=STROKE)
    d.arc((4, 12.5, 14, 21.5), 0, 180, fill=d._ink, width=STROKE)
    d.ellipse((15.5, 6.5, 20.5, 11.5), outline=d._ink, width=STROKE)
    d.arc((13.5, 13, 21, 20), 20, 160, fill=d._ink, width=STROKE)


def _package(d, p):
    d.rounded_rectangle((4, 7.5, 20, 19), radius=2, outline=d._ink,
                        width=STROKE)
    d.line((12, 7.5, 12, 11.5), width=STROKE)
    d.line((4, 11.5, 20, 11.5), width=STROKE)


def _cart(d, p):
    d.line([(4, 5), (6, 5), (8, 15), (19, 15)], width=STROKE, joint="curve")
    d.line((8, 8.5, 20, 8.5), width=STROKE)
    d.line((17.5, 8.5, 19, 15), width=STROKE)
    d.ellipse((8, 17.5, 11, 20.5), outline=d._ink, width=STROKE)
    d.ellipse((15, 17.5, 18, 20.5), outline=d._ink, width=STROKE)


def _bell(d, p):
    d.arc((6, 4, 18, 16), 180, 360, fill=d._ink, width=STROKE)
    d.line((6, 10, 6, 15), width=STROKE)
    d.line((18, 10, 18, 15), width=STROKE)
    d.line((4.5, 15.5, 19.5, 15.5), width=STROKE)
    d.arc((10, 16, 14, 20), 0, 180, fill=d._ink, width=STROKE)


def _search(d, p):
    d.ellipse((4.5, 4.5, 15.5, 15.5), outline=d._ink, width=STROKE)
    d.line((14.5, 14.5, 20, 20), width=STROKE)


def _hourglass(d, p):
    d.line([(6, 4.5), (18, 4.5), (12, 12), (6, 4.5)], width=STROKE,
           joint="curve")
    d.line([(12, 12), (18, 19.5), (6, 19.5), (12, 12)], width=STROKE,
           joint="curve")


def _chart(d, p):
    d.line((5, 20, 19, 20), width=STROKE)
    d.line((7.5, 20, 7.5, 13), width=STROKE)
    d.line((12, 20, 12, 7), width=STROKE)
    d.line((16.5, 20, 16.5, 15), width=STROKE)


def _swap(d, p):
    d.line((4, 8.5, 17, 8.5), width=STROKE)
    d.line((14, 5.5, 17, 8.5, 14, 11.5), width=STROKE, joint="curve")
    d.line((20, 15.5, 7, 15.5), width=STROKE)
    d.line((10, 12.5, 7, 15.5, 10, 18.5), width=STROKE, joint="curve")


def _printer(d, p):
    d.rounded_rectangle((5, 8, 19, 16.5), radius=2, outline=d._ink,
                        width=STROKE)
    d.rounded_rectangle((8, 4, 16, 8), radius=1.5, outline=d._ink,
                        width=STROKE)
    d.line((8, 16.5, 8, 20), width=STROKE)
    d.line((16, 16.5, 16, 20), width=STROKE)
    d.line((8, 20, 16, 20), width=STROKE)


def _settings(d, p):
    d.ellipse((8.8, 8.8, 15.2, 15.2), outline=d._ink, width=STROKE)
    for i in range(8):
        a = math.pi / 4 * i
        cx, cy = 12 + 5.2 * math.cos(a), 12 + 5.2 * math.sin(a)
        dx, dy = 2.2 * math.cos(a), 2.2 * math.sin(a)
        d.line((cx - dx, cy - dy, cx + dx, cy + dy), width=STROKE)


def _plugin(d, p):
    d.line((12, 4, 12, 9), width=STROKE)
    d.line((8.5, 6, 15.5, 6), width=STROKE)
    d.rounded_rectangle((7.5, 9, 16.5, 20), radius=2.5, outline=d._ink,
                        width=STROKE)


ICONS = {
    "shield": _shield, "users": _users, "package": _package,
    "cart": _cart, "bell": _bell, "search": _search,
    "hourglass": _hourglass, "chart": _chart, "swap": _swap,
    "printer": _printer, "settings": _settings, "plugin": _plugin,
}


def render(name: str, color: str, size: int = 20) -> Image.Image:
    """One icon as an antialiased RGBA image (4x supersampled)."""
    if name not in ICONS:
        raise KeyError(f"unknown icon: {name}")
    scale = 4
    img = Image.new("RGBA", (GRID * scale, GRID * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d._ink = color
    ICONS[name](d, PAD)
    return img.resize((size, size), Image.LANCZOS)
