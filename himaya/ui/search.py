"""
Global search (Ctrl+K): one query searches customers, orders, blacklist
and products at once; double-click jumps straight to the right page.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import config
from ..i18n import t
from .widgets import F, center, make_tree


class GlobalSearchDialog(ctk.CTkToplevel):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.title(app.t("gs_title"))
        self.configure(fg_color=config.COLOR_BG_2)
        self.geometry("640x480")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(self, text=app.t("gs_title"), font=F(16, "bold")
                     ).pack(pady=(14, 4))
        self.query = tk.StringVar()
        entry = ctk.CTkEntry(self, textvariable=self.query, width=560, height=36,
                             placeholder_text=app.t("gs_hint"))
        entry.pack(padx=20)
        entry.focus_set()
        self.query.trace_add("write", lambda *_: self.search())
        self.bind("<Escape>", lambda e: self.destroy())

        cols = [("kind", "", 110), ("main", app.t("name"), 220),
                ("sub", app.t("phone"), 150), ("extra", "", 130)]
        self.tree = make_tree(self, cols, height=14)
        self.tree.pack(fill="both", expand=True, padx=16, pady=10)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.status = ctk.CTkLabel(self, text="", font=F(11),
                                   text_color=config.COLOR_FG_DIM)
        self.status.pack(pady=(0, 10))
        self._results: dict[str, tuple[str, int]] = {}   # iid -> (page, row_id)
        center(self, master)

    # ------------------------------------------------------------------

    def search(self) -> None:
        db, lang = self.app.db, self.app.lang
        q = self.query.get().strip()
        self.tree.delete(*self.tree.get_children())
        self._results.clear()
        if len(q) < 2:
            self.status.configure(text="")
            return
        like = f"%{q}%"

        for c in db.query(
                "SELECT id, name, phone, wilaya FROM customers "
                "WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT 8", (like, like)):
            iid = f"c{c['id']}"
            self._results[iid] = ("customers", c["id"])
            self.tree.insert("", "end", iid=iid, values=(
                "👤 " + t("nav_customers", lang), c["name"], c["phone"], c["wilaya"]))

        for o in db.query(
                """SELECT o.id, o.product, o.price, o.status, c.name AS cname,
                          c.phone FROM orders o JOIN customers c
                   ON c.id = o.customer_id
                   WHERE o.product LIKE ? OR c.name LIKE ? OR c.phone LIKE ?
                   ORDER BY o.id DESC LIMIT 12""", (like, like, like)):
            iid = f"o{o['id']}"
            self._results[iid] = ("orders", o["id"])
            status_txt = t(f"st_{o['status']}", lang)
            self.tree.insert("", "end", iid=iid, values=(
                "📦 " + t("nav_orders", lang), o["product"], o["cname"],
                f"#{o['id']} • {status_txt}"))

        for b in db.query(
                "SELECT id, phone, reason FROM blacklist WHERE phone LIKE ? "
                "OR reason LIKE ? ORDER BY id DESC LIMIT 8", (like, like)):
            iid = f"b{b['id']}"
            self._results[iid] = ("transfer", b["id"])
            self.tree.insert("", "end", iid=iid, tags=("danger",), values=(
                "🚫 " + t("nav_transfer", lang), b["reason"][:60], b["phone"], ""))

        for p in db.query(
                "SELECT id, name, sale_price, quantity FROM products "
                "WHERE name LIKE ? LIMIT 8", (like,)):
            iid = f"p{p['id']}"
            self._results[iid] = ("products", p["id"])
            self.tree.insert("", "end", iid=iid, values=(
                "🛒 " + t("nav_products", lang), p["name"],
                f"{p['sale_price']:,.0f} DA".replace(",", " "), f"x{p['quantity']}"))

        n = len(self._results)
        self.status.configure(text="" if n else self.app.t("gs_no_results"))
        if n:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)

    # ------------------------------------------------------------------

    def open_selected(self) -> None:
        sel = self.tree.selection() or ([self.tree.focus()] if self.tree.focus() else [])
        if not sel:
            return
        page, row_id = self._results.get(sel[0], (None, None))
        if not page:
            return
        self.destroy()
        self.app.show_page(page)
        target = self.app.page
        if page == "customers" and hasattr(target, "focus_customer"):
            target.focus_customer(row_id)
        elif page == "orders" and hasattr(target, "focus_order"):
            target.focus_order(row_id)
        elif page == "products" and hasattr(target, "focus_product"):
            target.focus_product(row_id)
