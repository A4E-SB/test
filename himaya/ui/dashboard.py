"""
Dashboard: today's summary, scam alerts, revenue vs losses chart, quick stats.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import config
from ..i18n import t
from ..models import blacklist, orders
from ..services import reports
from .widgets import BarChart, F, StatCard, make_tree, row_tag


class DashboardPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        rtl = app.lang == "ar"

        title = ctk.CTkLabel(self, text=app.t("nav_dashboard"), font=F(24, "bold"),
                             anchor="e" if rtl else "w", justify="right" if rtl else "left")
        title.grid(row=0, column=0, columnspan=4, sticky="ew", padx=8, pady=(4, 10))

        # ---- stat cards -------------------------------------------------------
        self.card_orders = StatCard(self, app.t("dash_today_new"), color=config.COLOR_ACCENT)
        self.card_shipped = StatCard(self, app.t("dash_today_shipped"), color="#8e7cc3")
        self.card_ghosts = StatCard(self, app.t("dash_today_ghosts"), color=config.COLOR_RED)
        self.card_saved = StatCard(self, app.t("dash_money_saved"), color=config.COLOR_GREEN)
        for i, card in enumerate([self.card_orders, self.card_shipped,
                                  self.card_ghosts, self.card_saved]):
            card.grid(row=1, column=i, sticky="nsew", padx=6, pady=4)

        self.card_completion = StatCard(self, app.t("dash_completion"),
                                        color=config.COLOR_GREEN)
        self.card_lost = StatCard(self, app.t("dash_total_lost"), color=config.COLOR_RED)
        self.card_customers = StatCard(self, app.t("dash_customers"),
                                       color=config.COLOR_ACCENT)
        self.card_blacklist = StatCard(self, app.t("dash_blacklist_size"),
                                       color=config.COLOR_ORANGE)
        for i, card in enumerate([self.card_completion, self.card_lost,
                                  self.card_customers, self.card_blacklist]):
            card.grid(row=2, column=i, sticky="nsew", padx=6, pady=4)

        # ---- chart ------------------------------------------------------------
        chart_frame = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        chart_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=6, pady=10)
        chart_frame.grid_columnconfigure(0, weight=1)
        chart_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(chart_frame, text=app.t("dash_chart_title"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        self.chart = BarChart(chart_frame, lang=app.lang, height=250)
        self.chart.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 12))

        # ---- alerts -----------------------------------------------------------
        self.alerts = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        self.alerts.grid(row=3, column=3, sticky="nsew", padx=6, pady=10)
        self.alerts.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.alerts, text=f"⚠️ {app.t('dash_alerts')}", font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        self.alerts_box = ctk.CTkFrame(self.alerts, fg_color="transparent")
        self.alerts_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # ---- recent orders ----------------------------------------------------
        recent_frame = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        recent_frame.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=6, pady=(0, 12))
        recent_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(recent_frame, text=app.t("dash_recent"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        cols = [("id", "#", 50), ("date", app.t("date"), 90),
                ("customer", app.t("ord_customer"), 180), ("phone", app.t("phone"), 120),
                ("product", app.t("product"), 160), ("price", app.t("price"), 90),
                ("status", app.t("status"), 110)]
        self.tree = make_tree(recent_frame, cols, height=8)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 12))

        self.grid_rowconfigure(4, weight=1)
        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        db, lang = self.app.db, self.app.lang
        self.card_orders.set(str(orders.count_today(db)))
        self.card_shipped.set(str(orders.shipped_today(db)))
        self.card_ghosts.set(str(orders.count_today(db, "ghosted")))
        self.card_saved.set(config.fmt_money(orders.money_saved(db), lang))
        self.card_completion.set(f"{orders.completion_rate(db):.0f}%")
        self.card_lost.set(config.fmt_money(orders.total_lost(db), lang))
        self.card_customers.set(str(db.scalar("SELECT COUNT(*) FROM customers") or 0))
        self.card_blacklist.set(str(blacklist.count(db)))

        self.chart.set_data(reports.revenue_series(db, months=6))

        # recent orders
        self.tree.delete(*self.tree.get_children())
        for o in orders.list_orders(db, limit=8):
            status_txt = t(f"st_{o['status']}", lang)
            self.tree.insert("", "end", iid=str(o["id"]), values=(
                o["id"], o["date"], o["customer_name"], o["phone"], o["product"],
                f"{o['price']:,.0f}".replace(",", " "), status_txt),
                tags=(row_tag(o["status"]),))

        # alerts: dangerous customers + blacklist size warning
        for w in self.alerts_box.winfo_children():
            w.destroy()
        rows = db.query(
            "SELECT name, phone, tags, trust_score FROM customers "
            "WHERE (',' || tags || ',') LIKE '%,scammer,%' OR trust_score < 25 "
            "ORDER BY trust_score ASC LIMIT 5")
        if not rows:
            ctk.CTkLabel(self.alerts_box, text=self.app.t("dash_no_alerts"),
                         text_color=config.COLOR_GREEN, font=F(12),
                         anchor="w", justify="left").pack(anchor="w", pady=2)
        for r in rows:
            ctk.CTkLabel(self.alerts_box,
                         text=f"🚨 {r['name']} — {r['phone']} ({r['trust_score']}/100)",
                         text_color=config.COLOR_RED, font=F(12),
                         anchor="w", justify="left").pack(anchor="w", pady=2)
