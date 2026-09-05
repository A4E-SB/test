"""
Products & stock page: catalog CRUD, live stock levels, low-stock alerts.

Stock is automatically decremented when an order becomes "real" (confirmed,
shipped, delivered…) and released when it is canceled/blocked/deleted —
that logic lives in models/products.py (stock_effect + recomputes).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from .. import config
from ..models import products as products_model
from .widgets import F, make_tree, rtl_anchor, rtl_side
from .widgets import bind_tree_tooltips, card as surface


class ProductsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))
        ctk.CTkLabel(top, text=app.t("prod_title"), font=F(22, "bold"),
                 anchor=rtl_anchor(app)).pack(side=rtl_side(app))
        ctk.CTkButton(top, text=app.t("prod_add"), height=36,
                      fg_color=config.COLOR_GREEN, hover_color="#27ae60",
                      command=self.add_product).pack(side="right")

        list_frame = surface(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 8))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)
        cols = [("name", app.t("prod_name"), 250), ("cost", app.t("prod_cost"), 105),
                ("sale", app.t("prod_sale"), 105), ("margin", app.t("prod_margin"), 95),
                ("qty", app.t("prod_qty"), 75), ("low", app.t("col_low_stock"), 70),
                ("sold", app.t("prod_sold"), 80), ("status", app.t("status"), 105)]
        self.tree = make_tree(list_frame, cols, height=18)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        bind_tree_tooltips(self.tree)
        self.tree.bind("<Double-1>", lambda e: self.edit_product())
        self.tree.bind("<Delete>", lambda e: self.delete_product())

        bar = ctk.CTkFrame(list_frame, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        ctk.CTkButton(bar, text=app.t("edit"), height=26, width=80,
                      command=self.edit_product).pack(side="left", padx=2)
        ctk.CTkButton(bar, text=app.t("delete"), height=26, width=80,
                      fg_color=config.COLOR_RED, hover_color="#c0392b",
                      command=self.delete_product).pack(side="left", padx=2)
        self.count_lbl = ctk.CTkLabel(bar, text="", font=F(11),
                                      text_color=config.COLOR_FG_DIM)
        self.count_lbl.pack(side="right")
        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        db = self.app.db
        rows = products_model.all_products(db)
        # ONE grouped query for all sold counts (v1.1.4) — the previous
        # per-product COUNT did a full orders scan per catalog row
        sold_map = {r["product_id"]: r["n"] for r in db.query(
            "SELECT product_id, COUNT(*) AS n FROM orders "
            "WHERE product_id IS NOT NULL "
            "AND status NOT IN ('canceled','blocked') "
            "GROUP BY product_id")}
        self.tree.delete(*self.tree.get_children())
        for p in rows:
            margin = (p["sale_price"] - p["cost_price"]) if p["sale_price"] else 0
            low = p["quantity"] <= (p["low_stock"] or 0)
            sold = sold_map.get(p["id"], 0)
            self.tree.insert("", "end", iid=str(p["id"]), values=(
                p["name"], f"{p['cost_price']:,.0f}".replace(",", " "),
                f"{p['sale_price']:,.0f}".replace(",", " "),
                f"+{margin:,.0f}".replace(",", " ") if margin >= 0 else str(margin),
                p["quantity"], p["low_stock"] or 0, sold,
                self.app.t("prod_low_alert") if low else "—"),
                tags=("caution",) if low else ())
        n_low = len(products_model.low_stock_products(db))
        self.count_lbl.configure(
            text=f"{len(rows)} • " + (self.app.t("dash_low_stock") + f" : {n_low}"
                                      if n_low else "✓"))

    def _selected_id(self) -> int | None:
        sel = self.tree.selection() or ([self.tree.focus()] if self.tree.focus() else [])
        return int(sel[0]) if sel else None

    def add_product(self) -> None:
        ProductDialog(self, self.app, on_saved=lambda: self.refresh())

    def edit_product(self) -> None:
        pid = self._selected_id()
        if pid:
            ProductDialog(self, self.app, product_id=pid,
                          on_saved=lambda: self.refresh())

    def delete_product(self) -> None:
        pid = self._selected_id()
        if not pid:
            return
        used = self.app.db.scalar(
            "SELECT COUNT(*) FROM orders WHERE product_id = ?", (pid,)) or 0
        if used and not messagebox.askyesno(
                "Himaya", self.app.t("prod_delete_confirm", n=used)):
            return
        products_model.delete(self.app.db, pid)
        self.app.toast(self.app.t("prod_deleted"), "ok")
        self.refresh()

    def focus_product(self, pid: int) -> None:
        """Select one product (global search jumps here)."""
        self.tree.selection_set(str(pid))
        self.tree.focus(str(pid))
        self.tree.see(str(pid))


class ProductDialog(ctk.CTkToplevel):
    """Create / edit a catalog product."""

    def __init__(self, master, app, product_id: int | None = None, on_saved=None):
        super().__init__(master)
        self.app = app
        self.product_id = product_id
        self.on_saved = on_saved
        editing = product_id is not None
        self.title(self.app.t("edit" if editing else "prod_add"))
        self.configure(fg_color=config.COLOR_BG_2)
        self.geometry("420x330")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(self, text=self.app.t("edit" if editing else "prod_add"),
                     font=F(18, "bold")).pack(pady=(14, 4))

        self.name = tk.StringVar()
        self.cost = tk.StringVar()
        self.sale = tk.StringVar()
        self.qty = tk.StringVar()
        self.low = tk.StringVar()
        fields = [(self.name, "prod_name", 300), (self.cost, "prod_cost", 300),
                  (self.sale, "prod_sale", 300)]
        for var, key, width in fields:
            ctk.CTkLabel(self, text=app.t(key), font=F(12), anchor="w"
                         ).pack(fill="x", padx=24)
            ctk.CTkEntry(self, textvariable=var, width=width).pack(padx=24)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(8, 0))
        ctk.CTkLabel(row, text=app.t("prod_qty"), font=F(12)).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(row, textvariable=self.qty, width=90).pack(side="left", padx=(0, 14))
        ctk.CTkLabel(row, text=app.t("prod_low"), font=F(12)).pack(side="left", padx=(0, 6))
        ctk.CTkEntry(row, textvariable=self.low, width=90).pack(side="left")

        if editing:
            p = products_model.get(app.db, product_id)
            self.name.set(p["name"])
            self.cost.set(str(int(p["cost_price"])))
            self.sale.set(str(int(p["sale_price"])))
            self.qty.set(str(p["quantity"]))
            self.low.set(str(p["low_stock"] or 0))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=12)
        ctk.CTkButton(btns, text=app.t("cancel"), fg_color="transparent",
                      text_color=config.COLOR_FG_DIM, border_width=1,
                      command=self.destroy).pack(side="right", padx=4)
        ctk.CTkButton(btns, text=app.t("save"), width=110,
                      command=self.save).pack(side="right", padx=4)

    def save(self) -> None:
        db = self.app.db
        if not self.name.get().strip():
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        try:
            cost = float(self.cost.get().replace(",", ".") or 0)
            sale = float(self.sale.get().replace(",", ".") or 0)
            qty = int(self.qty.get() or 0)
            low = int(self.low.get() or 0)
        except ValueError:
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        if self.product_id:
            products_model.update(db, self.product_id, name=self.name.get().strip(),
                                  cost_price=cost, sale_price=sale,
                                  quantity=qty, low_stock=low)
        else:
            products_model.create(db, self.name.get().strip(), cost_price=cost,
                                  sale_price=sale, quantity=qty, low_stock=low)
        self.app.toast(self.app.t("prod_saved"), "ok")
        self.destroy()
        if self.on_saved:
            self.on_saved()
