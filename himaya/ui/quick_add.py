"""
Quick add: paste one free-text line, get parsed fields.
Used by the Orders dialog (pre-fill) and the Customers page (create).
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import config
from ..services import quick_parse
from .widgets import F, HimayaDialog, center, fit_geometry


def ask_line(master, app) -> dict | None:
    """
    Small popup asking for the pasted line. WAITS until the user closes it,
    then returns the parsed fields (None if cancelled / invalid).
    v1.2.3: returned dialog.result immediately — always None, so the
    quick-paste button in the order dialog silently did nothing.
    """
    dialog = QuickAddDialog(master, app)
    master.wait_window(dialog)      # block until Parse / Escape / close
    return dialog.result


class QuickAddDialog(HimayaDialog):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.result: dict | None = None
        self.title(app.t("qa_title"))
        self.configure(fg_color=config.COLOR_BG_2)
        fit_geometry(self, 520, 300)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        ctk.CTkLabel(self, text=app.t("qa_title"), font=F(17, "bold")).pack(pady=(16, 2))
        ctk.CTkLabel(self, text=app.t("qa_hint"), font=F(11),
                     text_color=config.COLOR_FG_DIM).pack(pady=(0, 6))
        self.line = tk.StringVar()
        entry = ctk.CTkEntry(self, textvariable=self.line, width=470, height=34)
        entry.pack(padx=20)
        entry.focus_set()
        self.line.trace_add("write", lambda *_: self.preview())
        self.preview_lbl = ctk.CTkLabel(self, text="", font=F(12), anchor="w",
                                        justify="left", wraplength=470,
                                        text_color=config.COLOR_ACCENT)
        self.preview_lbl.pack(padx=24, pady=8, fill="x")
        self.bind("<Return>", lambda e: self.ok())
        ctk.CTkButton(self, text=app.t("qa_parse"), width=140,
                      command=self.ok).pack(pady=6)
        center(self, master)

    def preview(self) -> None:
        parsed = quick_parse.parse_line(self.line.get())
        if not parsed["phone"] and not parsed["name"]:
            self.preview_lbl.configure(text="")
            return
        self.preview_lbl.configure(
            text=f"{parsed['name'] or '—'} • {parsed['phone'] or '—'} • "
                 f"{parsed['wilaya'] or '—'} • {parsed['address'] or '—'}")

    def ok(self) -> None:
        parsed = quick_parse.parse_line(self.line.get())
        if not parsed["phone"]:
            self.app.toast(self.app.t("invalid_phone"), "warn")
            return
        self.result = parsed
        self.close()


def ask_text(master, app, title: str, placeholder: str = "") -> str | None:
    """
    Generic one-line prompt (used for 'add custom delivery company').
    WAITS until closed, returns the typed text (stripped) or None.
    """
    dialog = _TextDialog(master, app, title, placeholder)
    master.wait_window(dialog)
    return dialog.result


class _TextDialog(HimayaDialog):
    def __init__(self, master, app, title: str, placeholder: str):
        super().__init__(master)
        self.app = app
        self.result = None
        self.title(title)
        self.configure(fg_color=config.COLOR_BG_2)
        fit_geometry(self, 420, 170)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        ctk.CTkLabel(self, text=title, font=F(15, "bold")).pack(pady=(16, 4))
        self.entry_var = tk.StringVar()
        entry = ctk.CTkEntry(self, textvariable=self.entry_var, width=360,
                             height=32, placeholder_text=placeholder)
        entry.pack(padx=20)
        entry.focus_set()
        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.close())
        ctk.CTkButton(self, text=app.t("save"), width=110,
                      command=self.ok).pack(pady=10)
        center(self, master)

    def ok(self) -> None:
        self.result = self.entry_var.get().strip() or None
        self.close()
