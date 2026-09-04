"""
Packaging consistency tests — keeps installer/spec/app versions in sync.

Run:  python tests/test_packaging.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS = 0
FAIL = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} {extra}")


def get_version() -> str:
    src = (ROOT / "himaya" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', src)
    assert m, "no __version__ in himaya/__init__.py"
    return m.group(1)


def main() -> int:
    ver = get_version()
    print(f"[packaging] version = {ver}")

    iss = (ROOT / "installer" / "himaya.iss").read_text(encoding="utf-8")
    check("installer exists + version synced",
          f'#define MyAppVersion "{ver}"' in iss)
    check("installer has a stable AppId GUID",
          re.search(r"AppId=\{\{[0-9A-F-]{36}\}", iss) is not None)
    check("installer packages dist folder",
          "dist\\Himaya\\*" in iss)
    check("installer output name has version",
          "Himaya-Setup-{#MyAppVersion}" in iss)
    check("installer asks before deleting user data",
          "DataDirQuestion" in iss and "userappdata" in iss)
    check("installer ships French wizard language",
          'Languages\\French.isl' in iss)
    check("setup icon present", (ROOT / "assets" / "icon.ico").exists())
    check("brand logo present", (ROOT / "assets" / "logo.png").exists()
          and (ROOT / "tools" / "make_logo_assets.py").exists())

    # anti-fringe icon checks (v1.0.4 icons showed white halos at small sizes)
    from PIL import Image
    icon = Image.open(ROOT / "assets" / "icon.png").convert("RGBA")
    w, h = icon.size
    corners_ok = all(icon.getpixel(c)[3] == 0 and
                     sum(icon.getpixel(c)[:3]) / 3 < 80
                     for c in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)])
    check("icon corners transparent with dark RGB (anti-fringe)", corners_ok)
    light_under = sum(
        1 for x in range(0, w, 8) for y in range(0, h, 8)
        if icon.getpixel((x, y))[3] == 0
        and sum(icon.getpixel((x, y))[:3]) / 3 > 80)
    check("no light RGB under any transparent pixel", light_under == 0,
          f"{light_under} bad pixels")
    small = icon.resize((32, 32), Image.LANCZOS)
    halo = sum(
        1 for x in range(32) for y in range(32)
        if 20 < small.getpixel((x, y))[3] < 235
        and sum(small.getpixel((x, y))[:3]) / 3 > 110)
    check("no white halo when scaled to 32px", halo == 0, f"{halo} pixels")

    vinfo = (ROOT / "installer" / "file_version_info.txt").read_text(encoding="utf-8")
    check("exe version info synced", f"('{ver}')" in vinfo
          or f"'{ver}.0'" in vinfo or f"filevers=({ver.replace('.', ', ')}, 0)" in vinfo)

    spec = (ROOT / "himaya.spec").read_text(encoding="utf-8")
    check("spec includes version info", "file_version_info.txt" in spec)
    check("spec bundles schema.sql (freeze bug v1.0.0)",
          "himaya/database/schema.sql" in spec)
    dbmod = (ROOT / "himaya" / "database" / "db.py").read_text(encoding="utf-8")
    check("db resolves schema for frozen builds", "_MEIPASS" in dbmod)
    appsrc = (ROOT / "himaya" / "ui" / "app.py").read_text(encoding="utf-8")
    check("drag&drop is optional & never crashes startup (v1.0.1 bug)",
          "def _enable_dnd" in appsrc and "TkinterDnD.require" in appsrc
          and "except Exception" in appsrc)
    check("spec bundles tkdnd binaries", 'collect_data_files("tkinterdnd2")' in spec)

    bat = (ROOT / "build_installer.bat").read_text(encoding="utf-8", errors="replace")
    check("build script detects ISCC", "Inno Setup 6" in bat and "himaya.iss" in bat)
    check("build script builds exe first", "pyinstaller" in bat.lower())

    wf = ROOT / ".github" / "workflows" / "build-windows.yml"
    check("CI workflow exists",
          wf.exists() and "himaya.iss" in wf.read_text(encoding="utf-8"))

    check("installer bundles OCR component",
          "bundle\\tesseract\\*" in iss and "skipifsourcedoesntexist" in iss)
    desktop_task = [l for l in iss.splitlines() if l.strip().startswith('Name: "desktopicon"')]
    check("installer defaults to desktop icon (no unchecked flag)",
          len(desktop_task) == 1 and "unchecked" not in desktop_task[0])
    cfg = (ROOT / "himaya" / "config.py").read_text(encoding="utf-8")
    det = (ROOT / "himaya" / "services" / "detector.py").read_text(encoding="utf-8")
    check("app auto-detects bundled OCR",
          "def bundled_tesseract" in cfg and "config.bundled_tesseract()" in det)
    check("CI stages OCR bundle", "tesseract" in wf.read_text(encoding="utf-8"))

    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    check("gitignore excludes installer output", "installer/output" in gi)

    print(f"\n{'=' * 50}\n{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
