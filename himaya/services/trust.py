"""
Auto trust-score engine (0-100) + auto tags.

Baseline 50 ("new"). Each order outcome moves the score:
    delivered +10   paid +5 (on top)      ghosted -25     refused -12
    fake payment -45   phone off -10      canceled -6     blocked -35
Being blacklisted or having sent a fake screenshot pins the score at the
bottom. Tags (trusted/new/ghost/scammer/time_waster) are derived from the
same history and stored in customers.tags.
"""

from __future__ import annotations

from .. import config
from ..database.db import Database
from .. import models

# (status, weight) applied per order
_WEIGHTS = {
    "delivered": +10,
    "paid": +15,          # paid == delivered + confirmed money
    "ghosted": -25,
    "refused": -12,
    "phone_off": -10,
    "fake_payment": -45,
    "canceled": -6,
    "blocked": -35,
    "pending": 0,
    "confirmed": 0,
    "waiting_deposit": 0,
    "shipped": 0,
}

TIME_WASTER_INQUIRIES = 5       # >= 5 contacts with < 20% conversion
TIME_WASTER_CONVERSION = 20.0


def compute(db: Database, customer_id: int) -> tuple[int, list[str]]:
    """Recompute score + tags for one customer. Returns (score, tags)."""
    cust = models.customers.get(db, customer_id)
    if not cust:
        return 50, ["new"]

    orders = models.orders.list_for_customer(db, customer_id)
    counts = {s: 0 for s in config.ALL_STATUSES}
    for o in orders:
        counts[o["status"]] = counts.get(o["status"], 0) + 1

    score = 50
    for status, n in counts.items():
        score += _WEIGHTS.get(status, 0) * n

    # Hard pins
    bl = models.blacklist.is_blacklisted(db, cust["phone"])
    fake_history = models.screenshots.count_for_phone(db, cust["phone"])
    if bl or fake_history or counts["fake_payment"] > 0:
        score = min(score, 10)
    score = max(0, min(100, round(score)))

    # ---- tags ---------------------------------------------------------------
    tags: list[str] = []
    delivered = counts["delivered"] + counts["paid"]
    if counts["fake_payment"] > 0 or bl or fake_history:
        tags.append("scammer")
    if counts["ghosted"] >= 2:
        tags.append("ghost")
    inq = models.inquiries.stats_for_customer(db, customer_id)
    if (inq["contacts"] >= TIME_WASTER_INQUIRIES
            and inq["conversion_rate"] < TIME_WASTER_CONVERSION) or counts["refused"] >= 3:
        tags.append("time_waster")
    if score >= config.TRUST_TRUSTED and delivered >= 3 and "scammer" not in tags:
        tags.append("trusted")
    if not orders and inq["contacts"] == 0 and not tags:
        tags.append("new")

    return score, tags


def refresh(db: Database, customer_id: int) -> tuple[int, list[str]]:
    """compute() + persist into the customers row."""
    score, tags = compute(db, customer_id)
    models.customers.set_score_and_tags(db, customer_id, score, tags)
    return score, tags
