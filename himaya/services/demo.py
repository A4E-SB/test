"""
Demo data: a realistic little dataset so new users can explore every screen
before entering real data (offered on first launch, or from Settings).
"""

from __future__ import annotations

from datetime import date, timedelta

from ..database.db import Database
from ..models import (blacklist, customers, inquiries, orders, products)
from ..services import trust


def load_demo(db: Database) -> None:
    """Seed ~2 months of believable activity. Skips if demo already loaded."""
    if db.scalar("SELECT COUNT(*) FROM settings WHERE key = 'demo_loaded' "
                 "AND value = '1'"):
        return

    d = lambda days_ago: (date.today() - timedelta(days=days_ago)).isoformat()  # noqa: E731

    # products
    p1 = products.create(db, "Montre connectée", cost_price=1800, sale_price=4500,
                         quantity=8, low_stock=3)
    p2 = products.create(db, "Écouteurs TWS", cost_price=900, sale_price=2500,
                         quantity=2, low_stock=5)      # low stock on purpose
    p3 = products.create(db, "Crème visage", cost_price=350, sale_price=1500,
                         quantity=25, low_stock=6)

    # customers ------------------------------------------------------------
    c_amine = customers.create(db, "Amine Fiable", "0555111222", wilaya="Alger",
                               address="Bab Ezzouar, Cité 120 logts")
    c_sara = customers.create(db, "Sara Bou", "0661444555", wilaya="Oran",
                              address="Bir El Djir, Bt 4")
    c_ghost = customers.create(db, "Ghost Client", "0770333222", wilaya="Sétif",
                               address="Cité 200 logts")
    c_karim = customers.create(db, "Karim Négociant", "0555888777", wilaya="Constantine")
    c_nasba = customers.create(db, "Nasba King", "0661999000", wilaya="Blida")

    # good orders (Amine, Sara)
    for i, days in enumerate((52, 48, 40, 30)):
        oid = orders.create(db, c_amine, "Montre connectée", 4500, status="delivered",
                            delivery_method="Yalidine", wilaya="Alger",
                            shipping_cost=600, order_date=d(days),
                            product_id=p1, deposit=0)
        orders.set_status(db, oid, "delivered")
    oid = orders.create(db, c_amine, "Écouteurs TWS", 2500, status="paid",
                        delivery_method="Yalidine", wilaya="Alger",
                        shipping_cost=600, order_date=d(12), product_id=p2)
    orders.set_status(db, oid, "paid")
    oid = orders.create(db, c_sara, "Crème visage", 1500, status="paid",
                        delivery_method="ZR Express", wilaya="Oran",
                        shipping_cost=500, order_date=d(9), product_id=p3)
    orders.set_status(db, oid, "paid")

    # ghost + refused (Ghost Client)
    oid = orders.create(db, c_ghost, "Montre connectée", 4500, status="pending",
                        delivery_method="Yalidine", wilaya="Sétif",
                        shipping_cost=700, order_date=d(20), product_id=p1)
    orders.set_status(db, oid, "shipped")
    orders.set_status(db, oid, "ghosted")
    oid = orders.create(db, c_ghost, "Écouteurs TWS", 2500, status="pending",
                        delivery_method="Maystro", wilaya="Sétif",
                        shipping_cost=700, order_date=d(6), product_id=p2)
    orders.set_status(db, oid, "shipped")
    orders.set_status(db, oid, "refused")

    # negotiator with inquiries only
    for i in range(6):
        inquiries.log(db, c_karim, platform="Messenger", converted=False,
                      when=d(i + 1))

    # scammer: fake payment + blacklist entry
    oid = orders.create(db, c_nasba, "Montre connectée", 4500, status="pending",
                        delivery_method="Yalidine", wilaya="Blida",
                        shipping_cost=650, order_date=d(3), product_id=p1)
    orders.set_status(db, oid, "shipped")
    orders.set_status(db, oid, "fake_payment")
    blacklist.add(db, "0661999000", reason="Faux reçu BaridiMob (démo)",
                  severity=3)

    # deposit flow example (waiting deposit)
    orders.create(db, c_karim, "Crème visage", 1500, status="waiting_deposit",
                  delivery_method="ZR Express", wilaya="Constantine",
                  shipping_cost=500, order_date=d(1), product_id=p3, deposit=500)

    # refresh trust for everyone
    for cid in (c_amine, c_sara, c_ghost, c_karim, c_nasba):
        trust.refresh(db, cid)

    db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('demo_loaded', '1')")
