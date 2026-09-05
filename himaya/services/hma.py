"""
.hma file format — offline blacklist sharing between sellers (USB key).

A .hma file is a self-describing, human-readable JSON document with a magic
header. No encryption on purpose: sellers can inspect what they import, and
any Himaya app can read it. Entries are merged, the most severe wins.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..database.db import Database
from ..models import blacklist
from ..services.phone import normalize_phone

MAGIC = "HIMAYA-BLACKLIST"
FORMAT_VERSION = 2     # v2 adds fake-receipt hashes (known-fakes sharing)


def export_blacklist(db: Database, out_path: str | Path) -> dict:
    """Write the full blacklist to a .hma file. Returns {count, path}."""
    entries = []
    for row in blacklist.all_entries(db):
        entries.append({
            "phone": row["phone"],
            "reason": row["reason"],
            "severity": row["severity"],
            "reported_date": row["reported_date"],
        })
    # v2: share known fake-receipt hashes (no images, no private data)
    hashes = [{"hash": r["image_hash"], "phone": r["phone"] or "", "date": r["date"]}
              for r in db.query(
                  "SELECT image_hash, phone, date FROM fake_screenshots "
                  "ORDER BY id DESC LIMIT 500")]
    doc = {
        "magic": MAGIC,
        "version": FORMAT_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(entries),
        "entries": entries,
        "fake_hashes": hashes,
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"count": len(entries), "path": str(out)}


def import_blacklist(db: Database, in_path: str | Path) -> dict:
    """
    Merge a .hma file into the local blacklist.
    Returns {imported, skipped, invalid}.
    """
    doc = json.loads(Path(in_path).read_text(encoding="utf-8"))
    if doc.get("magic") != MAGIC:
        raise ValueError("not_a_hma_file")
    imported = skipped = invalid = 0
    for e in doc.get("entries", []):
        p = normalize_phone(e.get("phone", ""))
        if not p:
            invalid += 1
            continue
        existing = blacklist.is_blacklisted(db, p)
        if existing:
            skipped += 1
        blacklist.add(
            db, p,
            reason=str(e.get("reason", ""))[:500],
            severity=int(e.get("severity", 2)),
        )
        if not existing:
            imported += 1

    # v2: merge known fake hashes (idempotent — re-import skips known ones)
    hashes_added = 0
    from ..models import screenshots as screenshots_model
    for h in doc.get("fake_hashes", []):
        ih = str(h.get("hash", "")).strip()
        if ih and not screenshots_model.find_by_hash(db, ih):
            screenshots_model.save(db, ih, h.get("phone", ""),
                                   {"source": "hma", "date": h.get("date", "")})
            hashes_added += 1

    return {"imported": imported, "skipped": skipped, "invalid": invalid,
            "hashes_added": hashes_added}


# ---------------------------------------------------------------------------
# Orders CSV / Excel export + CSV import
# ---------------------------------------------------------------------------

ORDER_CSV_HEADERS = ["id", "date", "customer", "phone", "product", "price",
                     "status", "delivery_method", "wilaya", "shipping_cost", "notes"]


def export_orders_csv(db: Database, out_path: str | Path) -> int:
    import csv
    from ..models import orders as orders_model
    rows = orders_model.list_orders(db, limit=1000000)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(ORDER_CSV_HEADERS)
        for r in rows:
            w.writerow([r["id"], r["date"], r["customer_name"], r["phone"],
                        r["product"], r["price"], r["status"], r["delivery_method"],
                        r["wilaya"], r["shipping_cost"], r["notes"]])
    return len(rows)


def export_orders_excel(db: Database, out_path: str | Path) -> int:
    from openpyxl import Workbook
    from ..models import orders as orders_model
    rows = orders_model.list_orders(db, limit=1000000)
    wb = Workbook()
    ws = wb.active
    ws.title = "Orders"
    ws.append(ORDER_CSV_HEADERS)
    for r in rows:
        ws.append([r["id"], r["date"], r["customer_name"], r["phone"],
                   r["product"], float(r["price"]), r["status"],
                   r["delivery_method"], r["wilaya"],
                   float(r["shipping_cost"]), r["notes"]])
    for col, width in zip("ABCDEFGHIJK", (6, 12, 22, 14, 24, 10, 12, 16, 18, 14, 30)):
        ws.column_dimensions[col].width = width
    wb.save(out_path)
    return len(rows)


def import_orders_csv(db: Database, in_path: str | Path) -> dict:
    """
    Import orders from a CSV previously exported by Himaya (same headers).
    Customers are matched by phone; missing ones are created.
    Semi-colon or comma separated, utf-8(-sig) or latin-1.
    """
    import csv
    from ..models import customers as customers_model
    from ..models import orders as orders_model
    from ..services import trust

    created_orders = created_customers = 0
    path = Path(in_path)
    try:
        f = open(path, encoding="utf-8-sig", newline="")
    except UnicodeDecodeError:
        f = open(path, encoding="latin-1", newline="")
    with f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        reader = csv.DictReader(f, dialect=dialect)
        headers = {h.strip().lower(): h for h in (reader.fieldnames or [])}

        def col(row, name):
            return row.get(headers.get(name, name), "").strip()

        for row in reader:
            phone = col(row, "phone")
            name = col(row, "customer") or phone
            if not phone:
                continue
            cust = customers_model.find_by_phone(db, phone)
            if not cust:
                cid = customers_model.create(db, name, phone,
                                             wilaya=col(row, "wilaya"))
                created_customers += 1
            else:
                cid = cust["id"]
            orders_model.create(
                db, cid,
                product=col(row, "product") or "—",
                price=_f(col(row, "price")),
                status=col(row, "status") or "pending",
                delivery_method=col(row, "delivery_method"),
                wilaya=col(row, "wilaya"),
                shipping_cost=_f(col(row, "shipping_cost")),
                notes=col(row, "notes"),
                order_date=col(row, "date"),
            )
            created_orders += 1
            trust.refresh(db, cid)
    return {"orders": created_orders, "customers": created_customers}


def _f(v) -> float:
    try:
        return float(str(v).replace(",", ".").replace(" ", "") or 0)
    except ValueError:
        return 0.0
