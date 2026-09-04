"""
First-run seeding: default settings and smart reply templates (AR/FR).
Idempotent — safe to call on every launch.
"""

from __future__ import annotations

from ..database.db import Database

DEFAULT_SETTINGS = {
    "language": "fr",                 # 'fr' | 'ar'
    "default_delivery": "Yalidine",
    "ccp_number": "",                 # CCP account (ex: 0012345678 Cle 45)
    "ccp_name": "",                   # Account holder name
    "baridimob_rip": "",              # RIP 020 XXXX XXXX XXXX XXXX XXX
    "baridimob_phone": "",
    "default_shipping_cost": "600",   # average DZD shipping cost
    "tesseract_path": "",             # optional custom path to tesseract.exe
    "label_size": "a6",               # 'a6' (105x148) | 'square' (100x100)
}

# category: deposit / negotiation / ghost / warning / general
DEFAULT_TEMPLATES = [
    ("Demande d'acompte (standard)", "deposit",
     "السلام عليكم، لتثبيت الطلب نطلب acompte (تسبيق) لأن عدد الطلبات كبير. "
     "يمكنك التسديد عبر CCP أو BaridiMob: {ccp_info}. الباقي عند الاستلام. شكرا لثقتك 🙏",
     "Bonjour, pour confirmer votre commande nous demandons un acompte "
     "(les commandes sont nombreuses). Virement CCP / BaridiMob : {ccp_info}. "
     "Le reste à la livraison. Merci de votre confiance 🙏"),
    ("Demande d'acompte (après plusieurs annulations)", "deposit",
     "وعذرا منك، سجّلنا عندهم أكثر من طلب وكل مرة يلغى بعد التأكيد، لذلك التسبيق إجباري "
     "لتثبيت الطلب: {ccp_info}. وهذا التسبيق يُخصم من السعر النهائي.",
     "Désolé, ce numéro a déjà confirmé puis annulé plusieurs commandes. "
     "Un acompte est donc obligatoire pour confirmer : {ccp_info}. "
     "Il sera déduit du prix final."),
    ("Prix final ? (répéteurs)", "negotiation",
     "السلام عليكم 🌟 السعر المعلن هو السعر النهائي وثابت، بدون تفاوض. "
     "المنتج أصلي والجودة مضمونة، والتوصيل لـ 58 ولاية. إذا موافق قولي « أكد » ونثبت لك الطلب 🚚",
     "Bonjour 🌟 Le prix affiché est le prix final, non négociable. "
     "Produit original, qualité garantie, livraison dans les 58 wilayas. "
     "Si vous êtes d'accord, dites « je confirme » et je réserve 🚚"),
    ("Négociateur infatigable (dernier message)", "negotiation",
     "أخي/أختي، احتراما لوقتك ووقتي: السعر نهائي 🙏 أي نقص يعني خسارة لنا. "
     "عندك القرار، وإذا بدات تبدل رأيك نحن موجودين. توافق نكمل، وإلا سلام عليكم 🌹",
     "Merci pour votre intérêt. Par respect pour votre temps et le mien : "
     "le prix est final 🙏 Vous décidez — si ça vous convient on continue, "
     "sinon je reste à votre disposition 🌹"),
    ("Ghost après confirmation", "ghost",
     "مرحبا، لاحظنا أنك أكدت الطلب ولم تعد تجاوب. نعطيك 24 ساعة للتأكيد النهائي، "
     "بعد ذلك نلغي الطلب ونعطي المنتج لشخص آخر. شكرا للتفهم.",
     "Bonjour, vous aviez confirmé cette commande puis plus de réponse. "
     "Vous avez 24h pour confirmer, ensuite la commande sera annulée et le "
     "produit proposé à un autre client. Merci de votre compréhension."),
    ("Relance avant annulation", "ghost",
     "آخر تذكير: الطلب رقم {order_id} باقي عندك من {days} أيام بدون تأكيد. "
     "اليوم نلغيه بشكل نهائي. إذا ما زلت مهتما أرسل « أؤكد ».",
     "Dernier rappel : la commande n°{order_id} attend votre confirmation "
     "depuis {days} jours. Elle sera annulée aujourd'hui. Si vous êtes "
     "toujours intéressé(e), répondez « je confirme »."),
    ("Avertissement faux paiement", "warning",
     "الوصل (screenshot) الذي أرسلته غير صحيح — لا يوجد أي تحويل في حسابنا بهذا المبلغ "
     "أو التاريخ. نعطيك مهلة لإرسال وصل حقيقي، وإلا نعتبر الطلب ملغى ونحتفظ بحقنا في الإبلاغ.",
     "Le reçu (screenshot) envoyé est incorrect — aucun virement correspondant "
     "n'apparaît sur notre compte. Merci d'envoyer un reçu valide, sinon la "
     "commande sera annulée."),
    ("Refus à la livraison (recouvrement)", "warning",
     "وصل المنتج لمقر الشركة ورفضت الاستلام. هذا يعتبر طلب وهمي ومصاريف التوصيل "
     "({shipping} دج) على حسابنا. نطلب منك تسديد المصاريف عبر {ccp_info} وإلا رقمك "
     "سيدخل القائمة السوداء ويُشارك مع البائعين.",
     "Le colis est arrivé au bureau et vous avez refusé la livraison. "
     "C'est une commande fantôme : les frais ({shipping} DA) sont à notre charge. "
     "Merci de régler via {ccp_info}, sinon votre numéro sera blacklisté "
     "et partagé avec d'autres vendeurs."),
    ("Confirmation de commande", "general",
     "تم تسجيل طلبك ✅\nالمنتج: {product}\nالسعر: {price} دج\nالولاية: {wilaya}\n"
     "التوصيل خلال 48 ساعة. رقم الطلب: {order_id}. المرجو الرد بكلمة « مؤكد » لتثبيت الطلب.",
     "Commande enregistrée ✅\nProduit : {product}\nPrix : {price} DA\n"
     "Wilaya : {wilaya}\nLivraison sous 48h. N° commande : {order_id}. "
     "Répondez « confirmé » pour valider."),
    ("Rappel livraison", "general",
     "سلام، منتجك وصل مقر الشركة في ولايتك 📦 المرجو الاستلام خلال 48 ساعة "
     "وإلا يرجع المنتج ومصاريف التوصيل تبقى عليك.",
     "Bonjour, votre colis est arrivé au bureau de votre wilaya 📦 "
     "Merci de le récupérer sous 48h, sinon il sera retourné et les frais "
     "de livraison resteront à votre charge."),
]


def seed(db: Database) -> None:
    """Insert defaults only if missing. Never overwrites user choices."""
    for key, value in DEFAULT_SETTINGS.items():
        db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (key, value))

    if db.scalar("SELECT COUNT(*) FROM templates") == 0:
        for name, cat, ar, fr in DEFAULT_TEMPLATES:
            db.execute(
                "INSERT INTO templates(name, category, text_ar, text_fr) VALUES(?,?,?,?)",
                (name, cat, ar, fr),
            )
