"""
Settings page: language, CCP/BaridiMob info (used by reply templates),
delivery defaults, label size, tesseract path, backup/restore, wilaya list,
plus v1.1.0 security (app password + auto-backup on close), relance
threshold and demo-data loader.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from .. import config
from ..models import settings_store
from ..i18n import LANG_NAMES
from ..services import backup
from . import widgets as W
from .widgets import F


class SettingsPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=app.t("set_title"), font=F(22, "bold"),
                     anchor=W.rtl_anchor(app)).grid(row=0, column=0, sticky="ew",
                                                  padx=16, pady=(10, 4))

        db = app.db

        # ---- language ------------------------------------------------------
        lang_card = self._card(1)
        ctk.CTkLabel(lang_card, text=app.t("set_language"), font=F(14, "bold"),
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        row = ctk.CTkFrame(lang_card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 10))
        self.lang_var = tk.StringVar(value=LANG_NAMES.get(app.lang, "Français"))
        ctk.CTkSegmentedButton(row, values=[LANG_NAMES[l] for l in ("fr", "en", "ar")],
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
        brow.pack(fill="x", padx=14, pady=(4, 4))
        ctk.CTkButton(brow, text=app.t("set_backup_now"), height=32,
                      command=self.do_backup).pack(side="left", padx=(0, 8))
        ctk.CTkButton(brow, text=app.t("set_restore"), height=32, fg_color=config.COLOR_ORANGE,
                      hover_color="#d35400", command=self.do_restore).pack(side="left")
        ctk.CTkButton(brow, text=app.t("demo_load"), height=32,
                      fg_color=config.COLOR_BG_3, hover_color=config.COLOR_BG,
                      command=self.load_demo).pack(side="left", padx=8)

        # ---- security (v1.1.0) -----------------------------------------------
        sec = self._card(6)
        ctk.CTkLabel(sec, text="🔒 " + app.t("sec_title"), font=F(14, "bold"),
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        from ..services import security
        self._pw_state = ctk.CTkLabel(
            sec, text=app.t("sec_pw_active") if security.has_password(db)
            else app.t("sec_pw_none"), font=F(12),
            text_color=config.COLOR_GREEN if security.has_password(db)
            else config.COLOR_FG_DIM, anchor="w")
        self._pw_state.pack(fill="x", padx=14)
        pwrow = ctk.CTkFrame(sec, fg_color="transparent")
        pwrow.pack(fill="x", padx=14, pady=(4, 2))
        self.pw_entry = ctk.CTkEntry(pwrow, width=200, show="•",
                                     placeholder_text=app.t("sec_enter_pw"),
                                     height=32)
        self.pw_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(pwrow, text=app.t("sec_set_pw"), height=32,
                      command=self.set_password).pack(side="left", padx=2)
        ctk.CTkButton(pwrow, text=app.t("sec_remove_pw"), height=32,
                      fg_color=config.COLOR_BG_3, hover_color=config.COLOR_BG,
                      command=self.remove_password).pack(side="left", padx=2)
        self.auto_backup = ctk.CTkSwitch(
            sec, text=app.t("sec_autobackup"),
            command=self.toggle_auto_backup)
        self.auto_backup.pack(anchor="w", padx=14, pady=(2, 10))
        if security.auto_backup_enabled(db):
            self.auto_backup.select()

        # ---- relance threshold --------------------------------------------------
        rel = self._card(7)
        ctk.CTkLabel(rel, text="🔔 " + app.t("nav_relance"), font=F(14, "bold"),
                     anchor="w").pack(fill="x", padx=14, pady=(10, 2))
        rrow = ctk.CTkFrame(rel, fg_color="transparent")
        rrow.pack(fill="x", padx=14, pady=(2, 10))
        ctk.CTkLabel(rrow, text=app.t("rel_threshold"), font=F(12)).pack(
            side="left", padx=(0, 6))
        self.relance_days = ctk.CTkEntry(rrow, width=60, height=28)
        self.relance_days.insert(0, settings_store.get_setting(db, "relance_days", "3"))
        self.relance_days.pack(side="left")
        ctk.CTkLabel(rrow, text=app.t("rel_desc"), font=F(10),
                     text_color=config.COLOR_FG_DIM, wraplength=600,
                     justify="left").pack(side="left", padx=(12, 0))

    # ------------------------------------------------------------------ helpers

    def _card(self, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(self, fg_color=config.COLOR_CARD, corner_radius=12,
                            border_width=1, border_color=config.COLOR_BORDER)
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
        # reverse-lookup the language code from its display name
        lang = next((code for code, name in LANG_NAMES.items() if name == value), "fr")
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
        days = self.relance_days.get().strip()
        if days.isdigit() and 1 <= int(days) <= 30:
            settings_store.set_setting(db, "relance_days", days)
        self.app.toast(self.app.t("set_saved"), "ok")

    # ---- security / demo actions -------------------------------------------

    def set_password(self) -> None:
        from ..services import security
        pw = self.pw_entry.get()
        if len(pw) < 4:
            self.app.toast(self.app.t("sec_wrong_pw"), "warn")
            return
        security.set_password(self.app.db, pw)
        self.pw_entry.delete(0, "end")
        self._pw_state.configure(text=self.app.t("sec_pw_active"),
                                 text_color=config.COLOR_GREEN)
        self.app.toast(self.app.t("sec_pw_active"), "ok")

    def remove_password(self) -> None:
        from ..services import security
        if not security.has_password(self.app.db):
            return
        if not messagebox.askyesno("Himaya", self.app.t("delete_confirm")):
            return
        security.clear_password(self.app.db)
        self._pw_state.configure(text=self.app.t("sec_pw_none"),
                                 text_color=config.COLOR_FG_DIM)
        self.app.toast(self.app.t("sec_pw_none"), "ok")

    def toggle_auto_backup(self) -> None:
        from ..services import security
        security.set_auto_backup(self.app.db, bool(self.auto_backup.get()))

    def load_demo(self) -> None:
        if not messagebox.askyesno("Himaya", self.app.t("demo_load") + " ?"):
            return
        from ..services.demo import load_demo
        load_demo(self.app.db)
        self.app.toast(self.app.t("demo_loaded"), "ok")
        self.app.refresh_page()

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
