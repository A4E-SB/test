"""
Delivery label page: pick orders, generate a printable PDF (A6 / 100x100)
with risk level and warnings, open the folder for printing.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date

import customtkinter as ctk

from .. import config
from ..models import orders as orders_model
from ..services import labels as labels_service
from .widgets import (F, make_tree, row_tag, status_badge_text,
                      trust_badge_text)
from .widgets import bind_tree_tooltips, card as surface


def generate_and_open(app, order_ids: list[int]) -> str:
    """Shared helper (also used by the Orders page print button)."""
    out = config.DATA_DIR / f"labels_{date.today():%Y%m%d_%H%M%S}.pdf"
    labels_service.generate_labels(app.db, order_ids, out, lang=app.lang)
    app.toast(app.t("lb_generated", path=str(out)), "ok")
    _open_folder(out)
    return str(out)


def _open_folder(path) -> None:
    try:
        if sys.platform == "win32":
            os.startfile(str(path), "open")  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])
    except Exception:
        pass


class LabelsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text=app.t("lb_title"), font=F(22, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 2))
        ctk.CTkLabel(self, text=app.t("lb_desc"), font=F(12),
                     text_color=config.COLOR_FG_DIM, anchor="w", justify="left",
                     wraplength=860).grid(row=1, column=0, sticky="ew", padx=16)

        card = surface(self)
        card.grid(row=2, column=0, sticky="nsew", padx=16, pady=(6, 16))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        self.sel_lbl = ctk.CTkLabel(top, text="", font=F(12, "bold"),
                                    text_color=config.COLOR_ACCENT)
        self.sel_lbl.pack(side="left")
        ctk.CTkButton(top, text=app.t("lb_select_pending"), height=30, width=150,
                      command=self.select_confirmed).pack(side="left", padx=8)
        self.size_menu = ctk.CTkOptionMenu(top, width=180, height=30,
                                           values=[app.t("set_a6"), app.t("set_square")])
        from ..models import settings_store
        cur = settings_store.get_setting(app.db, "label_size", "a6")
        self.size_menu.set(app.t("set_a6" if cur == "a6" else "set_square"))
        self.size_menu.pack(side="left", padx=8)
        ctk.CTkButton(top, text=app.t("lb_generate"), height=30, width=140,
                      fg_color=config.COLOR_GREEN, hover_color="#27ae60",
                      command=self.generate).pack(side="right", padx=4)
        ctk.CTkButton(top, text=app.t("lb_open_folder"), height=30, width=130,
                      command=lambda: _open_folder(config.DATA_DIR)).pack(side="right",
                                                                          padx=4)

        cols = [("id", "#", 46), ("date", app.t("date"), 88),
                ("customer", app.t("ord_customer"), 190), ("phone", app.t("phone"), 120),
                ("product", app.t("product"), 170), ("price", app.t("price"), 90),
                ("status", app.t("status"), 110), ("wilaya", app.t("wilaya"), 130),
                ("risk", app.t("cust_trust"), 150)]
        self.tree = make_tree(card, cols, height=15)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 12))
        bind_tree_tooltips(self.tree)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_sel())
        self.refresh()

    def refresh(self) -> None:
        db, lang = self.app.db, self.app.lang
        self.tree.delete(*self.tree.get_children())
        for o in orders_model.list_orders(db, limit=300):
            # v1.2: the SAME trust icon set as Customers (score-based) —
            # previously tag-based here, score-based there
            self.tree.insert("", "end", iid=str(o["id"]), values=(
                o["id"], o["date"], o["customer_name"], o["phone"], o["product"],
                f"{o['price']:,.0f}".replace(",", " "),
                status_badge_text(o["status"], lang),
                o["wilaya"], trust_badge_text(o["trust_score"])),
                tags=(row_tag(o["status"]),))
        self.update_sel()

    def update_sel(self) -> None:
        n = len(self.tree.selection())
        self.sel_lbl.configure(text=self.app.t("lb_selected", n=n))

    def select_confirmed(self) -> None:
        # the status cell holds the badge text ("●  Label") — compare to that
        badge = status_badge_text("confirmed", self.app.lang)
        self.tree.selection_set([iid for iid in self.tree.get_children()
                                 if self.tree.set(iid, "status") == badge])
        self.update_sel()

    def generate(self) -> None:
        ids = [int(i) for i in self.tree.selection()]
        if not ids:
            self.app.toast(self.app.t("det_no_image"), "warn")
            return
        # persist chosen size
        from ..models import settings_store
        size = "a6" if self.size_menu.get() == self.app.t("set_a6") else "square"
        settings_store.set_setting(self.app.db, "label_size", size)
        generate_and_open(self.app, ids)
