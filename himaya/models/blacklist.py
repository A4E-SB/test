"""
Blacklist of bad phone numbers. This is the dataset sellers share with each
other offline via .hma files (see services.hma).
"""

from __future__ import annotations

from ..database.db import Database
from ..services.phone import normalize_phone

SEVERITY_LABELS = {1: "suspect", 2: "dangerous", 3: "confirmed_scammer"}


def add(db: Database, phone: str, reason: str = "", severity: int = 2,
        evidence_path: str = "") -> None:
    p = normalize_phone(phone) or phone.strip()
    db.execute(
        """INSERT INTO blacklist(phone, reason, severity, evidence_path)
           VALUES(?,?,?,?)
           ON CONFLICT(phone) DO UPDATE SET
               reason = excluded.reason,
               severity = MAX(severity, excluded.severity),
               evidence_path = CASE WHEN excluded.evidence_path != ''
                                    THEN excluded.evidence_path ELSE blacklist.evidence_path END""",
        (p, reason, severity, evidence_path),
    )


def remove(db: Database, entry_id: int) -> None:
    db.execute("DELETE FROM blacklist WHERE id = ?", (entry_id,))


def remove_phone(db: Database, phone: str) -> None:
    p = normalize_phone(phone) or phone.strip()
    db.execute("DELETE FROM blacklist WHERE phone = ?", (p,))


def is_blacklisted(db: Database, phone: str):
    """Return the blacklist row for this phone, or None."""
    p = normalize_phone(phone)
    if not p:
        return None
    return db.query_one("SELECT * FROM blacklist WHERE phone = ?", (p,))


def all_entries(db: Database) -> list:
    return db.query("SELECT * FROM blacklist ORDER BY severity DESC, reported_date DESC")


def search(db: Database, term: str) -> list:
    t = f"%{term.strip()}%"
    return db.query(
        "SELECT * FROM blacklist WHERE phone LIKE ? OR reason LIKE ? "
        "ORDER BY severity DESC, reported_date DESC", (t, t))


def count(db: Database) -> int:
    return db.scalar("SELECT COUNT(*) FROM blacklist") or 0
