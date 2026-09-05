"""
Courier manifest (bordereau): printable PDF listing the orders handed to a
delivery company — with totals and a signature line. One page, any count.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .. import config
from ..database.db import Database
from ..models import orders as orders_model


def generate_manifest(db: Database, order_ids: list[int], company: str,
                      out_path: str | Path, lang: str = "fr") -> str:
    wanted = set(order_ids)
    rows = sorted((r for r in orders_model.list_orders(db, limit=1000000)
                   if r["id"] in wanted), key=lambda r: r["id"])

    w, h = A4
    c = canvas.Canvas(str(out_path), pagesize=A4)
    dark = colors.HexColor("#14161a")

    # header
    c.setFillColor(dark)
    c.rect(0, h - 28 * mm, w, 28 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(config.COLOR_GREEN))
    c.setFont("Helvetica-Bold", 18)
    c.drawString(16 * mm, h - 14 * mm, "HIMAYA")
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 10)
    title = "Bordereau de remise / وصل التسليم" if lang != "en" else "Handover manifest"
    c.drawString(16 * mm, h - 21 * mm, f"{title} — {company} — {date.today():%d/%m/%Y}")

    # table header
    y = h - 36 * mm
    cols = [(16 * mm, "#"), (30 * mm, "Client"), (86 * mm, "Téléphone"),
            (118 * mm, "Wilaya"), (152 * mm, "Montant"), (180 * mm, "Statut")]
    c.setFillColor(colors.HexColor("#1e2128"))
    c.rect(14 * mm, y - 1 * mm, w - 28 * mm, 8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    for x, label in cols:
        c.drawString(x, y + 1.5 * mm, label)

    total = 0.0
    y -= 8 * mm
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    for r in rows:
        if y < 40 * mm:
            c.showPage()
            y = h - 30 * mm
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.black)
        amount = r["price"] - (r["deposit"] or 0)
        total += amount
        line = (f"{r['id']:05d}", r["customer_name"][:24], r["phone"],
                (r["wilaya"] or "")[:16], f"{amount:,.0f} DA".replace(",", " "),
                r["status"])
        for (x, _l), val in zip(cols, line):
            c.drawString(x, y, str(val))
        y -= 6.5 * mm

    # totals + signature
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(16 * mm, y, f"Total: {len(rows)} colis — {total:,.0f} DA".replace(",", " "))
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#6a7280"))
    y -= 8 * mm
    c.drawString(16 * mm, y, "Vendeur / البائع: ______________________")
    c.drawString(120 * mm, y, "Livreur / الموصّل: ______________________")
    c.showPage()
    c.save()
    return str(out_path)
