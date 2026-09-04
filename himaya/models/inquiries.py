"""
Inquiries log — every contact that may or may not become a sale.
Feeds the Time-Waster Tracker (conversion rate, deposit suggestions).
"""

from __future__ import annotations

from ..database.db import Database


def log(db: Database, customer_id: int, platform: str = "Messenger",
        converted: bool = False, notes: str = "", when: str = "") -> int:
    cur = db.execute(
        "INSERT INTO inquiries(customer_id, date, platform, converted, notes) VALUES(?,?,?,?,?)",
        (customer_id, when, platform, 1 if converted else 0, notes),
    )
    return cur.lastrowid


def list_for_customer(db: Database, customer_id: int) -> list:
    return db.query(
        "SELECT * FROM inquiries WHERE customer_id = ? ORDER BY id DESC", (customer_id,))


def recent(db: Database, limit: int = 200) -> list:
    return db.query(
        """SELECT i.*, c.name AS customer_name, c.phone AS phone
           FROM inquiries i JOIN customers c ON c.id = i.customer_id
           ORDER BY i.id DESC LIMIT ?""", (limit,))


def stats_for_customer(db: Database, customer_id: int) -> dict:
    row = db.query_one(
        """SELECT COUNT(*) AS contacts,
                  COALESCE(SUM(converted), 0) AS converted,
                  COUNT(CASE WHEN converted = 0 THEN 1 END) AS wasted
           FROM inquiries WHERE customer_id = ?""", (customer_id,))
    contacts = row["contacts"] or 0
    converted = row["converted"] or 0
    return {
        "contacts": contacts,
        "converted": converted,
        "wasted": row["wasted"] or 0,
        "conversion_rate": (converted / contacts * 100.0) if contacts else 0.0,
    }


def overall_conversion(db: Database) -> float:
    row = db.query_one("SELECT COUNT(*) n, COALESCE(SUM(converted),0) c FROM inquiries")
    return (row["c"] / row["n"] * 100.0) if row and row["n"] else 0.0
