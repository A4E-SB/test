"""
Phone normalization + instant risk check.

Algerian mobile numbers: 05 / 06 / 07 + 8 digits. Accepts +213, 00213,
spaces, dashes… and always returns the canonical 0XXXXXXXXX form so the same
scammer can't slip through by writing their number differently.
"""

from __future__ import annotations

import re

from ..database.db import Database
from .. import models

# Risk levels
OK, CAUTION, DANGER = "ok", "caution", "danger"
_RANK = {OK: 0, CAUTION: 1, DANGER: 2}


def worse(a: str, b: str) -> str:
    """Return the more severe of two risk levels."""
    return a if _RANK.get(a, 0) >= _RANK.get(b, 0) else b


_NON_DIGIT = re.compile(r"[^\d+]")


def normalize_phone(raw: str) -> str | None:
    """Return '0XXXXXXXXX' or None if unparseable."""
    if not raw:
        return None
    s = _NON_DIGIT.sub("", str(raw).strip())
    s = s.lstrip("+")
    if s.startswith("00213"):
        s = "0" + s[5:]
    elif s.startswith("213"):
        s = "0" + s[3:]
    if re.fullmatch(r"0[5-7]\d{8}", s):
        return s
    # Landlines / other formats: keep as-is if reasonable length
    if re.fullmatch(r"0\d{8,9}", s):
        return s
    return None


def phone_risk(db: Database, phone: str) -> dict:
    """
    Full risk picture for a phone number — powers the scam alert popup.

    Returns {level, reasons[], blacklisted, fake_count, lost_money,
             ghost_count, order_count, customer_id}
    """
    p = normalize_phone(phone)
    info = {"level": OK, "reasons": [], "blacklisted": False, "fake_count": 0,
            "lost_money": 0.0, "ghost_count": 0, "order_count": 0, "customer_id": None,
            "phone": p or (phone or "").strip()}
    if not p:
        return info

    reasons: list[str] = []
    level = OK

    bl = models.blacklist.is_blacklisted(db, p)
    if bl:
        info["blacklisted"] = True
        level = DANGER
        sev = bl["severity"] if "severity" in bl.keys() else 2
        reasons.append(("blacklisted_sev3" if sev >= 3 else "blacklisted")
                       + (f"::{bl['reason']}" if bl["reason"] else ""))

    fake_count = models.screenshots.count_for_phone(db, p)
    info["fake_count"] = fake_count
    if fake_count:
        level = DANGER
        reasons.append("fake_screenshot_history")

    cust = models.customers.find_by_phone(db, p)
    if cust:
        info["customer_id"] = cust["id"]
        if cust["tags"]:
            tags = [t for t in (cust["tags"] or "").split(",") if t]
            if "scammer" in tags:
                level = DANGER
                reasons.append("tag_scammer")
            if "ghost" in tags:
                level = worse(level, CAUTION)
                if "tag_ghost" not in reasons:
                    reasons.append("tag_ghost")
            if "time_waster" in tags and level == OK:
                level = CAUTION
                reasons.append("tag_time_waster")
        # money lost with this customer (bad statuses)
        lost = db.scalar(
            "SELECT COALESCE(SUM(shipping_cost),0) FROM orders "
            "WHERE customer_id = ? AND status IN ('ghosted','refused','phone_off','fake_payment')",
            (cust["id"],)) or 0
        fake_money = db.scalar(
            "SELECT COALESCE(SUM(price),0) FROM orders "
            "WHERE customer_id = ? AND status = 'fake_payment'", (cust["id"],)) or 0
        info["lost_money"] = float(lost) + float(fake_money)
        info["ghost_count"] = db.scalar(
            "SELECT COUNT(*) FROM orders WHERE customer_id = ? AND status = 'ghosted'",
            (cust["id"],)) or 0
        info["order_count"] = db.scalar(
            "SELECT COUNT(*) FROM orders WHERE customer_id = ?", (cust["id"],)) or 0
        if info["ghost_count"] >= 2 and level == OK:
            level = CAUTION
            reasons.append("repeat_ghost")
        if info["lost_money"] > 0 and level == OK:
            level = CAUTION
            reasons.append("money_lost_before")

    info["level"] = level
    info["reasons"] = reasons
    return info
