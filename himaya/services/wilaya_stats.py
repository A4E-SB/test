"""Per-wilaya statistics: ghost rate, losses, completion — per delivery zone."""

from __future__ import annotations

from ..database.db import Database
from .. import config

# At/above this ghost rate we suggest asking for a deposit in that wilaya
DEPOSIT_RULE_PCT = 30.0


def wilaya_stats(db: Database) -> list[dict]:
    """
    One row per wilaya with orders in it:
    {wilaya, orders, delivered, bad, ghost_rate, lost, revenue}
    Sorted by ghost rate (worst first).
    """
    rows = db.query(
        """SELECT o.wilaya AS wilaya,
                  COUNT(*) AS orders,
                  SUM(CASE WHEN o.status IN ('delivered','paid') THEN 1 ELSE 0 END) AS delivered,
                  SUM(CASE WHEN o.status IN ('ghosted','refused','phone_off') THEN 1 ELSE 0 END) AS bad,
                  SUM(CASE WHEN o.status IN ('ghosted','refused','phone_off') THEN o.shipping_cost
                           WHEN o.status = 'fake_payment' THEN o.shipping_cost + o.price
                           ELSE 0 END) AS lost,
                  SUM(CASE WHEN o.status = 'paid' THEN o.price ELSE 0 END) AS revenue
           FROM orders o
           WHERE o.wilaya != '' AND o.status != 'blocked'
           GROUP BY o.wilaya""")
    out = []
    for r in rows:
        orders = r["orders"] or 0
        bad = r["bad"] or 0
        out.append({
            "wilaya": r["wilaya"], "orders": orders,
            "delivered": r["delivered"] or 0, "bad": bad,
            "ghost_rate": (bad / orders * 100.0) if orders else 0.0,
            "lost": float(r["lost"] or 0),
            "revenue": float(r["revenue"] or 0),
            "suggest_deposit": orders >= 3 and (bad / orders * 100.0) >= DEPOSIT_RULE_PCT,
        })
    out.sort(key=lambda x: (-x["ghost_rate"], -x["lost"]))
    return out


def funnel(db: Database) -> dict:
    """
    Order funnel: how many orders ever reached each stage.
    A stage is "reached" if the status is at or beyond it in the lifecycle.
    """
    counts = {s: 0 for s in config.ALL_STATUSES}
    for r in db.query("SELECT status, COUNT(*) n FROM orders GROUP BY status"):
        counts[r["status"]] = r["n"]

    # v1.2 fix: a stage is "reached" if the order progressed AT LEAST that
    # far — including orders that later went bad (a ghosted order DID reach
    # "shipped"). The old mapping counted bad statuses nowhere, which made
    # Pending == Confirmed and inflated nothing after. waiting_deposit is a
    # parallel branch, not a sequential stage, so it is not a funnel bar.
    reached = {
        "pending": set(counts),                       # every order starts here
        "confirmed": {"confirmed", "waiting_deposit", "shipped", "delivered",
                      "paid", "ghosted", "refused", "phone_off", "fake_payment"},
        "shipped": {"shipped", "delivered", "paid", "ghosted", "refused",
                    "phone_off"},
        "delivered": {"delivered", "paid"},
        "paid": {"paid"},
    }
    order = ["pending", "confirmed", "shipped", "delivered", "paid"]
    total = sum(counts.values())
    stages = []
    for stage in order:
        n = sum(counts.get(s2, 0) for s2 in reached[stage])
        stages.append({"stage": stage, "count": n,
                       "pct": (n / total * 100.0) if total else 0.0})
    return {"total": total, "stages": stages}


def best_customers(db: Database, limit: int = 5) -> list[dict]:
    """Top customers by delivered orders, with revenue and trust score."""
    rows = db.query(
        """SELECT c.id, c.name, c.phone, c.trust_score, c.tags,
                  SUM(CASE WHEN o.status IN ('delivered','paid') THEN 1 ELSE 0 END) AS bought,
                  SUM(CASE WHEN o.status = 'paid' THEN o.price ELSE 0 END) AS revenue
           FROM customers c JOIN orders o ON o.customer_id = c.id
           GROUP BY c.id
           HAVING bought > 0
           ORDER BY bought DESC, revenue DESC
           LIMIT ?""", (limit,))
    return [dict(r) for r in rows]
