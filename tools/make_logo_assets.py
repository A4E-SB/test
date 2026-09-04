"""
Build every brand asset for Himaya.

Two sources, two purposes:

  assets/logo.png  — the MASTER logo (AI-generated, full wordmark). Used for
                     README banners and release pages. Never scaled to 16px.

  assets/icon.png / icon.ico — the APP ICON, drawn programmatically in the
                     same visual identity (dark rounded tile + emerald shield
                     + dark checkmark). Drawing it (instead of cropping the
                     AI logo) guarantees:
                       • crisp anti-aliased edges at any size (2x supersampled)
                       • NO white fringes when Windows scales it down — every
                         transparent pixel carries DARK RGB underneath
                         (v1.0.4 icons showed light halos at small sizes
                         because transparent pixels kept the light canvas
                         colour of the generated logo)

Run after changing the design:  python tools/make_logo_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# palette (kept in sync with himaya/config.py)
TILE_TOP = (23, 26, 32)       # dark tile gradient top
TILE_BOTTOM = (17, 19, 24)    # dark tile gradient bottom
EDGE_RGB = (18, 20, 26)       # RGB stored UNDER transparent pixels (anti-fringe)
SHIELD_LIGHT = (52, 224, 133) # emerald gradient top
SHIELD_DARK = (30, 178, 98)   # emerald gradient bottom
CHECK = (14, 26, 20)          # dark checkmark

SS = 4  # supersampling factor


def _rounded_tile(size: int) -> Image.Image:
    """Dark rounded-square tile with a subtle vertical gradient (RGBA)."""
    big = size * SS
    mask = Image.new("L", (big, big), 0)
    radius = int(big * 0.225)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1],
                                           radius=radius, fill=255)
    tile = Image.new("RGBA", (big, big))
    px = tile.load()
    for y in range(big):
        t = y / (big - 1)
        r = int(TILE_TOP[0] + (TILE_BOTTOM[0] - TILE_TOP[0]) * t)
        g = int(TILE_TOP[1] + (TILE_BOTTOM[1] - TILE_TOP[1]) * t)
        b = int(TILE_TOP[2] + (TILE_BOTTOM[2] - TILE_TOP[2]) * t)
        for x in range(big):
            px[x, y] = (r, g, b, 255)
    tile.putalpha(mask)
    return tile.resize((size, size), Image.LANCZOS)


def _shield_points(cx: float, cy: float, w: float, h: float) -> list:
    """Classic shield silhouette (flat top, tapered pointed bottom)."""
    return [
        (cx, cy - h / 2),                    # top centre
        (cx + w * 0.44, cy - h * 0.36),      # top right shoulder
        (cx + w * 0.50, cy - h * 0.02),      # right mid
        (cx + w * 0.42, cy + h * 0.26),      # right lower
        (cx, cy + h * 0.52),                 # bottom point
        (cx - w * 0.42, cy + h * 0.26),      # left lower
        (cx - w * 0.50, cy - h * 0.02),      # left mid
        (cx - w * 0.44, cy - h * 0.36),      # top left shoulder
    ]


def _draw_shield(size: int) -> Image.Image:
    """Emerald shield with vertical gradient + dark checkmark (RGBA)."""
    big = size * SS
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    pts = _shield_points(big / 2, big / 2, big * 0.62, big * 0.66)

    # vertical gradient inside the shield: draw per-scanline clipped polygon
    grad = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    top_y, bot_y = min(p[1] for p in pts), max(p[1] for p in pts)
    for y in range(int(top_y), int(bot_y) + 1):
        t = (y - top_y) / max(1, bot_y - top_y)
        r = int(SHIELD_LIGHT[0] + (SHIELD_DARK[0] - SHIELD_LIGHT[0]) * t)
        g = int(SHIELD_LIGHT[1] + (SHIELD_DARK[1] - SHIELD_LIGHT[1]) * t)
        b = int(SHIELD_LIGHT[2] + (SHIELD_DARK[2] - SHIELD_LIGHT[2]) * t)
        gd.line([(0, y), (big, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    layer.paste(grad, (0, 0), mask)

    # inner darker rim for depth
    d.polygon(_shield_points(big / 2, big / 2, big * 0.545, big * 0.585),
              outline=(24, 148, 84, 255), width=int(big * 0.012))

    # checkmark: two thick strokes with rounded joints
    lw = int(big * 0.055)
    a = (big * 0.335, big * 0.505)
    b = (big * 0.452, big * 0.625)
    c = (big * 0.675, big * 0.36)
    d.line([a, b], fill=CHECK + (255,), width=lw)
    d.line([b, c], fill=CHECK + (255,), width=lw)
    for p in (a, b, c):
        r = lw / 2 - 0.5
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=CHECK + (255,))

    return layer.resize((size, size), Image.LANCZOS)


def build_icon(size: int = 1024) -> Image.Image:
    """Compose the final app icon (RGBA, anti-fringe safe)."""
    icon = _rounded_tile(size)
    icon.alpha_composite(_draw_shield(size))

    # ANTI-FRINGE: give every transparent pixel a dark RGB so any downscale
    # (Windows taskbar, ICO generation) blends towards dark, never white.
    r, g, b, a = icon.split()
    dark = Image.new("L", icon.size, 0)
    rgb = Image.merge("RGB", (r.point(lambda v: v), g, b)).convert("RGB")
    solid = Image.new("RGB", icon.size, EDGE_RGB)
    rgb = Image.composite(rgb, solid, a.point(lambda v: 255 if v > 8 else 0))
    out = Image.merge("RGBA", (*rgb.split(), a))
    return out


def clean_logo() -> None:
    """
    Strip the light canvas around the dark tile in assets/logo.png (master).

    Only background pixels CONNECTED to the canvas border are removed, so the
    white HIMAYA wordmark inside the tile is untouched. Edges are feathered
    and every transparent pixel gets dark RGB underneath (anti-fringe — the
    logo showed white edges on GitHub's white pages in v1.0.5).
    """
    from PIL import ImageFilter

    img = Image.open(ASSETS / "logo.png").convert("RGB")
    a = np.array(img).astype(int)
    lum = (a[..., 0] * 299 + a[..., 1] * 587 + a[..., 2] * 114) // 1000
    light = lum > 140

    conn = np.zeros_like(light)
    conn[0, :] = light[0, :]
    conn[-1, :] = light[-1, :]
    conn[:, 0] |= light[:, 0]
    conn[:, -1] |= light[:, -1]
    for _ in range(2000):
        grown = conn.copy()
        grown[1:, :] |= conn[:-1, :]
        grown[:-1, :] |= conn[1:, :]
        grown[:, 1:] |= conn[:, :-1]
        grown[:, :-1] |= conn[:, 1:]
        grown &= light
        if (grown == conn).all():
            break
        conn = grown

    alpha = np.where(conn, 0, 255).astype(np.uint8)
    alpha = np.array(Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(1.2)))
    alpha = np.where(conn & (alpha < 200), 0, alpha)

    rgb = a.copy()
    trans = alpha < 220
    for c, v in enumerate((18, 20, 26)):
        rgb[..., c] = np.where(trans, v, rgb[..., c])
    Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA").save(
        ASSETS / "logo.png")
    print(f"logo.png cleaned: {int(conn.sum())} background pixels -> transparent")


def social_preview() -> None:
    """1280x640 social preview card (GitHub Settings -> Social preview)."""

    W, H = 1280, 640
    card = Image.new("RGB", (W, H), (20, 22, 27))
    d = ImageDraw.Draw(card)
    # subtle gradient
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=(int(20 - 6 * t), int(22 - 3 * t), int(27 + 5 * t)))
    # big icon on the left
    icon = build_icon(420)
    card.paste(icon, (90, (H - 420) // 2), icon)
    # text block
    try:
        f_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 92)
        f_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        f_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    except OSError:
        f_big = f_sub = f_small = ImageFont.load_default()
    x = 570
    d.text((x, 175), "Himaya", font=f_big, fill=(52, 224, 133))
    try:  # shape Arabic correctly (letters must join + read RTL)
        import arabic_reshaper
        from bidi.algorithm import get_display
        ar_txt = get_display(arabic_reshaper.reshape("حماية"))
    except Exception:
        ar_txt = ""
    if ar_txt:
        d.text((x + 330, 205), ar_txt, font=f_sub, fill=(240, 242, 246))
    d.text((x, 300), "100% offline protection for", font=f_sub, fill=(240, 242, 246))
    d.text((x, 352), "Algerian e-commerce sellers", font=f_sub, fill=(240, 242, 246))
    d.text((x, 440), "EN · FR · AR   •   fake receipt detector • trust scores",
           font=f_small, fill=(154, 163, 178))
    card.save(ASSETS / "social-preview.png")
    print("social-preview.png (1280x640) built")


def main() -> None:
    icon = build_icon(1024)
    icon.save(ASSETS / "icon.png")
    icon.save(ASSETS / "icon.ico",
              sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                     (128, 128), (256, 256)])

    # sanity: corners transparent AND dark under RGB (no white fringes)
    for corner in [(0, 0), (1023, 0), (0, 1023), (1023, 1023)]:
        r, g, b, a = icon.getpixel(corner)
        assert a == 0, corner
        assert (r + g + b) / 3 < 80, f"light RGB under transparency at {corner}"
    print("icon.png + icon.ico rebuilt (vector-style, anti-fringe)")

    import os
    if os.environ.get("HIMAYA_SKIP_LOGO_CLEAN") != "1":
        clean_logo()
        social_preview()


if __name__ == "__main__":
    main()
