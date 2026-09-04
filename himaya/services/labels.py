"""
Delivery label generator (ReportLab PDF, local only).

Two layouts: A6 (105x148 mm — the standard Yalidine-style label) and
100x100 mm square labels for thermal printers. Risk level and warning notes
are printed in color so the delivery guy sees them instantly.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .. import config
from ..database.db import Database
from ..models import orders as orders_model
from ..models import settings_store
from ..wilayas import wilaya_ar

SQUARE = (100 * mm, 100 * mm)

# Fonts: prefer bundled Noto Naskh Arabic -> Windows Arial -> Helvetica
_FONT_CACHE: dict[str, str] = {}


def _register_fonts() -> tuple[str, str]:
    """(latin_font, arabic_capable_font)."""
    if _FONT_CACHE:
        return _FONT_CACHE["latin"], _FONT_CACHE["arabic"]
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    latin, arabic = "Helvetica", "Helvetica"
    candidates = [
        config.ASSETS_DIR / "fonts" / "NotoNaskhArabic-Regular.ttf",
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for i, p in enumerate(candidates):
        try:
            if p.exists():
                pdfmetrics.registerFont(TTFont(f"HimayaFont{i}", str(p)))
                latin = f"HimayaFont{i}"
                arabic = latin
                break
        except Exception:
            continue
    _FONT_CACHE["latin"], _FONT_CACHE["arabic"] = latin, arabic
    return latin, arabic


def _ar(text: str) -> str:
    """Shape Arabic text for correct RTL rendering in ReportLab."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _risk_style(tags: str, status: str) -> tuple[str, colors.Color, str]:
    """(risk_key, color, note) for an order."""
    tags = set((tags or "").split(",")) - {""}
    if "scammer" in tags or status == "fake_payment":
        return "high", colors.HexColor(config.COLOR_RED), "ATTENTION : client à risque — ne pas expédier sans acompte / appel avant livraison"
    if "ghost" in tags or "time_waster" in tags:
        return "medium", colors.HexColor(config.COLOR_ORANGE), "Appeler avant la livraison (client fantôme / perditeur de temps)"
    if "trusted" in tags:
        return "low", colors.HexColor(config.COLOR_GREEN), "Client de confiance"
    return "normal", colors.HexColor(config.COLOR_ACCENT), ""


def generate_labels(db: Database, order_ids: list[int], out_path: str | Path,
                    lang: str = "fr") -> str:
    """One page per order. Returns the output path."""
    latin, arabic_font = _register_fonts()
    size_name = settings_store.get_setting(db, "label_size", "a6")
    pagesize = SQUARE if size_name == "square" else A6
    w, h = pagesize

    c = canvas.Canvas(str(out_path), pagesize=pagesize)
    for oid in order_ids:
        order = orders_model.get(db, oid)
        if not order:
            continue
        cust = db.query_one("SELECT * FROM customers WHERE id = ?", (order["customer_id"],))
        if not cust:
            continue
        risk_key, risk_color, note = _risk_style(cust["tags"] or "", order["status"])
        name = cust["name"]
        wil = order["wilaya"] or cust["wilaya"] or ""
        wil_display = wilaya_ar(wil) if lang == "ar" and wil else wil

        # Header band (risk colored)
        c.setFillColor(risk_color)
        c.rect(0, h - 14 * mm, w, 14 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(latin, 12)
        title = "حماية HIMAYA" if lang == "ar" else "HIMAYA"
        c.drawCentredString(w / 2, h - 9 * mm, title)
        c.setFont(latin, 9)
        risk_txt = {"high": "RISQUE ÉLEVÉ / خطر عالٍ", "medium": "PRUDENCE / حذر",
                    "low": "FIABLE / موثوق", "normal": ""}[risk_key]
        c.drawCentredString(w / 2, h - 12.2 * mm, risk_txt)

        # Order number big
        c.setFillColor(colors.HexColor(config.COLOR_FG if size_name == "square" else "#000000"))
        y = h - 24 * mm
        c.setFont(latin, 20)
        num = f"N° {oid:05d}"
        if size_name == "square":
            c.setFillColor(colors.black)
        c.drawString(6 * mm, y, num)
        c.setFont(latin, 10)
        c.drawRightString(w - 6 * mm, y, str(order["date"]))

        # Barcode-ish separator
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.line(6 * mm, y - 3 * mm, w - 6 * mm, y - 3 * mm)

        # Customer block
        y -= 14 * mm
        c.setFont(latin, 14)
        c.drawString(6 * mm, y, name[:28])
        y -= 7 * mm
        c.setFont(latin, 13)
        c.drawString(6 * mm, y, cust["phone"])
        y -= 7 * mm
        c.setFont(latin, 12)
        c.drawString(6 * mm, y, wil_display)
        y -= 7 * mm
        c.setFont(latin, 9)
        c.drawString(6 * mm, y, (order["delivery_method"] or "")[:30])

        # Address (wrapped, max 2 lines)
        addr = (cust["address"] or "")[:70]
        if addr:
            y -= 5.5 * mm
            c.setFont(latin, 9)
            c.drawString(6 * mm, y, addr[:42])
            if len(addr) > 42:
                y -= 5 * mm
                c.drawString(6 * mm, y, addr[42:])

        # Product + COD price
        y -= 11 * mm
        c.setFont(latin, 10)
        prod = order["product"][:34]
        c.drawString(6 * mm, y, prod)
        y -= 9 * mm
        c.setFont(latin, 17)
        price_txt = f"{order['price']:,.0f} DA".replace(",", " ")
        if lang == "ar":
            price_txt = f"{order['price']:,.0f} دج".replace(",", " ")
        c.drawString(6 * mm, y, price_txt)
        c.setFont(latin, 9)
        c.drawRightString(w - 6 * mm, y, "À PAYER À LA LIVRAISON / الدفع عند الاستلام")

        # Warning note
        if note:
            y -= 9 * mm
            c.setFillColor(risk_color)
            c.setFont(latin, 8.5)
            c.drawString(6 * mm, y, note[:58])
            if len(note) > 58:
                y -= 4.5 * mm
                c.drawString(6 * mm, y, note[58:116])
            c.setFillColor(colors.black)

        # Code128 barcode of the order id
        try:
            from reportlab.graphics.barcode import code128
            from reportlab.graphics.shapes import Drawing
            bar = code128.Code128(f"HM{oid:06d}", barHeight=12 * mm, barWidth=1.1)
            d = Drawing(0, 0)
            d.add(bar)
            d.drawOn(c, 6 * mm, 6 * mm)
        except Exception:
            pass

        c.showPage()
    c.save()
    return str(out_path)
