"""
Financial reports page: period summary cards, loss breakdown table,
export to CSV/Excel. Everything computed locally from the orders table.
"""

from __future__ import annotations

from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from .. import config
from ..i18n import t, month_name
from ..services import hma, reports
from .widgets import F, StatCard, make_tree


class ReportsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text=app.t("rep_title"), font=F(22, "bold"),
                     anchor="w").grid(row=0, column=0, columnspan=4, sticky="ew",
                                      padx=16, pady=(10, 2))

        # ---- period selector ---------------------------------------------------
        bar = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        bar.grid(row=1, column=0, columnspan=4, sticky="ew", padx=16, pady=(4, 8))
        self.month_menu = ctk.CTkOptionMenu(
            bar, width=140, values=[month_name(m, app.lang) for m in range(1, 13)],
            command=lambda _v: self.refresh())
        self.month_menu.set(month_name(date.today().month, app.lang))
        self.year_menu = ctk.CTkOptionMenu(
            bar, width=100,
            values=[str(y) for y in range(date.today().year - 4, date.today().year + 2)],
            command=lambda _v: self.refresh())
        self.year_menu.set(str(date.today().year))
        ctk.CTkLabel(bar, text=app.t("rep_month"), font=F(12)).pack(side="left", padx=(12, 4), pady=8)
        self.month_menu.pack(side="left", padx=4, pady=8)
        ctk.CTkLabel(bar, text=app.t("rep_year"), font=F(12)).pack(side="left", padx=(12, 4))
        self.year_menu.pack(side="left", padx=4)
        ctk.CTkButton(bar, text=app.t("rep_export_csv"), height=30,
                      command=self.export_csv).pack(side="right", padx=(4, 12))
        ctk.CTkButton(bar, text=app.t("rep_export_xlsx"), height=30,
                      command=self.export_xlsx).pack(side="right", padx=4)

        # ---- summary cards --------------------------------------------------------
        self.c_revenue = StatCard(self, app.t("rep_revenue"), color=config.COLOR_GREEN)
        self.c_pending = StatCard(self, app.t("rep_pending_rev"), color=config.COLOR_ACCENT)
        self.c_profit = StatCard(self, app.t("rep_profit"), color=config.COLOR_GREEN)
        self.c_losses = StatCard(self, app.t("rep_losses"), color=config.COLOR_RED)
        for i, card in enumerate([self.c_revenue, self.c_pending, self.c_profit,
                                  self.c_losses]):
            card.grid(row=3, column=i, sticky="nsew", padx=6, pady=4)

        self.c_costs = StatCard(self, app.t("rep_costs"), color=config.COLOR_ORANGE)
        self.c_saved = StatCard(self, app.t("rep_saved"), color=config.COLOR_GREEN)
        self.c_completion = StatCard(self, app.t("rep_completion"), color=config.COLOR_ACCENT)
        self.c_orders = StatCard(self, app.t("rep_orders"), color=config.COLOR_FG_DIM)
        for i, card in enumerate([self.c_costs, self.c_saved, self.c_completion,
                                  self.c_orders]):
            card.grid(row=4, column=i, sticky="nsew", padx=6, pady=4)

        # ---- loss breakdown ----------------------------------------------------------
        bd = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        bd.grid(row=5, column=0, columnspan=4, sticky="nsew", padx=16, pady=(8, 16))
        bd.grid_columnconfigure(0, weight=1)
        bd.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(bd, text=app.t("rep_breakdown"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        cols = [("status", app.t("status"), 220), ("count", app.t("rep_orders"), 140),
                ("amount", app.t("amount"), 180)]
        self.tree = make_tree(bd, cols, height=6)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 12))

        self.grid_rowconfigure(5, weight=1)
        self.refresh()

    # ------------------------------------------------------------------

    def _selected_month(self) -> tuple[int, int]:
        lang = self.app.lang
        for m in range(1, 13):
            if self.month_menu.get() == month_name(m, lang):
                return m, int(self.year_menu.get())
        return date.today().month, date.today().year

    def refresh(self) -> None:
        db, lang = self.app.db, self.app.lang
        m, y = self._selected_month()
        s = reports.monthly_summary(db, y, m)
        self.c_revenue.set(config.fmt_money(s["revenue"], lang))
        self.c_pending.set(config.fmt_money(s["pending_revenue"], lang))
        self.c_profit.set(config.fmt_money(s["profit"], lang))
        self.c_losses.set(config.fmt_money(s["losses"], lang))
        self.c_costs.set(config.fmt_money(s["costs"], lang))
        self.c_saved.set(config.fmt_money(s["saved"], lang))
        self.c_completion.set(f"{s['completion']:.0f}%")
        self.c_orders.set(str(s["orders"]))

        self.tree.delete(*self.tree.get_children())
        f, tt = s["from"], s["to"]
        for status, data in reports.loss_breakdown(db, f, tt).items():
            if status == "total":
                continue
            if data["count"] == 0:
                continue
            self.tree.insert("", "end", values=(
                t(f"st_{status}", lang), data["count"],
                config.fmt_money(data["amount"], lang)),
                tags=("danger" if status == "fake_payment" else "caution",))
        total = reports.loss_breakdown(db, f, tt)["total"]
        if total["count"]:
            self.tree.insert("", "end", values=(
                self.app.t("total"), total["count"],
                config.fmt_money(total["amount"], lang)), tags=("danger",))

    # ------------------------------------------------------------------

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"himaya_commandes_{date.today().isoformat()}.csv")
        if path:
            n = hma.export_orders_csv(self.app.db, path)
            self.app.toast(self.app.t("rep_exported", path=f"{path} ({n})"), "ok")

    def export_xlsx(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(), defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"himaya_commandes_{date.today().isoformat()}.xlsx")
        if path:
            n = hma.export_orders_excel(self.app.db, path)
            self.app.toast(self.app.t("rep_exported", path=f"{path} ({n})"), "ok")
