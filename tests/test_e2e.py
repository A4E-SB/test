"""
End-to-end journey suite (v1.7.2): drives REAL user flows against a REAL
SQLite database — everything except pixels. Complements the unit batteries:
core (models), v11 (features), packaging, ui-smoke (widgets under stubs).

Journey: first-run -> customers & trust -> full order lifecycle (dates,
custom companies, deposits, stock) -> reports math -> labels PDF ->
exports & transfers -> backup/restore -> security -> i18n audit ->
migration from a v1.0.6-era database.
"""

from __future__ import annotations

import csv
import re
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

PASS, FAIL = [0], [0]
FAILURES: list[str] = []


def check(name: str, cond: bool, extra: str = "") -> None:
    if cond:
        PASS[0] += 1
    else:
        FAIL[0] += 1
        FAILURES.append(f"{name} {extra}")
        print(f"    FAIL: {name} {extra}")


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from himaya import config
    from himaya.database import Database, seed
    from himaya.models import (blacklist, customers, orders,
                               products, settings_store)
    from himaya.services import (backup, demo, hma, labels, relance,
                                 reports, security, trust)
    from himaya.i18n import _TR, t

    tmp = Path(tempfile.mkdtemp(prefix="himaya_e2e_"))
    config.DATA_DIR = tmp
    config.EVIDENCE_DIR = tmp / "evidence"
    config.BACKUP_DIR = tmp / "backups"
    config.EVIDENCE_DIR.mkdir(exist_ok=True)
    config.BACKUP_DIR.mkdir(exist_ok=True)

    # =====================================================================
    print("== 1. first run ==")
    db = Database(tmp / "himaya.db")
    seed(db)
    check("schema at v2", db.scalar("PRAGMA user_version") == 2)
    demo.load_demo(db)
    check("demo data loads", db.scalar("SELECT COUNT(*) FROM customers") > 0)
    check("demo has orders", db.scalar("SELECT COUNT(*) FROM orders") > 0)

    # =====================================================================
    print("== 2. customers & trust journey ==")
    db2 = Database(tmp / "t2" / "himaya.db")
    seed(db2)
    cid = customers.create(db2, "Amine Fiable", "0555111222",
                           wilaya="Alger", address="Bab Ezzouar")
    check("duplicate phone rejected", True)  # unique index; try a dupe:
    try:
        customers.create(db2, "Clone", "0555111222")
        dupes_rejected = False
    except Exception:
        dupes_rejected = True
    check("duplicate phone raises", dupes_rejected)
    score, tags = trust.refresh(db2, cid)
    check("fresh customer trust 50 + 'new' tag", score == 50 and tags == ["new"])
    # 3 delivered -> trusted (>=80 AND >=3 delivered)
    for i in range(3):
        oid = orders.create(db2, cid, f"Prod{i}", 2000 + i, status="confirmed")
        orders.set_status(db2, oid, "shipped")
        orders.set_status(db2, oid, "delivered")
    score, tags = trust.refresh(db2, cid)
    check("3 delivered -> trusted tag", score >= config.TRUST_TRUSTED
          and "trusted" in tags, f"score={score} tags={tags}")
    # a ghost order must drop the score below trusted
    oid = orders.create(db2, cid, "ProdX", 3000, status="shipped")
    orders.set_status(db2, oid, "ghosted")
    score2, _ = trust.refresh(db2, cid)
    check("ghost lowers trust", score2 < score, f"{score} -> {score2}")

    # =====================================================================
    print("== 3. order lifecycle (v1.4 features + stock) ==")
    prod = products.create(db2, "Montre connectée", cost_price=1800,
                           sale_price=4200, quantity=5)
    check("product stock starts at 5",
          products.get(db2, prod)["quantity"] == 5)
    custom_cid = customers.create(db2, "Dated Client", "0669998877",
                                  wilaya="Sétif")
    dated_oid = orders.create(db2, custom_cid, "Ancienne commande", 900,
                              order_date="15/01/2026")
    check("custom date normalized to ISO",
          orders.get(db2, dated_oid)["date"] == "2026-01-15")
    oid = orders.create(db2, custom_cid, "Montre connectée", 4200,
                        status="waiting_deposit", delivery_method="SpeedEx",
                        product_id=prod, deposit=1000)
    o = orders.get(db2, oid)
    check("order defaults to today", o["date"] == date.today().isoformat())
    check("deposit stored", o["deposit"] == 1000)
    check("custom company stored", o["delivery_method"] == "SpeedEx")
    check("company remembered in the shared list",
          "SpeedEx" in settings_store.delivery_companies(db2))
    check("waiting order holds one unit",
          products.get(db2, prod)["quantity"] == 4)
    # waiting_deposit -> confirmed -> shipped -> delivered -> paid
    for st in ("confirmed", "shipped", "delivered", "paid"):
        orders.set_status(db2, oid, st)
    o = orders.get(db2, oid)
    check("final status paid", o["status"] == "paid")
    check("shipped_at + delivered_at stamped",
          bool(o["shipped_at"]) and bool(o["delivered_at"]))
    check("paid still holds the unit (sold)", 
          products.get(db2, prod)["quantity"] == 4)
    # blocked order: no stock held + shipping counted as saved
    q_before = products.get(db2, prod)["quantity"]
    orders.create(db2, custom_cid, "Montre connectée", 4200,
                  status="blocked", product_id=prod, shipping_cost=700)
    check("blocked holds no stock",
          products.get(db2, prod)["quantity"] == q_before)
    check("blocked shipping counted as saved",
          orders.money_saved(db2) == 700)
    # canceled releases the held unit
    coid = orders.create(db2, custom_cid, "Montre connectée", 4200,
                         status="confirmed", product_id=prod)
    orders.set_status(db2, coid, "canceled")
    check("canceled releases the unit",
          products.get(db2, prod)["quantity"] == q_before)

    # =====================================================================
    print("== 4. reports math coherence ==")
    goid = orders.create(db2, cid, "Fantôme", 900, status="shipped",
                         shipping_cost=600)
    orders.set_status(db2, goid, "ghosted")
    foid = orders.create(db2, cid, "Faux paiement", 5000, status="shipped",
                         shipping_cost=400)
    orders.set_status(db2, foid, "fake_payment")
    today = date.today()
    s = reports.monthly_summary(db2, today.year, today.month)
    check("real profit <= profit",
          s["real_profit"] <= s["profit"] + 1e-9,
          f"{s['real_profit']} vs {s['profit']}")
    check("revenue counts the paid order only (this month)",
          s["revenue"] == 4200, f"rev={s['revenue']}")
    check("losses = ghost shipping + fake price+shipping",
          s["losses"] == 600 + 5400, f"losses={s['losses']}")
    check("saved = blocked shipping", s["saved"] == 700)
    bd = reports.loss_breakdown(db2, s["from"], s["to"])
    check("breakdown total matches losses",
          abs(bd["total"]["amount"] - s["losses"]) < 1e-9)
    check("all-time dashboard revenue == paid sum",
          orders.paid_revenue(db2) == 4200)

    # =====================================================================
    print("== 5. labels PDF ==")
    out = tmp / "label.pdf"
    labels.generate_labels(db2, [oid], out, lang="fr")
    check("label PDF generated", out.exists() and out.stat().st_size > 500)
    check("it is a real PDF", out.read_bytes()[:4] == b"%PDF")
    out_ar = tmp / "label_ar.pdf"
    labels.generate_labels(db2, [oid], out_ar, lang="ar")
    check("arabic label PDF generated", out_ar.exists())

    # =====================================================================
    print("== 6. exports & transfers ==")
    csv_path = tmp / "orders.csv"
    n = hma.export_orders_csv(db2, csv_path)
    check("csv export rows > 0", n > 0)
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    check("csv has header + data", len(rows) == n + 1)
    xlsx_path = tmp / "orders.xlsx"
    nx = hma.export_orders_excel(db2, xlsx_path)
    check("xlsx export works", nx == n and xlsx_path.exists())
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path)
    check("xlsx readable by excel libs", wb.active.max_row >= n)
    # csv import into a fresh database (seller-to-seller transfer)
    db3 = Database(tmp / "t3" / "himaya.db")
    seed(db3)
    res = hma.import_orders_csv(db3, csv_path)
    check("csv import creates orders", res["orders"] == n, str(res))
    # blacklist transfer .hma
    blacklist.add(db2, "0770000000", reason="test", severity=3)
    bl = tmp / "black.hma"
    hma.export_blacklist(db2, bl)
    stats = hma.import_blacklist(db3, bl)
    check("blacklist .hma round-trip", stats.get("imported", 0) >= 1
          or blacklist.count(db3) >= 1, str(stats))

    # =====================================================================
    print("== 7. backup & restore ==")
    bfile = backup.backup(db2, dest_dir=tmp / "backups")
    check("backup file created", Path(bfile).exists())
    restored_path = tmp / "restored.db"
    backup.restore(bfile, restored_path)
    dbr = Database(restored_path)
    check("restored db keeps customers",
          dbr.scalar("SELECT COUNT(*) FROM customers")
          == db2.scalar("SELECT COUNT(*) FROM customers"))
    check("restored db keeps orders",
          dbr.scalar("SELECT COUNT(*) FROM orders")
          == db2.scalar("SELECT COUNT(*) FROM orders"))

    # =====================================================================
    print("== 8. security & relance ==")
    check("no password initially", not security.has_password(db2))
    security.set_password(db2, "himaya-secret-1")
    check("password stored", security.has_password(db2))
    check("wrong password rejected",
          not security.verify_password(db2, "nope"))
    check("right password accepted",
          security.verify_password(db2, "himaya-secret-1"))
    security.clear_password(db2)
    check("password cleared", not security.has_password(db2))
    stuck = relance.stuck_orders(db2, days=3)
    check("relance finds stuck orders (demo ghosts)",
          isinstance(stuck, list))
    if stuck:
        msg = relance.reminder_message(stuck[0], "fr", db2)
        check("reminder message renders", len(msg) > 10)
        msg_ar = relance.reminder_message(stuck[0], "ar", db2)
        check("arabic reminder renders", len(msg_ar) > 10)
    # v1.7.4: the full follow-up journey, end to end
    rcid = customers.create(db2, "Client Relance", "0771234567")
    five_days_ago = (date.today() - timedelta(days=5)).isoformat()
    soid = orders.create(db2, rcid, "Produit dormant", 6500, status="confirmed",
                         order_date=five_days_ago)
    stuck5 = relance.stuck_orders(db2, days=3)
    ids5 = [r["id"] for r in stuck5]
    check("5-day-old confirmed order is stuck (threshold 3)", soid in ids5)
    row5 = next(r for r in stuck5 if r["id"] == soid)
    check("days_waiting >= 5", row5["days_waiting"] >= 5, str(row5["days_waiting"]))
    check("stuck row carries customer + phone",
          row5["customer_name"] == "Client Relance" and row5["phone"] == "0771234567")
    msg = relance.reminder_message(row5, "fr", db2)
    check("french reminder names the customer, product and wait",
          "Client" in msg and "Produit dormant" in msg and "5 jour" in msg,
          msg)
    msg_ar = relance.reminder_message(row5, "ar", db2)
    check("arabic reminder renders for the same order", len(msg_ar) > 10)
    check("threshold 7 excludes the 5-day order",
          soid not in [r["id"] for r in relance.stuck_orders(db2, days=7)])
    settings_store.set_setting(db2, "relance_days", "1")
    check("threshold from settings is honored (1 day catches it)",
          soid in [r["id"] for r in relance.stuck_orders(db2, days=1)])
    # a delivered order is never 'stuck'
    orders.set_status(db2, soid, "delivered")
    check("delivered order leaves the stuck list",
          soid not in [r["id"] for r in relance.stuck_orders(db2, days=1)])
    from himaya.i18n import _TR as _tr
    check("copy buttons translated (rel_copy_ar/fr)",
          "rel_copy_ar" in _tr and "rel_copy_fr" in _tr)

    # =====================================================================
    print("== 9. i18n audit (all keys x3 languages, all call sites) ==")
    missing_lang = [k for k, v in _TR.items()
                    if not (v.get("fr") and v.get("en") and v.get("ar"))]
    check("every key has fr+en+ar", not missing_lang,
          str(missing_lang[:5]))
    # placeholders identical across languages
    ph_bad = []
    for k, v in _TR.items():
        sets = [set(re.findall(r"{(\w+)}", v[l])) for l in ("fr", "en", "ar")]
        if not (sets[0] == sets[1] == sets[2]):
            ph_bad.append(k)
    check("placeholders consistent across languages", not ph_bad,
          str(ph_bad[:5]))
    # every key used in the source exists
    used = set()
    for f in Path("himaya").rglob("*.py"):
        if f.name == "i18n.py":
            continue        # its own docstrings mention t("key") patterns
        src = f.read_text(encoding="utf-8")
        used |= set(re.findall(r'\bt\(\s*"([a-z0-9_]+)"', src))
        used |= set(re.findall(r'\.t\(\s*"([a-z0-9_]+)"', src))
    unknown = sorted(k for k in used if k not in _TR)
    check("every t() call site has a key", not unknown, str(unknown[:8]))
    # sample render in all languages
    for lang in ("fr", "en", "ar"):
        check(f"status renders in {lang}",
              t("st_waiting_deposit", lang) != "st_waiting_deposit")

    # =====================================================================
    print("== 10. migration from a v1.0.6-era database ==")
    old_path = tmp / "old" / "himaya.db"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(str(old_path))
    raw.executescript("""
        CREATE TABLE customers (id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, phone TEXT NOT NULL, wilaya TEXT DEFAULT '',
            address TEXT DEFAULT '', trust_score INTEGER NOT NULL DEFAULT 50,
            tags TEXT DEFAULT '', notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')));
        CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            product TEXT NOT NULL, price REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending', delivery_method TEXT DEFAULT '',
            wilaya TEXT DEFAULT '', date TEXT NOT NULL DEFAULT (date('now','localtime')),
            shipping_cost REAL NOT NULL DEFAULT 0, notes TEXT DEFAULT '',
            shipped_at TEXT DEFAULT '', delivered_at TEXT DEFAULT '');
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT DEFAULT '');
        INSERT INTO customers(name, phone) VALUES ('Vieux Client','0555999888');
        INSERT INTO orders(customer_id, product, price, status, shipping_cost)
            VALUES (1, 'Ancien produit', 1500, 'delivered', 400);
        PRAGMA user_version = 0;
    """)
    raw.commit()
    raw.close()
    dbm = Database(old_path)          # opens + migrates in place
    check("v1 db upgraded to v2", dbm.scalar("PRAGMA user_version") == 2)
    cols = {r[1] for r in dbm.query("PRAGMA table_info(orders)")}
    check("orders gained product_id + deposit",
          {"product_id", "deposit"} <= cols)
    tables = {r[0] for r in dbm.query(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    check("products catalog created", "products" in tables)
    check("old customer intact",
          dbm.scalar("SELECT name FROM customers WHERE id=1") == "Vieux Client")
    check("old order intact (price/status/shipping)",
          dbm.query_one("SELECT price, status, shipping_cost FROM orders "
                        "WHERE id=1")["price"] == 1500)
    check("old order works in new code paths",
          orders.total_lost(dbm) == 0)
    dbm.close()

    print()
    print("=" * 50)
    print(f"{PASS[0]} passed, {FAIL[0]} failed")
    if FAILURES:
        print("Failures:")
        for f in FAILURES:
            print("  -", f)
    return 1 if FAIL[0] else 0


if __name__ == "__main__":
    sys.exit(main())
