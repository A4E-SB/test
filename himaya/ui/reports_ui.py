"""
Financial reports page: period summary cards (incl. REAL profit from the
product catalog), order funnel, per-wilaya stats with deposit suggestions,
best customers with loyalty copy, loss breakdown, CSV/Excel export.
Everything computed locally from the orders table.
"""

from __future__ import annotations

from datetime import date
from tkinter import filedialog

import customtkinter as ctk

from .. import config
from ..i18n import month_name
from ..models import templates_store
from ..services import hma, reports, wilaya_stats
from . import widgets as W
from .widgets import (CompactStat, F, FunnelChart, HBarChart,
                      copy_to_clipboard, make_tree, section_header,
                      trust_badge_text)
from .widgets import card as surface


class ReportsPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(self, text=app.t("rep_title"), font=F(21, "extrabold"),
                     anchor=W.rtl_anchor(app)).grid(row=0, column=0, columnspan=4,
                                                    sticky="ew", padx=16, pady=(10, 2))

        # ---- period selector ---------------------------------------------------
        bar = surface(self)
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

        # ---- v1.5 dense clusters: MONEY (the P&L row) then HEALTH -----------
        section_header(self, app.t("sec_money")).grid(
            row=3, column=0, columnspan=4, sticky="w", padx=18, pady=(8, 0))
        self.c_revenue = CompactStat(self, app.t("rep_revenue"),
                                     color=config.COLOR_GREEN)
        self.c_costs = CompactStat(self, app.t("rep_costs"),
                                   color=config.COLOR_ORANGE)
        self.c_profit = CompactStat(self, app.t("rep_profit"),
                                    color=config.COLOR_GREEN)
        self.c_real = CompactStat(self, app.t("prod_real_profit"),
                                  color=config.COLOR_GREEN)
        for i, card in enumerate([self.c_revenue, self.c_costs, self.c_profit,
                                  self.c_real]):
            card.grid(row=4, column=i, sticky="nsew", padx=4, pady=3)

        section_header(self, app.t("sec_health")).grid(
            row=5, column=0, columnspan=4, sticky="w", padx=18, pady=(8, 0))
        self.c_pending = CompactStat(self, app.t("rep_pending_rev"),
                                     color=config.COLOR_ACCENT)
        self.c_losses = CompactStat(self, app.t("rep_losses"),
                                    color=config.COLOR_RED)
        self.c_completion = CompactStat(self, app.t("rep_completion"),
                                        color=config.COLOR_ACCENT)
        self.c_orders = CompactStat(self, app.t("rep_orders"),
                                    color=config.COLOR_ACCENT)
        for i, card in enumerate([self.c_pending, self.c_losses,
                                  self.c_completion, self.c_orders]):
            card.grid(row=6, column=i, sticky="nsew", padx=4, pady=3)

        # ---- funnel + loss bars (v1.5: the old near-empty loss table became
        #      a proportional bar list — shares read at a glance) --------------
        fun = surface(self)
        fun.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=6, pady=(8, 4))
        fun.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(fun, text=app.t("fun_title"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        self.funnel = FunnelChart(fun, lang=app.lang, height=230)
        self.funnel.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 12))

        bd = surface(self)
        bd.grid(row=7, column=2, columnspan=2, sticky="nsew", padx=6, pady=(8, 4))
        bd.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(bd, text=app.t("rep_breakdown"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        self.loss_bars = HBarChart(bd)
        self.loss_bars.grid(row=1, column=0, sticky="ew", padx=14, pady=(2, 12))

        bc = surface(self)
        bc.grid(row=8, column=0, columnspan=4, sticky="nsew", padx=6, pady=4)
        bc.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(bc, text="🏅 " + app.t("bc_title"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        self.bc_box = ctk.CTkFrame(bc, fg_color="transparent")
        self.bc_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 12))

        # ---- wilaya stats ------------------------------------------------------------
        wst = surface(self)
        # full width: the 7 columns need it (columnspan=2 clipped the last
        # ones -> "Total lost (sca…" v1.2 bug)
        wst.grid(row=9, column=0, columnspan=4, sticky="nsew", padx=6, pady=4)
        wst.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(wst, text=app.t("wst_title"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        wcols = [("wilaya", app.t("wilaya"), 170), ("orders", app.t("rep_orders"), 80),
                 ("delivered", app.t("st_delivered"), 95), ("bad", app.t("wst_bad"), 80),
                 ("rate", app.t("wst_rate"), 95), ("lost", app.t("dash_total_lost"), 115),
                 ("adv", "", 230)]
        self.wtree = make_tree(wst, wcols, height=6)
        self.wtree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 12))
        W.bind_tree_tooltips(self.wtree)

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
        self.c_revenue.set(config.fmt_money(s["revenue"], lang),
                           sub=self.app.t("dep_received_lbl") + " : "
                               + config.fmt_money(s["deposits"], lang))
        self.c_pending.set(config.fmt_money(s["pending_revenue"], lang))
        # v1.5: real profit is a first-class card, not a sub-label
        self.c_profit.set(config.fmt_money(s["profit"], lang),
                          sub=self.app.t("rep_margin") + " : "
                              + (f"{s['profit'] / s['revenue'] * 100:.0f}%"
                                 if s["revenue"] else "—"))
        self.c_real.set(config.fmt_money(s["real_profit"], lang))
        self.c_losses.set(config.fmt_money(s["losses"], lang),
                          sub="🛡️ " + self.app.t("rep_saved") + " : "
                              + config.fmt_money(s["saved"], lang))
        self.c_costs.set(
            config.fmt_money(s["costs"] + s.get("product_costs", 0), lang),
            sub="🚚 " + config.fmt_money(s["costs"], lang)
                + "  •  📦 " + config.fmt_money(s.get("product_costs", 0), lang))
        self.c_completion.set(f"{s['completion']:.0f}%")
        self.c_orders.set(str(s["orders"]))

        # funnel
        self.funnel.set_data(wilaya_stats.funnel(db)["stages"])

        # best customers + loyalty copy
        for w in self.bc_box.winfo_children():
            w.destroy()
        for c in wilaya_stats.best_customers(db, limit=5):
            row = ctk.CTkFrame(self.bc_box, fg_color="transparent")
            row.pack(fill="x", pady=3)
            row.grid_columnconfigure(0, weight=1)
            stars = "★" * min(5, max(1, c["bought"]))
            # line 1: name (wraps alone — v1.2 clipped it to "Ami"); copy btn
            ctk.CTkLabel(row, text=f"{stars} {c['name']}",
                         font=F(12, "bold"), anchor="w", wraplength=250,
                         justify="left").grid(row=0, column=0, sticky="w")
            ctk.CTkButton(row, text="📋", width=34, height=26,
                          fg_color=config.COLOR_BG_3, hover_color=config.COLOR_BG,
                          command=lambda cc=c: self.copy_loyalty(cc)
                          ).grid(row=0, column=1, rowspan=2, sticky="e", padx=(6, 0))
            # line 2: FULL phone (never truncated) + trust + stats
            ctk.CTkLabel(row, text=f"{c['phone']}  •  "
                                   f"{trust_badge_text(c['trust_score'])}  •  "
                                   f"{c['bought']} {self.app.t('bc_bought')} • "
                                   f"{config.fmt_money(c['revenue'], lang)}",
                         font=F(11), text_color=config.COLOR_FG_DIM, anchor="w"
                         ).grid(row=1, column=0, sticky="w")

        # wilaya stats
        self.wtree.delete(*self.wtree.get_children())
        for w in wilaya_stats.wilaya_stats(db)[:12]:
            self.wtree.insert("", "end", values=(
                w["wilaya"], w["orders"], w["delivered"], w["bad"],
                f"{w['ghost_rate']:.0f}%", config.fmt_money(w["lost"], lang),
                self.app.t("wst_suggest") if w["suggest_deposit"] else ""),
                tags=("danger",) if w["suggest_deposit"] else ())

        # loss breakdown as proportional bars (computed ONCE)
        f, tt = s["from"], s["to"]
        breakdown = reports.loss_breakdown(db, f, tt)
        bars = []
        for status, data in breakdown.items():
            if status == "total" or data["count"] == 0:
                continue
            bars.append((f"{W.status_badge_text(status, lang)}  ×{data['count']}",
                         data["amount"],
                         config.STATUS_COLORS.get(status, config.COLOR_RED)))
        self.loss_bars.set_data(bars)

    # ------------------------------------------------------------------

    def copy_loyalty(self, customer: dict) -> None:
        """Copy a loyalty message (first 'loyalty' template) for a top client."""
        db, lang = self.app.db, self.app.lang
        rows = templates_store.by_category(db, "loyalty")
        if not rows:
            return
        tpl = rows[0]
        text = tpl["text_ar"] if lang == "ar" else tpl["text_fr"]
        last = db.query_one(
            "SELECT product FROM orders WHERE customer_id = ? "
            "ORDER BY id DESC LIMIT 1", (customer["id"],))
        msg = text.format(name=customer["name"], count=customer["bought"],
                          last_product=last["product"] if last else "—")
        copy_to_clipboard(self, msg)
        self.app.toast(self.app.t("copied"), "ok")

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
