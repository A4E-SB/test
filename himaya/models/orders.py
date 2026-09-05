"""
Order CRUD + filtered listing + aggregates used by the dashboard/reports.

Status lifecycle:
    good : pending -> confirmed -> shipped -> delivered -> paid
    bad  : ghosted / refused / phone_off / fake_payment / canceled
    spec : blocked (never shipped: phone was blacklisted -> money saved)
"""

from __future__ import annotations

from datetime import date, timedelta

from .. import config
from ..database.db import Database


def create(db: Database, customer_id: int, product: str, price: float,
           status: str = "pending", delivery_method: str = "", wilaya: str = "",
           shipping_cost: float = 0.0, notes: str = "", order_date: str = "",
           product_id: int | None = None, deposit: float = 0.0) -> int:
    from . import products as products_model
    cur = db.execute(
        """INSERT INTO orders(customer_id, product_id, product, price, deposit,
                              status, delivery_method, wilaya, date,
                              shipping_cost, notes)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (customer_id, product_id, product.strip(), float(price or 0),
         float(deposit or 0), status, delivery_method, wilaya,
         order_date or date.today().isoformat(), float(shipping_cost or 0), notes),
    )
    # stock: a fresh non-blocked order holds one unit
    products_model.adjust_quantity(db, product_id,
                                   products_model.stock_effect(status))
    return cur.lastrowid


def update(db: Database, order_id: int, **fields) -> None:
    allowed = {"product", "price", "status", "delivery_method", "wilaya",
               "date", "shipping_cost", "notes", "product_id", "deposit"}
    sets, vals = [], []
    for k, v in fields.items():
        if k not in allowed:
            continue
        sets.append(f"{k} = ?")
        vals.append(v)
    if sets:
        vals.append(order_id)
        db.execute(f"UPDATE orders SET {', '.join(sets)} WHERE id = ?", vals)


def set_status(db: Database, order_id: int, status: str) -> None:
    """Change status and maintain shipped_at / delivered_at timestamps."""
    if status not in config.ALL_STATUSES:
        raise ValueError(f"Unknown status: {status}")
    from . import products as products_model
    row = db.query_one("SELECT status, product_id FROM orders WHERE id = ?", (order_id,))
    if row is None:
        return
    extra = ""
    if status in config.SHIPPED_STATUSES:
        extra += ", shipped_at = COALESCE(NULLIF(shipped_at, ''), datetime('now','localtime'))"
    if status in ("delivered", "paid"):
        extra += ", delivered_at = COALESCE(NULLIF(delivered_at, ''), datetime('now','localtime'))"
    db.execute(f"UPDATE orders SET status = ?{extra} WHERE id = ?", (status, order_id))
    # stock: recompute the held-unit difference between old and new status
    delta = (products_model.stock_effect(status)
             - products_model.stock_effect(row["status"]))
    if delta:
        products_model.adjust_quantity(db, row["product_id"], delta)


def delete(db: Database, order_id: int) -> None:
    # release the held unit before deleting (if the order held one)
    from . import products as products_model
    row = db.query_one("SELECT status, product_id FROM orders WHERE id = ?", (order_id,))
    if row is not None:
        delta = -products_model.stock_effect(row["status"])
        if delta:
            products_model.adjust_quantity(db, row["product_id"], delta)
    db.execute("DELETE FROM orders WHERE id = ?", (order_id,))


def get(db: Database, order_id: int):
    return db.query_one("SELECT * FROM orders WHERE id = ?", (order_id,))


def list_orders(db: Database, status: str = "", wilaya: str = "",
                date_from: str = "", date_to: str = "", query: str = "",
                customer_id: int | None = None, limit: int = 500) -> list:
    """Filtered order list joined with the customer name/phone."""
    sql = ("SELECT o.*, c.name AS customer_name, c.phone AS phone, c.tags AS tags, "
           "c.trust_score AS trust_score, p.cost_price AS product_cost "
           "FROM orders o JOIN customers c ON c.id = o.customer_id "
           "LEFT JOIN products p ON p.id = o.product_id WHERE 1=1")
    params: list = []
    if status:
        sql += " AND o.status = ?"
        params.append(status)
    if wilaya:
        sql += " AND o.wilaya = ?"
        params.append(wilaya)
    if date_from:
        sql += " AND o.date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND o.date <= ?"
        params.append(date_to)
    if query:
        sql += " AND (o.product LIKE ? OR c.name LIKE ? OR c.phone LIKE ?)"
        q = f"%{query.strip()}%"
        params += [q, q, q]
    if customer_id is not None:
        sql += " AND o.customer_id = ?"
        params.append(customer_id)
    sql += " ORDER BY o.id DESC LIMIT ?"
    params.append(limit)
    return db.query(sql, params)


def list_for_customer(db: Database, customer_id: int) -> list:
    return db.query("SELECT * FROM orders WHERE customer_id = ? ORDER BY id DESC",
                    (customer_id,))


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------

def count_today(db: Database, status: str | None = None) -> int:
    """Orders created today, optionally with a given status."""
    today = date.today().isoformat()
    if status:
        return db.scalar("SELECT COUNT(*) FROM orders WHERE date = ? AND status = ?",
                         (today, status)) or 0
    return db.scalar("SELECT COUNT(*) FROM orders WHERE date = ?", (today,)) or 0


def shipped_today(db: Database) -> int:
    today = date.today().isoformat()
    return db.scalar(
        "SELECT COUNT(*) FROM orders WHERE shipped_at LIKE ?", (f"{today}%",)) or 0


def count_by_status(db: Database) -> dict:
    rows = db.query("SELECT status, COUNT(*) n FROM orders GROUP BY status")
    return {r["status"]: r["n"] for r in rows}


def completion_rate(db: Database) -> float:
    """% of all orders that reached delivered/paid."""
    total = db.scalar("SELECT COUNT(*) FROM orders") or 0
    done = db.scalar(
        "SELECT COUNT(*) FROM orders WHERE status IN ('delivered','paid')") or 0
    return (done / total * 100.0) if total else 0.0


def total_lost(db: Database) -> float:
    """Total money lost to bad orders (see services.reports for the breakdown)."""
    lost_shipping = db.scalar(
        "SELECT COALESCE(SUM(shipping_cost),0) FROM orders WHERE status IN ({})".format(
            ",".join(f"'{s}'" for s in config.LOST_SHIPPING_STATUSES))) or 0
    fake = db.scalar(
        "SELECT COALESCE(SUM(price + shipping_cost),0) FROM orders "
        "WHERE status = 'fake_payment'") or 0
    return float(lost_shipping) + float(fake)


def money_saved(db: Database) -> float:
    """Shipping costs avoided by blocking orders from bad numbers."""
    saved = db.scalar(
        "SELECT COALESCE(SUM(shipping_cost),0) FROM orders WHERE status = 'blocked'") or 0
    return float(saved)


def count_since(db: Database, days: int, statuses: list[str]) -> int:
    since = (date.today() - timedelta(days=days)).isoformat()
    q = ",".join(f"'{s}'" for s in statuses)
    return db.scalar(
        f"SELECT COUNT(*) FROM orders WHERE date >= ? AND status IN ({q})",
        (since,)) or 0
