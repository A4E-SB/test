"""
Customers page: searchable list with trust colors, detail panel with trust
bar, tags, order history, money lost, and one-click blacklisting.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .. import config
from ..i18n import t
from ..models import blacklist as blacklist_model
from ..models import customers as customers_model
from ..models import inquiries as inquiries_model
from ..models import orders as orders_model
from ..services import trust
from ..wilayas import WILAYA_NAMES_FR
from . import widgets as W
from .widgets import (F, HimayaDialog, fit_geometry, TrustBadge, EmptyState,
                      make_tree, row_tag,
                      tags_frame, trust_badge_text)
from .widgets import card as surface


class CustomersPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.selected_id: int | None = None
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        # ---- toolbar ------------------------------------------------------
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 2))
        ctk.CTkLabel(top, text=app.t("cust_title"), font=F(21, "extrabold"),
                 anchor=W.rtl_anchor(app)).pack(side=W.rtl_side(app))
        self.search_var = tk.StringVar()
        self._search_deb = W.Debouncer(self, 250)
        self.search_var.trace_add("write",
                                  lambda *_: self._search_deb.call(self.refresh))
        entry = ctk.CTkEntry(top, textvariable=self.search_var, width=280,
                             placeholder_text=app.t("search"), height=36)
        entry.pack(side="left", padx=12)
        self.tag_filter = ctk.CTkOptionMenu(
            top, width=170, height=32, values=[app.t("all")] + [
                app.t(f"tag_{tg}") for tg in config.KNOWN_TAGS],
            command=lambda _v: self.refresh())
        self.tag_filter.pack(side="left", padx=4)
        ctk.CTkButton(top, text=app.t("dup_btn"), height=36, fg_color=config.COLOR_BG_3,
                      hover_color=config.COLOR_BG,
                      command=self.show_duplicates).pack(side="right", padx=4)
        ctk.CTkButton(top, text=app.t("qa_btn"), height=36, fg_color=config.COLOR_BG_3,
                      hover_color=config.COLOR_BG,
                      command=self.quick_add).pack(side="right", padx=4)
        ctk.CTkButton(top, text=app.t("cust_add"), height=36, fg_color=config.COLOR_GREEN,
                      hover_color="#27ae60",
                      command=self.add_customer).pack(side="right")

        # ---- list ------------------------------------------------------------
        list_frame = surface(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=(8, 4), pady=(4, 8))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        cols = [("name", app.t("name"), 170), ("phone", app.t("phone"), 125),
                ("wilaya", app.t("wilaya"), 140), ("score", app.t("cust_trust"), 70),
                ("tags", app.t("cust_tags"), 190)]
        self.tree = make_tree(list_frame, cols, height=16)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", lambda e: self.edit_customer())

        # ---- detail (v1.7.4: fills the WHOLE panel — identity, stats, and an
        #      order-history table that expands into the remaining space;
        #      skeleton built ONCE, only values update per click) -------------
        self.detail = surface(self)
        self.detail.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=(4, 8))
        self.detail.grid_columnconfigure(0, weight=1)
        self.detail.grid_rowconfigure(2, weight=1)      # history row grows

        self.det_empty = EmptyState(self.detail, "👤",
                                    app.t("es_customers"),
                                    app.t("es_customers_hint"))

        # identity card
        self.det_head = surface(self.detail)
        self.det_head.grid(row=0, column=0, sticky="ew")
        self.det_head.grid_columnconfigure(0, weight=1)
        self.det_name = ctk.CTkLabel(self.det_head, text="—",
                                     font=F(20, "semibold"), anchor="w")
        self.det_name.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))
        ctk.CTkButton(self.det_head, text="✏️ " + app.t("edit"), width=96,
                      height=28, fg_color=config.COLOR_BG_3,
                      hover_color=config.COLOR_BG,
                      command=self.edit_customer).grid(
                          row=0, column=1, sticky="e", padx=12, pady=(10, 0))
        self.det_phone = ctk.CTkLabel(self.det_head, text="—", font=F(14),
                                      text_color=config.COLOR_FG_DIM,
                                      anchor="w")
        self.det_phone.grid(row=1, column=0, columnspan=2, sticky="w",
                            padx=14, pady=(0, 2))
        self.det_trust_slot = ctk.CTkFrame(self.det_head, fg_color="transparent")
        self.det_trust_slot.grid(row=2, column=0, sticky="w", padx=14)
        self.det_tags_slot = ctk.CTkFrame(self.det_head, fg_color="transparent")
        self.det_tags_slot.grid(row=3, column=0, sticky="w", padx=14,
                                pady=(0, 10))

        # stats card (small rows, rebuilt per click — cheap)
        self.det_meta = surface(self.detail)
        self.det_meta.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.det_meta.grid_columnconfigure(0, weight=1)

        # order history — a real table that EXPANDS into the free space
        # (v1.3-: a short hand-built list left 2/3 of the panel empty and
        # cost 3 widgets per order; the tree fills the panel and handles
        # any history size)
        self.det_hist = surface(self.detail)
        self.det_hist.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        self.det_hist.grid_columnconfigure(0, weight=1)
        self.det_hist.grid_rowconfigure(1, weight=1)
        self.det_hist_lbl = ctk.CTkLabel(self.det_hist, text=app.t("cust_order_history"),
                                         font=F(12, "semibold"), anchor="w")
        self.det_hist_lbl.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        # v1.7.7 fix: the detail column is ~420px — the old 506px of columns
        # pushed the status column out of view (no scrollbar). Widths now
        # fit ~390px AND a horizontal scrollbar handles any narrow window
        # or long product name (nothing is ever unreachable).
        hcols = [("id", "#", 38), ("date", app.t("date"), 78),
                 ("product", app.t("product"), 120), ("price", app.t("price"), 78),
                 ("status", app.t("status"), 112)]
        hist_body = ctk.CTkFrame(self.det_hist, fg_color="transparent")
        hist_body.grid(row=1, column=0, sticky="nsew", padx=8, pady=(2, 10))
        hist_body.grid_columnconfigure(0, weight=1)
        hist_body.grid_rowconfigure(0, weight=1)
        self.det_tree = make_tree(hist_body, hcols, height=6)
        self.det_tree.grid(row=0, column=0, sticky="nsew")
        from tkinter import ttk as _ttk
        xs = _ttk.Scrollbar(hist_body, orient="horizontal",
                            command=self.det_tree.xview)
        xs.grid(row=1, column=0, sticky="ew")
        self.det_tree.configure(xscrollcommand=xs.set)
        W.bind_tree_tooltips(self.det_tree)

        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        db, lang = self.app.db, self.app.lang
        tag_sel = self.tag_filter.get()
        tag = ""
        for k in config.KNOWN_TAGS:
            if tag_sel == self.app.t(f"tag_{k}"):
                tag = k
        term = self.search_var.get()
        rows = customers_model.search(db, term, tag=tag)
        W.fill_tree_chunked(self.tree, [{
            "iid": str(c["id"]),
            "values": (c["name"], c["phone"], c["wilaya"],
                       trust_badge_text(c["trust_score"]),
                       ", ".join(t(f"tag_{tg}", lang)
                                 for tg in (c["tags"] or "").split(",") if tg)),
            "tags": (self._color_tag(c["trust_score"]),),
        } for c in rows])
        self.render_detail()

    def _color_tag(self, score: int) -> str:
        if score >= config.TRUST_TRUSTED:
            return "good"
        if score >= config.TRUST_CAUTION:
            return ""
        return "danger"

    # ------------------------------------------------------------------

    def on_select(self, _e=None) -> None:
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None
        self.render_detail()

    def render_detail(self) -> None:
        """Update the static detail skeleton in place (v1.7.4: no full
        rebuild per click — the old one destroyed ~20 widgets + 3 per
        history order on every selection)."""
        db, lang = self.app.db, self.app.lang
        cust = (customers_model.get(db, self.selected_id)
                if self.selected_id else None)
        if not cust:
            self.det_empty.grid(row=0, column=0, rowspan=3, sticky="nsew")
            for card in (self.det_head, self.det_meta, self.det_hist):
                card.grid_remove()
            return
        self.det_empty.grid_remove()
        for card in (self.det_head, self.det_meta, self.det_hist):
            card.grid()

        self.det_name.configure(text=cust["name"])
        self.det_phone.configure(text=cust["phone"])
        for w in self.det_trust_slot.winfo_children():
            w.destroy()
        TrustBadge(self.det_trust_slot, cust["trust_score"], lang).pack(anchor="w")
        for w in self.det_tags_slot.winfo_children():
            w.destroy()
        if cust["tags"]:
            tags_frame(self.det_tags_slot,
                       [x for x in cust["tags"].split(",") if x], lang).pack(
                           anchor="w", pady=(2, 0))

        # stats rows (small, rebuilt)
        for w in self.det_meta.winfo_children():
            w.destroy()
        meta = [(self.app.t("wilaya"), cust["wilaya"]),
                (self.app.t("address"), cust["address"]),
                (self.app.t("date"), cust["created_at"][:10])]
        lost = db.scalar(
            "SELECT COALESCE(SUM(shipping_cost),0)+COALESCE((SELECT SUM(price) FROM orders "
            "WHERE customer_id=? AND status='fake_payment'),0) FROM orders "
            "WHERE customer_id=? AND status IN ('ghosted','refused','phone_off','fake_payment')",
            (cust["id"], cust["id"])) or 0
        meta.append((self.app.t("cust_lost_money"), config.fmt_money(float(lost), lang)))
        inq = inquiries_model.stats_for_customer(db, cust["id"])
        meta.append((self.app.t("tw_contacts"),
                     f"{inq['contacts']} ({self.app.t('tw_conversion')}: "
                     f"{inq['conversion_rate']:.0f}%)"))
        if cust["notes"]:
            meta.append((self.app.t("notes"), cust["notes"]))
        for label, value in meta:
            row = ctk.CTkFrame(self.det_meta, fg_color="transparent")
            row.pack(fill="x", pady=1)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label, text_color=config.COLOR_FG_DIM,
                         font=F(11), anchor="w").grid(row=0, column=0,
                                                      sticky="w", padx=(14, 8))
            ctk.CTkLabel(row, text=str(value), font=F(12),
                         anchor="e" if lang == "ar" else "w").grid(
                             row=0, column=1, sticky="e", padx=(8, 14))

        # order history: chunked fill (any size, status-colored rows)
        hist = orders_model.list_for_customer(db, cust["id"])
        self.det_hist_lbl.configure(
            text=f"{self.app.t('cust_order_history')}  ({len(hist)})")
        W.fill_tree_chunked(self.det_tree, [{
            "iid": str(o["id"]),
            "values": (o["id"], o["date"], o["product"],
                       config.fmt_money(o["price"], lang),
                       W.status_badge_text(o["status"], lang)),
            "tags": (row_tag(o["status"]),),
        } for o in hist])


    def quick_add(self) -> None:
        """Paste a line -> parsed fields -> create the customer."""
        from .quick_add import QuickAddDialog
        dlg = QuickAddDialog(self, self.app)
        self.wait_window(dlg)
        parsed = dlg.result
        if not parsed or not parsed.get("phone"):
            return
        db = self.app.db
        existing = customers_model.find_by_phone(db, parsed["phone"])
        if existing:
            self.app.toast(f"ℹ️ {existing['name']} — {existing['phone']}", "warn")
            self.focus_customer(existing["id"])
            return
        customers_model.create(db, parsed["name"] or parsed["phone"], parsed["phone"],
                               wilaya=parsed["wilaya"], address=parsed["address"])
        self.app.toast(self.app.t("cust_added"), "ok")
        self.refresh()

    def show_duplicates(self) -> None:
        from .duplicates_ui import DuplicatesDialog
        DuplicatesDialog(self, self.app, on_merged=lambda: self.refresh())

    def focus_customer(self, cid: int) -> None:
        """Select one customer (global search / quick add jump here)."""
        self.selected_id = cid
        try:
            self.tree.selection_set(str(cid))
            self.tree.focus(str(cid))
            self.tree.see(str(cid))
        except tk.TclError:
            self.after(80, lambda: self.focus_customer(cid))   # row arriving
            return
        self.render_detail()

    def add_customer(self) -> None:
        CustomerDialog(self, self.app, on_saved=lambda: self.refresh())

    def edit_customer(self) -> None:
        if self.selected_id:
            CustomerDialog(self, self.app, customer_id=self.selected_id,
                           on_saved=lambda: self.refresh())

    def delete_customer(self) -> None:
        if not self.selected_id:
            return
        if messagebox.askyesno("Himaya", self.app.t("delete_confirm")):
            customers_model.delete(self.app.db, self.selected_id)
            self.selected_id = None
            self.app.toast(self.app.t("cust_deleted"), "ok")
            self.refresh()

    def blacklist_customer(self) -> None:
        if not self.selected_id:
            return
        cust = customers_model.get(self.app.db, self.selected_id)
        if not cust:
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Himaya")
        dlg.configure(fg_color=config.COLOR_BG_2)
        dlg.geometry("420x200")
        dlg.transient(self.winfo_toplevel())
        ctk.CTkLabel(dlg, text=f"{self.app.t('cust_blacklist_btn')} : {cust['phone']}",
                     font=F(14, "bold")).pack(pady=(16, 6))
        reason = ctk.CTkEntry(dlg, width=340, placeholder_text=self.app.t("cust_blacklist_prompt"))
        reason.pack(pady=4)
        sev = ctk.CTkOptionMenu(dlg, values=["1", "2", "3"], width=100)
        sev.set("2")
        sev.pack(pady=4)

        def do_it() -> None:
            blacklist_model.add(self.app.db, cust["phone"],
                                reason=reason.get().strip(), severity=int(sev.get()))
            trust.refresh(self.app.db, cust["id"])
            dlg.destroy()
            self.app.toast("✓ " + self.app.t("reason_blacklisted"), "err")
            self.refresh()

        ctk.CTkButton(dlg, text=self.app.t("confirm"), fg_color=config.COLOR_RED,
                      command=do_it).pack(pady=8)


class CustomerDialog(HimayaDialog):
    """Add / edit customer form with instant phone risk check."""

    def __init__(self, master, app, customer_id: int | None = None, on_saved=None):
        super().__init__(master)
        self.app = app
        self.customer_id = customer_id
        self.on_saved = on_saved
        editing = customer_id is not None
        self.title(self.app.t("edit" if editing else "cust_add"))
        self.configure(fg_color=config.COLOR_BG_2)
        fit_geometry(self, 440, 520)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

        ctk.CTkLabel(self, text=self.app.t("edit" if editing else "cust_add"),
                     font=F(18, "bold")).pack(pady=(16, 4))

        fields = [("name", app.t("name")), ("phone", app.t("phone")),
                  ("address", app.t("address")), ("notes", app.t("notes"))]
        self.vars: dict[str, tk.StringVar] = {}
        for key, label in fields:
            ctk.CTkLabel(self, text=label, font=F(12), anchor="w").pack(
                fill="x", padx=24, pady=(8, 0))
            var = tk.StringVar()
            self.vars[key] = var
            ent = ctk.CTkEntry(self, textvariable=var, width=390,
                               justify="right" if key == "notes" and app.lang == "ar" else "left")
            ent.pack(padx=24, pady=(0, 0))

        ctk.CTkLabel(self, text=app.t("wilaya"), font=F(12), anchor="w").pack(
            fill="x", padx=24, pady=(8, 0))
        self.wilaya = ctk.CTkComboBox(self, values=WILAYA_NAMES_FR, width=390)
        self.wilaya.pack(padx=24)
        from .widgets import wheel_combo
        wheel_combo(self.wilaya, WILAYA_NAMES_FR)

        if editing:
            c = customers_model.get(app.db, customer_id)
            for k in self.vars:
                self.vars[k].set(c[k] or "")
            self.wilaya.set(c["wilaya"] or WILAYA_NAMES_FR[0])

        self.risk_lbl = ctk.CTkLabel(self, text="", font=F(11, "bold"))
        self.risk_lbl.pack(pady=(6, 0))
        # instant risk check while typing the phone
        self.vars["phone"].trace_add("write", lambda *_: self.live_check())

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=14)
        ctk.CTkButton(btns, text=app.t("cancel"), fg_color="transparent",
                      text_color=config.COLOR_FG_DIM, border_width=1,
                      command=self.destroy).pack(side="right", padx=4)
        ctk.CTkButton(btns, text=app.t("save"), width=120,
                      command=self.save).pack(side="right", padx=4)

    def live_check(self) -> None:
        from ..services.phone import phone_risk, DANGER, CAUTION
        phone = self.vars["phone"].get()
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

    def save(self) -> None:
        from ..services.phone import normalize_phone, phone_risk, DANGER
        name = self.vars["name"].get().strip()
        phone = self.vars["phone"].get().strip()
        if not name or not phone:
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        if not normalize_phone(phone):
            self.app.toast(self.app.t("invalid_phone"), "warn")
            return
        existing = customers_model.find_by_phone(self.app.db, phone)
        if existing and existing["id"] != self.customer_id:
            self.app.toast(self.app.t("cust_phone_exists", name=existing["name"]), "err")
            return

        def persist() -> None:
            if self.customer_id:
                customers_model.update(self.app.db, self.customer_id, name=name, phone=phone,
                                       wilaya=self.wilaya.get(),
                                       address=self.vars["address"].get().strip(),
                                       notes=self.vars["notes"].get().strip())
                trust.refresh(self.app.db, self.customer_id)
                self.app.toast(self.app.t("cust_updated"), "ok")
            else:
                cid = customers_model.create(self.app.db, name, phone,
                                             wilaya=self.wilaya.get(),
                                             address=self.vars["address"].get().strip(),
                                             notes=self.vars["notes"].get().strip())
                trust.refresh(self.app.db, cid)
                self.app.toast(self.app.t("cust_added"), "ok")
            self.close()
            if self.on_saved:
                self.on_saved()

        # scam alert on save if the number is dangerous
        risk = phone_risk(self.app.db, phone)
        if risk["level"] == DANGER and not self.customer_id:
            from .widgets import ScamAlert
            ScamAlert(self, self.app, risk, on_continue=persist)
        else:
            persist()
