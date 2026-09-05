"""
Financial reports: revenue, costs, profit, loss breakdown, savings.

Conventions (documented in the README):
    revenue  = sum(price) of orders paid
    costs    = shipping costs actually paid (delivered/paid orders)
    profit   = revenue - costs
    losses   = ghosted/refused/phone_off shipping costs
               + fake_payment (shipping + full COD price)
    saved    = shipping costs avoided on 'blocked' orders
"""

from __future__ import annotations

from datetime import date, timedelta

from .. import config
from ..database.db import Database


def month_bounds(year: int, month: int) -> tuple[str, str]:
    first = date(year, month, 1)
    last = date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)
    return first.isoformat(), last.isoformat()


def summary_for_range(db: Database, date_from: str, date_to: str) -> dict:
    def scal(sql: str, params=()) -> float:
        return float(db.scalar(sql, params) or 0)

    rev = scal("SELECT COALESCE(SUM(price),0) FROM orders "
               "WHERE status = 'paid' AND date BETWEEN ? AND ?", (date_from, date_to))
    pending = scal("SELECT COALESCE(SUM(price),0) FROM orders "
                   "WHERE status IN ('pending','confirmed','shipped','delivered') "
                   "AND date BETWEEN ? AND ?", (date_from, date_to))
    costs = scal("SELECT COALESCE(SUM(shipping_cost),0) FROM orders "
                 "WHERE status IN ('delivered','paid') AND date BETWEEN ? AND ?",
                 (date_from, date_to))
    q = ",".join(f"'{s}'" for s in config.LOST_SHIPPING_STATUSES)
    lost_shipping = scal(f"SELECT COALESCE(SUM(shipping_cost),0) FROM orders "
                         f"WHERE status IN ({q}) AND date BETWEEN ? AND ?",
                         (date_from, date_to))
    fake_loss = scal("SELECT COALESCE(SUM(price + shipping_cost),0) FROM orders "
                     "WHERE status = 'fake_payment' AND date BETWEEN ? AND ?",
                     (date_from, date_to))
    saved = scal("SELECT COALESCE(SUM(shipping_cost),0) FROM orders "
                 "WHERE status = 'blocked' AND date BETWEEN ? AND ?", (date_from, date_to))
    # real profit: subtract product costs when the catalog knows them
    real_profit = scal(
        "SELECT COALESCE(SUM(o.price - COALESCE(p.cost_price, 0) - o.shipping_cost), 0) "
        "FROM orders o LEFT JOIN products p ON p.id = o.product_id "
        "WHERE o.status = 'paid' AND o.date BETWEEN ? AND ?", (date_from, date_to))
    deposits = scal("SELECT COALESCE(SUM(deposit),0) FROM orders "
                    "WHERE deposit > 0 AND date BETWEEN ? AND ?",
                    (date_from, date_to))
    n_orders = scal("SELECT COUNT(*) FROM orders WHERE date BETWEEN ? AND ?",
                    (date_from, date_to))
    n_done = scal("SELECT COUNT(*) FROM orders WHERE status IN ('delivered','paid') "
                  "AND date BETWEEN ? AND ?", (date_from, date_to))
    return {
        "revenue": rev, "pending_revenue": pending, "costs": costs,
        "profit": rev - costs,
        "lost_shipping": lost_shipping,
        "fake_loss": fake_loss,
        "losses": lost_shipping + fake_loss,
        "saved": saved, "real_profit": real_profit, "deposits": deposits,
        "orders": int(n_orders),
        "delivered": int(n_done),
        "completion": (n_done / n_orders * 100.0) if n_orders else 0.0,
    }


def monthly_summary(db: Database, year: int, month: int) -> dict:
    f, t = month_bounds(year, month)
    s = summary_for_range(db, f, t)
    s["from"], s["to"] = f, t
    return s


def loss_breakdown(db: Database, date_from: str = "2000-01-01",
                   date_to: str | None = None) -> dict:
    """Loss per bad status (money + count), for the pie/list in Reports."""
    to = date_to or date.today().isoformat()
    out = {}
    for status in config.LOST_SHIPPING_STATUSES:
        row = db.query_one(
            "SELECT COUNT(*) n, COALESCE(SUM(shipping_cost),0) s FROM orders "
            "WHERE status = ? AND date BETWEEN ? AND ?", (status, date_from, to))
        out[status] = {"count": row["n"], "amount": float(row["s"])}
    row = db.query_one(
        "SELECT COUNT(*) n, COALESCE(SUM(price + shipping_cost),0) s FROM orders "
        "WHERE status = 'fake_payment' AND date BETWEEN ? AND ?", (date_from, to))
    out["fake_payment"] = {"count": row["n"], "amount": float(row["s"])}
    out["total"] = {
        "count": sum(v["count"] for k, v in out.items() if k != "total"),
        "amount": sum(v["amount"] for k, v in out.items() if k != "total"),
    }
    return out


def revenue_series(db: Database, months: int = 6) -> list[dict]:
    """Last N months: [{label, revenue, losses}] for the dashboard chart."""
    today = date.today()
    series = []
    for i in range(months - 1, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year - (today.month - i - 1) // 12
        f, t = month_bounds(y, m)
        rev = db.scalar("SELECT COALESCE(SUM(price),0) FROM orders "
                        "WHERE status='paid' AND date BETWEEN ? AND ?", (f, t)) or 0
        q = ",".join(f"'{s}'" for s in config.LOST_SHIPPING_STATUSES)
        lost_ship = db.scalar(f"SELECT COALESCE(SUM(shipping_cost),0) FROM orders "
                              f"WHERE status IN ({q}) AND date BETWEEN ? AND ?",
                              (f, t)) or 0
        fake = db.scalar("SELECT COALESCE(SUM(price + shipping_cost),0) FROM orders "
                         "WHERE status='fake_payment' AND date BETWEEN ? AND ?",
                         (f, t)) or 0
        series.append({"label": f"{m:02d}/{str(y)[2:]}", "year": y, "month": m,
                       "revenue": float(rev), "losses": float(lost_ship) + float(fake)})
    return series
