"""
Global configuration: paths, colors, constants.

All user data lives in ONE folder so it can be backed up / moved on a USB key:
    - Windows : %APPDATA%\\Himaya
    - Others  : ~/.himaya
Override with the HIMAYA_DATA_DIR environment variable or --db on the CLI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import __version__

APP_NAME = "Himaya"
APP_VERSION = __version__

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def get_data_dir() -> Path:
    """Resolve the writable data directory (created if missing)."""
    env = os.environ.get("HIMAYA_DATA_DIR")
    if env:
        d = Path(env)
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(Path.home())
        d = Path(appdata) / "Himaya"
    else:
        d = Path.home() / ".himaya"
    d.mkdir(parents=True, exist_ok=True)
    return d


DATA_DIR = get_data_dir()
DB_PATH = DATA_DIR / "himaya.db"
EVIDENCE_DIR = DATA_DIR / "evidence"        # copies of analysed screenshots
BACKUP_DIR = DATA_DIR / "backups"
def bundle_dir() -> Path:
    """
    Root of bundled read-only resources.
    Frozen (PyInstaller): sys._MEIPASS (one-folder build: .../_internal).
    Dev checkout: the repository root.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


ASSETS_DIR = bundle_dir() / "assets"

EVIDENCE_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# --------------------------------------------------------------------------
# Theme / colors (dark theme, semantic color coding)
# --------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# v1.6 design tokens (dark theme, one brand accent tied to the shield)
# ---------------------------------------------------------------------------
COLOR_BG = "#0A0C12"          # page / window background
COLOR_BG_2 = "#141724"        # surface: sidebar / table rows
COLOR_BG_3 = "#1B1F2E"        # surface-raised: inputs, hover
COLOR_CARD = "#141724"        # cards / panels (surface)
COLOR_BORDER = "#232838"      # hairline 1px borders / dividers
COLOR_FG = "#EEF0F5"          # text-primary: headings, values
COLOR_FG_DIM = "#9AA0B4"      # text-secondary: labels, support
COLOR_FG_MUTED = "#6B7185"    # text-muted: hints, placeholders
COLOR_ACCENT = "#2FD98A"      # THE brand accent (protection green)
COLOR_GREEN = "#2FD98A"       # success: paid / delivered / trusted
COLOR_YELLOW = "#F5B942"      # warning (alias kept for older call sites)
COLOR_RED = "#F2555A"         # danger: scams / ghosts / refused
COLOR_ORANGE = "#F5B942"      # warning: medium-risk / waiting / low stock
COLOR_INFO = "#5B8DEF"        # informational: new orders / shipments


def tint(color: str, alpha: float = 0.13, base: str = COLOR_CARD) -> str:
    """
    Semantic tint (~12-14% opacity of `color` over `base`) for badge and
    icon-chip backgrounds — never a solid semantic fill.
    """
    def hx(c: str) -> tuple[int, int, int]:
        c = c.lstrip("#")
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    r, g, b = (round(a * (1 - alpha) + b_ * alpha)
               for a, b_ in zip(hx(base), hx(color)))
    return f"#{r:02x}{g:02x}{b:02x}"

# --------------------------------------------------------------------------
# Domain constants
# --------------------------------------------------------------------------

# Good statuses (order lifecycle); waiting_deposit = acompte asked, not yet received
GOOD_STATUSES = ["pending", "confirmed", "waiting_deposit", "shipped", "delivered", "paid"]
# Bad statuses (money / time lost)
BAD_STATUSES = ["ghosted", "refused", "phone_off", "fake_payment", "canceled"]
# Special: order blocked before shipping because of a bad phone number
BLOCKED_STATUS = "blocked"
ALL_STATUSES = GOOD_STATUSES + BAD_STATUSES + [BLOCKED_STATUS]

# Statuses that mean the product was actually shipped out
SHIPPED_STATUSES = ["shipped", "delivered", "paid", "ghosted", "refused", "phone_off", "fake_payment"]
# Statuses that end badly after shipping -> shipping cost is lost
LOST_SHIPPING_STATUSES = ["ghosted", "refused", "phone_off"]
# Fake payment: shipping cost AND product price are lost
FAKE_PAYMENT_STATUS = "fake_payment"

# Trust score thresholds
TRUST_TRUSTED = 80   # >= 80 and 3+ delivered -> tag "trusted"
TRUST_CAUTION = 40   # < 40 -> shown in red

# Customer tags (auto-derived by services.trust)
KNOWN_TAGS = ["trusted", "new", "ghost", "scammer", "time_waster"]

# Semantic colors per order status — exactly the four semantic tokens
# (v1.6): success = paid/delivered, danger = scams/ghosts/refused-failed,
# warning = waiting, info = fresh orders and shipments. No stray hues.
STATUS_COLORS = {
    "pending": COLOR_INFO, "confirmed": COLOR_INFO, "shipped": COLOR_INFO,
    "delivered": COLOR_GREEN, "paid": COLOR_GREEN,
    "ghosted": COLOR_RED, "refused": COLOR_RED, "phone_off": COLOR_RED,
    "fake_payment": COLOR_RED, "canceled": COLOR_FG_DIM,
    "blocked": COLOR_RED, "waiting_deposit": COLOR_ORANGE,
}

# Colors per auto tag
TAG_COLORS = {"trusted": COLOR_GREEN, "new": COLOR_INFO,
              "ghost": COLOR_ORANGE, "scammer": COLOR_RED,
              "time_waster": COLOR_ORANGE}

# Delivery companies commonly used in Algeria
DELIVERY_COMPANIES = ["Yalidine", "ZR Express", "Maystro", "NOEST Express", "Guepex", "E-Comdel", "Autre"]

# Inquiries platforms
PLATFORMS = ["Messenger", "WhatsApp", "Instagram", "Téléphone", "TikTok", "Autre"]

CURRENCY_FR = "DA"
CURRENCY_AR = "دج"


def bundled_tesseract() -> str:
    """
    Path to a Tesseract OCR engine bundled NEXT TO the app (installer build).

    OCR engine resolution order:
      1. explicit setting (Settings page),
      2. <app dir>\\tesseract\\tesseract.exe  (bundled by the installer),
      3. system PATH (pytesseract default).
    Returns '' when nothing is bundled.
    """
    candidates = []
    if getattr(sys, "frozen", False):            # PyInstaller build
        candidates.append(Path(sys.executable).parent / "tesseract" / "tesseract.exe")
    candidates.append(ASSETS_DIR / "tesseract" / "tesseract.exe")  # dev layout
    candidates.append(Path(__file__).resolve().parent.parent / "tesseract" / "tesseract.exe")
    for cand in candidates:
        if cand.exists():
            return str(cand)
    return ""


def fmt_money(amount: float, lang: str = "fr") -> str:
    """Format an amount in DZD, e.g. 12 500 DA / 12 500 دج."""
    try:
        amount = float(amount or 0)
    except (TypeError, ValueError):
        amount = 0.0
    s = f"{amount:,.0f}".replace(",", " ")
    cur = CURRENCY_AR if lang == "ar" else CURRENCY_FR
    return f"{s} {cur}" if lang == "ar" else f"{s} {cur}"
