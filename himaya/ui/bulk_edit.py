"""
Bulk edit: change status / delivery company / wilaya / shipping cost for
several selected orders at once. Empty fields are left untouched.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import config
from ..i18n import t
from ..models import orders as orders_model
from ..services import trust
from ..wilayas import WILAYA_NAMES_FR
from . import widgets as W
from .widgets import F, HimayaDialog, center, fit_geometry


class BulkEditDialog(HimayaDialog):
    def __init__(self, master, app, order_ids: list[int], on_done=None):
        super().__init__(master)
        self.app = app
        self.order_ids = order_ids
        self.on_done = on_done
        self.title(app.t("me_title") + f" ({len(order_ids)})")
        self.configure(fg_color=config.COLOR_BG_2)
        fit_geometry(self, 440, 380)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        ctk.CTkLabel(self, text=f"{app.t('me_title')} — {len(order_ids)} 📦",
                     font=F(17, "bold")).pack(pady=(14, 4))
        ctk.CTkLabel(self, text=app.t("me_hint"), font=F(11),
                     text_color=config.COLOR_FG_DIM).pack(pady=(0, 8))

        # status
        ctk.CTkLabel(self, text=app.t("status"), font=F(12), anchor="w"
                     ).pack(fill="x", padx=24)
        status_values = ["—"] + [t(f"st_{s}", app.lang) for s in config.ALL_STATUSES]
        self.status = ctk.CTkOptionMenu(self, values=status_values, width=200)
        self.status.set("—")
        self.status.pack(padx=24, anchor="w")

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(10, 0))
        ctk.CTkLabel(row, text=app.t("delivery_method"), font=F(12)).pack(
            side="left", padx=(0, 6))
        self.delivery = ctk.CTkComboBox(row, values=["—"] + config.DELIVERY_COMPANIES,
                                        width=150)
        self.delivery.set("—")
        self.delivery.pack(side="left", padx=(0, 14))
        ctk.CTkLabel(row, text=app.t("shipping_cost"), font=F(12)).pack(
            side="left", padx=(0, 6))
        self.shipping = tk.StringVar()
        ctk.CTkEntry(row, textvariable=self.shipping, width=90,
                     placeholder_text="—").pack(side="left")

        ctk.CTkLabel(self, text=app.t("wilaya"), font=F(12), anchor="w"
                     ).pack(fill="x", padx=24, pady=(10, 0))
        self.wilaya = ctk.CTkComboBox(self, values=["—"] + WILAYA_NAMES_FR, width=200)
        self.wilaya.set("—")
        self.wilaya.pack(padx=24, anchor="w")
        W.wheel_combo(self.wilaya, ["—"] + WILAYA_NAMES_FR)

        ctk.CTkButton(self, text=app.t("save"), width=140,
                      command=self.apply).pack(pady=14)
        center(self, master)

    def apply(self) -> None:
        db = self.app.db
        lang = self.app.lang
        fields: dict = {}
        status_label = self.status.get()
        if status_label != "—":
            for s in config.ALL_STATUSES:
                if t(f"st_{s}", lang) == status_label:
                    fields["status"] = s
                    break
        if self.delivery.get() != "—":
            fields["delivery_method"] = self.delivery.get()
        if self.wilaya.get() != "—":
            fields["wilaya"] = self.wilaya.get()
        if self.shipping.get().strip():
            try:
                fields["shipping_cost"] = float(self.shipping.get().replace(",", "."))
            except ValueError:
                self.app.toast(self.app.t("fill_required"), "warn")
                return
        if not fields:
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        new_status = fields.pop("status", None)
        for oid in self.order_ids:
            if new_status:
                orders_model.set_status(db, oid, new_status)
            if fields:
                orders_model.update(db, oid, **fields)
            o = orders_model.get(db, oid)
            if o:
                trust.refresh(db, o["customer_id"])
        self.app.toast(self.app.t("ord_status_changed"), "ok")
        self.close()
        if self.on_done:
            self.on_done()
