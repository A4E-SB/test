"""
Settings page: language, CCP/BaridiMob info (used by reply templates),
delivery defaults, label size, tesseract path, backup/restore, wilaya list.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import config
from ..models import settings_store
from ..services import backup
from .widgets import F


class SettingsPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=app.t("set_title"), font=F(22, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))

        db = app.db

        # ---- language ------------------------------------------------------
        lang_card = self._card(1)
        ctk.CTkLabel(lang_card, text=app.t("set_language"), font=F(14, "bold"),
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        row = ctk.CTkFrame(lang_card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))
        self.lang_var = tk.StringVar(value=("Français" if app.lang == "fr" else "العربية"))
        ctk.CTkSegmentedButton(row, values=["Français", "العربية"],
                               variable=self.lang_var,
                               command=self.change_language).pack(side="left")

        # ---- general defaults ---------------------------------------------
        gen = self._card(2)
        ctk.CTkLabel(gen, text=app.t("set_general"), font=F(14, "bold"),
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        self.e_delivery = self._combo(gen, app.t("set_default_delivery"),
                                      config.DELIVERY_COMPANIES,
                                      settings_store.get_setting(db, "default_delivery"))
        self.e_shipping = self._entry(gen, app.t("set_default_shipping"),
                                      settings_store.get_setting(db, "default_shipping_cost"))
        self.e_tesseract = self._entry(gen, app.t("set_tesseract"),
                                       settings_store.get_setting(db, "tesseract_path"))
        size_row = ctk.CTkFrame(gen, fg_color="transparent")
        size_row.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(size_row, text=app.t("set_label_size"), font=F(12)).pack(side="left",
                                                                              padx=(0, 8))
        self.size_menu = ctk.CTkOptionMenu(size_row, width=190,
                                           values=[app.t("set_a6"), app.t("set_square")])
        cur = settings_store.get_setting(db, "label_size", "a6")
        self.size_menu.set(app.t("set_a6" if cur == "a6" else "set_square"))
        self.size_menu.pack(side="left")
        ctk.CTkLabel(gen, text=app.t("set_wilayas"), text_color=config.COLOR_GREEN,
                     font=F(12)).pack(anchor="w", padx=14, pady=(6, 2))

        # ---- CCP / BaridiMob ------------------------------------------------
        ccp = self._card(3)
        ctk.CTkLabel(ccp, text=app.t("set_ccp_title"), font=F(14, "bold"),
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        self.e_ccp = self._entry(ccp, app.t("set_ccp_number"),
                                 settings_store.get_setting(db, "ccp_number"))
        self.e_ccp_name = self._entry(ccp, app.t("set_ccp_name"),
                                      settings_store.get_setting(db, "ccp_name"))
        self.e_rip = self._entry(ccp, app.t("set_rip"),
                                 settings_store.get_setting(db, "baridimob_rip"))
        self.e_bm = self._entry(ccp, app.t("set_bm_phone"),
                                settings_store.get_setting(db, "baridimob_phone"))

        ctk.CTkButton(self, text=app.t("save"), width=140,
                      command=self.save).grid(row=4, column=0, sticky="w", padx=16, pady=6)

        # ---- data / backup ------------------------------------------------------
        data = self._card(5)
        ctk.CTkLabel(data, text=app.t("set_data"), font=F(14, "bold"),
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        ctk.CTkLabel(data, text=f"{app.t('set_db_path')} : {config.DB_PATH}",
                     font=F(11), text_color=config.COLOR_FG_DIM, anchor="w",
                     wraplength=820).pack(fill="x", padx=14, pady=2)
        brow = ctk.CTkFrame(data, fg_color="transparent")
        brow.pack(fill="x", padx=14, pady=(4, 10))
        ctk.CTkButton(brow, text=app.t("set_backup_now"), height=32,
                      command=self.do_backup).pack(side="left", padx=(0, 8))
        ctk.CTkButton(brow, text=app.t("set_restore"), height=32, fg_color=config.COLOR_ORANGE,
                      hover_color="#d35400", command=self.do_restore).pack(side="left")

    # ------------------------------------------------------------------ helpers

    def _card(self, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", padx=16, pady=6)
        card.grid_columnconfigure(0, weight=1)
        return card

    def _entry(self, parent, label: str, value: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=F(12), anchor="w").pack(
            fill="x", padx=14, pady=(4, 0))
        var = tk.StringVar(value=value or "")
        ent = ctk.CTkEntry(parent, textvariable=var, width=420)
        ent.pack(padx=14, anchor="w")
        ent._himaya_var = var
        return ent

    def _combo(self, parent, label: str, values: list[str], value: str) -> ctk.CTkComboBox:
        ctk.CTkLabel(parent, text=label, font=F(12), anchor="w").pack(
            fill="x", padx=14, pady=(4, 0))
        combo = ctk.CTkComboBox(parent, values=values, width=220)
        combo.set(value or (values[0] if values else ""))
        combo.pack(padx=14, anchor="w")
        return combo

    # ------------------------------------------------------------------ actions

    def change_language(self, value: str) -> None:
        lang = "ar" if value == "العربية" else "fr"
        settings_store.set_setting(self.app.db, "language", lang)
        self.app.set_language(lang)

    def save(self) -> None:
        db = self.app.db
        settings_store.set_setting(db, "default_delivery", self.e_delivery.get())
        settings_store.set_setting(db, "default_shipping_cost",
                                   self.e_shipping._himaya_var.get().strip() or "600")
        settings_store.set_setting(db, "tesseract_path", self.e_tesseract._himaya_var.get().strip())
        settings_store.set_setting(db, "ccp_number", self.e_ccp._himaya_var.get().strip())
        settings_store.set_setting(db, "ccp_name", self.e_ccp_name._himaya_var.get().strip())
        settings_store.set_setting(db, "baridimob_rip", self.e_rip._himaya_var.get().strip())
        settings_store.set_setting(db, "baridimob_phone", self.e_bm._himaya_var.get().strip())
        settings_store.set_setting(db, "label_size",
                                   "a6" if self.size_menu.get() == self.app.t("set_a6")
                                   else "square")
        self.app.toast(self.app.t("set_saved"), "ok")

    def do_backup(self) -> None:
        path = backup.backup(self.app.db)
        self.app.toast(self.app.t("set_backup_done", path=path), "ok")

    def do_restore(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[("Himaya backup", "*.db"), ("All", "*.*")])
        if not path:
            return
        if not messagebox.askyesno("Himaya", self.app.t("set_restore_confirm")):
            return
        backup.backup(self.app.db)  # safety copy of current data first
        backup.restore(path, config.DB_PATH)
        self.app.toast(self.app.t("set_restored"), "warn")
