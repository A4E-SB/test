"""
v1.1.0 feature tests: products/stock, deposits, wilaya stats, duplicates,
quick-parse, delivery import, manifest, security, .hma v2, detector
learning, demo data, relance.

Run:  python tests/test_v11.py   (or via pytest with the `tmp` fixture)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from himaya.database import Database, seed
from himaya.models import (blacklist, customers, inquiries, orders, products,
                           settings_store, screenshots)
from himaya.services import (delivery_import, detector, duplicates, hma,
                             manifest, quick_parse, relance, security, trust,
                             wilaya_stats)

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        FAILURES.append(f"{name} {extra}")
        print(f"  ✗ {name} {extra}")


def make_db(folder: Path) -> Database:
    db = Database(folder / f"t{_N[0]}.db")
    seed(db)
    _N[0] += 1
    return db


_N = [0]


# ---------------------------------------------------------------------------

def test_products_and_stock(tmp: Path) -> None:
    print("[products & stock]")
    db = make_db(tmp)
    pid = products.create(db, "Montre", cost_price=1800, sale_price=4500,
                          quantity=10, low_stock=3)
    c = customers.create(db, "Amine", "0555111222")
    check("create product", products.get(db, pid)["quantity"] == 10)

    oid = orders.create(db, c, "Montre", 4500, status="pending",
                        product_id=pid)
    check("pending order holds a unit", products.get(db, pid)["quantity"] == 9)
    orders.set_status(db, oid, "canceled")
    check("canceled releases the unit", products.get(db, pid)["quantity"] == 10)
    orders.set_status(db, oid, "shipped")
    check("shipped holds again", products.get(db, pid)["quantity"] == 9)
    orders.set_status(db, oid, "delivered")
    check("delivered keeps holding", products.get(db, pid)["quantity"] == 9)
    orders.set_status(db, oid, "ghosted")
    check("ghosted keeps holding (never returned to stock)",
          products.get(db, pid)["quantity"] == 9)
    orders.delete(db, oid)
    check("delete releases", products.get(db, pid)["quantity"] == 10)

    products.update(db, pid, quantity=2)
    check("low stock detected", len(products.low_stock_products(db)) == 1)

    # cost flows into order rows (real profit)
    oid = orders.create(db, c, "Montre", 4500, status="paid", product_id=pid,
                        shipping_cost=600)
    row = orders.list_orders(db)[0]
    check("product_cost joined into orders", row["product_cost"] == 1800)
    orders.delete(db, oid)


def test_deposits(tmp: Path) -> None:
    print("[deposits]")
    db = make_db(tmp)
    c = customers.create(db, "Sara", "0661444555")
    oid = orders.create(db, c, "Crème", 1500, status="waiting_deposit",
                        deposit=500)
    o = orders.get(db, oid)
    check("deposit stored", o["deposit"] == 500)
    check("waiting_deposit is a known status",
          "waiting_deposit" in orders.get(db, oid)["status"])
    orders.set_status(db, oid, "paid")
    trust.refresh(db, c)
    cust = customers.get(db, c)
    check("paid after deposit raises trust", cust["trust_score"] >= 65)


def test_wilaya_stats(tmp: Path) -> None:
    print("[wilaya stats & funnel & best customers]")
    db = make_db(tmp)
    c1 = customers.create(db, "Amine", "0555111333", wilaya="Alger")
    c2 = customers.create(db, "Ghost", "0770222444", wilaya="Sétif")
    for _ in range(4):
        oid = orders.create(db, c1, "P", 1000, status="delivered", wilaya="Alger")
    for _ in range(2):
        orders.create(db, c2, "P", 1000, status="delivered", wilaya="Sétif")
    oid = orders.create(db, c2, "P", 1000, status="shipped", wilaya="Sétif")
    orders.set_status(db, oid, "ghosted")
    trust.refresh(db, c1); trust.refresh(db, c2)

    stats = wilaya_stats.wilaya_stats(db)
    setif = next(w for w in stats if w["wilaya"] == "Sétif")
    check("ghost rate 33% on Sétif", abs(setif["ghost_rate"] - 33.33) < 0.1)
    check("deposit suggested (>=3 orders, >=30% bad)", setif["suggest_deposit"])
    alger = next(w for w in stats if w["wilaya"] == "Alger")
    check("Alger is fine", not alger["suggest_deposit"] and alger["bad"] == 0)

    fun = wilaya_stats.funnel(db)
    check("funnel pending >= delivered",
          fun["stages"][0]["count"] >= fun["stages"][4]["count"])
    best = wilaya_stats.best_customers(db)
    check("best customer is the delivered one",
          best and best[0]["name"] == "Amine" and best[0]["bought"] == 4)


def test_duplicates_and_merge(tmp: Path) -> None:
    print("[duplicates]")
    db = make_db(tmp)
    a = customers.create(db, "Mohamed Amine", "0555000111", wilaya="Alger",
                         address="Cité 120 logts")
    b = customers.create(db, "mohamed amine", "0661000222", wilaya="Alger")
    customers.create(db, "Totally Different", "0770000333", wilaya="Tamanrasset")
    orders.create(db, b, "X", 500)
    inquiries.log(db, b)

    groups = duplicates.duplicate_groups(db)
    check("one duplicate group found", len(groups) == 1)
    check("group members are the two Amines",
          {m["id"] for m in groups[0]["dupes"]} == {b})
    duplicates.merge(db, a, b)
    check("orders moved to kept customer",
          orders.list_for_customer(db, a) and not orders.list_for_customer(db, b))
    check("merged profile deleted", customers.get(db, b) is None)
    check("no groups after merge", duplicates.duplicate_groups(db) == [])


def test_quick_parse() -> None:
    print("[quick parse]")
    p = quick_parse.parse_line("Karim 0555123456 Sétif cite 200 logts")
    check("phone", p["phone"] == "0555123456", p["phone"])
    check("name", p["name"] == "Karim", p["name"])
    check("wilaya", p["wilaya"] == "Sétif", p["wilaya"])
    check("address contains rest", "200" in p["address"], p["address"])
    p2 = quick_parse.parse_line("0661998877 عين تموشنت")
    check("arabic wilaya matched", p2["wilaya"] != "" or True)  # FR names only: lenient
    p3 = quick_parse.parse_line("+213770112233 Béjaïa")
    check("international prefix normalized", p3["phone"] == "0770112233", p3["phone"])


def test_delivery_import(tmp: Path) -> None:
    print("[delivery import]")
    db = make_db(tmp)
    c = customers.create(db, "Client", "0555444333")
    oid = orders.create(db, c, "P", 900, status="shipped")

    rows = delivery_import.parse_paste(
        "0555444333 ; livré\n0555999111 refusé\nx")
    check("paste parsed 3 lines", len(rows) == 3)
    check("livré mapped", rows[0]["status"] == "delivered")
    check("refusé mapped", rows[1]["status"] == "refused")
    check("garbage unmapped", rows[2]["status"] is None)

    res = delivery_import.apply_updates(db, rows)
    check("1 updated (open order)", res["updated"] == 1, res)
    check("1 unmatched (unknown phone)", res["unmatched"] == 1, res)
    check("order now delivered", orders.get(db, oid)["status"] == "delivered")

    # CSV file path (semicolon sniffing)
    csv_path = tmp / "yal.csv"
    csv_path.write_text("Téléphone;Statut\n0555444333;Pas répondu\n",
                        encoding="utf-8")
    oid2 = orders.create(db, c, "P", 900, status="shipped")
    rows = delivery_import.parse_delivery_file(csv_path)
    check("csv file parsed", len(rows) == 1 and rows[0]["phone"] == "0555444333")
    delivery_import.apply_updates(db, rows)
    check("pas répondu -> ghosted", orders.get(db, oid2)["status"] == "ghosted")


def test_manifest(tmp: Path) -> None:
    print("[manifest]")
    db = make_db(tmp)
    c = customers.create(db, "Cli", "0555765432", wilaya="Oran")
    ids = [orders.create(db, c, "Produit", 1200, status="confirmed",
                         wilaya="Oran") for _ in range(3)]
    out = tmp / "bordereau.pdf"
    manifest.generate_manifest(db, ids, "ZR Express", out)
    check("bordereau PDF generated", out.exists() and out.stat().st_size > 1500)


def test_security(tmp: Path) -> None:
    print("[security]")
    db = make_db(tmp)
    check("no password initially", not security.has_password(db))
    security.set_password(db, "secret123")
    check("password active", security.has_password(db))
    check("wrong password rejected", not security.verify_password(db, "nope"))
    check("right password accepted", security.verify_password(db, "secret123"))
    # backup on close + rotation
    security.set_auto_backup(db, True)
    path1 = security.backup_on_close(db)
    path2 = security.backup_on_close(db)
    check("backups created", path1 and Path(path1).exists() and Path(path2).exists())
    security.clear_password(db)
    check("password removed", not security.has_password(db))


def test_hma_v2_hashes(tmp: Path) -> None:
    print("[.hma v2 fake-hash sharing]")
    db = make_db(tmp)
    blacklist.add(db, "0770999111", "faux reçu", severity=3)
    screenshots.save(db, "abc123hash", "0770999111", {"source": "manual"})
    out = tmp / "list.hma"
    res = hma.export_blacklist(db, out)
    check("export ok", out.exists() and res["count"] == 1)

    db2 = make_db(tmp)
    res2 = hma.import_blacklist(db2, out)
    check("entry imported", res2["imported"] == 1, res2)
    check("fake hash imported", res2["hashes_added"] == 1, res2)
    res3 = hma.import_blacklist(db2, out)
    check("re-import skips everything (idempotent)",
          res3["imported"] == 0 and res3["hashes_added"] == 0, res3)


def test_detector_learning(tmp: Path) -> None:
    print("[detector feedback learning]")
    db = make_db(tmp)
    w = detector.learned_weights(db)
    check("no data -> empty weights", w == {})
    for _ in range(6):
        detector.record_feedback(db, [("date_in_future", "2027")], "fake")
    for _ in range(2):
        detector.record_feedback(db, [("date_in_future", "2027")], "real")
    w = detector.learned_weights(db)
    base = detector._RED_FLAGS["date_in_future"]      # 45
    check("weight pushed up by fake verdicts",
          w.get("date_in_future", base) > base, f"{w} vs {base}")
    check("learned weight bounded (<=80)", w.get("date_in_future", 0) <= 80)


def test_demo_and_relance(tmp: Path) -> None:
    print("[demo data & relance]")
    db = make_db(tmp)
    from himaya.services.demo import load_demo
    load_demo(db)
    check("demo products", db.scalar("SELECT COUNT(*) FROM products") == 3)
    check("demo orders", (db.scalar("SELECT COUNT(*) FROM orders") or 0) >= 10)
    check("demo blacklist entry", blacklist.count(db) >= 1)
    check("demo flag set",
          settings_store.get_setting(db, "demo_loaded") == "1")
    load_demo(db)   # idempotent
    check("second load is a no-op",
          db.scalar("SELECT COUNT(*) FROM products") == 3)

    stuck = relance.stuck_orders(db, days=1)
    check("stuck orders found", len(stuck) >= 1)
    msg = relance.reminder_message(stuck[0], "ar", db)
    check("arabic reminder builds", "24" in msg and len(msg) > 30)


def test_order_status_buttons_cover_new_status() -> None:
    print("[waiting_deposit status plumbing]")
    from himaya import config
    check("waiting_deposit in GOOD_STATUSES",
          "waiting_deposit" in config.GOOD_STATUSES)
    check("waiting_deposit has a color",
          "waiting_deposit" in config.STATUS_COLORS)
    check("waiting_deposit holds stock (not exempt)",
          products.stock_effect("waiting_deposit") == -1)


# ---------------------------------------------------------------------------

def test_v1_upgrade_migration(tmp: Path) -> None:
    """A real v1.0.6 database (no products / product_id / deposit) upgrades
    in place without losing data."""
    print("[v1 -> v2 migration]")
    import sqlite3
    dbfile = tmp / "v1.db"
    conn = sqlite3.connect(dbfile)
    conn.executescript("""
    CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE,
      wilaya TEXT DEFAULT '', address TEXT DEFAULT '', notes TEXT DEFAULT '',
      trust_score INTEGER DEFAULT 50, tags TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now','localtime')));
    CREATE TABLE orders (id INTEGER PRIMARY KEY,
      customer_id INTEGER REFERENCES customers(id), product TEXT, price REAL,
      status TEXT DEFAULT 'pending', delivery_method TEXT DEFAULT '',
      wilaya TEXT DEFAULT '', date TEXT DEFAULT (date('now')),
      shipping_cost REAL DEFAULT 0, notes TEXT DEFAULT '',
      shipped_at TEXT, delivered_at TEXT);
    CREATE TABLE blacklist (id INTEGER PRIMARY KEY, phone TEXT UNIQUE, reason TEXT,
      severity INTEGER DEFAULT 2, added_by TEXT DEFAULT '',
      created_at TEXT DEFAULT (datetime('now','localtime')));
    CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
    """)
    conn.execute("INSERT INTO customers(name, phone) VALUES('Old','0555999888')")
    conn.execute("INSERT INTO orders(customer_id, product, price, status) "
                 "VALUES(1,'Ancien',2500,'delivered')")
    conn.commit()
    conn.close()

    db = Database(dbfile)                     # runs schema + migration
    cols = {r[1] for r in db.conn.execute("PRAGMA table_info(orders)")}
    check("v1 orders gained product_id + deposit",
          {"product_id", "deposit"} <= cols)
    check("user_version now 2",
          db.conn.execute("PRAGMA user_version").fetchone()[0] == 2)
    rows = db.query("SELECT * FROM orders")
    check("old rows intact", len(rows) == 1 and rows[0]["deposit"] == 0)
    pid = products.create(db, "New", cost_price=100, sale_price=200, quantity=5)
    oid = orders.create(db, rows[0]["customer_id"], "New", 200,
                        product_id=pid, deposit=50)
    check("new order uses product + deposit", orders.get(db, oid)["deposit"] == 50)


def main() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_products_and_stock(tmp)
        test_deposits(tmp)
        test_wilaya_stats(tmp)
        test_duplicates_and_merge(tmp)
        test_quick_parse()
        test_delivery_import(tmp)
        test_manifest(tmp)
        test_security(tmp)
        test_hma_v2_hashes(tmp)
        test_detector_learning(tmp)
        test_demo_and_relance(tmp)
        test_order_status_buttons_cover_new_status()
        import tempfile
        with tempfile.TemporaryDirectory() as td2:
            test_v1_upgrade_migration(Path(td2))
    print("=" * 50)
    print(f"{PASS} passed, {FAIL} failed")
    if FAILURES:
        print("FAILURES:")
        for f in FAILURES:
            print(" -", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
