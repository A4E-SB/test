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




# ---------------------------------------------------------------------------
# v1.2.2: ttk option lint — validates option NAMES passed to Treeview
# .column()/.heading()/.tag_configure() against the documented ttk sets.
# Real tkinter isn't importable headless, so the stubs can't reject bad
# option names (the v1.2.1 crash: 'minsize' -> TclError at first table).
# ---------------------------------------------------------------------------

_TTK_COLUMN_OPTS = {"id", "anchor", "minwidth", "stretch", "width"}
_TTK_HEADING_OPTS = {"text", "image", "command", "anchor", "state"}


def lint_ttk_options() -> list[str]:
    import ast
    problems: list[str] = []
    for path in sorted(Path("himaya").rglob("*.py")):
        if "ui" not in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("column", "heading")):
                continue
            receiver = node.func.value
            if not (isinstance(receiver, ast.Attribute)
                    and receiver.attr in ("tree", "tv", "listbox")) and not (
                    isinstance(receiver, ast.Name) and receiver.id == "tree"):
                continue
            allowed = (_TTK_COLUMN_OPTS if node.func.attr == "column"
                       else _TTK_HEADING_OPTS)
            for kw in node.keywords:
                if kw.arg and kw.arg not in allowed:
                    problems.append(
                        f"{path}:{node.lineno} .{node.func.attr}() bad option "
                        f"'{kw.arg}' (allowed: {sorted(allowed)})")
    return problems


