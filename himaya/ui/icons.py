"""
Himaya icon set (v1.7.1) — ONE consistent stroke-icon family, drawn with PIL.

Why drawn instead of downloaded: Himaya is 100% offline and the build
sandbox has no access to icon CDNs — but PIL is already bundled, and a
Feather-style set is just strokes on a 24px grid. Every icon shares the
same geometry rules (24-grid, 2px stroke, round forms), rendered at 4x
and downscaled for antialiasing.

v1.7.1 FIX: the first version drew 24-grid coordinates directly on the
4x canvas — every icon came out as a tiny squiggle in the top-left
corner. All coordinates are now multiplied by the scale factor k (and
so is the stroke width). A bbox regression test guards this forever.

This module imports PIL only (no tkinter) — unit-testable headless.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw

GRID = 24          # design grid
STROKE = 2         # stroke width, in grid units
SS = 4             # supersampling factor


def _shield(d, k):
    pts = [(12, 3.5), (20, 6.5), (20, 11.5), (12, 20.5), (4, 11.5), (4, 6.5)]
    flat = [v for p in pts for v in (p[0] * k, p[1] * k)]
    d.line(flat + [flat[0], flat[1]], fill=d._ink, width=STROKE * k, joint="curve")


def _users(d, k):
    d.ellipse((5.5 * k, 5 * k, 12.5 * k, 12 * k), outline=d._ink, width=STROKE * k)
    d.arc((4 * k, 12.5 * k, 14 * k, 21.5 * k), 0, 180, fill=d._ink, width=STROKE * k)
    d.ellipse((15.5 * k, 6.5 * k, 20.5 * k, 11.5 * k), outline=d._ink, width=STROKE * k)
    d.arc((13.5 * k, 13 * k, 21 * k, 20 * k), 20, 160, fill=d._ink, width=STROKE * k)


def _package(d, k):
    d.rounded_rectangle((4 * k, 7.5 * k, 20 * k, 19 * k), radius=2 * k,
                        outline=d._ink, width=STROKE * k)
    d.line((12 * k, 7.5 * k, 12 * k, 11.5 * k), fill=d._ink, width=STROKE * k)
    d.line((4 * k, 11.5 * k, 20 * k, 11.5 * k), fill=d._ink, width=STROKE * k)


def _cart(d, k):
    d.line([(4 * k, 5 * k), (6 * k, 5 * k), (8 * k, 15 * k), (19 * k, 15 * k)],
           fill=d._ink, width=STROKE * k, joint="curve")
    d.line((8 * k, 8.5 * k, 20 * k, 8.5 * k), fill=d._ink, width=STROKE * k)
    d.line((17.5 * k, 8.5 * k, 19 * k, 15 * k), fill=d._ink, width=STROKE * k)
    d.ellipse((8 * k, 17.5 * k, 11 * k, 20.5 * k), outline=d._ink, width=STROKE * k)
    d.ellipse((15 * k, 17.5 * k, 18 * k, 20.5 * k), outline=d._ink, width=STROKE * k)


def _bell(d, k):
    d.arc((6 * k, 4 * k, 18 * k, 16 * k), 180, 360, fill=d._ink, width=STROKE * k)
    d.line((6 * k, 10 * k, 6 * k, 15 * k), fill=d._ink, width=STROKE * k)
    d.line((18 * k, 10 * k, 18 * k, 15 * k), fill=d._ink, width=STROKE * k)
    d.line((4.5 * k, 15.5 * k, 19.5 * k, 15.5 * k), fill=d._ink, width=STROKE * k)
    d.arc((10 * k, 16 * k, 14 * k, 20 * k), 0, 180, fill=d._ink, width=STROKE * k)


def _search(d, k):
    d.ellipse((4.5 * k, 4.5 * k, 15.5 * k, 15.5 * k), outline=d._ink, width=STROKE * k)
    d.line((14.5 * k, 14.5 * k, 20 * k, 20 * k), fill=d._ink, width=STROKE * k)


def _hourglass(d, k):
    d.line([(6 * k, 4.5 * k), (18 * k, 4.5 * k), (12 * k, 12 * k), (6 * k, 4.5 * k)],
           fill=d._ink, width=STROKE * k, joint="curve")
    d.line([(12 * k, 12 * k), (18 * k, 19.5 * k), (6 * k, 19.5 * k), (12 * k, 12 * k)],
           fill=d._ink, width=STROKE * k, joint="curve")


def _chart(d, k):
    d.line((5 * k, 20 * k, 19 * k, 20 * k), fill=d._ink, width=STROKE * k)
    d.line((7.5 * k, 20 * k, 7.5 * k, 13 * k), fill=d._ink, width=STROKE * k)
    d.line((12 * k, 20 * k, 12 * k, 7 * k), fill=d._ink, width=STROKE * k)
    d.line((16.5 * k, 20 * k, 16.5 * k, 15 * k), fill=d._ink, width=STROKE * k)


def _swap(d, k):
    d.line((4 * k, 8.5 * k, 17 * k, 8.5 * k), fill=d._ink, width=STROKE * k)
    d.line((14 * k, 5.5 * k, 17 * k, 8.5 * k, 14 * k, 11.5 * k),
           fill=d._ink, width=STROKE * k, joint="curve")
    d.line((20 * k, 15.5 * k, 7 * k, 15.5 * k), fill=d._ink, width=STROKE * k)
    d.line((10 * k, 12.5 * k, 7 * k, 15.5 * k, 10 * k, 18.5 * k),
           fill=d._ink, width=STROKE * k, joint="curve")


def _printer(d, k):
    d.rounded_rectangle((5 * k, 8 * k, 19 * k, 16.5 * k), radius=2 * k,
                        outline=d._ink, width=STROKE * k)
    d.rounded_rectangle((8 * k, 4 * k, 16 * k, 8 * k), radius=1.5 * k,
                        outline=d._ink, width=STROKE * k)
    d.line((8 * k, 16.5 * k, 8 * k, 20 * k), fill=d._ink, width=STROKE * k)
    d.line((16 * k, 16.5 * k, 16 * k, 20 * k), fill=d._ink, width=STROKE * k)
    d.line((8 * k, 20 * k, 16 * k, 20 * k), fill=d._ink, width=STROKE * k)


def _settings(d, k):
    d.ellipse((8.8 * k, 8.8 * k, 15.2 * k, 15.2 * k), outline=d._ink, width=STROKE * k)
    for i in range(8):
        a = math.pi / 4 * i
        cx, cy = 12 + 5.2 * math.cos(a), 12 + 5.2 * math.sin(a)
        dx, dy = 2.2 * math.cos(a), 2.2 * math.sin(a)
        d.line((cx * k - dx * k, cy * k - dy * k, cx * k + dx * k, cy * k + dy * k),
               fill=d._ink, width=STROKE * k)


def _plugin(d, k):
    d.line((12 * k, 4 * k, 12 * k, 9 * k), fill=d._ink, width=STROKE * k)
    d.line((8.5 * k, 6 * k, 15.5 * k, 6 * k), fill=d._ink, width=STROKE * k)
    d.rounded_rectangle((7.5 * k, 9 * k, 16.5 * k, 20 * k), radius=2.5 * k,
                        outline=d._ink, width=STROKE * k)


def _truck(d, k):
    d.rounded_rectangle((3.5 * k, 6.5 * k, 14.5 * k, 17.5 * k), radius=1.5 * k,
                        outline=d._ink, width=STROKE * k)
    d.line((14.5 * k, 10 * k, 18.5 * k, 10 * k), fill=d._ink, width=STROKE * k)
    d.line((18.5 * k, 10 * k, 20.5 * k, 12.5 * k), fill=d._ink, width=STROKE * k)
    d.line((20.5 * k, 12.5 * k, 20.5 * k, 17.5 * k), fill=d._ink, width=STROKE * k)
    d.line((14.5 * k, 17.5 * k, 20.5 * k, 17.5 * k), fill=d._ink, width=STROKE * k)
    d.ellipse((6 * k, 16 * k, 9.5 * k, 19.5 * k), outline=d._ink, width=STROKE * k)
    d.ellipse((15.5 * k, 16 * k, 19 * k, 19.5 * k), outline=d._ink, width=STROKE * k)


def _check(d, k):
    d.ellipse((4 * k, 4 * k, 20 * k, 20 * k), outline=d._ink, width=STROKE * k)
    d.line((8 * k, 12.2 * k, 11 * k, 15.2 * k, 16.2 * k, 9 * k),
           fill=d._ink, width=STROKE * k, joint="curve")


def _ghost(d, k):
    d.arc((5 * k, 3.5 * k, 19 * k, 17.5 * k), 180, 360, fill=d._ink, width=STROKE * k)
    d.line((5 * k, 10.5 * k, 5 * k, 17 * k), fill=d._ink, width=STROKE * k)
    d.line((19 * k, 10.5 * k, 19 * k, 17 * k), fill=d._ink, width=STROKE * k)
    d.line((5 * k, 17 * k, 8 * k, 14.5 * k, 12 * k, 17 * k, 16 * k, 14.5 * k,
            19 * k, 17 * k), fill=d._ink, width=STROKE * k, joint="curve")
    d.ellipse((8.6 * k, 9 * k, 10.2 * k, 10.6 * k), fill=d._ink)
    d.ellipse((13.8 * k, 9 * k, 15.4 * k, 10.6 * k), fill=d._ink)


ICONS = {
    "shield": _shield, "users": _users, "package": _package,
    "cart": _cart, "bell": _bell, "search": _search,
    "hourglass": _hourglass, "chart": _chart, "swap": _swap,
    "printer": _printer, "settings": _settings, "plugin": _plugin,
    "truck": _truck, "check": _check, "ghost": _ghost,
}


_CACHE: dict[tuple, Image.Image] = {}


def render(name: str, color: str, size: int = 20) -> Image.Image:
    """One icon as an antialiased RGBA image (4x supersampled, k-scaled).
    Cached: the same (name, color, size) renders ONCE per process — weak
    machines were paying the supersample+LANCZOS cost on every page build
    that recreates its icons (dashboard hero/chips rebuild per visit)."""
    if name not in ICONS:
        raise KeyError(f"unknown icon: {name}")
    key = (name, color, size)
    if key in _CACHE:
        return _CACHE[key]
    img = Image.new("RGBA", (GRID * SS, GRID * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d._ink = color
    ICONS[name](d, SS)
    out = img.resize((size, size), Image.LANCZOS)
    _CACHE[key] = out
    return out
