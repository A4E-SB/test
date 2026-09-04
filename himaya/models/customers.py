"""
Customer CRUD + search. Trust score / tags are recomputed via services.trust
whenever an order or inquiry touching this customer changes.
"""

from __future__ import annotations

from ..database.db import Database
from ..services.phone import normalize_phone


def create(db: Database, name: str, phone: str, wilaya: str = "",
           address: str = "", notes: str = "") -> int:
    """Insert a customer; returns the new id. Raises if the phone is a dup."""
    p = normalize_phone(phone) or phone.strip()
    cur = db.execute(
        "INSERT INTO customers(name, phone, wilaya, address, notes) VALUES(?,?,?,?,?)",
        (name.strip(), p, wilaya, address, notes),
    )
    return cur.lastrowid


def update(db: Database, customer_id: int, **fields) -> None:
    """Update editable fields; phone is normalized when present."""
    allowed = {"name", "phone", "wilaya", "address", "notes"}
    sets, vals = [], []
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "phone":
            v = normalize_phone(v) or v
        sets.append(f"{k} = ?")
        vals.append(v)
    if sets:
        vals.append(customer_id)
        db.execute(f"UPDATE customers SET {', '.join(sets)} WHERE id = ?", vals)


def delete(db: Database, customer_id: int) -> None:
    """Delete a customer (orders/inquiries cascade)."""
    db.execute("DELETE FROM customers WHERE id = ?", (customer_id,))


def get(db: Database, customer_id: int):
    return db.query_one("SELECT * FROM customers WHERE id = ?", (customer_id,))


def find_by_phone(db: Database, phone: str):
    p = normalize_phone(phone)
    if not p:
        return None
    return db.query_one("SELECT * FROM customers WHERE phone = ?", (p,))


def search(db: Database, term: str = "", tag: str = "") -> list:
    """Search by name/phone/wilaya, optionally filtered by one auto tag."""
    term = f"%{term.strip()}%"
    sql = ("SELECT * FROM customers WHERE (name LIKE ? OR phone LIKE ? OR wilaya LIKE ?)")
    params: list = [term, term, term]
    if tag:
        sql += " AND (',' || tags || ',') LIKE ?"
        params.append(f"%,{tag},%")
    sql += " ORDER BY trust_score ASC, name ASC LIMIT 500"
    return db.query(sql, params)


def all_customers(db: Database) -> list:
    return db.query("SELECT * FROM customers ORDER BY name")


def set_score_and_tags(db: Database, customer_id: int, score: int, tags: list[str]) -> None:
    db.execute("UPDATE customers SET trust_score = ?, tags = ? WHERE id = ?",
               (score, ",".join(tags), customer_id))