def main() -> int:
    # ---- static lints FIRST: run on real source, no stubs ----------------
    problems = lint_init_order() + lint_ttk_options()
    for pr in problems:
        print("  ✗ " + pr)
    if problems:
        print(f"UI SMOKE TEST: {len(problems)} static lint bug(s)")
        return 1
    print("  ✓ init-order lint: no self.X read before assignment (v1.2.1)")
    print("  ✓ ttk option lint: .column()/.heading() options all valid (v1.2.2)")
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

    for name, _label, _icon, _emoji in PAGES:
        app.show_page(name)
        print(f"  ✓ page: {name}")
    app.show_page("dashboard")

    app.set_language("ar")
    print("  ✓ switched to Arabic")
    for name, _label, _icon, _emoji in PAGES:
        app.show_page(name)
        print(f"  ✓ page (ar): {name}")
    # English pass (v1.0.3: full EN UI)
    app.set_language("en")
    print("  ✓ switched to English")
    for name, _label, _icon, _emoji in PAGES:
        app.show_page(name)
    print("  ✓ all pages (en)")
    app.set_language("fr")

    # ---- v1.1.2: language switch from EVERY page must rebuild a LIVE page --
    # (v1.1.1 bug: set_language destroyed pages but self.page kept pointing
    # at the dead frame -> show_page's grid_remove raised TclError and
    # aborted, leaving a blank window and dead navigation)
    from himaya.ui.app import PAGES as ALL_PAGES
    for name, _lbl, _ico, _emoji in ALL_PAGES:
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

    # ---- v1.3: shared status-badge + trust helpers --------------------------
    from himaya.ui import widgets as w
    assert w.row_tag("paid") == "row_paid" and w.row_tag("ghosted") == "row_ghosted"
    assert w.row_tag("weird") in ("danger", "caution", "good", "dim", "")
    assert w._blend("#000000", "#ffffff", 0.5) == "#808080"
    assert w.status_badge_text("paid", "fr").startswith("\u25cf")
    assert (w.trust_glyph(90)[0] == "\u2713" and w.trust_glyph(50)[0] == "\u26a0"
            and w.trust_glyph(10)[0] == "\U0001f512")
    # every status must have its tinted row tag configured by make_tree
    from himaya import config as _cfg
    import inspect as _insp
    _src = _insp.getsource(w.make_tree)
    assert 'row_{status}' in _src, "make_tree must configure per-status tags"
    for _st in _cfg.STATUS_COLORS:
        assert w.row_tag(_st) == f"row_{_st}"
    print("  ✓ shared badge helpers + per-status row tags (v1.3)")

    # ---- v1.2.3: quick-add ask_line must WAIT and return the fields --------
    # (v1.2.0-2 bug: it returned dialog.result immediately — always None —
    # so the ⚡ quick-paste button in the order dialog did nothing)
    import himaya.ui.quick_add as qa_mod
    _real_dlg_cls = qa_mod.QuickAddDialog

    class _FakeQuickDlg:
        def __init__(self, master, app):
            self.result = None            # empty until the user clicks Parse

        def user_presses_parse(self):
            self.result = {"phone": "0555123456", "name": "Karim",
                           "wilaya": "Sétif", "address": "cite 200"}

    class _FakeMaster:
        def wait_window(self, dlg):
            dlg.user_presses_parse()      # simulate the interaction

    qa_mod.QuickAddDialog = _FakeQuickDlg
    parsed = qa_mod.ask_line(_FakeMaster(), app)
    qa_mod.QuickAddDialog = _real_dlg_cls
    assert parsed and parsed.get("phone") == "0555123456", \
        "ask_line must wait for the user and return the parsed fields"
    print("  ✓ quick-add ask_line waits & returns the fields (v1.2.3)")

    # ---- dialog constructors + safe-dialog behavior (v1.3.1) ----------------
    from himaya.ui.customers import CustomerDialog
    from himaya.ui.orders import OrderDialog
    from himaya.ui.widgets import HimayaDialog
    from himaya.ui.products import ProductDialog
    from himaya.ui.quick_add import QuickAddDialog
    from himaya.ui.bulk_edit import BulkEditDialog
    from himaya.ui.duplicates_ui import DuplicatesDialog
    from himaya.ui.search import GlobalSearchDialog
    from himaya.ui.tour import TourDialog, PasswordGate
    from himaya.ui.widgets import ScamAlert
    for cls in (CustomerDialog, OrderDialog, ProductDialog, QuickAddDialog,
                BulkEditDialog, DuplicatesDialog, GlobalSearchDialog,
                TourDialog, PasswordGate, ScamAlert):
        assert issubclass(cls, HimayaDialog), \
            f"{cls.__name__} must use the safe HimayaDialog base"
    print("  ✓ all 10 dialogs on the HimayaDialog base (v1.3.1)")

    dlg = CustomerDialog(app, app)
    print("  ✓ CustomerDialog")
    # behavioral: close() must release the modal grab BEFORE destroying,
    # and must be idempotent (X + Cancel + double-click safe)
    order = []
    alive = [True]
    dlg.winfo_exists = lambda: alive[0]   # stub default is falsy; real tk: True
    dlg.grab_release = lambda: order.append("release")
    dlg.destroy = lambda: (order.append("destroy"), alive.__setitem__(0, False))
    dlg._closed = False
    dlg.close()
    dlg.close()   # window is gone now -> must be a no-op
    assert order == ["release", "destroy"], f"close() sequence wrong: {order}"
    print("  ✓ close(): grab released before destroy, idempotent")

    dlg2 = OrderDialog(app, app)
    print("  ✓ OrderDialog")
    dlg2.close()

    # ---- v1.7.2: chunked table fill (no long burst after a switch) -----------
    from himaya.ui.widgets import fill_tree_chunked as _ftc

    class _FakeTree:
        def __init__(self):
            self.rows, self.deleted = [], 0
        def get_children(self):
            return ()
        def delete(self, *a):
            self.deleted += 1
            self.rows = []
        def insert(self, _parent, _end, iid=None, values=None, tags=None):
            self.rows.append((iid, values, tags))

    rows = [{"iid": str(i), "values": (i,), "tags": ("good",)} for i in range(7)]
    ft = _FakeTree()
    _ftc(ft, rows, batch=3, schedule=lambda ms, fn: fn())   # pumped scheduler
    assert ft.deleted == 1 and len(ft.rows) == 7, (ft.deleted, len(ft.rows))
    assert ft.rows[0][0] == "0" and ft.rows[-1][0] == "6"
    print("  ✓ v1.7.2: chunked fill completes when the scheduler runs")

    pending = []
    cap = lambda ms, fn: pending.append(fn)
    fa = _FakeTree()
    _ftc(fa, rows[:4], batch=2, schedule=cap)      # A: 2 rows now, 1 pending
    assert len(fa.rows) == 2
    _ftc(fa, rows[4:], batch=2, schedule=cap)      # B supersedes A
    assert len(fa.rows) == 2                        # cleared, B's first batch
    pending[0]()                                    # A's stale continuation
    assert len(fa.rows) == 2, "superseded fill must not add rows"
    pending[1]()                                    # B's continuation
    assert len(fa.rows) == 3 and fa.rows[-1][0] == "6"   # B had 3 rows
    print("  ✓ v1.7.2: a newer fill cancels the in-flight one")

    for f in ("himaya/ui/orders.py", "himaya/ui/customers.py",
              "himaya/ui/labels_ui.py"):
        assert "fill_tree_chunked" in Path(f).read_text(encoding="utf-8"), f
    _app_src = Path("himaya/ui/app.py").read_text(encoding="utf-8")
    assert "_last_switch_ts" in _app_src and "after(180, self._prebuild_pages)" \
        in _app_src, "prebuild must pace itself and yield on switches"
    import time as _t
    app._pages.pop("settings", None)                # simulate one unbuilt page
    n_before = len(app._pages)
    sched, _orig_after = [], app.after
    app.after = lambda ms, fn=None: sched.append(ms)
    try:
        app._last_switch_ts = _t.time()             # user JUST switched
        app._prebuild_pages()
        assert len(app._pages) == n_before, \
            "prebuild must yield right after a click"
        assert sched and sched[0] == 150
        app._last_switch_ts = _t.time() - 10        # long idle -> builds again
        app._prebuild_pages()
        assert len(app._pages) == n_before + 1, "idle prebuild must resume"
    finally:
        app.after = _orig_after
    print("  ✓ v1.7.2: prebuild yields to fresh clicks, resumes when idle")

    # ---- v1.7.1: switch micro-costs + icon contracts --------------------------
    # nav highlight updates ONLY the changed buttons, with SHARED fonts
    app.show_page("orders")
    b_orders = app._nav_buttons["orders"]
    b_cust = app._nav_buttons["customers"]
    counts = {"o": 0, "c": 0}
    b_orders.configure = lambda **kw: counts.__setitem__("o", counts["o"] + 1)
    b_cust.configure = lambda **kw: counts.__setitem__("c", counts["c"] + 1)
    app._nav_buttons["dashboard"].configure = lambda **kw: None   # untouched
    app.show_page("customers")
    assert counts == {"o": 1, "c": 1}, counts
    print("  ✓ v1.7.1: nav reconfigures only the changed buttons")
    assert "_nav_font_active" in app.__dict__, "nav fonts must be cached once"
    assert app.__dict__["_nav_font_active"] is app.__dict__["_nav_font_active"]
    dash_src = Path("himaya/ui/dashboard.py").read_text(encoding="utf-8")
    assert 'icon="shield"' in dash_src and 'icon="truck"' in dash_src
    w_src = Path("himaya/ui/widgets.py").read_text(encoding="utf-8")
    assert "_icon_render(icon, color, 28)" in w_src, "hero badge uses the vector icon"
    assert "_icon_render(icon, color, 18)" in w_src, "chips use the vector icon"
    orders_src = Path("himaya/ui/orders.py").read_text(encoding="utf-8")
    assert "limit=200" in orders_src, "orders rows capped (map cost)"
    assert "limit=200" in Path("himaya/ui/labels_ui.py").read_text(encoding="utf-8")
    print("  ✓ v1.7.1: vector hero/chip icons; table rows capped at 200")

    # ---- v1.7: navigation must not refresh clean pages (lag fix) -------------
    from himaya.ui.app import PAGES as _P
    app.show_page("orders")
    page = app.page
    app._mark_fresh(page)
    calls = []
    page.refresh = lambda: calls.append(1)
    app.show_page("customers")
    app.show_page("orders")            # away and back with ZERO writes
    assert calls == [], "clean page re-rendered on switch (the lag bug)"
    print("  ✓ v1.7: clean pages do NOT refresh on switch")
    app.db.mutation_count += 1         # simulate a data change
    assert app._page_stale(page) is True
    app.show_page("orders")            # marks fresh + schedules the deferred
    assert app._page_stale(app.page) is False
    calls.clear()
    app._deferred_refresh(app.page)    # the deferred callback itself
    assert calls == [1], "dirty page must refresh (deferred path)"
    old = app.page
    app.show_page("customers")
    calls.clear()
    app._deferred_refresh(old)         # not the current page anymore
    assert calls == [], "deferred refresh must not fire for stale nav"
    print("  ✓ v1.7: data change -> one deferred refresh; stale nav guarded")

    # ---- v1.7: bars are rounded on TOP only, baseline flush -------------------
    from himaya.ui.widgets import bar_points as _bp
    pts = _bp(10, 100, 44, 200, 4)
    xs_, ys_ = pts[0::2], pts[1::2]
    assert ys_[0] == 200 and ys_[-1] == 200, "baseline must be flush"
    assert min(ys_) >= 100 and max(ys_) <= 200
    assert abs(xs_[1] - 10) < 1e-6 and abs(ys_[1] - 104) < 1e-6, \
        "sides straight until the top corner"
    flat = _bp(10, 196, 44, 200, 4)     # too short to round
    assert len(flat) == 8, "degenerate bar falls back to a rectangle"
    print("  ✓ v1.7: bar_points top-only rounding, flush baseline")

    # ---- v1.7: sidebar contracts ----------------------------------------------
    assert app._icon_mode == "vector", "PIL present -> vector icon set"
    for key, _lbl, _iname, _emoji in _P:
        assert key in app._nav_icons and "accent" in app._nav_icons[key]
    _app_src = Path("himaya/ui/app.py").read_text(encoding="utf-8")
    assert "border_width=1" in _app_src and "border_color=config.COLOR_BORDER" in _app_src, \
        "search box must use surface+border tokens"
    assert "smooth=True" not in _app_src.split("class BarChart")[0], "no capsule bars"
    print("  ✓ v1.7: vector nav icons for every page; search box themed")

    # ---- v1.6 design system contracts ---------------------------------------
    from himaya.ui import widgets as _Ws
    _Ws.FONT_FAMILY = _Ws.LATIN_FONT_FAMILY
    check_smoke = lambda name, cond: (_ for _ in ()).throw(AssertionError(name)) \
        if not cond else None
    check_smoke("400 map", _Ws._font_choice("normal") == ("Segoe UI", "normal"))
    check_smoke("600 map", _Ws._font_choice("semibold") == ("Segoe UI Semibold", "normal"))
    check_smoke("800 map", _Ws._font_choice("extrabold") == ("Segoe UI Black", "normal"))
    check_smoke("bold aliases semibold",
                _Ws._font_choice("bold") == _Ws._font_choice("semibold"))
    _srcw = Path("himaya/ui/widgets.py").read_text(encoding="utf-8")
    assert ".upper() if is_latin" in _srcw, "section headers uppercase (latin)"
    # truncation fix: status columns wide enough for 'Waiting deposit'
    for f in ("himaya/ui/orders.py", "himaya/ui/labels_ui.py",
              "himaya/ui/dashboard.py"):
        src = Path(f).read_text(encoding="utf-8")
        import re as _re
        widths = [int(w) for w in _re.findall(
            r'\("status", app\.t\("status"\), (\d{3})\)', src)]
        assert widths and all(w >= 130 for w in widths), (f, widths)
    print("  ✓ v1.6: type map 400/600/800, uppercase headers, status cols >=132")

    # ---- v1.5 design kit: hero / compact stats / horizontal bars -------------
    from himaya.ui.widgets import HeroCard, CompactStat, HBarChart
    hero = HeroCard(app, "Money saved")
    hero.set("12 400 DA", sub="3 blocked")
    assert hero.value_lbl is not None
    cs = CompactStat(app, "Revenue", value="9 000 DA", sub="deposits: 1 000")
    cs.set("9 500 DA")            # StatCard.set contract works
    bars = HBarChart(app)
    bars.set_data([("●  Ghosted  ×3", 1200, "#e74c3c"),
                   ("●  Refused  ×1", 400, "#e67e22"),
                   ("zero", 0, "#fff")])   # zeros skipped
    assert len(bars._rows) == 2, len(bars._rows)
    bars.set_data([])             # empty data clears
    assert len(bars._rows) == 0
    print("  ✓ v1.5 design kit: HeroCard/CompactStat/HBarChart behave")

    _dash_src = Path("himaya/ui/dashboard.py").read_text(encoding="utf-8")
    _rep_src = Path("himaya/ui/reports_ui.py").read_text(encoding="utf-8")
    assert "HeroCard(self" in _dash_src, "dashboard must have the hero card"
    assert "money_saved(db, days)" in _dash_src, "hero must follow the period"
    assert "completion_rate(db, days)" in _dash_src, "completion follows period"
    assert "paid_revenue(db, days)" in _dash_src, "revenue follows period"
    assert "total_lost(db, days)" in _dash_src, "losses follow the period"
    assert "self.c_real = CompactStat" in _rep_src, "real profit is its own card"
    assert "self.loss_bars = HBarChart" in _rep_src, "losses shown as bars"
    assert _rep_src.count("make_tree(") == 1, "only the wilaya table remains"
    print("  ✓ dashboard & reports follow the v1.5 design contracts")

    # ---- v1.4.2: windows must fit the screen (DPI-aware) --------------------
    from himaya.ui import widgets as _W2
    from himaya.ui.widgets import fit_geometry as _fg

    class _FakeScale:
        @staticmethod
        def get_window_scaling(win):
            return _FakeScale.v
    _W2.ctk.ScalingTracker = _FakeScale

    class _Win:
        def __init__(self, w, h):
            self._sz, self.calls = (w, h), []
        def winfo_screenwidth(self):
            return self._sz[0]
        def winfo_screenheight(self):
            return self._sz[1]
        def geometry(self, g):
            self.calls.append(g)

    # 1366x768 laptop at 125%: 730-unit window would be 912px -> must clamp
    _FakeScale.v = 1.25
    w = _Win(1366, 768)
    assert _fg(w, 480, 730) == (480, 524), _fg(w, 480, 730)
    assert w.calls == ["480x524"]
    # big screen at 100%: unchanged
    _FakeScale.v = 1.0
    w = _Win(1920, 1080)
    assert _fg(w, 480, 730) == (480, 730)
    # tiny screen at 150%: never below the sane floor
    _FakeScale.v = 1.5
    w = _Win(1024, 600)
    fitted = _fg(w, 480, 730)
    assert fitted == (480, 310), fitted   # width fits; height clamps to 310
    print("  ✓ fit_geometry: clamps to screen, DPI-aware, sane floor")

    # no dialog may size itself with a raw geometry() call anymore
    import subprocess
    raw = subprocess.run(["grep", "-rn", r'self\.geometry("', "himaya/ui/"],
                         capture_output=True, text=True).stdout.strip()
    assert not raw, f"raw self.geometry() found (use fit_geometry):\n{raw}"
    _orders_src = Path("himaya/ui/orders.py").read_text(encoding="utf-8")
    assert "fit_geometry(self, 480, 730)" in _orders_src
    assert "self.resizable(True, True)" in _orders_src
    _w_src = Path("himaya/ui/widgets.py").read_text(encoding="utf-8")
    assert 'self.bind("<Escape>", lambda _e: self.close())' in _w_src
    assert 'self.unbind("<Escape>")' in Path("himaya/ui/tour.py").read_text(
        encoding="utf-8")
    print("  ✓ every window screen-fitted; Esc closes dialogs (not the lock)")

    # ---- v1.4.1: CTk constructor kwargs lint (the 'empty order window'
    # bug was CTkComboBox(textvariable=...) — not a CTk argument, CTk raises
    # ValueError mid-build; stubs could never see it) -------------------------
    lint_ctk_kwargs()

    # ---- v1.4.1: dialog crash guard — a raising __init__ must log + close --
    from himaya.ui.widgets import HimayaDialog as _HD

    class _BoomDialog(_HD):
        def __init__(self, master, app):
            super().__init__(master)
            self._closed = False
            raise RuntimeError("boom-constructor")

    crashed = False
    try:
        _BoomDialog(app, app)
    except RuntimeError:
        crashed = True
    assert crashed, "guard must re-raise the original error"
    log_path = config.DATA_DIR / "error.log"
    assert log_path.exists() and "boom-constructor" in log_path.read_text(
        encoding="utf-8"), "crash must be written to error.log"
    print("  ✓ dialog crash guard: logged + window closed + re-raised")

    # ---- v1.4.1: close() never leaves a zombie ------------------------------
    z = OrderDialog(app, app)
    calls = []
    z.winfo_exists = lambda: True
    z.grab_release = lambda: calls.append("release")
    z.destroy = lambda: (_ for _ in ()).throw(RuntimeError("broken child"))

    class _RawToplevelMod:                    # widgets.close() fallback path
        class Toplevel:
            @staticmethod
            def destroy(w): raise RuntimeError("raw broken")
    from himaya.ui import widgets as _W
    _real_tk = _W.tk
    _W.tk = _RawToplevelMod()
    try:
        z.withdraw = lambda: calls.append("withdraw")
        z.close()
        z.close()   # second click must be a safe no-op
    finally:
        _W.tk = _real_tk
    # every click runs one full safe escalation pass (a withdrawn window
    # still exists, so a retry must be possible — no permanent latch)
    assert calls == ["release", "withdraw", "release", "withdraw"], calls
    print("  ✓ close() escalates destroy -> withdraw, never zombies")

    # ---- v1.4 order-form behavior: price from stock, custom company, date --
    import inspect as _inspect
    from himaya.ui import orders as _orders_ui
    _src = _inspect.getsource(_orders_ui)
    assert "ord_date_today" in _src and "parse_date_text" in _src, \
        "order form must expose the date field + validator"
    assert 'self.price.set(str(int(p["sale_price"])))' in _src, \
        "catalog pick must fill the catalog sale price"
    assert "delivery_companies" in _src and "_add_company_tag" in _src, \
        "delivery combo must list saved companies + the add entry"
    assert "order_date=date_iso" in _src, "create must pass the order date"
    assert '**({"date": date_iso} if date_iso else {})' in _src, \
        "update must only set the date when one was typed"
    print("  ✓ order form: date + company + price wiring present")

    class _Var:
        def __init__(self, v=""):
            self.v, self.set_calls = v, []
        def get(self):
            return self.v
        def set(self, v):
            self.v, _ = v, self.set_calls.append(v)

    dlg3 = OrderDialog(app, app)
    dlg3._catalog = [{"id": 7, "name": "Montre connectée", "sale_price": 4200}]
    dlg3.product = _Var("Montre connectée")
    dlg3.price = _Var("999")          # already-filled price must be OVERWRITTEN
    dlg3._on_catalog_pick()
    assert dlg3.price.set_calls == ["4200"], dlg3.price.set_calls
    print("  ✓ catalog pick overwrites price with the stock price")

    class _Combo:
        def __init__(self, v):
            self.v, self.set_calls, self.cfg = v, [], {}
        def get(self):
            return self.v
        def set(self, v):
            self.v, _ = v, self.set_calls.append(v)
        def configure(self, **kw):
            self.cfg.update(kw)

    from himaya.ui import quick_add as _qa
    from himaya.models import settings_store as _ss
    dlg3._add_company_tag, dlg3._last_company = "➕ ADD", "Yalidine"
    dlg3.delivery = _Combo("➕ ADD")
    _qa.ask_text = lambda *a, **k: "Kazi Tour Express"
    dlg3._on_company_pick()
    assert dlg3.delivery.set_calls == ["Kazi Tour Express"], dlg3.delivery.set_calls
    assert "Kazi Tour Express" in _ss.delivery_companies(app.db)
    dlg3.delivery = _Combo("➕ ADD")
    dlg3._last_company = "Yalidine"                # as if picked before
    _qa.ask_text = lambda *a, **k: None            # cancelled
    dlg3._on_company_pick()
    assert dlg3.delivery.set_calls == ["Yalidine"], dlg3.delivery.set_calls
    print("  ✓ custom delivery company: saved on add, kept on cancel")
    dlg3.close()

    # source-level guarantee: no dialog grabs directly (deferred grab only)
    import subprocess
    bad = subprocess.run(
        ["grep", "-rn", r"self\.grab_set()", "himaya/ui/"],
        capture_output=True, text=True).stdout.strip()
    assert "widgets.py" in bad and bad.count(":") >= 1 and \
        all("widgets.py" in line for line in bad.splitlines()), \
        f"raw grab_set() outside the safe base:\n{bad}"
    print("  ✓ no raw grab_set() outside HimayaDialog")

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




