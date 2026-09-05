"""
First-launch tour (4 lines + optional demo data) and the password gate
shown at startup when the seller enabled the app lock.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import config
from ..models import settings_store
from .widgets import F, HimayaDialog, center


class TourDialog(HimayaDialog):
    """Welcome popup on first launch: mini-tour + demo-data offer."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("Himaya")
        self.configure(fg_color=config.COLOR_BG_2)
        self.geometry("520x400")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        ctk.CTkLabel(self, text=app.t("tour_welcome"), font=F(22, "bold"),
                     text_color=config.COLOR_ACCENT).pack(pady=(22, 8))
        for key in ("tour_l1", "tour_l2", "tour_l3", "tour_l4"):
            ctk.CTkLabel(self, text=app.t(key), font=F(13), anchor="w",
                         justify="left", wraplength=460,
                         text_color=config.COLOR_FG).pack(fill="x", padx=30, pady=3)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=(24, 16))
        ctk.CTkButton(btns, text=app.t("tour_start"), width=170,
                      command=self._start_empty).pack(side="right", padx=4)
        ctk.CTkButton(btns, text=app.t("demo_load"), width=210,
                      fg_color=config.COLOR_GREEN, hover_color="#27ae60",
                      command=self._load_demo).pack(side="right", padx=4)
        center(self, master)

    def _mark_done(self) -> None:
        settings_store.set_setting(self.app.db, "tour_done", "1")

    def _start_empty(self) -> None:
        self._mark_done()
        self.close()

    def _load_demo(self) -> None:
        from ..services.demo import load_demo
        load_demo(self.app.db)
        self._mark_done()
        self.close()
        self.app.toast(self.app.t("demo_loaded"), "ok")
        self.app.show_page("dashboard")


class PasswordGate(HimayaDialog):
    """Modal lock screen: asks for the app password before showing data."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title("Himaya 🔒")
        self.configure(fg_color=config.COLOR_BG_2)
        self.geometry("380x220")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", lambda: None)   # must unlock

        ctk.CTkLabel(self, text="🔒", font=F(34)).pack(pady=(24, 4))
        ctk.CTkLabel(self, text=app.t("sec_enter_pw"), font=F(14, "bold")
                     ).pack(pady=(0, 8))
        self.pw = tk.StringVar()
        entry = ctk.CTkEntry(self, textvariable=self.pw, width=240, show="•",
                             height=34)
        entry.pack()
        entry.focus_set()
        self.bind("<Return>", lambda e: self.try_unlock())
        self.msg = ctk.CTkLabel(self, text="", font=F(11),
                                text_color=config.COLOR_RED)
        self.msg.pack(pady=(4, 0))
        ctk.CTkButton(self, text=app.t("sec_unlock"), width=140,
                      command=self.try_unlock).pack(pady=10)
        center(self, master)

    def try_unlock(self) -> None:
        from ..services import security
        if security.verify_password(self.app.db, self.pw.get()):
            self.app._unlocked = True
            self.close()
            # resume background page pre-building (paused behind the lock)
            self.app._prebuilding_off = False
            self.app.after(400, self.app._prebuild_pages)
            # first launch + password: the tour was postponed until now
            if not security_settings_done(self.app.db):
                self.app.after(200, self.app._show_tour)
        else:
            self.msg.configure(text=self.app.t("sec_wrong_pw"))
            self.pw.set("")


def security_settings_done(db) -> bool:
    from ..models import settings_store
    return settings_store.get_setting(db, "tour_done", "") == "1"
