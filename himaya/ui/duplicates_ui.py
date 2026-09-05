"""
Duplicates dialog: spots the same person behind several phone numbers
(similar name + same wilaya or similar address). One click merges the
profiles — orders and inquiries move to the kept customer.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import config
from ..services import duplicates
from .widgets import F, HimayaDialog, center, fit_geometry


class DuplicatesDialog(HimayaDialog):
    def __init__(self, master, app, on_merged=None):
        super().__init__(master)
        self.app = app
        self.on_merged = on_merged
        self.title(app.t("dup_title"))
        self.configure(fg_color=config.COLOR_BG_2)
        fit_geometry(self, 700, 520)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        ctk.CTkLabel(self, text="👥 " + app.t("dup_title"), font=F(17, "bold")
                     ).pack(pady=(14, 2))
        ctk.CTkLabel(self, text=app.t("dup_hint"), font=F(11), wraplength=640,
                     justify="left", text_color=config.COLOR_FG_DIM).pack(padx=20,
                                                                         pady=(0, 8))
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                           height=380)
        self.body.pack(fill="both", expand=True, padx=12, pady=4)
        self.render_groups()
        center(self, master)

    # ------------------------------------------------------------------

    def render_groups(self) -> None:
        app = self.app
        for w in self.body.winfo_children():
            w.destroy()
        groups = duplicates.duplicate_groups(app.db)
        if not groups:
            ctk.CTkLabel(self.body, text=app.t("dup_none"), font=F(14),
                         text_color=config.COLOR_GREEN).pack(pady=40)
            return
        for g in groups:
            card = ctk.CTkFrame(self.body, fg_color=config.COLOR_BG, corner_radius=10)
            card.pack(fill="x", pady=6, padx=4)
            members = [g["main"]] + g["dupes"]
            for i, m in enumerate(members):
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=(8 if i == 0 else 0, 0))
                txt = (f"{'🥇' if i == 0 else '  '} {m['name']} — {m['phone']} "
                       f"({m['wilaya'] or '—'})")
                ctk.CTkLabel(row, text=txt, font=F(12), anchor="w").pack(
                    side="left", pady=2)
                if i > 0:   # merge INTO the first (oldest) profile
                    ctk.CTkButton(
                        row, text=app.t("dup_merge"), width=100, height=26,
                        fg_color=config.COLOR_ACCENT,
                        command=lambda a=g["main"]["id"], b=m["id"]:
                            self.merge(a, b)).pack(side="right", padx=4)
            ctk.CTkLabel(card, text="↳ " + app.t("dup_merge") + " : " +
                         g["main"]["name"], font=F(10),
                         text_color=config.COLOR_FG_DIM, anchor="w"
                         ).pack(fill="x", padx=(34, 10), pady=(0, 8))

    def merge(self, keep_id: int, remove_id: int) -> None:
        duplicates.merge(self.app.db, keep_id, remove_id)
        self.app.toast(self.app.t("dup_merged"), "ok")
        self.render_groups()
        if self.on_merged:
            self.on_merged()
