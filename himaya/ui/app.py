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
from ..i18n import LANG_NAMES, next_lang, t
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
        ctk.CTkLabel(self.sidebar,
                     text=f"حماية — {t('offline_badge', self.lang)}",
                     font=F(11), text_color=config.COLOR_FG_DIM
                     ).grid(row=1, column=0, padx=22, pady=(0, 14),
                            sticky="e" if self.rtl else "w")

        # global search button (Ctrl+K)
        search_btn = ctk.CTkButton(
            self.sidebar, text="🔎 " + t("gs_title", self.lang), anchor="c",
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

        # language quick switch at the bottom: FR -> EN -> AR cycle,
        # the button always shows the NEXT language name
        lang_btn = ctk.CTkButton(
            self.sidebar,
            text="🌐 " + LANG_NAMES[next_lang(self.lang)],
            font=F(13), height=36, fg_color=config.COLOR_BG_3,
            hover_color=config.COLOR_BG, text_color=config.COLOR_FG,
            command=self.toggle_language)
        lang_btn.grid(row=len(PAGES) + 3, column=0, sticky="ew", padx=12, pady=(6, 4))
        ctk.CTkLabel(self.sidebar, text=f"Himaya v{config.APP_VERSION}",
                     font=F(10), text_color=config.COLOR_FG_DIM
                     ).grid(row=len(PAGES) + 4, column=0, padx=12, pady=(0, 12))

    # ------------------------------------------------------------------ pages

    def show_page(self, name: str) -> None:
        # import here to avoid circular imports at module load
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

        classes = {
            "dashboard": DashboardPage, "customers": CustomersPage,
            "orders": OrdersPage, "products": ProductsPage,
            "relance": RelancePage, "detector": DetectorPage,
            "time_wasters": TimeWastersPage, "reports": ReportsPage,
            "transfer": TransferPage, "labels": LabelsPage,
            "settings": SettingsPage,
        }
        # hide current page, then show the target one — pages are CACHED so
        # switching is instant after the first visit (no rebuild lag)
        if self.page is not None:
            self.page.grid_remove()
        for k, btn in self._nav_buttons.items():
            active = k == name
            btn.configure(fg_color=config.COLOR_ACCENT if active else "transparent",
                          text_color="#ffffff" if active else config.COLOR_FG)
        self.page_name = name
        if name not in self._pages:
            self._pages[name] = classes[name](self.main, self)
        self.page = self._pages[name]
        self.page.grid(row=0, column=0, sticky="nsew")
        if hasattr(self.page, "refresh"):
            self.page.refresh()

    def refresh_page(self) -> None:
        if self.page is not None and hasattr(self.page, "refresh"):
            self.page.refresh()

    # ------------------------------------------------------------------ lang

    def set_language(self, lang: str) -> None:
        settings_store.set_setting(self.db, "language", lang)
        self.lang = lang
        # cached pages hold translated strings -> rebuild them lazily
        for page in self._pages.values():
            try:
                page.destroy()
            except Exception:
                pass
        self._pages.clear()
        self.title(t("app_title", lang))
        for w in self.sidebar.winfo_children():
            w.destroy()
        self._nav_buttons.clear()
        self._apply_rtl()
        # re-grid main frame on the correct side of the mirrored layout
        self.main.grid(row=0, column=self._main_col, sticky="nsew")
        self._build_sidebar()
        self.show_page(self.page_name or "dashboard")

    def toggle_language(self) -> None:
        self.set_language(next_lang(self.lang))

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
        from .tour import PasswordGate
        PasswordGate(self, self)

    # ------------------------------------------------------------------ helpers

    def t(self, key: str, **kwargs) -> str:
        return t(key, self.lang, **kwargs)

    def toast(self, message: str, kind: str = "info") -> None:
        """Small transient status popup (bottom-right)."""
        color = {"info": config.COLOR_ACCENT, "ok": config.COLOR_GREEN,
                 "warn": config.COLOR_ORANGE, "err": config.COLOR_RED}.get(kind,
                                                                           config.COLOR_ACCENT)
        popup = ctk.CTkToplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        frame = ctk.CTkFrame(popup, fg_color=config.COLOR_BG_2, corner_radius=10,
                             border_width=1, border_color=color)
        frame.pack(padx=2, pady=2)
        ctk.CTkLabel(frame, text=message, font=F(12), text_color=color,
                     wraplength=380, justify="left").pack(padx=16, pady=10)
        x = self.winfo_rootx() + self.winfo_width() - 420
        y = self.winfo_rooty() + self.winfo_height() - 110
        popup.geometry(f"+{max(10, x)}+{max(10, y)}")
        popup.after(3200, popup.destroy)

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
