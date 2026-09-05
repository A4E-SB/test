"""
Main window: sidebar navigation + page container + language switching.

The App object is passed to every page: it exposes db, lang, t(), toast()
and the risk-check helper used to fire scam alerts.

v1.1.0: full RTL mirroring in Arabic (sidebar flips to the right), global
search (Ctrl+K), first-launch tour and optional password lock.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import config
from ..database.db import Database
from ..i18n import t
from ..models import settings_store
from . import widgets as W
from .widgets import F

def _enable_dnd(root) -> bool:
    """
    Enable native drag & drop on an existing CTk root — OPTIONAL feature.

    Uses tkinterdnd2's official require() helper for external frameworks
    (the library monkey-patches drop_target_register onto all widgets when
    its module loads). ANY failure — package missing, version drift, tkdnd
    binaries absent — simply disables drag & drop; the app must NEVER crash
    because of it (v1.0.1 froze at startup because of an API-name change
    in tkinterdnd2 0.4: the mixin is DnDWrapper, no longer DnD).
    """
    try:
        from tkinterdnd2 import TkinterDnD
        TkinterDnD.require(root)
        return True
    except Exception:
        return False


PAGES = [
    ("dashboard", "nav_dashboard", "🏠"),
    ("customers", "nav_customers", "👥"),
    ("orders", "nav_orders", "📦"),
    ("products", "nav_products", "🛒"),
    ("relance", "nav_relance", "🔔"),
    ("detector", "nav_detector", "🔍"),
    ("time_wasters", "nav_time_wasters", "⏳"),
    ("reports", "nav_reports", "💰"),
    ("transfer", "nav_transfer", "🔌"),
    ("labels", "nav_labels", "🖨️"),
    ("settings", "nav_settings", "⚙️"),
]


class HimayaApp(ctk.CTk):
    def __init__(self, db: Database):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=config.COLOR_BG)
        self.dnd_enabled = _enable_dnd(self)   # optional drag & drop
        # typeface: Tajawal (bundled) when the UI is Arabic, Segoe UI otherwise
        W.set_ui_font(arabic=self.lang == "ar")
        self.db = db
        self.lang = settings_store.get_setting(db, "language", "fr")
        self.page_name: str | None = None
        self.page = None
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._pages: dict[str, object] = {}   # cache -> instant page switching
        self._unlocked = False                # set by the password gate

        self.title(t("app_title", self.lang))
        self.geometry("1280x760")
        self.minsize(1150, 700)
        try:
            ico = config.ASSETS_DIR / "icon.ico"
            if ico.exists():
                self.iconbitmap(str(ico))
        except Exception:
            pass

        self.grid_rowconfigure(0, weight=1)

        self._apply_rtl()
        self._build_sidebar()
        self.main = ctk.CTkFrame(self, fg_color=config.COLOR_BG, corner_radius=0)
        self.main.grid(row=0, column=self._main_col,
                       sticky="nsew", padx=0, pady=0)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        # global search: Ctrl+K from anywhere
        self.bind_all("<Control-k>", lambda e: self.open_global_search())
        self.bind_all("<Control-K>", lambda e: self.open_global_search())

        self.show_page("dashboard")
        # build the other pages in the background -> instant first switches
        self.after(400, self._prebuild_pages)

        # password lock first (if the seller set one in Settings → Security);
        # on success it shows the first-launch tour itself when due
        self.after(200, self._check_password_gate)
        if not security_has_password(db):
            # first launch: quick tour + optional demo data
            if not settings_store.get_setting(db, "tour_done", ""):
                self.after(300, self._show_tour)

    # ------------------------------------------------------------------ layout

    # Layout columns — LTR: sidebar 0 / content 1, RTL (Arabic): mirrored.
    # Single source of truth so the two frames can NEVER share a cell
    # (v1.1.0 regression: both gridded on the same column -> the content
    # frame covered the sidebar completely).
    @property
    def _side_col(self) -> int:
        return 1 if self.rtl else 0

    @property
    def _main_col(self) -> int:
        return 0 if self.rtl else 1

    def _apply_rtl(self) -> None:
        """Remember the layout direction: Arabic mirrors the whole window
        (sidebar on the right, anchors flipped on every page). Also sets
        which column stretches (the content one) in each direction."""
        self._rtl = self.lang == "ar"
        self.grid_columnconfigure(self._main_col, weight=1)
        self.grid_columnconfigure(self._side_col, weight=0)

    @property
    def rtl(self) -> bool:
        return getattr(self, "_rtl", self.lang == "ar")

    def _build_sidebar(self) -> None:
        # defense in depth: if a previous sidebar frame still exists
        # (rebuild on language switch), remove it so exactly ONE sidebar
        # is ever gridded — on the column matching the current direction
        prev = getattr(self, "sidebar", None)
        if prev is not None:
            try:
                prev.destroy()
            except Exception:
                pass
        self.sidebar = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=0,
                                    width=230)
        self.sidebar.grid(row=0, column=self._side_col,
                          sticky="nse" if self.rtl else "nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(len(PAGES) + 3, weight=1)

        # brand block: logo + name (falls back to text if the asset is missing)
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, padx=18, pady=(20, 2),
                   sticky="e" if self.rtl else "w")
        logo_first = self.rtl  # in RTL the text comes first, logo last
        try:
            from PIL import Image as PILImage
            self._logo_img = ctk.CTkImage(
                light_image=PILImage.open(config.ASSETS_DIR / "icon.png"),
                size=(44, 44))
            ctk.CTkLabel(brand, image=self._logo_img, text=""
                         ).pack(side="right" if logo_first else "left",
                                padx=(10 if logo_first else 0,
                                      0 if logo_first else 10))
        except Exception:
            pass
        ctk.CTkLabel(brand, text="Himaya", font=F(24, "bold"),
                     text_color=config.COLOR_ACCENT).pack(
            side="left" if logo_first else "right")
        # one translated string — never concatenate Arabic + Latin here
        # (v1.0 tagline mixed both and rendered as "100 — حماية% offline")
        ctk.CTkLabel(self.sidebar, text=t("tagline", self.lang),
                     font=F(10), text_color=config.COLOR_FG_DIM, wraplength=190,
                     justify="right" if self.rtl else "left"
                     ).grid(row=1, column=0, padx=18, pady=(0, 12),
                            sticky="e" if self.rtl else "w")

        # global search button (Ctrl+K)
        search_btn = ctk.CTkButton(
            self.sidebar, text="🔍 " + t("gs_title", self.lang), anchor="c",
            font=F(12), height=32, corner_radius=8, fg_color=config.COLOR_BG_3,
            hover_color=config.COLOR_BG, text_color=config.COLOR_FG,
            command=self.open_global_search)
        search_btn.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

        for i, (key, label_key, icon) in enumerate(PAGES, start=3):
            btn = ctk.CTkButton(
                self.sidebar, text=f"{icon}  {t(label_key, self.lang)}",
                anchor="e" if self.rtl else "w", font=F(13), height=38,
                corner_radius=8, fg_color="transparent",
                hover_color=config.COLOR_BG_3, text_color=config.COLOR_FG,
                command=lambda k=key: self.show_page(k))
            btn.grid(row=i, column=0, sticky="ew", padx=12, pady=2)
            self._nav_buttons[key] = btn

        # v1.2: the floating language button is GONE — language is switched
        # from Settings only (one switcher, not two)
        ctk.CTkLabel(self.sidebar, text=f"Himaya v{config.APP_VERSION}",
                     font=F(10), text_color=config.COLOR_FG_DIM
                     ).grid(row=len(PAGES) + 4, column=0, padx=12, pady=(0, 12))

    # ------------------------------------------------------------------ pages

    def _page_class(self, name: str):
        """Lazy class lookup (imports here avoid circular imports)."""
        from .dashboard import DashboardPage
        from .customers import CustomersPage
        from .orders import OrdersPage
        from .products import ProductsPage
        from .relance import RelancePage
        from .detector_ui import DetectorPage
        from .time_wasters import TimeWastersPage
        from .reports_ui import ReportsPage
        from .transfer import TransferPage
        from .labels_ui import LabelsPage
        from .settings_ui import SettingsPage

        return {
            "dashboard": DashboardPage, "customers": CustomersPage,
            "orders": OrdersPage, "products": ProductsPage,
            "relance": RelancePage, "detector": DetectorPage,
            "time_wasters": TimeWastersPage, "reports": ReportsPage,
            "transfer": TransferPage, "labels": LabelsPage,
            "settings": SettingsPage,
        }[name]

    def show_page(self, name: str) -> None:
        # hide current page, then show the target one — pages are CACHED so
        # switching is instant after the first visit (no rebuild lag)
        if self.page is not None:
            try:
                self.page.grid_remove()
            except Exception:
                pass   # already destroyed (e.g. right after a language switch)
        for k, btn in self._nav_buttons.items():
            active = k == name
            btn.configure(fg_color=config.COLOR_ACCENT if active else "transparent",
                          text_color="#ffffff" if active else config.COLOR_FG)
        self.page_name = name
        if name not in self._pages:
            self._pages[name] = self._page_class(name)(self.main, self)
        self.page = self._pages[name]
        self.page.grid(row=0, column=0, sticky="nsew")
        if hasattr(self.page, "refresh"):
            self.page.refresh()

    def _prebuild_pages(self) -> None:
        """
        Build the remaining pages in small idle slices (v1.1.4): building a
        page means creating 100-300 widgets, which froze the UI the first
        time each section was opened. Pre-building them in the background
        makes EVERY first click instant; startup stays responsive because
        only one page is built per slice.
        """
        if getattr(self, "_prebuilding_off", False):
            return
        remaining = [key for key, _lbl, _ico in PAGES
                     if key not in self._pages]
        if not remaining:
            return
        try:
            self._pages[remaining[0]] = self._page_class(remaining[0])(
                self.main, self)
        except Exception:
            pass   # a failed prebuild must never break the app
        self.after(60, self._prebuild_pages)

    def refresh_page(self) -> None:
        if self.page is not None and hasattr(self.page, "refresh"):
            self.page.refresh()

    # ------------------------------------------------------------------ lang

    def set_language(self, lang: str) -> None:
        settings_store.set_setting(self.db, "language", lang)
        self.lang = lang
        W.set_ui_font(arabic=lang == "ar")   # family for all rebuilt widgets
        # cached pages hold translated strings -> rebuild them lazily.
        # Order matters (v1.1.2): DETACH each page before destroying it —
        # calling grid_remove() on a destroyed frame raises TclError, and
        # CTkScrollableFrame pages keep an outer shell frame alive after
        # destroy() (the shell must leave the grid or empty shells stack).
        for page in self._pages.values():
            try:
                page.grid_remove()
            except Exception:
                pass
            try:
                page.destroy()
            except Exception:
                pass
            shell = getattr(page, "_parent_frame", None)
            if shell is not None:
                try:
                    shell.destroy()
                except Exception:
                    pass
        self._pages.clear()
        # self.page refers to a destroyed frame now — reset it so
        # show_page() never calls grid methods on a dead widget (that
        # TclError aborted show_page mid-way and left a blank window).
        self.page = None
        self.title(t("app_title", lang))
        # v1.1.3: destroy the old sidebar FRAME ENTIRELY before rebuilding.
        # v1.1.2 only destroyed its children, then _build_sidebar() created
        # a new frame on the (mirrored) other side — the old empty 230px
        # frame stayed gridded in the previous column, overlapping the
        # content cell: an empty strip on the original side and, once
        # leaked frames stacked above the content, a dead panel over it.
        try:
            self.sidebar.destroy()
        except Exception:
            pass
        self._nav_buttons.clear()
        self._apply_rtl()
        # re-grid main frame on the correct side of the mirrored layout
        self.main.grid(row=0, column=self._main_col, sticky="nsew")
        self._build_sidebar()
        self.show_page(self.page_name or "dashboard")

    # ------------------------------------------------------------------ search

    def open_global_search(self) -> None:
        from .search import GlobalSearchDialog
        GlobalSearchDialog(self, self)

    # ------------------------------------------------------------------ tour / lock

    def _show_tour(self) -> None:
        from .tour import TourDialog
        TourDialog(self, self)

    def _check_password_gate(self) -> None:
        if self._unlocked:
            return
        from ..services import security
        if not security.has_password(self.db):
            self._unlocked = True
            return
        self._prebuilding_off = True   # don't build pages behind a lock
        from .tour import PasswordGate
        PasswordGate(self, self)

    # ------------------------------------------------------------------ helpers

    def t(self, key: str, **kwargs) -> str:
        return t(key, self.lang, **kwargs)

    def toast(self, message: str, kind: str = "info") -> None:
        """
        Small transient status popup (bottom-right). The window is created
        ONCE and reused: spawning a fresh Toplevel per click is one of the
        slowest tk operations (this was announced in v1.1.4 but the patch
        never landed — applied for real in v1.2).
        """
        color = {"info": config.COLOR_ACCENT, "ok": config.COLOR_GREEN,
                 "warn": config.COLOR_ORANGE, "err": config.COLOR_RED}.get(kind,
                                                                           config.COLOR_ACCENT)
        win = getattr(self, "_toast_win", None)
        alive = False
        if win is not None:
            try:
                alive = bool(win.winfo_exists())
            except Exception:
                alive = True    # headless test stubs: assume reusable
        if not alive:
            self._toast_win = win = ctk.CTkToplevel(self)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            self._toast_frame = ctk.CTkFrame(win, fg_color=config.COLOR_CARD,
                                             corner_radius=10, border_width=1)
            self._toast_frame.pack(padx=2, pady=2)
            self._toast_lbl = ctk.CTkLabel(self._toast_frame, text="", font=F(12),
                                           wraplength=380, justify="left")
            self._toast_lbl.pack(padx=16, pady=10)
        try:
            self._toast_frame.configure(border_color=color)
            self._toast_lbl.configure(text=message, text_color=color)
            x = self.winfo_rootx() + self.winfo_width() - 420
            y = self.winfo_rooty() + self.winfo_height() - 110
            win.geometry(f"+{max(10, x)}+{max(10, y)}")
            win.deiconify()
        except Exception:
            pass   # headless test stubs: constructing is all we verify
        if getattr(self, "_toast_job", None) is not None:
            try:
                self.after_cancel(self._toast_job)
            except Exception:
                pass
        self._toast_job = self.after(3200, self._hide_toast)

    def _hide_toast(self) -> None:
        self._toast_job = None
        win = getattr(self, "_toast_win", None)
        if win is not None:
            try:
                win.withdraw()
            except Exception:
                pass

    def check_phone(self, phone: str, on_block=None, on_continue=None,
                    show_block_btn: bool = False) -> dict:
        """
        Run a phone risk check; show the scam alert popup if risky.
        Always returns the risk dict (caller decides what to do).
        """
        from ..services.phone import phone_risk
        risk = phone_risk(self.db, phone)
        if risk["level"] in ("caution", "danger"):
            W.ScamAlert(self, self, risk, on_block=on_block, on_continue=on_continue,
                        show_block_btn=show_block_btn)
        return risk


def security_has_password(db) -> bool:
    """Module-level helper (kept lazy: services may be stubbed in tests)."""
    try:
        from ..services import security
        return security.has_password(db)
    except Exception:
        return False
