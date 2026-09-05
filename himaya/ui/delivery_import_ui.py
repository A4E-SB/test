"""
Delivery statuses import dialog: load a courier CSV/XLSX export
(Yalidine / ZR Express / Maystro) or paste 'phone ; status' lines, then
apply the new statuses to matching orders in bulk.
"""

from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from .. import config
from ..services import delivery_import
from .widgets import F, center


class ImportStatusesDialog(ctk.CTkToplevel):
    def __init__(self, master, app, on_done=None):
        super().__init__(master)
        self.app = app
        self.on_done = on_done
        self.updates: list[dict] = []
        self.title(app.t("dim_title"))
        self.configure(fg_color=config.COLOR_BG_2)
        self.geometry("640x520")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(self, text=app.t("dim_title"), font=F(17, "bold")).pack(pady=(14, 2))
        ctk.CTkLabel(self, text=app.t("dim_desc"), font=F(11), wraplength=580,
                     justify="left", text_color=config.COLOR_FG_DIM).pack(padx=20)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=8)
        ctk.CTkButton(row, text=app.t("dim_file"), width=170,
                      command=self.choose_file).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(row, text=app.t("dim_or_paste"), font=F(12)
                     ).pack(side="left", padx=(0, 8))

        self.paste = ctk.CTkTextbox(self, width=590, height=120)
        self.paste.pack(padx=20)
        self.result_lbl = ctk.CTkLabel(self, text="", font=F(12, "bold"),
                                       text_color=config.COLOR_ACCENT)
        self.result_lbl.pack(pady=6)
        ctk.CTkButton(self, text=app.t("dim_apply"), width=160,
                      fg_color=config.COLOR_GREEN, hover_color="#27ae60",
                      command=self.apply).pack(pady=(2, 12))
        center(self, master)

    # ------------------------------------------------------------------

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, title=self.app.t("dim_file"),
            filetypes=[("CSV / Excel", "*.csv *.xlsx *.xls"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.updates = delivery_import.parse_delivery_file(path)
        except Exception as exc:
            self.app.toast(f"⚠️ {exc}", "err")
            return
        self.result_lbl.configure(
            text=f"✓ {len(self.updates)} lignes — " + self.app.t("dim_apply") + " ?")

    def apply(self) -> None:
        updates = self.updates
        pasted = self.paste.get("1.0", "end").strip()
        if pasted:
            updates = updates + delivery_import.parse_paste(pasted)
        if not updates:
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        res = delivery_import.apply_updates(self.app.db, updates)
        self.result_lbl.configure(
            text=self.app.t("dim_result", **res))
        self.updates = []
        if self.on_done:
            self.on_done()
