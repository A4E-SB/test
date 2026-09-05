"""
Dashboard: today's summary, scam alerts, revenue vs losses chart, quick stats.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import config
from ..models import blacklist, orders
from ..services import reports
from .widgets import (BarChart, CompactStat, F, HeroCard, make_tree,
                      row_tag, section_header, status_badge_text,
                      trust_badge_text)
from .widgets import card as surface


class DashboardPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)
        rtl = app.lang == "ar"

        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=0, columnspan=4, sticky="ew", padx=8, pady=(4, 6))
        ctk.CTkLabel(title_row, text=app.t("nav_dashboard"), font=F(24, "bold"),
                     anchor="e" if rtl else "w",
                     justify="right" if rtl else "left").pack(side="left")
        self.period_labels = {k: app.t(k) for k in
                              ("dash_today", "dash_7d", "dash_30d", "dash_all")}
        self.period = ctk.CTkSegmentedButton(
            title_row, values=list(self.period_labels.values()),
            command=lambda _v: self.refresh())
        self.period.set(self.period_labels["dash_today"])
        self.period.pack(side="right")

        self._period_days = {"dash_today": 0, "dash_7d": 7,
                             "dash_30d": 30, "dash_all": None}

        # ---- v1.5 dense analytics layout --------------------------------------
        # ONE hero number (money saved — the anti-scam promise), then tight
        # labelled clusters. Every figure respects the selected period (the
        # v1.4 dashboard mixed period cards with all-time cards: numbers
        # that didn't match the selector).

        # hero: money protected from scammers this period
        self.hero = HeroCard(self, app.t("dash_money_saved"),
                             color=config.COLOR_GREEN,
                             on_click=lambda: self._goto_orders("blocked"))
        self.hero.grid(row=1, column=0, columnspan=4, sticky="ew",
                       padx=8, pady=(4, 2))

        # cluster: activity --------------------------------------------------
        section_header(self, app.t("sec_activity")).grid(
            row=2, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 0))
        go = self.app.show_page
        self.card_orders = CompactStat(self, app.t("dash_today_new"),
                                       color=config.COLOR_ACCENT,
                                       on_click=lambda: self._goto_orders(""))
        self.card_shipped = CompactStat(self, app.t("dash_today_shipped"),
                                        color=config.COLOR_ACCENT,
                                        on_click=lambda: self._goto_orders("shipped"))
        self.card_delivered = CompactStat(self, app.t("dash_delivered"),
                                          color=config.COLOR_GREEN,
                                          on_click=lambda: self._goto_orders("delivered"))
        self.card_ghosts = CompactStat(self, app.t("dash_today_ghosts"),
                                       color=config.COLOR_RED,
                                       on_click=lambda: self._goto_orders("ghosted"))
        for i, card in enumerate([self.card_orders, self.card_shipped,
                                  self.card_delivered, self.card_ghosts]):
            card.grid(row=3, column=i, sticky="nsew", padx=4, pady=3)

        # cluster: money -----------------------------------------------------
        section_header(self, app.t("sec_money")).grid(
            row=4, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 0))
        self.card_revenue = CompactStat(self, app.t("rep_revenue"),
                                        color=config.COLOR_GREEN)
        self.card_pending = CompactStat(self, app.t("rep_pending_rev"),
                                        color=config.COLOR_ACCENT)
        self.card_lost = CompactStat(self, app.t("dash_total_lost"),
                                     color=config.COLOR_RED,
                                     on_click=lambda: go("reports"))
        self.card_completion = CompactStat(self, app.t("dash_completion"),
                                           color=config.COLOR_GREEN,
                                           on_click=lambda: go("reports"))
        for i, card in enumerate([self.card_revenue, self.card_pending,
                                  self.card_lost, self.card_completion]):
            card.grid(row=5, column=i, sticky="nsew", padx=4, pady=3)

        # ---- chart ------------------------------------------------------------ 
        chart_frame = surface(self)
        chart_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=6, pady=(10, 4))
        chart_frame.grid_columnconfigure(0, weight=1)
        chart_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(chart_frame, text=app.t("dash_chart_title"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        self.chart = BarChart(chart_frame, lang=app.lang, height=230)
        self.chart.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 12))

        # ---- alerts (risk cluster: counts + danger list) ----------------------
        self.alerts = surface(self)
        self.alerts.grid(row=6, column=3, sticky="nsew", padx=6, pady=(10, 4))
        self.alerts.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(self.alerts, text=f"⚠️ {app.t('dash_alerts')}", font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, columnspan=2,
                                      sticky="ew", padx=14, pady=(10, 4))
        self.chip_customers = CompactStat(self.alerts, app.t("dash_customers"),
                                          color=config.COLOR_ACCENT,
                                          on_click=lambda: go("customers"))
        self.chip_customers.grid(row=1, column=0, sticky="nsew", padx=6, pady=2)
        self.chip_blacklist = CompactStat(self.alerts, app.t("dash_blacklist_size"),
                                          color=config.COLOR_RED,
                                          on_click=lambda: go("transfer"))
        self.chip_blacklist.grid(row=1, column=1, sticky="nsew", padx=6, pady=2)
        self.alerts_box = ctk.CTkFrame(self.alerts, fg_color="transparent")
        self.alerts_box.grid(row=2, column=0, columnspan=2, sticky="nsew",
                             padx=10, pady=(2, 10))

        # ---- recent orders ----------------------------------------------------
        recent_frame = surface(self)
        recent_frame.grid(row=7, column=0, columnspan=4, sticky="nsew", padx=6, pady=(4, 12))
        recent_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(recent_frame, text=app.t("dash_recent"), font=F(14, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        cols = [("id", "#", 50), ("date", app.t("date"), 90),
                ("customer", app.t("ord_customer"), 180), ("phone", app.t("phone"), 120),
                ("product", app.t("product"), 160), ("price", app.t("price"), 90),
                ("status", app.t("status"), 110)]
        self.tree = make_tree(recent_frame, cols, height=8)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 12))

        self.grid_rowconfigure(7, weight=1)
        self.refresh()

    # ------------------------------------------------------------------

    def _goto_orders(self, status: str) -> None:
        """Jump to the Orders page and apply a status filter ("" = all)."""
        self.app.show_page("orders")
        page = self.app.page
        if hasattr(page, "filter_status"):
            page.filter_status(status)

    def refresh(self) -> None:
        db, lang = self.app.db, self.app.lang

        # ---- every figure follows the selected period (v1.5 consistency) ----
        sel = "dash_today"
        for key, label in self.period_labels.items():
            if self.period.get() == label:
                sel = key
                break
        days = self._period_days[sel]
        p_label = self.period_labels[sel]

        def n_status(statuses: list[str]) -> int:
            if days is None:
                q = ",".join(f"'{x}'" for x in statuses)
                return db.scalar(
                    f"SELECT COUNT(*) FROM orders WHERE status IN ({q})") or 0
            return orders.count_since(db, days, statuses)

        n_new = (db.scalar("SELECT COUNT(*) FROM orders") or 0) if days is None \
            else orders.count_since(db, days, list(config.ALL_STATUSES))
        n_shipped = n_status(["shipped"])
        n_delivered = n_status(["delivered", "paid"])
        n_ghost = n_status(["ghosted"])
        n_blocked = n_status(["blocked"])

        self.hero.set(config.fmt_money(orders.money_saved(db, days), lang),
                      sub=self.app.t("dash_blocked_n", n=n_blocked)
                          + ("  •  " + p_label if sel != "dash_today" else ""))
        self.card_orders.set(str(n_new))
        self.card_shipped.set(str(n_shipped))
        self.card_delivered.set(str(n_delivered))
        self.card_ghosts.set(str(n_ghost))
        self.card_revenue.set(config.fmt_money(orders.paid_revenue(db, days), lang))
        self.card_pending.set(config.fmt_money(orders.pending_revenue(db, days), lang))
        self.card_lost.set(config.fmt_money(orders.total_lost(db, days), lang))
        self.card_completion.set(f"{orders.completion_rate(db, days):.0f}%")
        self.chip_customers.set(str(db.scalar("SELECT COUNT(*) FROM customers") or 0))
        self.chip_blacklist.set(str(blacklist.count(db)))

        self.chart.set_data(reports.revenue_series(db, months=6))

        # recent orders
        self.tree.delete(*self.tree.get_children())
        for o in orders.list_orders(db, limit=8):
            self.tree.insert("", "end", iid=str(o["id"]), values=(
                o["id"], o["date"], o["customer_name"], o["phone"], o["product"],
                f"{o['price']:,.0f}".replace(",", " "),
                status_badge_text(o["status"], lang)),
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
                         text=f"🚨 {r['name']} — {r['phone']}  •  {trust_badge_text(r['trust_score'])}",
                         text_color=config.COLOR_RED, font=F(12),
                         anchor="w", justify="left").pack(anchor="w", pady=2)
        # low-stock products (v1.1.0 catalog)
        from ..models import products as products_model
        low = products_model.low_stock_products(db)
        if low:
            ctk.CTkLabel(self.alerts_box,
                         text=f"📦 {self.app.t('dash_low_stock')} :",
                         text_color=config.COLOR_ORANGE, font=F(12, "bold"),
                         anchor="w", justify="left").pack(anchor="w", pady=(8, 0))
            for p in low[:4]:
                ctk.CTkLabel(self.alerts_box,
                             text=f"   • {p['name']} : {p['quantity']}",
                             text_color=config.COLOR_ORANGE, font=F(12),
                             anchor="w", justify="left").pack(anchor="w", pady=1)
