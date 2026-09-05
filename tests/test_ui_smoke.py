"""
Headless UI smoke test — runs every page constructor without a display.

tkinter/customtkinter are replaced by permissive stubs (AnyObj): any
attribute access returns a callable factory, any call returns an AnyObj.
This catches import errors, typos and attribute errors in all UI code paths
that run at construction time (the parts static analysis can't verify).

Run:  python tests/test_ui_smoke.py
"""

from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Permissive stub: usable as a base class, a factory, and an instance whose
# every attribute/method exists.
# ---------------------------------------------------------------------------

class AnyObj:
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return _factory(name)

    def __call__(self, *a, **k):
        return AnyObj()

    def __iter__(self):
        return iter([])

    def __len__(self):
        return 0

    def __bool__(self):
        return False

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __str__(self):
        return ""

    def __format__(self, spec):
        return ""

    def __conform__(self, protocol):     # sqlite3 binding -> empty string
        return ""

    # comparisons / arithmetic so stubs survive math in drawing code
    def __lt__(self, other): return False
    def __le__(self, other): return True
    def __gt__(self, other): return False
    def __ge__(self, other): return True

    def __add__(self, other): return 0.0
    __radd__ = __add__
    def __sub__(self, other): return 0.0
    __rsub__ = __sub__
    def __mul__(self, other): return 0.0
    __rmul__ = __mul__
    def __truediv__(self, other): return 0.0
    __rtruediv__ = __truediv__
    def __floordiv__(self, other): return 0.0
    def __mod__(self, other): return 0.0


def _factory(name: str):
    """A fresh subclass of AnyObj — subclassable AND callable."""
    return type(name, (AnyObj,), {})


def install_stubs() -> None:
    """Install permissive stub modules for tkinter / customtkinter."""
    def make_mod(name: str) -> types.ModuleType:
        m = types.ModuleType(name)
        m.__getattr__ = lambda attr: _factory(attr)  # type: ignore[method-assign]
        return m

    tk = make_mod("tkinter")
    for sub in ("ttk", "filedialog", "messagebox", "font"):
        m = make_mod(f"tkinter.{sub}")
        sys.modules[f"tkinter.{sub}"] = m
        setattr(tk, sub, m)          # so `from tkinter import ttk` binds the module
    sys.modules["tkinter"] = tk
    sys.modules["customtkinter"] = make_mod("customtkinter")

    # tkinterdnd2 stub mimicking the REAL v0.4 layout: a MODULE named
    # TkinterDnD (no DnD mixin class! that's what crashed v1.0.1) exposing
    # the official require() helper for external frameworks + constants.
    tkdnd = types.ModuleType("tkinterdnd2")
    tkdnd_mod = types.ModuleType("tkinterdnd2.TkinterDnD")
    tkdnd_mod.require = lambda root: "2.9.3-stub"
    tkdnd_mod.DnDWrapper = type("DnDWrapper", (), {})  # exists, unused by us
    tkdnd.TkinterDnD = tkdnd_mod
    tkdnd.DND_FILES = "DND_Files"
    sys.modules["tkinterdnd2"] = tkdnd
    sys.modules["tkinterdnd2.TkinterDnD"] = tkdnd_mod




# ---------------------------------------------------------------------------
# v1.2.1: init-order lint — catches reads of self.X BEFORE it is assigned
# in the same __init__ (the v1.2.0 crash: self.lang read 3 lines too early).
# The stub environment cannot catch this class of bug (any attribute returns
# a stub), so we check the REAL source with the AST instead.
# ---------------------------------------------------------------------------

