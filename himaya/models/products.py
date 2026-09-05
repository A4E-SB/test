"""Product catalog model: CRUD + stock helpers (stock follows order statuses)."""

from __future__ import annotations

from ..database.db import Database


def create(db: Database, name: str, cost_price: float = 0, sale_price: float = 0,
           quantity: int = 0, low_stock: int = 5) -> int:
    cur = db.execute(
        "INSERT INTO products(name, cost_price, sale_price, quantity, low_stock) "
        "VALUES(?,?,?,?,?)",
        (name.strip(), float(cost_price or 0), float(sale_price or 0),
         int(quantity or 0), int(low_stock or 0)),
    )
    return cur.lastrowid


def update(db: Database, product_id: int, **fields) -> None:
    allowed = {"name", "cost_price", "sale_price", "quantity", "low_stock"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            vals.append(v)
    if sets:
        vals.append(product_id)
        db.execute(f"UPDATE products SET {', '.join(sets)} WHERE id = ?", vals)


def delete(db: Database, product_id: int) -> None:
    """Delete a product (orders keep their free-text product label)."""
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))


def get(db: Database, product_id: int):
    return db.query_one("SELECT * FROM products WHERE id = ?", (product_id,))


def find_by_name(db: Database, name: str):
    return db.query_one("SELECT * FROM products WHERE name = ?", (name.strip(),))


def all_products(db: Database) -> list:
    return db.query("SELECT * FROM products ORDER BY name")


def adjust_quantity(db: Database, product_id: int | None, delta: int) -> None:
    if not product_id or delta == 0:
        return
    db.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?",
               (int(delta), product_id))


# ---------------------------------------------------------------------------
# Stock policy: a product unit is "held" (-1) by any active order status and
# released (0) when the order is canceled/blocked (never leaves the shop) —
# transitions recompute the difference, so returns restock exactly once.
# ---------------------------------------------------------------------------

HELD_STATUSES_EXEMPT = ("canceled", "blocked")   # these statuses hold no stock


def stock_effect(status: str) -> int:
    """Stock impact of an order being AT this status (-1 held, 0 released)."""
    return 0 if status in HELD_STATUSES_EXEMPT else -1


def low_stock_products(db: Database) -> list:
    return db.query(
        "SELECT * FROM products WHERE quantity <= low_stock ORDER BY quantity ASC")
