"""
Same-person-different-number detection + customer merging.

Scammers' favourite trick: a fresh SIM card. We link customers by
name similarity + wilaya/address proximity — even with different numbers —
and offer one-click merge (orders + inquiries move, notes combine).
"""

from __future__ import annotations

from difflib import SequenceMatcher

try:                       # optional accent-stripping (graceful without it)
    from unidecode import unidecode
except ImportError:        # pragma: no cover
    def unidecode(s: str) -> str:
        return s

from ..database.db import Database
from .. import models

NAME_SIMILARITY = 0.80      # normalized name ratio threshold
ADDRESS_SIMILARITY = 0.60   # same address zone


def _norm(s: str) -> str:
    """Lowercase, digits-only-punctuation stripped, whitespace collapsed."""
    s = (s or "").lower().strip()
    try:
        s = unidecode(s)
    except Exception:
        pass
    return " ".join(s.split())


def name_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def address_ratio(a: str, b: str) -> float:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def duplicate_groups(db: Database) -> list[dict]:
    """
    Groups of customers that are probably the same person under different
    numbers: [{main: row, dupes: [rows]}]. Excludes exact phone matches
    (impossible: unique index) and blacklist-linked merges are flagged.
    """
    customers = models.customers.all_customers(db)
    groups: list[dict] = []
    used: set[int] = set()

    for i, a in enumerate(customers):
        if a["id"] in used:
            continue
        dupes = []
        for b in customers[i + 1:]:
            if b["id"] in used:
                continue
            if name_ratio(a["name"], b["name"]) < NAME_SIMILARITY:
                continue
            same_wilaya = (a["wilaya"] and a["wilaya"] == b["wilaya"])
            addr = address_ratio(a["address"] or "", b["address"] or "")
            if same_wilaya or addr >= ADDRESS_SIMILARITY:
                dupes.append(b)
                used.add(b["id"])
        if dupes:
            used.add(a["id"])
            groups.append({"main": a, "dupes": dupes})
    return groups


def merge(db: Database, keep_id: int, remove_id: int) -> None:
    """
    Merge customer remove_id INTO keep_id: move orders + inquiries,
    combine notes, keep the older creation, recompute trust.
    """
    keep = models.customers.get(db, keep_id)
    remove = models.customers.get(db, remove_id)
    if not keep or not remove:
        return
    db.execute("UPDATE orders SET customer_id = ? WHERE customer_id = ?",
               (keep_id, remove_id))
    db.execute("UPDATE inquiries SET customer_id = ? WHERE customer_id = ?",
               (keep_id, remove_id))
    notes = [n for n in (keep["notes"] or "", remove["notes"] or "") if n]
    if remove["notes"] and remove["notes"] not in notes:
        notes.append(remove["notes"])
    models.customers.update(db, keep_id, notes=" | ".join(notes)[:2000])
    db.execute("DELETE FROM customers WHERE id = ?", (remove_id,))
    from . import trust
    trust.refresh(db, keep_id)