def lint_ctk_kwargs() -> None:
    """Every ctk.<Widget>(...) call may only use REAL CTk 5.2.2 arguments.
    Signature table extracted from the customtkinter 5.2.2 source."""
    import ast
    SIGS = {
        "CTk": {"fg_color"},
        "CTkBaseClass": {"bg_color", "height", "master", "width"},
        "CTkButton": {"anchor", "background_corner_colors", "bg_color",
            "border_color", "border_spacing", "border_width", "command",
            "compound", "corner_radius", "fg_color", "font", "height", "hover",
            "hover_color", "image", "master",
            "round_height_to_even_numbers", "round_width_to_even_numbers",
            "state", "text", "text_color", "text_color_disabled",
            "textvariable", "width"},
        "CTkCheckBox": {"bg_color", "border_color", "border_width",
            "checkbox_height", "checkbox_width", "checkmark_color", "command",
            "corner_radius", "fg_color", "font", "height", "hover",
            "hover_color", "master", "offvalue", "onvalue", "state", "text",
            "text_color", "text_color_disabled", "textvariable", "variable",
            "width"},
        "CTkComboBox": {"bg_color", "border_color", "border_width",
            "button_color", "button_hover_color", "command", "corner_radius",
            "dropdown_fg_color", "dropdown_font", "dropdown_hover_color",
            "dropdown_text_color", "fg_color", "font", "height", "hover",
            "justify", "master", "state", "text_color", "text_color_disabled",
            "values", "variable", "width"},
        "CTkEntry": {"bg_color", "border_color", "border_width",
            "corner_radius", "fg_color", "font", "height", "master",
            "placeholder_text", "placeholder_text_color", "state",
            "text_color", "textvariable", "width"},
        "CTkFont": {"family", "overstrike", "size", "slant", "underline",
            "weight"},
        "CTkFrame": {"background_corner_colors", "bg_color", "border_color",
            "border_width", "corner_radius", "fg_color", "height", "master",
            "overwrite_preferred_drawing_method", "width"},
        "CTkImage": {"dark_image", "light_image", "size"},
        "CTkLabel": {"anchor", "bg_color", "compound", "corner_radius",
            "fg_color", "font", "height", "image", "master", "text",
            "text_color", "text_color_disabled", "width", "wraplength"},
        "CTkOptionMenu": {"anchor", "bg_color", "button_color",
            "button_hover_color", "command", "corner_radius",
            "dropdown_fg_color", "dropdown_font", "dropdown_hover_color",
            "dropdown_text_color", "dynamic_resizing", "fg_color", "font",
            "height", "hover", "master", "state", "text_color",
            "text_color_disabled", "values", "variable", "width"},
        "CTkProgressBar": {"bg_color", "border_color", "border_width",
            "corner_radius", "determinate_speed", "fg_color", "height",
            "indeterminate_speed", "master", "mode", "orientation",
            "progress_color", "variable", "width"},
        "CTkRadioButton": {"bg_color", "border_color", "border_width_checked",
            "border_width_unchecked", "command", "corner_radius", "fg_color",
            "font", "height", "hover", "hover_color", "master",
            "radiobutton_height", "radiobutton_width", "state", "text",
            "text_color", "text_color_disabled", "textvariable", "value",
            "variable", "width"},
        "CTkScrollableFrame": {"bg_color", "border_color", "border_width",
            "corner_radius", "fg_color", "height", "label_anchor",
            "label_fg_color", "label_font", "label_text", "label_text_color",
            "master", "orientation", "scrollbar_button_color",
            "scrollbar_button_hover_color", "scrollbar_fg_color", "width"},
        "CTkScrollbar": {"bg_color", "border_spacing", "button_color",
            "button_hover_color", "command", "corner_radius", "fg_color",
            "height", "hover", "master", "minimum_pixel_length", "orientation",
            "width"},
        "CTkSegmentedButton": {"background_corner_colors", "bg_color",
            "border_width", "command", "corner_radius", "dynamic_resizing",
            "fg_color", "font", "height", "master", "selected_color",
            "selected_hover_color", "state", "text_color",
            "text_color_disabled", "unselected_color", "unselected_hover_color",
            "values", "variable", "width"},
        "CTkSlider": {"bg_color", "border_color", "border_width",
            "button_color", "button_corner_radius", "button_hover_color",
            "button_length", "command", "corner_radius", "fg_color", "from_",
            "height", "hover", "master", "number_of_steps", "orientation",
            "progress_color", "state", "to", "variable", "width"},
        "CTkSwitch": {"bg_color", "border_color", "border_width",
            "button_color", "button_hover_color", "button_length", "command",
            "corner_radius", "fg_color", "font", "height", "hover", "master",
            "offvalue", "onvalue", "progress_color", "state", "switch_height",
            "switch_width", "text", "text_color", "text_color_disabled",
            "textvariable", "variable", "width"},
        "CTkTabview": {"anchor", "bg_color", "border_color", "border_width",
            "command", "corner_radius", "fg_color", "height", "master",
            "segmented_button_fg_color", "segmented_button_selected_color",
            "segmented_button_selected_hover_color",
            "segmented_button_unselected_color",
            "segmented_button_unselected_hover_color", "state", "text_color",
            "text_color_disabled", "width"},
        "CTkTextbox": {"activate_scrollbars", "bg_color", "border_color",
            "border_spacing", "border_width", "corner_radius", "fg_color",
            "font", "height", "master", "scrollbar_button_color",
            "scrollbar_button_hover_color", "text_color", "width"},
        "CTkToplevel": {"fg_color"},
    }
    # widgets that forward extra tk attributes (from the CTk 5.2.2 source:
    # _valid_tk_label_attributes / _valid_tk_entry_attributes / _valid_tk_text_attributes)
    EXTRA = {"cursor"}   # every widget: forwarded to the tkinter.Frame
    PER_CLASS_EXTRA = {
        "CTkLabel": {"justify", "padx", "pady", "textvariable", "state",
                     "takefocus", "underline", "cursor"},
        "CTkEntry": {"exportselection", "insertborderwidth", "insertofftime",
                     "insertontime", "insertwidth", "justify",
                     "selectborderwidth", "show", "takefocus", "validate",
                     "validatecommand", "xscrollcommand"},
        "CTkTextbox": {"autoseparators", "cursor", "exportselection",
                       "insertborderwidth", "insertofftime", "insertontime",
                       "insertwidth", "maxundo", "padx", "pady",
                       "selectborderwidth", "spacing1", "spacing2", "spacing3",
                       "state", "tabs", "takefocus", "undo", "wrap",
                       "xscrollcommand", "yscrollcommand"},
    }

    def check_source(name: str, source: str) -> list:
        problems, tree = [], ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            cls = None
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) \
                    and fn.value.id in ("ctk", "W") and fn.attr in SIGS:
                cls = fn.attr
            elif isinstance(fn, ast.Name) and fn.id in SIGS:
                cls = fn.id
            if not cls:
                continue
            allowed = SIGS[cls] | EXTRA | PER_CLASS_EXTRA.get(cls, set())
            for kw in node.keywords:
                if kw.arg is None:            # **kwargs pass-through
                    continue
                if kw.arg not in allowed:
                    problems.append(f"{name}:{node.lineno} {cls}({kw.arg}=…)")
        return problems

    # self-test: the exact v1.0-v1.4 bug must be flagged
    bad = check_source("selftest.py",
                       "import customtkinter as ctk\n"
                       "ctk.CTkComboBox(None, values=[], textvariable=v)\n")
    assert bad and "CTkComboBox(textvariable" in bad[0], bad
    good = check_source("selftest.py",
                        "import customtkinter as ctk\n"
                        "ctk.CTkComboBox(None, values=[], variable=v)\n")
    assert not good, good

    problems = []
    for path in sorted(Path(".").glob("himaya/**/*.py")):
        problems += check_source(str(path), path.read_text(encoding="utf-8"))
    assert not problems, "invalid CTk arguments:\n  " + "\n  ".join(problems)
    print("  ✓ CTk kwargs lint: every ctk.*() call uses real CTk arguments")


if __name__ == "__main__":
    sys.exit(main())
