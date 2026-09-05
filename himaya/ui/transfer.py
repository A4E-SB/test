"""
Import / Export page (USB sharing): .hma blacklist exchange, orders
CSV/Excel export, CSV import.
"""

from __future__ import annotations

from datetime import date
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import config
from ..models import blacklist as blacklist_model
from ..services import hma
from .widgets import F, make_tree
from .widgets import card as surface


class TransferPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=app.t("tr_title"), font=F(22, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 2))

        # ---- .hma blacklist (hero card: flagship offline feature) -------------
        hma_card = ctk.CTkFrame(self, fg_color="#1c2740", corner_radius=12,
                                border_width=1, border_color=config.COLOR_ACCENT)
        hma_card.grid(row=1, column=0, sticky="ew", padx=16, pady=6)
        hma_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hma_card, text="🔌 🔐 .hma", font=F(18, "bold"),
                     text_color=config.COLOR_ACCENT,
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        ctk.CTkLabel(hma_card, text=app.t("tr_hma_desc"), font=F(12),
                     text_color=config.COLOR_FG_DIM, anchor="w", justify="left",
                     wraplength=860).grid(row=1, column=0, sticky="ew", padx=14)
        btns = ctk.CTkFrame(hma_card, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 12))
        ctk.CTkButton(btns, text=app.t("tr_export_hma"), height=34,
                      command=self.export_hma).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns, text=app.t("tr_import_hma"), height=34,
                      fg_color=config.COLOR_ORANGE, hover_color="#d35400",
                      command=self.import_hma).pack(side="left")

        # ---- blacklist table -------------------------------------------------------
        bl_card = surface(self)
        bl_card.grid(row=2, column=0, sticky="nsew", padx=16, pady=6)
        bl_card.grid_columnconfigure(0, weight=1)
        bl_card.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1, minsize=240)
        ctk.CTkLabel(bl_card, text=self.app.t("reason_blacklisted") + " — "
                     + str(blacklist_model.count(app.db)), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        # icon legend: what the per-row severity icons mean (v1.2)
        ctk.CTkLabel(bl_card, text=self.app.t("tr_legend"), font=F(10),
                     text_color=config.COLOR_FG_DIM, anchor="w"
                     ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 2))
        cols = [("phone", app.t("phone"), 130),
                ("reason", app.t("cust_blacklist_prompt"), 380),
                ("severity", app.t("tr_severity"), 110),
                ("date", app.t("date"), 110)]
        self.tree = make_tree(bl_card, cols, height=9)
        self.tree.grid(row=2, column=0, sticky="nsew", padx=10, pady=(2, 6))
        bl_card.grid_rowconfigure(2, weight=1)
        ctk.CTkButton(bl_card, text=app.t("delete"), height=28, width=100,
                      fg_color=config.COLOR_RED, hover_color="#c0392b",
                      command=self.remove_selected).grid(row=2, column=0,
                                                         sticky="e", padx=10, pady=(0, 10))

        # ---- orders import/export ----------------------------------------------------
        io_card = surface(self)
        io_card.grid(row=3, column=0, sticky="ew", padx=16, pady=(6, 16))
        ctk.CTkLabel(io_card, text=app.t("tr_orders_export"), font=F(16, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        btns2 = ctk.CTkFrame(io_card, fg_color="transparent")
        btns2.grid(row=1, column=0, sticky="ew", padx=14, pady=(4, 12))
        ctk.CTkButton(btns2, text=app.t("rep_export_csv"), height=34,
                      command=self.export_orders_csv).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btns2, text=app.t("rep_export_xlsx"), height=34,
                      command=self.export_orders_xlsx).pack(side="left", padx=8)
        ctk.CTkButton(btns2, text=app.t("tr_orders_import"), height=34,
                      fg_color=config.COLOR_ORANGE, hover_color="#d35400",
                      command=self.import_orders).pack(side="left", padx=8)

        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        db = self.app.db
        self.tree.delete(*self.tree.get_children())
        for e in blacklist_model.all_entries(db):
            sev_txt = {1: "⚠️", 2: "🚨", 3: "🚨🚨"}.get(e["severity"], "🚨")
            self.tree.insert("", "end", iid=str(e["id"]),
                             values=(e["phone"], e["reason"], sev_txt, e["reported_date"]),
                             tags=("danger" if e["severity"] >= 2 else "caution",))

    def remove_selected(self) -> None:
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Himaya", self.app.t("delete_confirm")):
            for iid in sel:
                blacklist_model.remove(self.app.db, int(iid))
            self.refresh()

    # ------------------------------------------------------------------

    def export_hma(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), defaultextension=".hma",
            filetypes=[("Himaya Blacklist", "*.hma")],
            initialfile=f"blacklist_{date.today():%Y%m%d}.hma")
        if not path:
            return
        res = hma.export_blacklist(self.app.db, path)
        self.app.toast(self.app.t("tr_hma_exported", n=res["count"],
                                  path=res["path"]), "ok")

    def import_hma(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(), filetypes=[("Himaya Blacklist", "*.hma"),
                                                     ("All", "*.*")])
        if not path:
            return
        try:
            res = hma.import_blacklist(self.app.db, path)
        except ValueError:
            self.app.toast(self.app.t("tr_not_hma"), "err")
            return
        res.setdefault("hashes", 0)
        self.app.toast(self.app.t("tr_hma_imported", **res), "ok")
        self.refresh()

    def export_orders_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"himaya_commandes_{date.today():%Y%m%d}.csv")
        if path:
            n = hma.export_orders_csv(self.app.db, path)
            self.app.toast(self.app.t("rep_exported", path=f"{path} ({n})"), "ok")

    def export_orders_xlsx(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"himaya_commandes_{date.today():%Y%m%d}.xlsx")
        if path:
            n = hma.export_orders_excel(self.app.db, path)
            self.app.toast(self.app.t("rep_exported", path=f"{path} ({n})"), "ok")

    def import_orders(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(), filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            res = hma.import_orders_csv(self.app.db, path)
        except Exception as e:
            self.app.toast(f"{self.app.t('error')}: {e}", "err")
            return
        self.app.toast(self.app.t("tr_orders_imported", **res), "ok")
