"""
Derive every brand asset from assets/logo.png (the master logo):

    assets/icon.png   — rounded app-icon tile (1024px, emblem-centred)
    assets/icon.ico   — Windows multi-size icon (16..256)
    assets/logo.png   — master, untouched (full logo with wordmark)

The icon crops the EMBLEM (green shield) rather than the full logo so it
stays readable at 16px in the Windows taskbar.

Run after replacing the master logo:  python tools/make_logo_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / "assets" / "logo.png"


def find_emblem(img: Image.Image) -> tuple:
    """Bounding box of the dominant green element (the shield)."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    xs, ys = [], []
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            r, g, b = px[x, y]
            if g > 130 and g > r + 40 and g > b + 30:  # green-ish
                xs.append(x)
                ys.append(y)
    if not xs:
        return (0, 0, w, h)
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1)


def rounded(img: Image.Image, radius_frac: float = 0.14) -> Image.Image:
    """Apply a rounded-corner mask (returns RGBA)."""
    s = img.size
    r = int(min(s) * radius_frac)
    mask = Image.new("L", s, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s[0] - 1, s[1] - 1], radius=r, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def main() -> None:
    master = Image.open(LOGO).convert("RGB")
    x0, y0, x1, y1 = find_emblem(master)

    # square crop around the emblem with a 16% margin
    ew, eh = x1 - x0, y1 - y0
    side = int(max(ew, eh) * 1.16)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    left, top = cx - side // 2, cy - side // 2
    # clamp to canvas (shift if needed)
    left = max(0, min(left, master.width - side))
    top = max(0, min(top, master.height - side))
    if side > master.width or side > master.height:
        side = min(master.width, master.height)
        left, top = (master.width - side) // 2, (master.height - side) // 2
    tile = master.crop((left, top, left + side, top + side)).resize((1024, 1024), Image.LANCZOS)

    icon = rounded(tile)
    icon.save(ROOT / "assets" / "icon.png")
    icon.save(ROOT / "assets" / "icon.ico",
              sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                     (128, 128), (256, 256)])
    print(f"emblem {x0, y0, x1, y1} -> square crop {side}px -> icon.png + icon.ico done")


if __name__ == "__main__":
    main()
