"""
Relance service: find orders stuck too long in confirmed/shipped and build
polite reminder messages (AR/FR) with the CCP/BaridiMob info for deposits.
"""

from __future__ import annotations

from ..database.db import Database
from ..models import settings_store


def stuck_orders(db: Database, days: int = 3) -> list[dict]:
    """Orders sitting in confirmed/shipped/waiting_deposit for >= `days` days."""
    rows = db.query(
        """SELECT o.id, o.date, o.status, o.product, o.price, o.wilaya,
                  o.customer_id, c.name AS customer_name, c.phone,
                  julianday('now') - julianday(o.date) AS days_waiting
           FROM orders o JOIN customers c ON c.id = o.customer_id
           WHERE o.status IN ('confirmed', 'shipped', 'waiting_deposit')
             AND o.date <= date('now', ?)
           ORDER BY days_waiting DESC""",
        (f"-{int(days)} days",))
    out = []
    for r in rows:
        d = dict(r)
        d["days_waiting"] = int(d["days_waiting"] or 0)
        out.append(d)
    return out


def _ccp_info(db: Database) -> str:
    ccp = settings_store.get_setting(db, "ccp_number", "")
    rip = settings_store.get_setting(db, "baridimob_rip", "")
    parts = []
    if ccp:
        parts.append(f"CCP {ccp}")
    if rip:
        parts.append(f"BaridiMob RIP {rip}")
    return " / ".join(parts) or "CCP (voir page Sécurité & paramètres)"


def reminder_message(order: dict, lang: str, db: Database) -> str:
    """A ready-to-paste reminder for one stuck order (AR or FR)."""
    name = (order.get("customer_name") or "").split(" ")[0] or ""
    days = int(order.get("days_waiting") or 0)
    oid = order.get("id")
    product = order.get("product") or ""
    if lang == "ar":
        msg = (f"مرحبا {name} 🌟 بخصوص طلبك رقم {oid} ({product})، "
               f"لاحظنا أنه في انتظار الرد من {days} أيام. "
               "نعطيك 24 ساعة للتأكيد النهائي، وإلا سنلغي الطلب. "
               "شكرا لتفهمك 🙏")
        if order.get("status") == "waiting_deposit":
            msg += f"\nللتسبيق: {_ccp_info(db)}"
        return msg
    msg = (f"Bonjour {name} 🌟 concernant votre commande n°{oid} ({product}) : "
           f"elle attend votre réponse depuis {days} jours. "
           "Vous avez 24h pour confirmer, sinon la commande sera annulée. "
           "Merci de votre compréhension 🙏")
    if order.get("status") == "waiting_deposit":
        msg += f"\nPour l'acompte : {_ccp_info(db)}"
    return msg
