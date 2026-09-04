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
COLOR_BG = "#14161a"          # window background
COLOR_BG_2 = "#1e2128"        # cards / sidebar
COLOR_BG_3 = "#2a2e37"        # inputs, hover
COLOR_FG = "#f2f4f8"          # main text
COLOR_FG_DIM = "#9aa3b2"      # secondary text
COLOR_ACCENT = "#3b82f6"      # primary action blue
COLOR_GREEN = "#2ecc71"       # trusted / success
COLOR_YELLOW = "#f1c40f"      # caution
COLOR_RED = "#e74c3c"         # blocked / danger
COLOR_ORANGE = "#e67e22"      # warnings

# --------------------------------------------------------------------------
# Domain constants
# --------------------------------------------------------------------------

# Good statuses (order lifecycle)
GOOD_STATUSES = ["pending", "confirmed", "shipped", "delivered", "paid"]
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

# Semantic colors per order status (UI color coding)
STATUS_COLORS = {
    "pending": COLOR_FG_DIM, "confirmed": COLOR_ACCENT,
    "shipped": "#8e7cc3", "delivered": COLOR_GREEN, "paid": COLOR_GREEN,
    "ghosted": COLOR_RED, "refused": COLOR_ORANGE,
    "phone_off": COLOR_ORANGE, "fake_payment": COLOR_RED,
    "canceled": COLOR_FG_DIM, "blocked": COLOR_RED,
}

# Colors per auto tag
TAG_COLORS = {"trusted": COLOR_GREEN, "new": COLOR_ACCENT,
              "ghost": COLOR_ORANGE, "scammer": COLOR_RED,
              "time_waster": COLOR_YELLOW}

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
