"""
Build every brand asset for Himaya from the MASTER logo.

The master is assets/logo.png — the seller's own logo (2048x2048, dark
background reaching every edge, artwork centred; text lines at the bottom).

Derived assets (run: python tools/make_logo_assets.py):
  assets/brand.png          — README banner (same art, fresh filename vs CDN)
  assets/icon.png / .ico    — app icon: EMBLEM crop (text excluded), inset
                              inside a dark tile with rounded corners and
                              anti-fringe edges (no white halos at 16px)
  assets/social-preview.png — 1280x640 share card (GitHub Social preview)

The master itself is never modified.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = (19, 22, 34)        # master's dark navy background
EMBLEM_Y_MAX = 1454      # content below this line is text -> excluded from icon


def load_master() -> Image.Image:
    p = ASSETS / "logo.png"
    if not p.exists():
        raise SystemExit("assets/logo.png (master logo) is missing")
    return Image.open(p).convert("RGB")


def find_emblem(a: np.ndarray) -> tuple:
    """Bounding box of the green/white emblem artwork (text excluded)."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    emblem = ((g > 130) & (g > r + 40) & (g > b + 20)) | \
             ((r > 170) & (g > 170) & (b > 170))
    emblem[EMBLEM_Y_MAX:, :] = False
    ys, xs = np.nonzero(emblem)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def build_icon(master: Image.Image, size: int = 1024) -> Image.Image:
    """Emblem crop inset in a dark rounded tile — anti-fringe at any scale."""
    a = np.array(master).astype(int)
    h, w = a.shape[:2]
    x0, y0, x1, y1 = find_emblem(a)
    side = int(max(x1 - x0, y1 - y0) * 1.14)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    lx = max(0, min(cx - side // 2, w - side))
    ty = max(0, min(cy - side // 2, h - side))
    crop = master.crop((lx, ty, lx + side, ty + side))

    inset = size * 6 // 100                      # dark ring: art never touches
    tile = Image.new("RGB", (size, size), BG)    # the rounded edge
    tile.paste(crop.resize((size - 2 * inset, size - 2 * inset), Image.LANCZOS),
               (inset, inset))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1],
                                           radius=int(size * 0.225), fill=255)
    rgba = Image.new("RGBA", (size, size), BG + (0,))
    rgba.paste(tile, (0, 0), mask)
    return rgba


def verify_icon(rgba: Image.Image) -> None:
    v = np.array(rgba)
    for c in [(0, 0), (rgba.width - 1, 0), (0, rgba.height - 1),
              (rgba.width - 1, rgba.height - 1)]:
        assert v[c][3] == 0 and v[c][:3].mean() < 60, f"corner {c}"
    for s in (16, 24, 32, 48, 64):
        small = np.array(rgba.resize((s, s)))
        halo = int(((small[..., 3] > 20) & (small[..., 3] < 235) &
                    (small[..., :3].mean(axis=2) > 150)).sum())
        assert halo == 0, f"{halo} halo pixels at {s}px"


def social_preview(icon: Image.Image) -> None:
    card = Image.new("RGB", (1280, 640), BG)
    d = ImageDraw.Draw(card)
    big = icon.resize((420, 420))
    card.paste(big, (90, 110), big)
    try:
        FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        f_big, f_sub, f_small = (ImageFont.truetype(FB, s) for s in (92, 38, 28))
    except OSError:
        f_big = f_sub = f_small = ImageFont.load_default()
    d.text((570, 170), "Himaya", font=f_big, fill=(52, 224, 133))
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        ar = get_display(arabic_reshaper.reshape("حماية"))
        d.text((910, 200), ar, font=f_sub, fill=(240, 242, 246))
    except Exception:
        pass
    d.text((570, 300), "100% offline protection for", font=f_sub, fill=(240, 242, 246))
    d.text((570, 350), "Algerian e-commerce sellers", font=f_sub, fill=(240, 242, 246))
    d.text((570, 440), "EN · FR · AR   •   fake receipt detector · trust scores",
           font=f_small, fill=(154, 163, 178))
    card.save(ASSETS / "social-preview.png")
    print("social-preview.png (1280x640) built")


def main() -> None:
    master = load_master()

    master.save(ASSETS / "brand.png")            # README banner
    print("brand.png written (fresh filename vs CDN cache)")

    icon = build_icon(master)
    verify_icon(icon)
    icon.save(ASSETS / "icon.png")
    icon.save(ASSETS / "icon.ico",
              sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                     (128, 128), (256, 256)])
    print("icon.png + icon.ico built (emblem crop, anti-fringe verified)")

    social_preview(icon)


if __name__ == "__main__":
    main()
