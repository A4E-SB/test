"""
Orders page: filtered list, status changes, order dialog with live phone
risk check and the 'Block order' anti-scam flow, label shortcut.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import messagebox

import customtkinter as ctk

from .. import config
from ..i18n import t
from ..models import customers as customers_model
from ..models import orders as orders_model
from ..models import settings_store
from ..services import trust
from ..wilayas import WILAYA_NAMES_FR
from . import widgets as W
from .widgets import F, HimayaDialog, make_tree, row_tag


class OrdersPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---- toolbar ----------------------------------------------------------
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))
        ctk.CTkLabel(top, text=app.t("ord_title"), font=F(22, "bold"),
                 anchor=W.rtl_anchor(app)).pack(side=W.rtl_side(app))
        ctk.CTkButton(top, text=app.t("ord_new"), height=36, fg_color=config.COLOR_GREEN,
                      hover_color="#27ae60",
                      command=self.new_order).pack(side="right")
        # v1.1 actions live in the TOP toolbar — the bottom status bar is
        # already full with the 12 status buttons (v1.1.0 clipped them)
        ctk.CTkButton(top, text=app.t("dim_btn"), height=36, fg_color=config.COLOR_BG_3,
                      hover_color="#3a4150",
                      command=self.import_statuses).pack(side="right", padx=4)
        ctk.CTkButton(top, text=app.t("me_btn"), height=36, fg_color=config.COLOR_BG_3,
                      hover_color="#3a4150",
                      command=self.bulk_edit).pack(side="right", padx=4)
        ctk.CTkButton(top, text=app.t("man_btn"), height=36, fg_color=config.COLOR_BG_3,
                      hover_color="#3a4150",
                      command=self.make_manifest).pack(side="right", padx=4)

        # ---- filters ------------------------------------------------------------
        filters = W.card(self)
        filters.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 6))
        status_labels = [app.t("all")] + [t(f"st_{s}", app.lang) for s in config.ALL_STATUSES]
        self.status_keys = [""] + config.ALL_STATUSES
        self.f_status = ctk.CTkOptionMenu(filters, width=170, values=status_labels,
                                          command=lambda _v: self.refresh())
        self.f_status.set(status_labels[0])
        self.f_status.pack(side="left", padx=(10, 4), pady=8)
        self.f_wilaya = ctk.CTkOptionMenu(filters, width=160,
                                          values=[app.t("all")] + WILAYA_NAMES_FR,
                                          command=lambda _v: self.refresh())
        self.f_wilaya.pack(side="left", padx=4, pady=8)
        W.wheel_combo(self.f_wilaya, [app.t("all")] + WILAYA_NAMES_FR)
        self.f_query = tk.StringVar()
        ctk.CTkEntry(filters, textvariable=self.f_query, width=200,
                     placeholder_text=app.t("search"),
                     height=32).pack(side="left", padx=4, pady=8)
        # debounced: one refresh after typing pauses, not one per keystroke
        self._search_deb = W.Debouncer(self, 250)
        self.f_query.trace_add("write", lambda *_: self._search_deb.call(self.refresh))
        ctk.CTkLabel(filters, text=app.t("ord_from"), font=F(11),
                     text_color=config.COLOR_FG_DIM).pack(side="left", padx=(10, 2))
        self.f_from = ctk.CTkEntry(filters, width=95, height=32, placeholder_text="2025-01-01")
        self.f_from.pack(side="left", padx=2, pady=8)
        ctk.CTkLabel(filters, text=app.t("ord_to"), font=F(11),
                     text_color=config.COLOR_FG_DIM).pack(side="left", padx=(6, 2))
        self.f_to = ctk.CTkEntry(filters, width=95, height=32)
        self.f_to.pack(side="left", padx=2, pady=8)

        # ---- list ----------------------------------------------------------------
        list_frame = W.card(self)
        list_frame.grid(row=2, column=0, sticky="nsew", padx=8, pady=(2, 8))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        cols = [("id", "#", 46), ("date", app.t("date"), 88),
                ("customer", app.t("ord_customer"), 170), ("phone", app.t("phone"), 118),
                ("product", app.t("product"), 150), ("price", app.t("price"), 88),
                ("dep", app.t("col_deposit"), 78),
                ("status", app.t("status"), 110), ("delivery", app.t("col_delivery"), 92),
                ("wilaya", app.t("wilaya"), 120)]
        self.tree = make_tree(list_frame, cols, height=17)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        W.bind_tree_tooltips(self.tree)   # full text on hover if clipped
        self.tree.bind("<Double-1>", lambda e: self.edit_order())
        self.tree.bind("<Delete>", lambda e: self.delete_order())

        # ---- status change bar -----------------------------------------------------
        # v1.3 layout rule: the 12 status chips live in a HORIZONTALLY
        # SCROLLABLE strip -- they can never clip the last chip ("Block...")
        # or squeeze the right-side buttons, whatever the window width.
        bar = ctk.CTkFrame(list_frame, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right")
        self.count_lbl = ctk.CTkLabel(right, text="", font=F(11),
                                      text_color=config.COLOR_FG_DIM)
        self.count_lbl.pack(side="right")
        ctk.CTkButton(right, text=self.app.t("edit"), height=26, width=70,
                      command=self.edit_order).pack(side="right", padx=4)
        ctk.CTkButton(right, text="🖨️", height=26, width=44,
                      fg_color=config.COLOR_BG_3,
                      command=self.print_labels).pack(side="right", padx=2)

        chips = ctk.CTkScrollableFrame(bar, orientation="horizontal",
                                       height=36, fg_color="transparent")
        chips.pack(side="left", fill="x", expand=True)
        self.status_btns = []
        for st_name in config.ALL_STATUSES:
            color = config.STATUS_COLORS.get(st_name, config.COLOR_BG_3)
            btn = ctk.CTkButton(chips, text=f"●  {t(f'st_{st_name}', app.lang)}",
                                height=26, width=88,
                                fg_color=config.COLOR_BG_3, hover_color=color,
                                text_color=color, font=F(10, "bold"),
                                command=lambda st=st_name: self.set_status(st))
            btn.pack(side="left", padx=2)
            self.status_btns.append(btn)
        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        db, lang = self.app.db, self.app.lang
        status_label = self.f_status.get()
        status = ""
        for i, key in enumerate(self.status_keys):
            if status_label == (self.app.t("all") if i == 0 else t(f"st_{key}", lang)):
                status = key
        wilaya = "" if self.f_wilaya.get() == self.app.t("all") else self.f_wilaya.get()
        rows = orders_model.list_orders(
            db, status=status, wilaya=wilaya,
            date_from=self.f_from.get().strip(), date_to=self.f_to.get().strip(),
            query=self.f_query.get())
        self.tree.delete(*self.tree.get_children())
        for o in rows:
            self.tree.insert("", "end", iid=str(o["id"]), values=(
                o["id"], o["date"], o["customer_name"], o["phone"], o["product"],
                f"{o['price']:,.0f}".replace(",", " "),
                (f"{o['deposit']:,.0f}".replace(",", " ") if o["deposit"] else "—"),
                W.status_badge_text(o["status"], lang),
                o["delivery_method"], o["wilaya"]), tags=(row_tag(o["status"]),))
        total = sum(r["price"] for r in rows)
        self.count_lbl.configure(
            text=self.app.t("ord_new_orders_count", n=len(rows)) + " • "
                + config.fmt_money(total, lang))

    def selected_ids(self) -> list[int]:
        return [int(i) for i in self.tree.selection()] or (
            [int(self.tree.focus())] if self.tree.focus() else [])

    # ------------------------------------------------------------------

    def set_status(self, status: str) -> None:
        ids = self.selected_ids()
        if not ids:
            # buttons LOOKED dead without a selection -> always give feedback
            self.app.toast(self.app.t("ord_select_first"), "warn")
            return
        for oid in ids:
            orders_model.set_status(self.app.db, oid, status)
            o = orders_model.get(self.app.db, oid)
            if o:
                trust.refresh(self.app.db, o["customer_id"])
        self.app.toast(self.app.t("ord_status_changed"), "ok")
        self.refresh()

    def filter_status(self, status: str) -> None:
        """Select a status in the filter bar (used by dashboard cards)."""
        label = self.app.t("all") if not status else t(f"st_{status}", self.app.lang)
        self.f_status.set(label)
        self.refresh()

    def new_order(self) -> None:
        OrderDialog(self, self.app, on_saved=lambda: self.refresh())

    def edit_order(self) -> None:
        ids = self.selected_ids()
        if ids:
            OrderDialog(self, self.app, order_id=ids[0], on_saved=lambda: self.refresh())

    def delete_order(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        if messagebox.askyesno("Himaya", self.app.t("delete_confirm")):
            for oid in ids:
                o = orders_model.get(self.app.db, oid)
                orders_model.delete(self.app.db, oid)
                if o:
                    trust.refresh(self.app.db, o["customer_id"])
            self.app.toast(self.app.t("ord_deleted"), "ok")
            self.refresh()

    def print_labels(self) -> None:
        ids = self.selected_ids()
        if not ids:
            return
        from .labels_ui import generate_and_open
        generate_and_open(self.app, ids)

    def make_manifest(self) -> None:
        """Printable handover bordereau for the selected orders."""
        ids = self.selected_ids()
        if not ids:
            self.app.toast(self.app.t("ord_select_first"), "warn")
            return
        from ..services.manifest import generate_manifest
        from .labels_ui import _open_folder   # same "open after generate" helper
        out = config.DATA_DIR / f"bordereau_{ids[0]}_{len(ids)}.pdf"
        generate_manifest(self.app.db, ids, "Yalidine", out, lang=self.app.lang)
        _open_folder(out)
        self.app.toast(self.app.t("lb_generated", path=str(out)), "ok")

    def import_statuses(self) -> None:
        from .delivery_import_ui import ImportStatusesDialog
        ImportStatusesDialog(self, self.app, on_done=lambda: self.refresh())

    def bulk_edit(self) -> None:
        ids = self.selected_ids()
        if not ids:
            self.app.toast(self.app.t("ord_select_first"), "warn")
            return
        from .bulk_edit import BulkEditDialog
        BulkEditDialog(self, self.app, ids, on_done=lambda: self.refresh())

    def focus_order(self, oid: int) -> None:
        """Select one order (global search jumps here)."""
        self.tree.selection_set(str(oid))
        self.tree.focus(str(oid))
        self.tree.see(str(oid))


class OrderDialog(HimayaDialog):
    """Create / edit an order, with live phone risk check + block flow."""

    def __init__(self, master, app, order_id: int | None = None, on_saved=None):
        super().__init__(master)
        self.app = app
        self.order_id = order_id
        self.on_saved = on_saved
        self.blocked = False
        editing = order_id is not None
        self.title(self.app.t("edit" if editing else "ord_new"))
        self.configure(fg_color=config.COLOR_BG_2)
        self.geometry("480x730")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        # ---- bottom bar (OUTSIDE the scroll area: always visible) -----------
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=24, pady=10)
        ctk.CTkButton(btns, text=app.t("cancel"), fg_color="transparent",
                      text_color=config.COLOR_FG_DIM, border_width=1,
                      command=self.close).pack(side="right", padx=4)
        ctk.CTkButton(btns, text=app.t("save"), width=120,
                      command=self.save).pack(side="right", padx=4)

        # ---- guided form: one numbered section per topic, scrollable so it
        #      never overflows on small screens / high-DPI scaling -------------
        form = ctk.CTkScrollableFrame(self, fg_color="transparent")
        form.pack(side="top", fill="both", expand=True)
        db = app.db

        def sec(key: str) -> None:
            ctk.CTkLabel(form, text=app.t(key), font=F(12, "bold"), anchor="w",
                         text_color=config.COLOR_ACCENT).pack(
                             fill="x", padx=24, pady=(12, 2))

        ctk.CTkLabel(form, text=self.app.t("edit" if editing else "ord_new"),
                     font=F(18, "bold")).pack(pady=(8, 2))

        # §1 customer: one picked from the Customers page (or quick-create)
        sec("ord_customer")
        custs = customers_model.all_customers(db)
        self.cust_labels = {f"{c['name']} — {c['phone']}": c["id"] for c in custs}
        self.cust_combo = ctk.CTkComboBox(
            form, values=list(self.cust_labels.keys()), width=420,
            command=lambda _v: self._on_customer_pick())
        if custs:
            self.cust_combo.set(list(self.cust_labels.keys())[0])
        self.cust_combo.pack(padx=24, pady=(0, 2))

        # quick new-customer name/phone (still possible without leaving the order)
        self.newc_frame = ctk.CTkFrame(form, fg_color=config.COLOR_BG, corner_radius=8)
        self.newc_frame.pack(fill="x", padx=24, pady=4)
        self.new_name = tk.StringVar()
        self.new_phone = tk.StringVar()
        ctk.CTkEntry(self.newc_frame, textvariable=self.new_name, width=200,
                     placeholder_text=app.t("name")).grid(row=0, column=0, padx=6, pady=6)
        ctk.CTkEntry(self.newc_frame, textvariable=self.new_phone, width=180,
                     placeholder_text=app.t("phone")).grid(row=0, column=1, padx=6, pady=6)
        self.newc_frame.grid_columnconfigure((0, 1), weight=1)
        self.risk_lbl = ctk.CTkLabel(form, text="", font=F(11, "bold"))
        self.risk_lbl.pack()
        self.new_phone.trace_add("write", lambda *_: self.live_check())
        ctk.CTkButton(self.newc_frame, text=app.t("qa_btn"), width=110, height=28,
                      fg_color=config.COLOR_BG_3, hover_color=config.COLOR_BG,
                      command=self.quick_paste).grid(row=0, column=2, padx=6, pady=6)

        # §2 order date: today (one click) or a custom date
        sec("ord_date")
        drow = ctk.CTkFrame(form, fg_color="transparent")
        drow.pack(fill="x", padx=24)
        self.odate = tk.StringVar()
        ctk.CTkEntry(drow, textvariable=self.odate, width=170,
                     placeholder_text=date.today().isoformat()).pack(side="left")
        ctk.CTkButton(drow, text="📅 " + app.t("ord_date_today"), width=130, height=28,
                      fg_color=config.COLOR_BG_3, hover_color=config.COLOR_BG,
                      command=lambda: self.odate.set(date.today().isoformat())
                      ).pack(side="left", padx=8)
        ctk.CTkLabel(form, text=app.t("ord_date_hint"), font=F(10),
                     text_color=config.COLOR_FG_DIM, anchor="w").pack(fill="x", padx=26)

        # §3 product: picked from Products & Stock, price auto-filled from it
        sec("product")
        self.product = tk.StringVar()
        self.price = tk.StringVar()
        self.shipping = tk.StringVar(
            value=settings_store.get_setting(db, "default_shipping_cost", "600"))
        self.notes = tk.StringVar()
        self.deposit = tk.StringVar()
        from ..models import products as products_model
        self._catalog = products_model.all_products(db)
        catalog_names = [p["name"] for p in self._catalog]
        self.product_combo = ctk.CTkComboBox(
            form, values=catalog_names, textvariable=self.product, width=420,
            command=lambda _v: self._on_catalog_pick())
        self.product_combo.pack(padx=24)
        prow = ctk.CTkFrame(form, fg_color="transparent")
        prow.pack(fill="x", padx=24)
        ctk.CTkLabel(prow, text=app.t("price"), font=F(12)).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(prow, textvariable=self.price, width=130).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(prow, text=app.t("deposit"), font=F(12)).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(prow, textvariable=self.deposit, width=110,
                     placeholder_text="0").pack(side="left")
        self.dep_hint = ctk.CTkLabel(form, text="", font=F(11), anchor="w",
                                     text_color=config.COLOR_YELLOW)
        self.dep_hint.pack(fill="x", padx=24)
        self.deposit.trace_add("write", lambda *_: self._update_deposit_hint())

        # §4 delivery: wilaya, company (or add a custom one), shipping cost
        sec("ord_delivery_sec")
        srow = ctk.CTkFrame(form, fg_color="transparent")
        srow.pack(fill="x", padx=24)
        ctk.CTkLabel(srow, text=app.t("wilaya"), font=F(12)).pack(side="left", padx=(0, 6))
        self.wilaya = ctk.CTkComboBox(srow, values=WILAYA_NAMES_FR, width=170)
        self.wilaya.pack(side="left", padx=(0, 12))
        W.wheel_combo(self.wilaya, WILAYA_NAMES_FR)
        ctk.CTkLabel(srow, text=app.t("delivery_method"), font=F(12)).pack(
            side="left", padx=(0, 6))
        self._companies = settings_store.delivery_companies(db)
        self._add_company_tag = "➕ " + app.t("ord_add_company")
        self.delivery = ctk.CTkComboBox(
            srow, values=self._companies + [self._add_company_tag],
            width=190, command=self._on_company_pick)
        default = settings_store.get_setting(db, "default_delivery", "Yalidine")
        self._last_company = (default if default in self._companies
                              else (self._companies[0] if self._companies else "Yalidine"))
        self.delivery.set(self._last_company)
        self.delivery.pack(side="left")
        ship_row = ctk.CTkFrame(form, fg_color="transparent")
        ship_row.pack(fill="x", padx=24, pady=(6, 0))
        ctk.CTkLabel(ship_row, text=app.t("shipping_cost"), font=F(12)).pack(
            side="left", padx=(0, 6))
        ctk.CTkEntry(ship_row, textvariable=self.shipping, width=110).pack(side="left")

        # §5 status
        sec("status")
        self.status = ctk.CTkOptionMenu(
            form, values=[t(f"st_{s}", app.lang) for s in config.ALL_STATUSES],
            width=200)
        self.status.set(t("st_pending", app.lang))
        self.status.pack(padx=24, anchor="w")

        # §6 notes
        sec("notes")
        ctk.CTkEntry(form, textvariable=self.notes, width=420).pack(
            padx=24, pady=(0, 8))

        if editing:
            o = orders_model.get(db, order_id)
            cust = customers_model.get(db, o["customer_id"])
            if cust:
                label = f"{cust['name']} — {cust['phone']}"
                if label in self.cust_labels:
                    self.cust_combo.set(label)
            self.product.set(o["product"])
            self.price.set(str(int(o["price"])))
            self.shipping.set(str(int(o["shipping_cost"])))
            self.deposit.set(str(int(o["deposit"])) if o["deposit"] else "")
            self.notes.set(o["notes"] or "")
            self.odate.set(o["date"] or "")
            if o["delivery_method"]:
                self.delivery.set(o["delivery_method"])
                self._last_company = o["delivery_method"]
            self.wilaya.set(o["wilaya"] or WILAYA_NAMES_FR[0])
            self.status.set(t(f"st_{o['status']}", app.lang))

    # ------------------------------------------------------------------

    def _on_catalog_pick(self) -> None:
        """Choosing a catalog product always fills its sale price
        (the price set in Products & Stock) and remembers the link."""
        name = self.product.get()
        for p in self._catalog:
            if p["name"] == name:
                self.price.set(str(int(p["sale_price"])))
                break

    def _on_customer_pick(self, *__) -> None:
        """Picking an existing customer pre-fills their wilaya."""
        cid = self.cust_labels.get(self.cust_combo.get())
        if not cid:
            return
        cust = customers_model.get(self.app.db, cid)
        if cust and cust["wilaya"] in WILAYA_NAMES_FR:
            self.wilaya.set(cust["wilaya"])

    def _on_company_pick(self, _value: str = "") -> None:
        """The '➕ add' entry opens a name prompt; typed once, remembered."""
        current = self.delivery.get().strip()
        if current != self._add_company_tag:
            if current:
                self._last_company = current
            return
        from .quick_add import ask_text
        name = ask_text(self, self.app, self.app.t("ord_company_prompt"))
        if name:
            self._companies = settings_store.add_delivery_company(self.app.db, name)
            self.delivery.configure(
                values=self._companies + [self._add_company_tag])
            self.delivery.set(name)
            self._last_company = name
        else:
            self.delivery.set(self._last_company)

    def _update_deposit_hint(self) -> None:
        """'Remaining to collect' = price - deposit (shown live)."""
        try:
            price = float(self.price.get().replace(",", ".") or 0)
            dep = float(self.deposit.get().replace(",", ".") or 0)
        except ValueError:
            self.dep_hint.configure(text="")
            return
        if dep > 0 and price > dep:
            self.dep_hint.configure(
                text="💰 " + self.app.t("dep_remaining") + " : "
                     + f"{price - dep:,.0f} DA".replace(",", " "))
        else:
            self.dep_hint.configure(text="")

    def quick_paste(self) -> None:
        """Paste a whole line ('Karim 0555123456 Sétif cite 200') → fields."""
        from .quick_add import ask_line
        parsed = ask_line(self, self.app)
        if not parsed or not parsed.get("phone"):
            return
        self.new_phone.set(parsed["phone"])
        if parsed.get("name"):
            self.new_name.set(parsed["name"])
        if parsed.get("wilaya") and parsed["wilaya"] in WILAYA_NAMES_FR:
            self.wilaya.set(parsed["wilaya"])

    def live_check(self) -> None:
        from ..services.phone import phone_risk, DANGER, CAUTION
        phone = self.new_phone.get()
        if len(phone.replace(" ", "")) < 9:
            self.risk_lbl.configure(text="")
            return
        risk = phone_risk(self.app.db, phone)
        if risk["level"] == DANGER:
            self.risk_lbl.configure(text="🚨 " + self.app.t("reason_blacklisted"),
                                    text_color=config.COLOR_RED)
        elif risk["level"] == CAUTION:
            self.risk_lbl.configure(text="⚠️ " + self.app.t("scam_caution_body"),
                                    text_color=config.COLOR_ORANGE)
        else:
            self.risk_lbl.configure(text="✓", text_color=config.COLOR_GREEN)

    def _selected_status(self) -> str:
        label = self.status.get()
        for s in config.ALL_STATUSES:
            if t(f"st_{s}", self.app.lang) == label:
                return s
        return "pending"

    def save(self) -> None:
        from ..services.phone import normalize_phone, phone_risk, DANGER
        db = self.app.db

        # resolve customer (existing selection or quick-create)
        cid = None
        quick_phone = self.new_phone.get().strip()
        if quick_phone:
            if not normalize_phone(quick_phone):
                self.app.toast(self.app.t("invalid_phone"), "warn")
                return
            existing = customers_model.find_by_phone(db, quick_phone)
            cid = existing["id"] if existing else customers_model.create(
                db, self.new_name.get().strip() or quick_phone, quick_phone,
                wilaya=self.wilaya.get())
        elif self.cust_labels and self.cust_combo.get() in self.cust_labels:
            cid = self.cust_labels[self.cust_combo.get()]
        if cid is None:
            self.app.toast(self.app.t("fill_required"), "warn")
            return

        if not self.product.get().strip() or not self.price.get().strip():
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        try:
            price = float(self.price.get().replace(",", "."))
            ship = float(self.shipping.get().replace(",", ".") or 0)
            dep = float(self.deposit.get().replace(",", ".") or 0)
        except ValueError:
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        if dep < 0 or dep > price:
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        date_iso = orders_model.parse_date_text(self.odate.get())
        if date_iso is None:
            self.app.toast(self.app.t("ord_bad_date"), "warn")
            return
        company = self.delivery.get().strip()
        if company and company != self._add_company_tag:
            # a name typed directly in the box is remembered for next time
            self._companies = settings_store.add_delivery_company(db, company)
            self.delivery.configure(
                values=self._companies + [self._add_company_tag])

        # catalog product id (when the name matches exactly)
        product_id = None
        for prod in self._catalog:
            if prod["name"] == self.product.get().strip():
                product_id = prod["id"]
                break

        def persist(status: str = self._selected_status()) -> None:
            if self.order_id:
                orders_model.update(db, self.order_id, product=self.product.get().strip(),
                                    price=price, status=status,
                                    delivery_method=company,
                                    **({"date": date_iso} if date_iso else {}),
                                    wilaya=self.wilaya.get(), shipping_cost=ship,
                                    notes=self.notes.get().strip(),
                                    product_id=product_id, deposit=dep)
            else:
                orders_model.create(db, cid, self.product.get().strip(), price,
                                    status=status, delivery_method=company,
                                    order_date=date_iso,
                                    wilaya=self.wilaya.get(), shipping_cost=ship,
                                    notes=self.notes.get().strip(),
                                    product_id=product_id, deposit=dep)
            trust.refresh(db, cid)
            self.close()
            if self.on_saved:
                self.on_saved()

        def block() -> None:
            """Save as blocked -> shipping cost counted as money saved."""
            if not self.order_id:
                orders_model.create(db, cid, self.product.get().strip(), price,
                                    status="blocked", delivery_method=company,
                                    order_date=date_iso,
                                    wilaya=self.wilaya.get(), shipping_cost=ship,
                                    notes=self.notes.get().strip(),
                                    product_id=product_id, deposit=dep)
                trust.refresh(db, cid)
                self.app.toast(self.app.t("ord_blocked_saved"), "ok")
                self.close()
                if self.on_saved:
                    self.on_saved()
            else:
                persist(status="blocked")

        # Anti-scam gate: blacklisted / dangerous number -> offer blocking
        cust = customers_model.get(db, cid)
        risk = phone_risk(db, cust["phone"])
        if risk["level"] == DANGER and not self.order_id:
            from .widgets import ScamAlert
            ScamAlert(self, self.app, risk, on_block=block, on_continue=persist,
                      show_block_btn=True)
        else:
            persist()
