"""
Follow-up center ("relances"): orders stuck in confirmed/shipped for too
long. One click copies a polite AR/FR reminder (paste it in Messenger /
WhatsApp) — either the client answers (order saved) or stays silent
(ghost revealed, blacklist candidate).
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import config
from ..i18n import t
from ..models import settings_store
from ..services import relance
from .widgets import F, Debouncer, copy_to_clipboard, make_tree, row_tag
from .widgets import rtl_anchor, rtl_side


class RelancePage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))
        ctk.CTkLabel(top, text=app.t("rel_title"), font=F(22, "bold"),
                 anchor=rtl_anchor(app)).pack(side=rtl_side(app))

        # threshold row
        thr = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        thr.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 6))
        ctk.CTkLabel(thr, text=app.t("rel_desc"), font=F(11),
                     text_color=config.COLOR_FG_DIM, wraplength=760,
                     justify="left").pack(side="left", padx=(12, 8), pady=8)
        ctk.CTkLabel(thr, text=app.t("rel_threshold"), font=F(12)
                     ).pack(side="right", padx=(6, 2))
        self.thr_var = tk.StringVar(value=settings_store.get_setting(
            app.db, "relance_days", "3"))
        self.thr_spin = ctk.CTkEntry(thr, textvariable=self.thr_var, width=46,
                                     height=28)
        self.thr_spin.pack(side="right", padx=(0, 10))
        # debounced + change-guard: re-querying on every keystroke made the
        # field feel heavy while typing
        self._thr_deb = Debouncer(self, 350)
        self._thr_applied = self.thr_var.get()
        self.thr_var.trace_add("write", lambda *_: self._thr_deb.call(
            self._save_threshold))

        # stuck orders list
        list_frame = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(2, 8))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        cols = [("id", "#", 46), ("days", app.t("rel_days"), 90),
                ("date", app.t("date"), 92), ("customer", app.t("ord_customer"), 190),
                ("phone", app.t("phone"), 125), ("product", app.t("product"), 170),
                ("price", app.t("price"), 95), ("status", app.t("status"), 120)]
        self.tree = make_tree(list_frame, cols, height=17)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        bar = ctk.CTkFrame(list_frame, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(bar, text="📢 " + app.t("rel_copy") + " (AR)", height=30,
                      command=lambda: self.copy_reminder("ar")
                      ).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="📢 " + app.t("rel_copy") + " (FR)", height=30,
                      command=lambda: self.copy_reminder("fr")
                      ).pack(side="left", padx=2)
        self.count_lbl = ctk.CTkLabel(bar, text="", font=F(11),
                                      text_color=config.COLOR_FG_DIM)
        self.count_lbl.pack(side="right")
        self.refresh()

    # ------------------------------------------------------------------

    def _save_threshold(self) -> None:
        val = self.thr_var.get().strip()
        if (val.isdigit() and 1 <= int(val) <= 30
                and val != self._thr_applied):
            settings_store.set_setting(self.app.db, "relance_days", val)
            self._thr_applied = val
            self.refresh()

    def _threshold(self) -> int:
        val = self.thr_var.get().strip()
        return int(val) if val.isdigit() and 1 <= int(val) <= 30 else 3

    def refresh(self) -> None:
        db, lang = self.app.db, self.app.lang
        rows = relance.stuck_orders(db, days=self._threshold())
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", iid=str(r["id"]), values=(
                r["id"], r["days_waiting"], r["date"], r["customer_name"],
                r["phone"], r["product"],
                f"{r['price']:,.0f}".replace(",", " "),
                t(f"st_{r['status']}", lang)), tags=(row_tag(r["status"]),))
        self.count_lbl.configure(
            text=self.app.t("rel_none") if not rows else f"{len(rows)} 🔔")

    def _selected(self) -> list[dict]:
        ids = {int(i) for i in self.tree.selection()} or (
            {int(self.tree.focus())} if self.tree.focus() else set())
        rows = relance.stuck_orders(self.app.db, days=self._threshold())
        return [r for r in rows if r["id"] in ids] or rows

    def copy_reminder(self, msg_lang: str) -> None:
        rows = self._selected()
        if not rows:
            self.app.toast(self.app.t("rel_none"), "ok")
            return
        text = "\n\n".join(
            relance.reminder_message(r, msg_lang, self.app.db) for r in rows[:10])
        copy_to_clipboard(self, text)
        self.app.toast(self.app.t("copied"), "ok")