def lint_init_order() -> list[str]:
    import ast
    problems: list[str] = []
    for path in sorted(Path("himaya").rglob("*.py")):
        if "ui" not in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            # names that are methods or properties of the class -> always ok
            ok_names = set()
            for item in cls.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    ok_names.add(item.name)
                    if any(isinstance(d, ast.Name) and d.id == "property"
                           for d in item.decorator_list):
                        ok_names.add(item.name)
            for fn in (n for n in cls.body if isinstance(n, ast.FunctionDef)
                       and n.name == "__init__"):
                events = []
                for node in ast.walk(fn):
                    if (isinstance(node, ast.Attribute)
                            and isinstance(node.value, ast.Name)
                            and node.value.id == "self"):
                        if isinstance(node.ctx, ast.Store):
                            events.append((node.lineno, "W", node.attr))
                        elif node.attr not in ok_names:
                            events.append((node.lineno, "R", node.attr))
                events.sort()
                # a read is a bug if that attr is WRITTEN LATER in this fn
                writes = {a for _l, k, a in events if k == "W"}
                seen_written = set()
                for _l, kind, attr in events:
                    if kind == "W":
                        seen_written.add(attr)
                    elif attr in writes and attr not in seen_written:
                        problems.append(
                            f"{path}:{_l} self.{attr} read before assignment")
    return problems


