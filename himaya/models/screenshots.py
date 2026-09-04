"""
Fake screenshot evidence store. Each analysis saves:
  - a perceptual hash (dHash) to catch re-used / slightly edited fakes,
  - the phone number (optional),
  - a JSON dump of the analysis for later review.
"""

from __future__ import annotations

import json

from ..database.db import Database
from ..services.phone import normalize_phone


def save(db: Database, image_hash: str, phone: str, details: dict,
         when: str = "") -> int:
    p = normalize_phone(phone) or (phone or "").strip()
    cur = db.execute(
        "INSERT INTO fake_screenshots(image_hash, phone, date, details) VALUES(?,?,?,?)",
        (image_hash, p, when, json.dumps(details, ensure_ascii=False, indent=1)),
    )
    return cur.lastrowid


def find_by_hash(db: Database, image_hash: str) -> list:
    """Exact perceptual-hash matches (re-used fake image)."""
    return db.query("SELECT * FROM fake_screenshots WHERE image_hash = ?", (image_hash,))


def count_for_phone(db: Database, phone: str) -> int:
    p = normalize_phone(phone)
    if not p:
        return 0
    return db.scalar("SELECT COUNT(*) FROM fake_screenshots WHERE phone = ?", (p,)) or 0


def recent(db: Database, limit: int = 100) -> list:
    rows = db.query("SELECT * FROM fake_screenshots ORDER BY id DESC LIMIT ?", (limit,))
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["details"] = json.loads(d.get("details") or "{}")
        except json.JSONDecodeError:
            d["details"] = {}
        out.append(d)
    return out
