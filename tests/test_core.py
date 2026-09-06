"""
Headless test suite for Himaya's logic layer (no GUI needed).

Run:  python -m pytest tests/test_core.py -v
  or: python tests/test_core.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from himaya import i18n
from himaya.database import Database, seed
from himaya.models import (blacklist, customers, inquiries, orders,
                           settings_store, templates_store)
from himaya.services import backup, detector, hma, labels, phone, reports, trust

PASS = 0
FAIL = 0
FAILURES = []
_DB_N = [0]


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        FAILURES.append(f"{name} {extra}")
        print(f"  ✗ {name} {extra}")


def make_db(tmp: Path) -> Database:
    """A fresh, uniquely-named database per call (tests stay independent)."""
    _DB_N[0] += 1
    sub = tmp / f"db_{_DB_N[0]}"
    sub.mkdir(parents=True, exist_ok=True)
    db = Database(sub / "himaya.db")
    seed(db)
    return db


# ---------------------------------------------------------------------------

def test_phone_normalization(tmp: Path) -> None:
    print("[phone] normalization")
    check("local 0555…", phone.normalize_phone("0555123456") == "0555123456")
    check("with spaces", phone.normalize_phone("05 55 12 34 56") == "0555123456")
    check("+213 form", phone.normalize_phone("+213661234567") == "0661234567")
    check("00213 form", phone.normalize_phone("00213770011223") == "0770011223")
    check("dashes", phone.normalize_phone("06-61-23-45-67") == "0661234567")
    check("garbage -> None", phone.normalize_phone("abc") is None)
    check("too short -> None", phone.normalize_phone("0555") is None)


def test_customers_and_trust(tmp: Path) -> None:
    print("[customers + trust]")
    db = make_db(tmp)
    cid = customers.create(db, "Amine", "0555111222", wilaya="Alger")
    check("created", cid == 1)
    dup = customers.find_by_phone(db, "05 55 111 222")
    check("found despite formatting", dup is not None and dup["id"] == cid)

    trust.refresh(db, cid)
    c = customers.get(db, cid)
    check("new customer score 50, tag new",
          c["trust_score"] == 50 and c["tags"] == "new")

    # 3 delivered + paid orders -> trusted
    for i in range(3):
        oid = orders.create(db, cid, f"Prod{i}", 2000, shipping_cost=600,
                            wilaya="Alger")
        orders.set_status(db, oid, "delivered")
    oid4 = orders.create(db, cid, "Prod3", 2500, shipping_cost=600)
    orders.set_status(db, oid4, "paid")
    score, tags = trust.refresh(db, cid)
    check("trusted after 4 good orders", score >= 80 and "trusted" in tags,
          f"score={score} tags={tags}")

    # ghost twice -> ghost tag + score drops
    other = customers.create(db, "Karim", "0661999888")
    for i in range(2):
        oid = orders.create(db, other, "X", 1000, shipping_cost=500)
        orders.set_status(db, oid, "ghosted")
    score2, tags2 = trust.refresh(db, other)
    check("ghost tag", "ghost" in tags2, f"tags={tags2}")
    check("ghost score low", score2 < 50, f"score={score2}")

    # fake payment -> scammer pinned at 10
    scammer = customers.create(db, "Nasba", "0770000111")
    oid = orders.create(db, scammer, "Y", 9000, shipping_cost=700)
    orders.set_status(db, oid, "fake_payment")
    score3, tags3 = trust.refresh(db, scammer)
    check("scammer tag", "scammer" in tags3)
    check("scammer pinned <=10", score3 <= 10, f"score={score3}")


def test_phone_risk(tmp: Path) -> None:
    print("[phone risk]")
    db = make_db(tmp)
    blacklist.add(db, "0555123456", reason="faux reçu", severity=3)
    r = phone.phone_risk(db, "+213 555 123 456")  # formatted differently!
    check("blacklist detected via formatted number",
          r["level"] == phone.DANGER and r["blacklisted"])
    check("reason includes severity", any(x.startswith("blacklisted") for x in r["reasons"]))

    # repeat ghost -> caution
    cid = customers.create(db, "Ghost", "0661111000")
    for i in range(2):
        oid = orders.create(db, cid, "G", 1000, shipping_cost=500)
        orders.set_status(db, oid, "ghosted")
    trust.refresh(db, cid)
    r2 = phone.phone_risk(db, "0661111000")
    check("repeat ghost caution/danger", r2["level"] in (phone.CAUTION, phone.DANGER))
    check("lost money computed", r2["lost_money"] == 1000.0)

    r3 = phone.phone_risk(db, "0770123999")
    check("clean number ok", r3["level"] == phone.OK)


def test_orders_and_aggregates(tmp: Path) -> None:
    print("[orders + aggregates]")
    db = make_db(tmp)
    cid = customers.create(db, "Sara", "0555444333", wilaya="Oran")
    o1 = orders.create(db, cid, "Montre", 4500, shipping_cost=600, wilaya="Oran")
    orders.set_status(db, o1, "paid")
    o2 = orders.create(db, cid, "Sac", 3000, shipping_cost=600)
    orders.set_status(db, o2, "ghosted")

    check("list filter by status",
          len(orders.list_orders(db, status="ghosted")) == 1)
    check("list filter by wilaya (o2 has none)",
          len(orders.list_orders(db, wilaya="Oran")) == 1)
    check("search by product", len(orders.list_orders(db, query="Montre")) == 1)

    check("count_today", orders.count_today(db) == 2)
    check("shipped_today maintained", orders.shipped_today(db) == 2)

    total_lost = orders.total_lost(db)
    check("total_lost = ghost shipping", total_lost == 600.0, f"{total_lost}")

    # blocked order -> money saved
    bl = customers.create(db, "Block", "0771222333")
    blacklist.add(db, "0771222333", "test")
    orders.create(db, bl, "Z", 1000, status="blocked", shipping_cost=650)
    check("money_saved counts blocked shipping", orders.money_saved(db) == 650.0)


def test_mutation_counter_and_icons(tmp: Path) -> None:
    """v1.7: data-change signal + the offline stroke-icon set."""
    from himaya.models import customers

    db = make_db(tmp)
    before = db.mutation_count
    db.query("SELECT COUNT(*) FROM customers")           # read: no bump
    check("reads do not bump mutations", db.mutation_count == before)
    customers.create(db, "Mut", "0555443322")             # write: bump
    check("writes bump mutations", db.mutation_count == before + 1)

    from himaya.ui.icons import render, ICONS
    check("15 icons in the set (v1.7.1: +truck/check/ghost)",
          len(ICONS) == 15)
    for n in ICONS:
        im = render(n, "#2FD98A", 20)
        check(f"icon {n} renders 20x20 RGBA",
              im.size == (20, 20) and im.mode == "RGBA")
        # v1.7.1 regression guard: icons once rendered squished into the
        # top-left quarter (unscaled coords on the supersampled canvas).
        # At size 96 the ink bbox must be centered and span the grid.
        big = render(n, "#2FD98A", 96)
        bbox = big.getchannel("A").getbbox()
        ok = bool(bbox)
        if ok:
            x0, y0, x1, y1 = bbox
            cx, cy, span = (x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0)
            ok = 36 <= cx <= 60 and 36 <= cy <= 60 and span >= 55
        check(f"icon {n} centered & full-size (k-scaling)", ok)
    a = render("shield", "#2FD98A").tobytes()
    b = render("shield", "#F2555A").tobytes()
    check("icons are color-parameterized", a != b)


def test_design_tokens() -> None:
    """v1.6 design system: the four semantic tokens, tint math, type map."""
    from himaya import config as C

    check("brand accent is the protection green", C.COLOR_ACCENT == "#2FD98A")
    check("success == accent (one brand color)", C.COLOR_GREEN == C.COLOR_ACCENT)
    check("dark surfaces are the spec tokens",
          (C.COLOR_BG, C.COLOR_BG_2, C.COLOR_BG_3, C.COLOR_BORDER)
          == ("#0A0C12", "#141724", "#1B1F2E", "#232838"))
    semantic = {C.COLOR_GREEN, C.COLOR_RED, C.COLOR_ORANGE, C.COLOR_INFO,
                C.COLOR_FG_DIM}
    bad = {st: c for st, c in C.STATUS_COLORS.items() if c not in semantic}
    check(f"every status maps to a semantic token {bad or ''}", not bad)
    check("paid/delivered are success",
          C.STATUS_COLORS["paid"] == C.STATUS_COLORS["delivered"] == C.COLOR_GREEN)
    check("waiting_deposit is warning",
          C.STATUS_COLORS["waiting_deposit"] == C.COLOR_ORANGE)
    check("ghost/fake/refused are danger",
          C.STATUS_COLORS["ghosted"] == C.STATUS_COLORS["fake_payment"]
          == C.STATUS_COLORS["refused"] == C.COLOR_RED)
    # tint: ~13% of the color over the surface, hex-form, never solid
    t = C.tint(C.COLOR_ACCENT)
    check("tint returns hex", t.startswith("#") and len(t) == 7)
    r, g, b = (int(t[i:i + 2], 16) for i in (1, 3, 5))
    base = (0x14, 0x17, 0x24)
    check("tint is between surface and color",
          base[0] < r <= 0x2F and base[1] < g <= 0xD9 and base[2] < b <= 0x8A)
    check("tint alpha=0 is the base", C.tint(C.COLOR_RED, 0) == "#141724")


def test_period_aware_aggregates(tmp: Path) -> None:
    """v1.5: dashboard figures must respect the selected period."""
    from datetime import date as _d, timedelta as _td
    from himaya.models.orders import (money_saved, total_lost, completion_rate,
                                      paid_revenue, pending_revenue, create)

    db = make_db(tmp)
    cid = customers.create(db, "Period Client", "0770001122", wilaya="Alger")
    old = (_d.today() - _td(days=20)).isoformat()
    create(db, cid, "Ancien bloqué", 1000, status="blocked",
           shipping_cost=700, order_date=old)
    create(db, cid, "Ancien payé", 2000, status="paid",
           order_date=old)
    create(db, cid, "Bloqué récent", 1000, status="blocked", shipping_cost=500)
    create(db, cid, "Payé récent", 3000, status="paid")
    create(db, cid, "En cours", 1500, status="confirmed")

    check("saved all-time", money_saved(db) == 1200)
    check("saved 7d window", money_saved(db, days=7) == 500)
    check("lost all-time == lost 7d (no losses yet)",
          total_lost(db) == total_lost(db, days=7) == 0)
    create(db, cid, "Fantôme", 900, status="ghosted", shipping_cost=600)
    check("lost 7d sees fresh ghost", total_lost(db, days=7) == 600)
    check("today window sees the fresh ghost", total_lost(db, days=0) == 600)
    check("revenue all-time", paid_revenue(db) == 5000)
    check("revenue 7d", paid_revenue(db, days=7) == 3000)
    check("pending 7d", pending_revenue(db, days=7) == 1500)
    # at this point: 6 orders all-time (2 paid), 4 in the last 7d (1 paid)
    check("completion all-time (2/6)",
          abs(completion_rate(db) - 33.3333) < 0.001)
    check("completion 7d (1/4)",
          abs(completion_rate(db, days=7) - 25.0) < 0.001)


def test_order_date_and_companies(tmp: Path) -> None:
    """v1.4: custom order date + custom delivery companies."""
    from datetime import date as _date
    from himaya.models.orders import parse_date_text, create, update, get
    from himaya.models import customers, settings_store

    db = make_db(tmp)
    cid = customers.create(db, "Dated Client", "0669998877", wilaya="Alger")

    # -- date parsing: ISO, day-first, both separators, empty, invalid
    check("parse ISO", parse_date_text("2026-09-12") == "2026-09-12")
    check("parse DD/MM/YYYY", parse_date_text("12/09/2026") == "2026-09-12")
    check("parse DD-MM-YYYY", parse_date_text("12-09-2026") == "2026-09-12")
    check("parse YYYY/MM/DD", parse_date_text("2026/09/12") == "2026-09-12")
    check("parse empty -> ''", parse_date_text("   ") == "")
    check("parse 31/02 invalid", parse_date_text("31/02/2026") is None)
    check("parse garbage invalid", parse_date_text("soon") is None)
    check("parse partial invalid", parse_date_text("12/09") is None)

    # -- order date stored / updated / defaulted
    oid = create(db, cid, "Produit daté", 1000, order_date="15/01/2026",
                 delivery_method="SpeedEx")
    check("custom date stored (ISO)",
          get(db, oid)["date"] == "2026-01-15")
    update(db, oid, date="2026-02-20")
    check("date updated", get(db, oid)["date"] == "2026-02-20")
    oid2 = create(db, cid, "Autre", 500, order_date="")
    check("empty date -> today",
          get(db, oid2)["date"] == _date.today().isoformat())

    # -- delivery companies: preset + custom saved + used-on-order
    base = settings_store.delivery_companies(db)
    check("presets listed", "Yalidine" in base and "Autre" in base)
    check("company used on order listed", "SpeedEx" in base)
    lst = settings_store.add_delivery_company(db, "SpeedEx")   # already known
    check("no duplicate company", lst.count("SpeedEx") == 1)
    lst = settings_store.add_delivery_company(db, "Kazi Tour")
    check("custom company added", "Kazi Tour" in lst)
    check("custom company persisted (settings)",
          "Kazi Tour" in settings_store.delivery_companies(
              Database(db.path)))     # reopen the same file
    check("add empty ignored",
          settings_store.add_delivery_company(db, "  ") == lst)


def test_reports(tmp: Path) -> None:
    print("[reports]")
    db = make_db(tmp)
    cid = customers.create(db, "Ali", "0555777888")
    o1 = orders.create(db, cid, "A", 10000, shipping_cost=600, wilaya="Alger")
    orders.set_status(db, o1, "paid")
    o2 = orders.create(db, cid, "B", 5000, shipping_cost=500)
    orders.set_status(db, o2, "refused")
    o3 = orders.create(db, cid, "C", 7000, shipping_cost=400)
    orders.set_status(db, o3, "fake_payment")

    now = date.today()
    s = reports.monthly_summary(db, now.year, now.month)
    check("revenue", s["revenue"] == 10000.0)
    check("costs", s["costs"] == 600.0)
    check("profit", s["profit"] == 9400.0)
    check("lost shipping (refused)", s["lost_shipping"] == 500.0)
    check("fake loss (price+ship)", s["fake_loss"] == 7400.0)
    check("losses total", s["losses"] == 7900.0)
    check("completion 33%", abs(s["completion"] - 100 / 3) < 0.1)

    series = reports.revenue_series(db, 6)
    check("series 6 months", len(series) == 6)
    check("series current has data", series[-1]["revenue"] == 10000.0)

    bd = reports.loss_breakdown(db)
    check("breakdown fake", bd["fake_payment"]["amount"] == 7400.0)
    check("breakdown total", bd["total"]["amount"] == 7900.0)


def test_inquiries(tmp: Path) -> None:
    print("[inquiries / time-wasters]")
    db = make_db(tmp)
    cid = customers.create(db, "Hicham", "0555333222")
    for i in range(6):
        inquiries.log(db, cid, platform="Messenger", converted=False)
    inquiries.log(db, cid, platform="WhatsApp", converted=True)
    st = inquiries.stats_for_customer(db, cid)
    check("contacts", st["contacts"] == 7)
    check("conversion ~14%", abs(st["conversion_rate"] - 100 / 7) < 0.1)
    score, tags = trust.refresh(db, cid)
    check("time_waster tag", "time_waster" in tags, f"tags={tags}")


def test_blacklist_and_hma(tmp: Path) -> None:
    print("[blacklist .hma roundtrip]")
    db = make_db(tmp)
    blacklist.add(db, "0555999888", "faux reçu BaridiMob", severity=3)
    blacklist.add(db, "0661777666", "3 refus de livraison", severity=2)

    out = tmp / "share.hma"
    res = hma.export_blacklist(db, out)
    check("exported 2", res["count"] == 2)
    doc = json.loads(out.read_text())
    check("magic header", doc["magic"] == "HIMAYA-BLACKLIST")

    # import into a fresh database
    db2 = make_db(tmp)
    res2 = hma.import_blacklist(db2, out)
    check("imported 2", res2["imported"] == 2)
    check("blacklist works in db2",
          blacklist.is_blacklisted(db2, "0555999888") is not None)
    # re-import -> skipped
    res3 = hma.import_blacklist(db2, out)
    check("re-import skipped", res3["imported"] == 0 and res3["skipped"] == 2)

    try:
        hma.import_blacklist(db2, tmp / "definitely_missing.hma")
        bad_json = tmp / "bad.hma"
        bad_json.write_text("{}")
        hma.import_blacklist(db2, bad_json)
        check("invalid .hma rejected", False)
    except (FileNotFoundError, ValueError):
        check("invalid .hma rejected", True)


def test_orders_csv_roundtrip(tmp: Path) -> None:
    print("[orders CSV/Excel roundtrip]")
    db = make_db(tmp)
    cid = customers.create(db, "Yacine", "0555222111", wilaya="Sétif")
    orders.create(db, cid, "Écouteurs", 3500, status="paid",
                  delivery_method="Yalidine", wilaya="Sétif", shipping_cost=600)
    csvp = tmp / "orders.csv"
    n = hma.export_orders_csv(db, csvp)
    check("csv export 1", n == 1)
    xl = tmp / "orders.xlsx"
    n2 = hma.export_orders_excel(db, xl)
    check("xlsx export 1", n2 == 1 and xl.exists())

    db2 = make_db(tmp)
    res = hma.import_orders_csv(db2, csvp)
    check("csv import", res["orders"] == 1 and res["customers"] == 1)
    imported = orders.list_orders(db2)
    check("imported row ok",
          imported and imported[0]["product"] == "Écouteurs"
          and imported[0]["status"] == "paid")


def test_arabic_shaping() -> None:
    print("[labels] Arabic shaping (PDF was backwards in v1.0.3)")
    from himaya.services.labels import _ar, _RISK_NOTES, _RISK_TEXT
    raw = "حماية"
    shaped = _ar(raw)
    check("shaper installed & changes text", shaped != raw or len(raw) == 0,
          "arabic-reshaper/python-bidi missing?")
    # presentation forms (U+FB50–U+FEFF) prove visual shaping happened
    check("shaped text uses presentation forms",
          any(0xFB50 <= ord(ch) <= 0xFEFF for ch in shaped))
    check("Latin text untouched by shaper", _ar("HIMAYA 123") == "HIMAYA 123")
    check("risk notes exist in fr+ar",
          all(set(v) >= {"fr", "ar"} and (v["fr"] and v["ar"] or k == "normal")
              for k, v in _RISK_NOTES.items()))
    check("risk text exists in fr+ar",
          all(set(v) >= {"fr", "ar"} for v in _RISK_TEXT.values()))


def test_labels(tmp: Path) -> None:
    print("[PDF labels]")
    db = make_db(tmp)
    cid = customers.create(db, "Walid", "0661555444", wilaya="Blida",
                           address="Cité 200 logements, Bt B")
    o1 = orders.create(db, cid, "Parfum", 6500, shipping_cost=600, wilaya="Blida")
    o2 = orders.create(db, cid, "Crème", 2500, shipping_cost=600)
    out = tmp / "label.pdf"
    labels.generate_labels(db, [o1, o2], out, lang="fr")
    check("pdf created", out.exists() and out.stat().st_size > 1000)
    data = out.read_bytes()[:200]
    check("looks like pdf", data.startswith(b"%PDF"))
    out2 = tmp / "label_ar.pdf"
    labels.generate_labels(db, [o1], out2, lang="ar")
    check("arabic label ok", out2.exists())


def test_backup(tmp: Path) -> None:
    print("[backup/restore]")
    db = make_db(tmp)
    cid = customers.create(db, "Mehdi", "0770888777")
    del cid
    dest = backup.backup(db, tmp / "back")
    check("backup file exists", Path(dest).exists())
    db.close()
    backup.restore(dest, tmp / "other.db")
    db2 = Database(tmp / "other.db")
    check("restored data intact",
          customers.find_by_phone(db2, "0770888777") is not None)


def test_detector_hashing_and_parsing(tmp: Path) -> None:
    print("[detector] hashing + parsing (no OCR binary needed)")
    from PIL import Image

    # dHash stability
    img = Image.new("RGB", (300, 500), (250, 250, 250))
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.rectangle([40, 60, 260, 110], fill=(30, 30, 30))
    d.text((50, 130), "4500 DA", fill=(0, 0, 0))
    h1 = detector.dhash(img)
    h2 = detector.dhash(img.resize((280, 480)))  # slight rescale
    check("dhash stable under resize", detector.hamming_hex(h1, h2) <= 4,
          f"dist={detector.hamming_hex(h1, h2)}")
    img2 = Image.new("RGB", (300, 500), (10, 90, 200))
    check("dhash differs for other image", detector.hamming_hex(h1, detector.dhash(img2)) > 10)

    # receipt parsing
    ex = detector.parse_receipt("Virement recu\nMontant : 4 500,00 DA\n"
                                "Date : 03/09/2026 14:22\nRéf : 123456789\n"
                                "De : 0555111222")
    check("amount parsed", ex["amount"] == 4500)
    check("date parsed", isinstance(ex["date"], datetime) and ex["date"].year == 2026)
    check("ref parsed", ex["ref"] == "123456789")
    check("phone parsed", ex["phone"] == "0555111222")

    # plausibility: future date -> reason
    future = datetime.now() + timedelta(days=30)
    reasons = detector.check_extracted({"date": future, "ref": "123456789",
                                        "amount": 100})
    check("future date flagged", "date_in_future" in reasons)

    # metadata editor signature
    edited = Image.new("RGB", (10, 10))
    edited.info["Software"] = "PicsArt Studio"
    check("editor signature detected",
          any(r.startswith("editor_signature") for r in detector.check_metadata(edited)))


def test_detector_full_flow(tmp: Path) -> None:
    print("[detector] full flow (OCR mocked)")
    from PIL import Image, ImageDraw

    db = make_db(tmp)

    # mock pytesseract module (binary not available in test env).
    # the detector uses the module-level API: pytesseract.image_to_string()
    import types
    fake = types.ModuleType("pytesseract")
    holder = {"text": ""}

    class _Cfg:  # stands for pytesseract.pytesseract (cmd config object)
        tesseract_cmd = ""

    fake.pytesseract = _Cfg()

    def _image_to_string(image, lang=None):
        return holder["text"]

    fake.image_to_string = _image_to_string
    sys.modules["pytesseract"] = fake

    # 1) "real"-looking receipt (plausible data)
    holder["text"] = ("BaridiMob\nVirement reçu\nMontant : 4 500,00 DA\n"
                      f"Date : {datetime.now().strftime('%d/%m/%Y')}\nRéf : 223344556\n0\n")
    try:
        img = tmp / "receipt_ok.png"
        pic = Image.new("RGB", (400, 700), (245, 246, 250))
        d = ImageDraw.Draw(pic)
        for i, line in enumerate(["BaridiMob", "Virement recu", "4500 DA",
                                  datetime.now().strftime("%d/%m/%Y"), "Ref 223344556"]):
            d.text((30, 60 + i * 40), line, fill=(20, 20, 20))
        pic.save(img)

        res = detector.analyze(img, db)
        check("plausible receipt -> real", res["verdict"] == detector.VERDICT_REAL,
              f"verdict={res['verdict']} reasons={res['reasons']}")
        check("extracted amount", res["extracted"]["amount"] == 4500)

        # 2) future date -> fake
        holder["text"] = "Montant : 9000 DA\nDate : 01/01/2099\nRéf : 998877665\n"
        res2 = detector.analyze(img, db)
        check("future date -> fake/suspicious",
              res2["verdict"] in (detector.VERDICT_FAKE, detector.VERDICT_SUSPICIOUS),
              f"verdict={res2['verdict']}")

        # 3) save evidence then re-analyse same image -> known fake match
        res3 = detector.analyze(img, db)
        detector.save_evidence(db, res3)
        res4 = detector.analyze(img, db)
        check("re-used fake detected by hash",
              res4["verdict"] == detector.VERDICT_FAKE
              and any(r[0] == "known_fake_match" for r in res4["reasons"]),
              f"verdict={res4['verdict']} reasons={res4['reasons']}")
    finally:
        sys.modules.pop("pytesseract", None)


def test_settings_templates(tmp: Path) -> None:
    print("[settings + templates]")
    db = make_db(tmp)
    check("default language", settings_store.get_setting(db, "language") == "fr")
    settings_store.set_setting(db, "language", "ar")
    check("set language", settings_store.get_setting(db, "language") == "ar")
    tpl = templates_store.all_templates(db)
    check("templates seeded", len(tpl) >= 10)
    check("template has ar+fr",
          all(t["text_ar"] and t["text_fr"] for t in tpl))
    cats = templates_store.categories(db)
    check("categories", set(cats) >= {"deposit", "negotiation", "ghost", "warning"})


def test_i18n() -> None:
    print("[i18n]")
    missing = []
    for key, entry in i18n._TR.items():
        for lang in ("fr", "en", "ar"):
            if not entry.get(lang):
                missing.append(f"{key}:{lang}")
    check("all keys translated fr+en+ar", not missing, str(missing[:5]))
    check("english dashboard label", i18n.t("nav_dashboard", "en") == "Dashboard")
    check("language cycle fr->en->ar->fr",
          i18n.next_lang("fr") == "en" and i18n.next_lang("en") == "ar"
          and i18n.next_lang("ar") == "fr")
    check("english months", i18n.month_name(1, "en") == "January")
    check("t fallback", i18n.t("nonexistent_key") == "nonexistent_key")
    check("t formatting", i18n.t("ord_new_orders_count", "fr", n=3) == "3 commande(s)")
    check("58 wilayas", len(__import__("himaya.wilayas", fromlist=["WILAYAS"]).WILAYAS) == 58)


def test_bundled_tesseract(tmp: Path) -> None:
    print("[config] bundled tesseract resolution")
    from himaya import config
    orig = config.ASSETS_DIR
    d = tmp / "assets_t" / "tesseract"
    d.mkdir(parents=True)
    (d / "tesseract.exe").write_bytes(b"")
    config.ASSETS_DIR = tmp / "assets_t"
    try:
        found = config.bundled_tesseract()
        check("bundled tesseract found", found.endswith("tesseract.exe"), found)
    finally:
        config.ASSETS_DIR = orig
    check("no bundle -> empty string", config.bundled_tesseract() == ""
          or config.bundled_tesseract().endswith("tesseract.exe"))


def test_schema_and_bundle_paths() -> None:
    print("[paths] schema + bundle resources resolve")
    from himaya.database.db import SCHEMA_PATH, _find_schema
    check("schema.sql found next to package", SCHEMA_PATH.exists(), str(SCHEMA_PATH))
    check("schema contains tables", "CREATE TABLE IF NOT EXISTS customers" in
          SCHEMA_PATH.read_text(encoding="utf-8"))
    check("find_schema deterministic", str(_find_schema()) == str(SCHEMA_PATH))
    from himaya import config
    check("assets dir exists (dev or bundle)", config.ASSETS_DIR.exists(),
          str(config.ASSETS_DIR))
    from himaya.services.detector import TFLiteClassifier
    clf = TFLiteClassifier()
    check("tflite slot optional, no crash", clf.available is False or clf.available is True)


def test_wilaya_rtl() -> None:
    print("[wilayas]")
    from himaya.wilayas import wilaya_ar, WILAYA_NAMES_FR
    check("sidi bel abbes -> arabic", wilaya_ar("Sidi Bel Abbès") == "سيدي بلعباس")
    check("58 unique fr names", len(set(WILAYA_NAMES_FR)) == 58)


# ---------------------------------------------------------------------------

def main() -> int:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="himaya_test_"))
    test_phone_normalization(tmp)
    test_customers_and_trust(tmp)
    test_phone_risk(tmp)
    test_orders_and_aggregates(tmp)
    test_order_date_and_companies(tmp)
    test_period_aware_aggregates(tmp)
    test_design_tokens()
    test_mutation_counter_and_icons(tmp)
    test_reports(tmp)
    test_inquiries(tmp)
    test_blacklist_and_hma(tmp)
    test_orders_csv_roundtrip(tmp)
    test_arabic_shaping()
    test_labels(tmp)
    test_backup(tmp)
    test_detector_hashing_and_parsing(tmp)
    test_detector_full_flow(tmp)
    test_settings_templates(tmp)
    test_i18n()
    test_wilaya_rtl()
    test_schema_and_bundle_paths()
    test_bundled_tesseract(tmp)
    print(f"\n{'=' * 50}\n{PASS} passed, {FAIL} failed")
    if FAILURES:
        print("Failures:")
        for f in FAILURES:
            print("  -", f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