def main() -> int:
    # ---- init-order lint FIRST: runs on real source, no stubs ----------
    problems = lint_init_order()
    for pr in problems:
        print("  ✗ " + pr)
    if problems:
        print(f"UI SMOKE TEST: {len(problems)} init-order bug(s)")
        return 1
    print("  ✓ init-order lint: no self.X read before assignment (v1.2.1)")
    install_stubs()

    # force a temp data dir so nothing touches a real profile
    tmp = Path(tempfile.mkdtemp(prefix="himaya_ui_test_"))
    import os
    os.environ["HIMAYA_DATA_DIR"] = str(tmp)

    # these modules cache paths at import time -> import AFTER env is set
    from himaya import config
    config.DATA_DIR = tmp
    config.DB_PATH = tmp / "himaya.db"
    config.EVIDENCE_DIR = tmp / "evidence"
    config.EVIDENCE_DIR.mkdir(exist_ok=True)
    config.BACKUP_DIR = tmp / "backups"
    config.BACKUP_DIR.mkdir(exist_ok=True)

    from himaya.database import Database, seed
    from himaya.models import customers, orders, blacklist, inquiries
    from himaya.models import orders as orders_model
    from himaya.services import trust

    db = Database(config.DB_PATH)
    seed(db)

    # ---- seed some data so every page renders real content ----------------
    good = customers.create(db, "Amine Fiable", "0555111222", wilaya="Alger",
                            address="Bab Ezzouar")
    for i in range(3):
        oid = orders.create(db, good, f"Produit {i}", 2500, shipping_cost=600,
                            wilaya="Alger")
        orders.set_status(db, oid, "delivered")
    oid = orders.create(db, good, "Produit X", 3000, shipping_cost=600)
    orders.set_status(db, oid, "paid")
    trust.refresh(db, good)

    ghost = customers.create(db, "Ghost Client", "0661333444", wilaya="Oran")
    for i in range(2):
        oid = orders.create(db, ghost, "Article", 1800, shipping_cost=500)
        orders.set_status(db, oid, "ghosted")
    trust.refresh(db, ghost)

    scammer = customers.create(db, "Nasba King", "0771555666")
    oid = orders.create(db, scammer, "iPhone", 45000, shipping_cost=800)
    orders.set_status(db, oid, "fake_payment")
    trust.refresh(db, scammer)
    blacklist.add(db, "0770999888", "faux reçu BaridiMob", severity=3)
    for i in range(5):
        inquiries.log(db, good, platform="Messenger", converted=False)
    trust.refresh(db, good)

    # ---- build the app + visit every page (FR then AR) --------------------
    from himaya.ui.app import HimayaApp, PAGES
    app = HimayaApp(db)
    print("  ✓ HimayaApp constructed")
    assert app.dnd_enabled is True, "dnd stub require() should have succeeded"

    # v1.1.1 regression: sidebar and content frame must NEVER share a grid
    # column (v1.1.0 put both on the same one -> sidebar hidden behind pages)
    for lang in ("fr", "en", "ar"):
        app.lang = lang
        app._apply_rtl()
        assert app._side_col != app._main_col, f"columns overlap in {lang}"
        assert app._main_col == (0 if lang == "ar" else 1), f"main col wrong in {lang}"
    app.lang = "fr"
    app._apply_rtl()
    print("  ✓ layout columns distinct in fr/en/ar (v1.1.1 fix)")

    for name, _label, _icon in PAGES:
        app.show_page(name)
        print(f"  ✓ page: {name}")
    app.show_page("dashboard")

    app.set_language("ar")
    print("  ✓ switched to Arabic")
    for name, _label, _icon in PAGES:
        app.show_page(name)
        print(f"  ✓ page (ar): {name}")
    # English pass (v1.0.3: full EN UI)
    app.set_language("en")
    print("  ✓ switched to English")
    for name, _label, _icon in PAGES:
        app.show_page(name)
    print("  ✓ all pages (en)")
    app.set_language("fr")

    # ---- v1.1.2: language switch from EVERY page must rebuild a LIVE page --
    # (v1.1.1 bug: set_language destroyed pages but self.page kept pointing
    # at the dead frame -> show_page's grid_remove raised TclError and
    # aborted, leaving a blank window and dead navigation)
    from himaya.ui.app import PAGES as ALL_PAGES
    for name, _lbl, _ico in ALL_PAGES:
        app.show_page(name)
        old_page = app.page
        app.set_language("ar")
        assert app.page is not old_page, f"dead page kept after switch from {name}"
        assert app.page_name == name, f"page name lost switching from {name}"
        assert app._pages.get(name) is app.page, f"cache not rebuilt for {name}"
        app.set_language("fr")
    print("  ✓ language switch from every page rebuilds a live page (v1.1.2)")

    # ---- v1.1.3: the old sidebar FRAME must die on language switch -------
    # (v1.1.2 destroyed only its children; the empty 230px frame stayed
    # gridded in the previous column -> empty strip on the original side,
    # and leaked frames stacked over the content)
    class _SidebarRecorder:
        def __init__(self):
            self.destroyed = False
        def winfo_children(self):
            return []
        def destroy(self):
            self.destroyed = True
    rec = _SidebarRecorder()
    app.sidebar = rec
    app.set_language("en")
    assert rec.destroyed, "old sidebar frame leaked on language switch"
    app.set_language("fr")
    print("  ✓ old sidebar frame destroyed on switch (v1.1.3 fix)")

    # ---- dialog constructors (no save() calls) -----------------------------
    from himaya.ui.customers import CustomerDialog
    from himaya.ui.orders import OrderDialog
    dlg = CustomerDialog(app, app)
    print("  ✓ CustomerDialog")
    dlg.destroy()
    dlg2 = OrderDialog(app, app)
    print("  ✓ OrderDialog")
    dlg2.destroy()

    # ---- scam alert popup ----------------------------------------------------
    from himaya.services.phone import phone_risk
    from himaya.ui.widgets import ScamAlert
    risk = phone_risk(db, "0770999888")
    alert = ScamAlert(app, app, risk)
    print("  ✓ ScamAlert popup")
    alert.destroy()

    # ---- widgets -------------------------------------------------------------
    from himaya.ui.widgets import BarChart, TrustBar, tags_frame, copy_to_clipboard
    chart = BarChart(app)
    from himaya.services.reports import revenue_series
    chart.set_data(revenue_series(db, 6))
    print("  ✓ BarChart render")
    tb = TrustBar(app, 73); tb.set(15)
    tags_frame(app, ["scammer", "ghost", "trusted"], "fr")
    print("  ✓ TrustBar / tags")

    # ---- interactive flows (with small monkeypatches on stub widgets) -------
    # 1) orders: change status of a selected order
    app.show_page("orders")
    page = app.page
    page.tree.selection = lambda: [str(oid)]  # type: ignore[assignment]
    page.set_status("delivered")
    after = orders_model.get(db, oid)
    assert after and after["status"] == "delivered", "status change failed"
    print("  ✓ OrdersPage.set_status")

    # 2) time-wasters: log an inquiry for the ghost customer
    app.show_page("time_wasters")
    tw = app.page
    label = f"{customers.get(db, ghost)['name']} — {customers.get(db, ghost)['phone']}"
    tw.cust_combo.get = lambda: label  # type: ignore[assignment]
    tw.platform.get = lambda: "WhatsApp"  # type: ignore[assignment]
    tw.log_inquiry()
    assert inquiries.recent(db, 1)[0]["platform"] == "WhatsApp"
    print("  ✓ TimeWastersPage.log_inquiry")

    # 3) detector: render a fake/real analysis result
    app.show_page("detector")
    det = app.page
    det.render_result({"verdict": "fake", "confidence": 87, "path": "x.png",
                       "hash": "abc123", "near_matches": 0,
                       "extracted": {"amount": 4500, "date": "01/01/2099",
                                     "ref": "223344556", "phone": "0771555666"},
                       "reasons": [("editor_signature::picsart", "picsart"),
                                   ("date_in_future", ""), ("known_fake_match", ""),
                                   ("amount_not_found", "")]})
    print("  ✓ DetectorPage.render_result")

    # 4) labels: generate a real PDF from the orders page selection
    from himaya.ui.labels_ui import generate_and_open
    out_pdf = generate_and_open(app, [oid])
    assert Path(out_pdf).exists()
    print("  ✓ labels.generate_and_open")

    # 5) clipboard helper
    copy_to_clipboard(det, "test 123")
    print("  ✓ copy_to_clipboard")

    # 6) phone risk popup triggers (blacklisted number)
    from himaya.services.phone import phone_risk
    r = phone_risk(db, "0770999888")
    assert r["level"] == "danger" and r["blacklisted"]
    print("  ✓ phone_risk (blacklisted)")

    # ---- v1.0.4 fixes -------------------------------------------------------
    # 1) wheel_combo cycling logic (fake combo records set() calls)
    from himaya.ui.widgets import wheel_combo

    class FakeCombo:
        def __init__(self):
            self.value = "Adrar"
            self.bindings = {}
            self.entry = self  # wheel_combo also binds the inner entry

        def bind(self, seq, fn):
            self.bindings[seq] = fn

        def get(self):
            return self.value

        def set(self, v):
            self.value = v

    from himaya.wilayas import WILAYA_NAMES_FR
    fc = FakeCombo()
    wheel_combo(fc, WILAYA_NAMES_FR)

    class FakeEvent:
        delta = -120  # scroll down

    fc.bindings["<MouseWheel>"](FakeEvent())
    assert fc.value == "Chlef", fc.value          # 01 -> 02
    fc.bindings["<MouseWheel>"](FakeEvent())
    assert fc.value == "Laghouat", fc.value       # 02 -> 03
    up = FakeEvent(); up.delta = 120              # scroll up
    fc.bindings["<MouseWheel>"](up)
    assert fc.value == "Chlef", fc.value
    print("  ✓ wheel_combo cycles wilayas (down/up)")

    # 2) status buttons give feedback instead of doing nothing silently
    app.show_page("orders")
    orders_page = app.page
    orders_page.tree.selection = lambda: []      # type: ignore[assignment]
    orders_page.tree.focus = lambda: ""          # type: ignore[assignment]
    orders_page.set_status("delivered")          # -> toast path, no crash
    print("  ✓ status button with no selection -> feedback (no silent no-op)")

    # 3) dashboard cards navigate + apply filters
    app.show_page("dashboard")
    dash = app.page
    dash._goto_orders("ghosted")
    assert app.page_name == "orders"
    print("  ✓ dashboard card click navigates + filters")

    # 4) page cache: revisiting a page must NOT rebuild it
    app.show_page("customers")
    cached_ref = app.page
    app.show_page("orders")
    app.show_page("customers")
    assert app.page is cached_ref
    print("  ✓ pages are cached (instant switching)")

    # ---- drag&drop must NEVER crash startup, whatever the library state ----
    from himaya.ui.app import _enable_dnd
    broken = types.ModuleType("tkinterdnd2")           # no TkinterDnD at all
    saved_pkg = sys.modules.pop("tkinterdnd2")
    saved_mod = sys.modules.pop("tkinterdnd2.TkinterDnD")
    sys.modules["tkinterdnd2"] = broken
    ok = _enable_dnd(app)
    sys.modules["tkinterdnd2"] = saved_pkg
    sys.modules["tkinterdnd2.TkinterDnD"] = saved_mod
    assert ok is False, "broken tkinterdnd2 must degrade to dnd-disabled"
    print("  ✓ broken tkinterdnd2 degrades gracefully (v1.0.1 regression)")

    print("\nUI SMOKE TEST: all pages OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
