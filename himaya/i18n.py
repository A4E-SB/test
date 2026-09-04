"""
i18n — French / Arabic translations, RTL helper.

t("key", lang) returns the translated string; missing keys fall back to
French, then to the key itself so the UI never crashes.
"""

from __future__ import annotations

_TR = {
    # ------------------------------------------------------------------ common
    "app_title": {"fr": "Himaya — Protection du vendeur", "ar": "حماية — حماية البائع"},
    "save": {"fr": "Enregistrer", "ar": "حفظ"},
    "cancel": {"fr": "Annuler", "ar": "إلغاء"},
    "delete": {"fr": "Supprimer", "ar": "حذف"},
    "edit": {"fr": "Modifier", "ar": "تعديل"},
    "add": {"fr": "Ajouter", "ar": "إضافة"},
    "close": {"fr": "Fermer", "ar": "إغلاق"},
    "confirm": {"fr": "Confirmer", "ar": "تأكيد"},
    "yes": {"fr": "Oui", "ar": "نعم"},
    "no": {"fr": "Non", "ar": "لا"},
    "copy": {"fr": "Copier", "ar": "نسخ"},
    "copied": {"fr": "Copié dans le presse-papier ✓", "ar": "تم النسخ ✓"},
    "all": {"fr": "Tous", "ar": "الكل"},
    "search": {"fr": "Rechercher…", "ar": "بحث…"},
    "date": {"fr": "Date", "ar": "التاريخ"},
    "actions": {"fr": "Actions", "ar": "إجراءات"},
    "total": {"fr": "Total", "ar": "المجموع"},
    "notes": {"fr": "Notes", "ar": "ملاحظات"},
    "warning": {"fr": "Attention", "ar": "تنبيه"},
    "error": {"fr": "Erreur", "ar": "خطأ"},
    "success": {"fr": "Succès", "ar": "نجاح"},
    "refresh": {"fr": "Actualiser", "ar": "تحديث"},
    "name": {"fr": "Nom", "ar": "الاسم"},
    "phone": {"fr": "Téléphone", "ar": "رقم الهاتف"},
    "wilaya": {"fr": "Wilaya", "ar": "الولاية"},
    "address": {"fr": "Adresse", "ar": "العنوان"},
    "price": {"fr": "Prix (DA)", "ar": "السعر (دج)"},
    "product": {"fr": "Produit", "ar": "المنتج"},
    "status": {"fr": "Statut", "ar": "الحالة"},
    "shipping_cost": {"fr": "Frais de livraison (DA)", "ar": "مصاريف التوصيل (دج)"},
    "delivery_method": {"fr": "Société de livraison", "ar": "شركة التوصيل"},
    "amount": {"fr": "Montant", "ar": "المبلغ"},
    "no_results": {"fr": "Aucun résultat", "ar": "لا توجد نتائج"},
    "fill_required": {"fr": "Veuillez remplir les champs obligatoires", "ar": "المرجو ملء الحقول الإجبارية"},
    "invalid_phone": {"fr": "Numéro de téléphone invalide (ex: 0555123456)", "ar": "رقم الهاتف غير صحيح (مثال: 0555123456)"},
    "delete_confirm": {"fr": "Voulez-vous vraiment supprimer ?", "ar": "هل أنت متأكد من الحذف؟"},

    # ------------------------------------------------------------------ nav
    "nav_dashboard": {"fr": "Tableau de bord", "ar": "لوحة التحكم"},
    "nav_customers": {"fr": "Clients", "ar": "الزبائن"},
    "nav_orders": {"fr": "Commandes", "ar": "الطلبيات"},
    "nav_detector": {"fr": "Détecteur de faux reçus", "ar": "كشف الوصولات المزيفة"},
    "nav_time_wasters": {"fr": "Perte de temps", "ar": "مضيعي الوقت"},
    "nav_reports": {"fr": "Rapports financiers", "ar": "التقارير المالية"},
    "nav_transfer": {"fr": "Import / Export", "ar": "استيراد / تصدير"},
    "nav_labels": {"fr": "Étiquettes", "ar": "البطاقات"},
    "nav_settings": {"fr": "Paramètres", "ar": "الإعدادات"},

    # ------------------------------------------------------------------ statuses
    "st_pending": {"fr": "En attente", "ar": "في الانتظار"},
    "st_confirmed": {"fr": "Confirmée", "ar": "مؤكدة"},
    "st_shipped": {"fr": "Expédiée", "ar": "مُرسلة"},
    "st_delivered": {"fr": "Livrée", "ar": "تم التوصيل"},
    "st_paid": {"fr": "Payée", "ar": "مدفوعة"},
    "st_ghosted": {"fr": "Fantôme", "ar": "وهمية"},
    "st_refused": {"fr": "Refusée", "ar": "مرفوضة"},
    "st_phone_off": {"fr": "Téléphone éteint", "ar": "الهاتف مغلق"},
    "st_fake_payment": {"fr": "Faux paiement", "ar": "دفع مزيف"},
    "st_canceled": {"fr": "Annulée", "ar": "ملغاة"},
    "st_blocked": {"fr": "Bloquée", "ar": "محجوبة"},

    # ------------------------------------------------------------------ tags
    "tag_trusted": {"fr": "Fiable", "ar": "موثوق"},
    "tag_new": {"fr": "Nouveau", "ar": "جديد"},
    "tag_ghost": {"fr": "Fantôme", "ar": "شبح"},
    "tag_scammer": {"fr": "Escroc", "ar": "نصاب"},
    "tag_time_waster": {"fr": "Perditeur de temps", "ar": "مضيع وقت"},

    # ------------------------------------------------------------------ dashboard
    "dash_today_new": {"fr": "Nouvelles commandes (aujourd'hui)", "ar": "طلبيات جديدة (اليوم)"},
    "dash_today_shipped": {"fr": "Expéditions (aujourd'hui)", "ar": "إرساليات (اليوم)"},
    "dash_today_ghosts": {"fr": "Commandes fantômes (aujourd'hui)", "ar": "طلبيات وهمية (اليوم)"},
    "dash_money_saved": {"fr": "Argent économisé (bloqué)", "ar": "المال الموفَّر (محجوب)"},
    "dash_completion": {"fr": "Taux de complétion", "ar": "نسبة الإتمام"},
    "dash_total_lost": {"fr": "Total perdu (arnaques)", "ar": "مجموع الخسائر (النصب)"},
    "dash_chart_title": {"fr": "Revenus vs Pertes (6 mois)", "ar": "الإيرادات مقابل الخسائر (6 أشهر)"},
    "dash_chart_revenue": {"fr": "Revenus", "ar": "الإيرادات"},
    "dash_chart_losses": {"fr": "Pertes", "ar": "الخسائر"},
    "dash_recent": {"fr": "Dernières commandes", "ar": "آخر الطلبيات"},
    "dash_alerts": {"fr": "Alertes", "ar": "تنبيهات"},
    "dash_no_alerts": {"fr": "Aucune alerte — tout va bien ✓", "ar": "لا توجد تنبيهات — كل شيء على ما يرام ✓"},
    "dash_customers": {"fr": "Clients", "ar": "الزبائن"},
    "dash_blacklist_size": {"fr": "Numéros en liste noire", "ar": "أرقام في القائمة السوداء"},

    # ------------------------------------------------------------------ scam alert
    "scam_alert": {"fr": "🚨 ALERTE ARNAQUE", "ar": "🚨 تحذير نصب"},
    "scam_danger_body": {"fr": "Ce numéro est DANGEREUX !", "ar": "هذا الرقم خطير!"},
    "scam_caution_body": {"fr": "Ce numéro présente des signes de risque.", "ar": "هذا الرقم يحمل علامات خطر."},
    "scam_proceed": {"fr": "Continuer quand même", "ar": "المتابعة رغم ذلك"},
    "scam_block_order": {"fr": "Bloquer (recommandé)", "ar": "حجب الطلب (موصى به)"},
    "scam_lost_with_him": {"fr": "Argent déjà perdu avec ce numéro", "ar": "مال ضائع سابقا مع هذا الرقم"},
    "scam_fake_count": {"fr": "Faux reçus détectés", "ar": "وصولات مزيفة مكتشفة"},
    "scam_blacklisted_by": {"fr": "Raison de la liste noire", "ar": "سبب القائمة السوداء"},

    # ------------------------------------------------------------------ reasons
    "reason_blacklisted": {"fr": "Numéro en liste noire", "ar": "الرقم في القائمة السوداء"},
    "reason_blacklisted_sev3": {"fr": "Escroc confirmé (liste noire)", "ar": "نصاب مؤكد (قائمة سوداء)"},
    "reason_fake_screenshot_history": {"fr": "A déjà envoyé un faux reçu", "ar": "أرسل سابقا وصل مزيف"},
    "reason_tag_scammer": {"fr": "Étiqueté : escroc", "ar": "مصنف: نصاب"},
    "reason_tag_ghost": {"fr": "Étiqueté : fantôme", "ar": "مصنف: شبح"},
    "reason_tag_time_waster": {"fr": "Étiqueté : perditeur de temps", "ar": "مصنف: مضيع وقت"},
    "reason_repeat_ghost": {"fr": "Plusieurs commandes fantômes", "ar": "عدة طلبيات وهمية"},
    "reason_money_lost_before": {"fr": "De l'argent a déjà été perdu", "ar": "سبب فقدان مال سابقا"},

    # ------------------------------------------------------------------ customers
    "cust_title": {"fr": "Base de clients", "ar": "قاعدة الزبائن"},
    "cust_add": {"fr": "+ Nouveau client", "ar": "+ زبون جديد"},
    "cust_order_history": {"fr": "Historique des commandes", "ar": "سجل الطلبيات"},
    "cust_trust": {"fr": "Score de confiance", "ar": "نقطة الثقة"},
    "cust_tags": {"fr": "Étiquettes", "ar": "التصنيفات"},
    "cust_blacklist_btn": {"fr": "Mettre en liste noire", "ar": "إضافة للقائمة السوداء"},
    "cust_blacklist_prompt": {"fr": "Raison (optionnel)", "ar": "السبب (اختياري)"},
    "cust_added": {"fr": "Client ajouté ✓", "ar": "تمت إضافة الزبون ✓"},
    "cust_updated": {"fr": "Client modifié ✓", "ar": "تم تعديل الزبون ✓"},
    "cust_deleted": {"fr": "Client supprimé", "ar": "تم حذف الزبون"},
    "cust_phone_exists": {"fr": "Ce numéro existe déjà : {name}", "ar": "هذا الرقم موجود مسبقا: {name}"},
    "cust_filter_tag": {"fr": "Filtrer par étiquette", "ar": "تصفية حسب التصنيف"},
    "cust_lost_money": {"fr": "Argent perdu avec ce client", "ar": "الخسارة مع هذا الزبون"},

    # ------------------------------------------------------------------ orders
    "ord_title": {"fr": "Gestion des commandes", "ar": "إدارة الطلبيات"},
    "ord_new": {"fr": "+ Nouvelle commande", "ar": "+ طلبية جديدة"},
    "ord_customer": {"fr": "Client", "ar": "الزبون"},
    "ord_pick_customer": {"fr": "— Choisir un client —", "ar": "— اختر زبونا —"},
    "ord_new_customer": {"fr": "Nouveau client", "ar": "زبون جديد"},
    "ord_existing": {"fr": "Client existant", "ar": "زبون موجود"},
    "ord_filter_status": {"fr": "Statut", "ar": "الحالة"},
    "ord_filter_wilaya": {"fr": "Wilaya", "ar": "الولاية"},
    "ord_from": {"fr": "Du", "ar": "من"},
    "ord_to": {"fr": "Au", "ar": "إلى"},
    "ord_saved": {"fr": "Commande enregistrée ✓", "ar": "تم تسجيل الطلبية ✓"},
    "ord_deleted": {"fr": "Commande supprimée", "ar": "تم حذف الطلبية"},
    "ord_status_changed": {"fr": "Statut mis à jour ✓", "ar": "تم تحديث الحالة ✓"},
    "ord_blocked_saved": {"fr": "Commande bloquée — frais économisés ✓", "ar": "تم حجب الطلبية — وفّرت المصاريف ✓"},
    "ord_check_phone": {"fr": "Vérifier ce numéro", "ar": "تحقق من الرقم"},
    "ord_new_orders_count": {"fr": "{n} commande(s)", "ar": "{n} طلبية"},

    # ------------------------------------------------------------------ detector
    "det_title": {"fr": "Détecteur de faux reçus BaridiMob", "ar": "كاشف الوصولات المزيفة BaridiMob"},
    "det_desc": {"fr": "Analyse locale (OCR + IA) : glissez une capture d'écran de paiement ici, ou cliquez pour choisir un fichier. Rien n'est envoyé sur internet.",
                 "ar": "تحليل محلي (OCR + ذكاء اصطناعي): أدرج صورة وصل الدفع هنا أو اضغط لاختيار ملف. لا شيء يُرسل عبر الإنترنت."},
    "det_drop": {"fr": "📄 Glissez la capture ici / cliquez pour parcourir", "ar": "📄 أدرج الصورة هنا / اضغط للاختيار"},
    "det_analyze": {"fr": "Analyser", "ar": "تحليل"},
    "det_analyzing": {"fr": "Analyse en cours…", "ar": "جارٍ التحليل…"},
    "det_real": {"fr": "✅ REÇU PROBABLEMENT AUTHENTIQUE", "ar": "✅ الوصل يبدو حقيقيا"},
    "det_fake": {"fr": "🚨 FAUX REÇU DÉTECTÉ", "ar": "🚨 وصل مزيف"},
    "det_suspicious": {"fr": "⚠️ SUSPECT — vérifiez manuellement", "ar": "⚠️ مشبوه — تحقق يدويا"},
    "det_confidence": {"fr": "Indice de confiance", "ar": "مؤشر الثقة"},
    "det_reasons": {"fr": "Raisons", "ar": "الأسباب"},
    "det_extracted": {"fr": "Données extraites (OCR)", "ar": "المعطيات المستخرجة (OCR)"},
    "det_ref": {"fr": "Référence transaction", "ar": "مرجع العملية"},
    "det_save_evidence": {"fr": "Enregistrer comme preuve", "ar": "حفظ كدليل"},
    "det_evidence_saved": {"fr": "Preuve enregistrée ✓ (hash ajouté à la base)", "ar": "تم حفظ الدليل ✓ (أُضيف البصمة للقاعدة)"},
    "det_blacklist_from_result": {"fr": "Blacklister ce numéro", "ar": "أضف الرقم للقائمة السوداء"},
    "det_no_image": {"fr": "Choisissez d'abord une image", "ar": "اختر صورة أولا"},
    "det_ocr_date": {"fr": "Date du reçu", "ar": "تاريخ الوصل"},
    "det_hash": {"fr": "Empreinte (hash)", "ar": "البصمة (hash)"},

    # detector reason codes
    "r_known_fake_match": {"fr": "Image identique à un faux reçu déjà enregistré", "ar": "الصورة مطابقة لوصل مزيف محفوظ سابقا"},
    "r_known_fake_near_match": {"fr": "Image très similaire à un faux reçu connu ({d} correspondances)", "ar": "الصورة مشابهة جدا لوصل مزيف معروف ({d})"},
    "r_editor_signature": {"fr": "Trace d'application de retouche : {d}", "ar": "أثر تطبيق تعديل الصور: {d}"},
    "r_png_missing_screenshot_chunks": {"fr": "PNG sans les marqueurs d'une capture d'écran", "ar": "صورة PNG بدون علامات لقطة شاشة"},
    "r_date_in_future": {"fr": "Date du reçu dans le futur", "ar": "تاريخ الوصل في المستقبل"},
    "r_date_invalid_format": {"fr": "Date illisible / invalide", "ar": "التاريخ غير مقروء أو غير صالح"},
    "r_date_too_old": {"fr": "Date trop ancienne (> 1 an)", "ar": "تاريخ قديم جدا (أكثر من سنة)"},
    "r_date_not_found": {"fr": "Aucune date détectée", "ar": "لم يُكتشف أي تاريخ"},
    "r_ref_not_found": {"fr": "Aucune référence de transaction détectée", "ar": "لم يُكتشف مرجع العملية"},
    "r_amount_not_found": {"fr": "Aucun montant détecté", "ar": "لم يُكتشف المبلغ"},
    "r_amount_implausible": {"fr": "Montant irréaliste", "ar": "المبلغ غير منطقي"},
    "r_font_inconsistency": {"fr": "Incohérence de police (texte collé détecté)", "ar": "عدم تناسق الخط (نص ملصوق)"},
    "r_ela_localized_edit": {"fr": "Analyse ELA : zone localement modifiée", "ar": "تحليل ELA: منطقة معدلة محليا"},
    "r_ocr_unavailable": {"fr": "OCR indisponible (installez Tesseract pour plus de précision)", "ar": "خدمة OCR غير متوفرة (ثبّت Tesseract لدقة أكبر)"},
    "r_pixel_checks_skipped": {"fr": "Analyse pixel ignorée (OpenCV absent)", "ar": "تخطي تحليل البكسل (OpenCV غير مثبت)"},
    "r_tflite_model": {"fr": "Classificateur IA local : {d}", "ar": "مصنّف الذكاء الاصطناعي المحلي: {d}"},
    "r_unreadable_image": {"fr": "Image illisible / corrompue", "ar": "الصورة غير مقروءة أو تالفة"},

    # ------------------------------------------------------------------ time wasters
    "tw_title": {"fr": "Suivi des perditeurs de temps", "ar": "تتبع مضيعي الوقت"},
    "tw_desc": {"fr": "Enregistrez chaque contact qui ne convertit pas. Himaya calcule le taux de conversion et vous dit quand demander un acompte.",
                "ar": "سجّل كل تواصل لا يتحول لبيع. حماية تحسب نسبة التحويل وتخبرك متى تطلب تسبيقا."},
    "tw_log": {"fr": "Journaliser un contact", "ar": "تسجيل تواصل"},
    "tw_platform": {"fr": "Plateforme", "ar": "المنصة"},
    "tw_converted": {"fr": "A converti (vente)", "ar": "تحوّل لبيع"},
    "tw_saved": {"fr": "Contact journalisé ✓", "ar": "تم تسجيل التواصل ✓"},
    "tw_contacts": {"fr": "Contacts", "ar": "التواصلات"},
    "tw_conversion": {"fr": "Taux de conversion global", "ar": "نسبة التحويل العامة"},
    "tw_suggest_deposit": {"fr": "💡 Demandez un acompte à {name} — {n} contacts sans achat.", "ar": "💡 اطلب تسبيقا من {name} — {n} تواصل بدون شراء."},
    "tw_no_suggest": {"fr": "Aucune suggestion pour le moment.", "ar": "لا توجد اقتراحات حاليا."},
    "tw_templates": {"fr": "Réponses intelligentes", "ar": "الردود الذكية"},
    "tw_copy_hint": {"fr": "Collez dans Messenger / WhatsApp Web", "ar": "الصق في ماسنجر / واتساب ويب"},
    "tw_cat_deposit": {"fr": "Acompte", "ar": "تسبيق"},
    "tw_cat_negotiation": {"fr": "Négociation", "ar": "تفاوض"},
    "tw_cat_ghost": {"fr": "Fantôme", "ar": "شبح"},
    "tw_cat_warning": {"fr": "Avertissement", "ar": "تحذير"},
    "tw_cat_general": {"fr": "Général", "ar": "عام"},
    "tw_recent": {"fr": "Derniers contacts", "ar": "آخر التواصلات"},

    # ------------------------------------------------------------------ reports
    "rep_title": {"fr": "Rapports financiers", "ar": "التقارير المالية"},
    "rep_month": {"fr": "Mois", "ar": "الشهر"},
    "rep_year": {"fr": "Année", "ar": "السنة"},
    "rep_week": {"fr": "Cette semaine", "ar": "هذا الأسبوع"},
    "rep_month_btn": {"fr": "Ce mois", "ar": "هذا الشهر"},
    "rep_year_btn": {"fr": "Cette année", "ar": "هذه السنة"},
    "rep_revenue": {"fr": "Revenus (payées)", "ar": "الإيرادات (مدفوعة)"},
    "rep_pending_rev": {"fr": "En cours (à encaisser)", "ar": "قيد التحصيل"},
    "rep_costs": {"fr": "Frais de livraison payés", "ar": "مصاريف التوصيل المدفوعة"},
    "rep_profit": {"fr": "Profit net", "ar": "الربح الصافي"},
    "rep_losses": {"fr": "Pertes totales", "ar": "مجموع الخسائر"},
    "rep_saved": {"fr": "Argent économisé (blocages)", "ar": "المال الموفَّر (الحجب)"},
    "rep_completion": {"fr": "Taux de complétion", "ar": "نسبة الإتمام"},
    "rep_orders": {"fr": "Commandes", "ar": "الطلبيات"},
    "rep_breakdown": {"fr": "Détail des pertes", "ar": "تفصيل الخسائر"},
    "rep_export_csv": {"fr": "Exporter CSV", "ar": "تصدير CSV"},
    "rep_export_xlsx": {"fr": "Exporter Excel", "ar": "تصدير Excel"},
    "rep_exported": {"fr": "Exporté : {path}", "ar": "تم التصدير: {path}"},

    # ------------------------------------------------------------------ transfer
    "tr_title": {"fr": "Import / Export (partage USB)", "ar": "استيراد / تصدير (مشاركة USB)"},
    "tr_hma_desc": {"fr": "Le fichier .hma est la liste noire officielle Himaya. Copiez-la sur clé USB et partagez-la avec d'autres vendeurs — 100% hors ligne.",
                    "ar": "ملف .hma هو القائمة السوداء الرسمية لحماية. انسخه على فلاشة USB وشاركه مع باعة آخرين — دون إنترنت."},
    "tr_export_hma": {"fr": "Exporter liste noire (.hma)", "ar": "تصدير القائمة السوداء (.hma)"},
    "tr_import_hma": {"fr": "Importer un fichier .hma", "ar": "استيراد ملف .hma"},
    "tr_hma_exported": {"fr": "{n} numéro(s) exportés vers {path}", "ar": "تم تصدير {n} رقم إلى {path}"},
    "tr_hma_imported": {"fr": "Importés : {imported} • déjà connus : {skipped} • invalides : {invalid}", "ar": "مستوردة: {imported} • معروفة: {skipped} • غير صالحة: {invalid}"},
    "tr_not_hma": {"fr": "Ce fichier n'est pas un fichier .hma valide", "ar": "هذا الملف ليس ملف .hma صالحا"},
    "tr_orders_export": {"fr": "Exporter les commandes", "ar": "تصدير الطلبيات"},
    "tr_orders_import": {"fr": "Importer des commandes (CSV)", "ar": "استيراد الطلبيات (CSV)"},
    "tr_orders_imported": {"fr": "{orders} commande(s) importée(s), {customers} nouveau(x) client(s)", "ar": "تم استيراد {orders} طلبية و {customers} زبون جديد"},

    # ------------------------------------------------------------------ labels
    "lb_title": {"fr": "Étiquettes de livraison", "ar": "بطاقات التوصيل"},
    "lb_desc": {"fr": "Générez des étiquettes PDF (A6 ou 100×100) avec le niveau de risque et les avertissements, prêtes pour l'impression.",
                "ar": "أنشئ بطاقات PDF (A6 أو 100×100) مع مستوى الخطر والتحذيرات، جاهزة للطباعة."},
    "lb_generate": {"fr": "Générer le PDF", "ar": "إنشاء PDF"},
    "lb_generated": {"fr": "PDF créé : {path}", "ar": "تم إنشاء PDF: {path}"},
    "lb_open_folder": {"fr": "Ouvrir le dossier", "ar": "فتح المجلد"},
    "lb_selected": {"fr": "{n} commande(s) sélectionnée(s)", "ar": "{n} طلبية محددة"},
    "lb_select_pending": {"fr": "Sélectionner confirmées", "ar": "تحديد المؤكدة"},
    "lb_size": {"fr": "Format", "ar": "المقاس"},

    # ------------------------------------------------------------------ settings
    "set_title": {"fr": "Paramètres", "ar": "الإعدادات"},
    "set_language": {"fr": "Langue / اللغة", "ar": "اللغة / Langue"},
    "set_lang_restart": {"fr": "La langue sera appliquée. Certains écrans se rechargeront.", "ar": "سيتم تطبيق اللغة. ستُعاد بعض الشاشات."},
    "set_general": {"fr": "Général", "ar": "عام"},
    "set_ccp_title": {"fr": "Compte CCP / BaridiMob (pour les acomptes)", "ar": "حساب CCP / BaridiMob (للتسبيقات)"},
    "set_ccp_number": {"fr": "Numéro CCP", "ar": "رقم CCP"},
    "set_ccp_name": {"fr": "Nom du compte", "ar": "اسم صاحب الحساب"},
    "set_rip": {"fr": "RIP BaridiMob", "ar": "RIP BaridiMob"},
    "set_bm_phone": {"fr": "Téléphone BaridiMob", "ar": "هاتف BaridiMob"},
    "set_default_delivery": {"fr": "Société de livraison par défaut", "ar": "شركة التوصيل الافتراضية"},
    "set_default_shipping": {"fr": "Frais de livraison par défaut (DA)", "ar": "مصاريف التوصيل الافتراضية (دج)"},
    "set_tesseract": {"fr": "Chemin de Tesseract (vide = OCR intégré / PATH)", "ar": "مسار Tesseract (فارغ = OCR المدمج)"},
    "set_label_size": {"fr": "Format d'étiquette", "ar": "مقاس البطاقة"},
    "set_data": {"fr": "Données & sauvegarde", "ar": "البيانات والنسخ الاحتياطي"},
    "set_backup_now": {"fr": "Sauvegarder maintenant", "ar": "نسخ احتياطي الآن"},
    "set_backup_done": {"fr": "Sauvegarde créée : {path}", "ar": "تم إنشاء النسخة: {path}"},
    "set_restore": {"fr": "Restaurer une sauvegarde…", "ar": "استعادة نسخة احتياطية…"},
    "set_restore_confirm": {"fr": "Restaurer cette sauvegarde ? L'application doit redémarrer.", "ar": "استعادة هذه النسخة؟ يجب إعادة تشغيل التطبيق."},
    "set_restored": {"fr": "Base restaurée. Redémarrez Himaya.", "ar": "تمت استعادة القاعدة. أعد تشغيل حماية."},
    "set_db_path": {"fr": "Base de données", "ar": "قاعدة البيانات"},
    "set_wilayas": {"fr": "58 wilayas intégrées ✓", "ar": "58 ولاية مدمجة ✓"},
    "set_saved": {"fr": "Paramètres enregistrés ✓", "ar": "تم حفظ الإعدادات ✓"},
    "set_a6": {"fr": "A6 (105×148 mm)", "ar": "A6 (105×148 مم)"},
    "set_square": {"fr": "Carré (100×100 mm)", "ar": "مربع (100×100 مم)"},
}

_MONTHS = {
    "fr": ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"],
    "ar": ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
           "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}


def t(key: str, lang: str = "fr", **kwargs) -> str:
    """Translate a key ('fr' default). Supports {placeholders}."""
    entry = _TR.get(key)
    if entry is None:
        return key
    s = entry.get(lang) or entry.get("fr") or key
    if kwargs:
        try:
            s = s.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return s


def month_name(month: int, lang: str = "fr") -> str:
    return _MONTHS.get(lang, _MONTHS["fr"])[month - 1]


def is_rtl(lang: str) -> bool:
    return lang == "ar"


def status_key(status: str) -> str:
    return f"st_{status}"


def tag_key(tag: str) -> str:
    return f"tag_{tag}"
