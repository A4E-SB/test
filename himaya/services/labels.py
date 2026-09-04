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


# Risk line + warning note per level, FR and AR (AR is shaped at draw time)
_RISK_TEXT = {
    "high":   {"fr": "RISQUE ÉLEVÉ",   "ar": "خطر عالٍ"},
    "medium": {"fr": "PRUDENCE",       "ar": "حذر"},
    "low":    {"fr": "FIABLE",         "ar": "موثوق"},
    "normal": {"fr": "",               "ar": ""},
}
_RISK_NOTES = {
    "high":   {"fr": "ATTENTION : client à risque — ne pas expédier sans acompte / appel avant livraison",
               "ar": "تنبيه: زبون خطير — لا ترسل بدون تسبيق أو اتصال قبل التوصيل"},
    "medium": {"fr": "Appeler avant la livraison (client fantôme / perditeur de temps)",
               "ar": "اتصل قبل التوصيل (زبون شبح / مضيع وقت)"},
    "low":    {"fr": "Client de confiance",
               "ar": "زبون موثوق"},
    "normal": {"fr": "", "ar": ""},
}


def _risk_style(tags: str, status: str, lang: str = "fr"
                ) -> tuple[str, colors.Color, str]:
    """(risk_key, color, localized+shaped note) for an order."""
    tags = set((tags or "").split(",")) - {""}
    if "scammer" in tags or status == "fake_payment":
        key = "high"
    elif "ghost" in tags or "time_waster" in tags:
        key = "medium"
    elif "trusted" in tags:
        key = "low"
    else:
        key = "normal"
    color = {"high": config.COLOR_RED, "medium": config.COLOR_ORANGE,
             "low": config.COLOR_GREEN, "normal": config.COLOR_ACCENT}[key]
    note = _RISK_NOTES[key][lang if lang in ("fr", "ar") else "fr"]
    if lang == "ar":
        note = _ar(note)
    return key, colors.HexColor(color), note


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
        risk_key, risk_color, note = _risk_style(cust["tags"] or "", order["status"], lang)
        ar = (lang == "ar")   # Arabic mode: shape every Arabic string
        name = _ar(cust["name"]) if ar else cust["name"]
        wil = order["wilaya"] or cust["wilaya"] or ""
        wil_display = _ar(wilaya_ar(wil)) if ar and wil else wil

        # Header band (risk colored)
        c.setFillColor(risk_color)
        c.rect(0, h - 14 * mm, w, 14 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont(latin, 12)
        title = _ar("حماية") + "  HIMAYA" if ar else "HIMAYA"
        c.drawCentredString(w / 2, h - 9 * mm, title)
        c.setFont(latin, 9)
        rt = _RISK_TEXT[risk_key][lang if lang in ("fr", "ar") else "fr"]
        if ar:
            rt = _ar(rt) + ("  •  " + _RISK_TEXT[risk_key]["fr"] if rt else "")
        c.drawCentredString(w / 2, h - 12.2 * mm, rt)

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
        delivery = order["delivery_method"] or ""
        c.drawString(6 * mm, y, (_ar(delivery) if ar else delivery)[:30])

        # Address (wrapped, max 2 lines)
        addr = (cust["address"] or "")[:70]
        if ar:
            addr = _ar(addr)
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
        c.drawString(6 * mm, y, _ar(prod) if ar else prod)
        y -= 9 * mm
        c.setFont(latin, 17)
        if ar:
            price_txt = f"{order['price']:,.0f} ".replace(",", " ") + _ar("دج")
        else:
            price_txt = f"{order['price']:,.0f} DA".replace(",", " ")
        c.drawString(6 * mm, y, price_txt)
        c.setFont(latin, 9)
        cod = "À PAYER À LA LIVRAISON"
        cod_ar = "الدفع عند الاستلام"
        c.drawRightString(w - 6 * mm, y,
                          (_ar(cod_ar) + "  •  " if ar else "") + cod)

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
