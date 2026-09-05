"""
Time-Waster Tracker: inquiry log, conversion stats, deposit suggestions and
the bilingual (AR/FR) smart-reply templates with copy-to-clipboard.
"""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .. import config
from ..models import customers as customers_model
from ..models import inquiries as inquiries_model
from ..models import settings_store
from ..models import templates_store
from ..services import trust
from .widgets import F, copy_to_clipboard, make_tree

CATEGORY_KEYS = {"deposit": "tw_cat_deposit", "negotiation": "tw_cat_negotiation",
                 "ghost": "tw_cat_ghost", "warning": "tw_cat_warning",
                 "loyalty": "tw_cat_loyalty",
                 "general": "tw_cat_general"}


class TimeWastersPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=app.t("tw_title"), font=F(22, "bold"),
                     anchor="w").grid(row=0, column=0, columnspan=2, sticky="ew",
                                      padx=16, pady=(10, 2))
        ctk.CTkLabel(self, text=app.t("tw_desc"), font=F(12),
                     text_color=config.COLOR_FG_DIM, anchor="w", justify="left",
                     wraplength=900).grid(row=0, column=0, columnspan=2, sticky="ew",
                                          padx=16, pady=(0, 6))

        # ---------------- left: log + stats + suggestions ----------------
        left = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 6), pady=(0, 16))
        left.grid_columnconfigure(0, weight=1)

        # log form
        form = ctk.CTkFrame(left, fg_color="transparent")
        form.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(form, text=app.t("tw_log"), font=F(13, "bold"),
                     anchor="w").pack(fill="x")
        db = app.db
        custs = customers_model.all_customers(db)
        self.cust_labels = {f"{c['name']} — {c['phone']}": c["id"] for c in custs}
        self.cust_combo = ctk.CTkComboBox(form, values=list(self.cust_labels.keys()) or ["—"])
        if custs:
            self.cust_combo.set(list(self.cust_labels.keys())[0])
        self.cust_combo.pack(fill="x", pady=2)
        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", pady=2)
        self.platform = ctk.CTkOptionMenu(row2, values=config.PLATFORMS, width=140)
        self.platform.set("Messenger")
        self.platform.pack(side="left", padx=(0, 6))
        self.converted = ctk.CTkSwitch(row2, text=app.t("tw_converted"))
        self.converted.pack(side="left", padx=4)
        self.inq_notes = tk.StringVar()
        ctk.CTkEntry(form, textvariable=self.inq_notes,
                     placeholder_text=app.t("notes")).pack(fill="x", pady=2)
        ctk.CTkButton(form, text=app.t("tw_log"), height=32,
                      command=self.log_inquiry).pack(pady=4)

        # global conversion
        self.conv_lbl = ctk.CTkLabel(left, text="", font=F(13, "bold"),
                                     text_color=config.COLOR_ACCENT)
        self.conv_lbl.pack(pady=(6, 2))

        # deposit suggestions
        sug_box = ctk.CTkFrame(left, fg_color=config.COLOR_BG, corner_radius=10)
        sug_box.pack(fill="both", expand=False, padx=10, pady=6)
        self.sug_frame = ctk.CTkFrame(sug_box, fg_color="transparent")
        self.sug_frame.pack(fill="x", padx=8, pady=8)

        # recent inquiries
        cols = [("date", app.t("date"), 90), ("customer", app.t("ord_customer"), 170),
                ("platform", app.t("tw_platform"), 100),
                ("converted", app.t("tw_converted"), 90)]
        self.tree = make_tree(left, cols, height=8)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # ---------------- right: templates --------------------------------
        right = ctk.CTkFrame(self, fg_color=config.COLOR_BG_2, corner_radius=12)
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 16), pady=(0, 16))
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text=app.t("tw_templates"), font=F(15, "bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(10, 4))

        frow = ctk.CTkFrame(right, fg_color="transparent")
        frow.pack(fill="x", padx=12)
        self.cat_menu = ctk.CTkOptionMenu(
            frow, width=170, values=[app.t("all")] + [
                app.t(v) for v in CATEGORY_KEYS.values()],
            command=lambda _v: self.load_templates())
        self.cat_menu.pack(side="left")
        ctk.CTkLabel(right, text=app.t("tw_copy_hint"), font=F(10),
                     text_color=config.COLOR_FG_DIM, anchor="w").pack(fill="x", padx=12)

        self.tpl_frame = ctk.CTkScrollableFrame(right, fg_color="transparent")
        self.tpl_frame.pack(fill="both", expand=True, padx=8, pady=6)

        self.refresh()

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        db = self.app.db
        # rebuild customer combo (customers may have been added)
        custs = customers_model.all_customers(db)
        self.cust_labels = {f"{c['name']} — {c['phone']}": c["id"] for c in custs}
        self.cust_combo.configure(values=list(self.cust_labels.keys()) or ["—"])
        if custs:
            self.cust_combo.set(list(self.cust_labels.keys())[0])

        conv = inquiries_model.overall_conversion(db)
        self.conv_lbl.configure(
            text=f"{self.app.t('tw_conversion')} : {conv:.0f}%")

        self.tree.delete(*self.tree.get_children())
        for i in inquiries_model.recent(db, 30):
            conv_txt = "✓" if i["converted"] else "✗"
            self.tree.insert("", "end", values=(
                i["date"], i["customer_name"], i["platform"], conv_txt),
                tags=("good" if i["converted"] else "caution",))

        # deposit suggestions: >=3 non-converted contacts
        for w in self.sug_frame.winfo_children():
            w.destroy()
        rows = db.query(
            """SELECT c.id, c.name, c.phone, COUNT(*) n FROM inquiries i
               JOIN customers c ON c.id = i.customer_id
               WHERE i.converted = 0
               GROUP BY c.id HAVING n >= 3 ORDER BY n DESC LIMIT 5""")
        if rows:
            for r in rows:
                ctk.CTkLabel(self.sug_frame,
                             text=self.app.t("tw_suggest_deposit", name=r["name"],
                                             n=r["n"]),
                             font=F(12), text_color=config.COLOR_ORANGE,
                             anchor="w", justify="left", wraplength=330
                             ).pack(anchor="w", pady=2)
        else:
            ctk.CTkLabel(self.sug_frame, text=self.app.t("tw_no_suggest"), font=F(11),
                         text_color=config.COLOR_FG_DIM, anchor="w").pack(anchor="w")

        self.load_templates()

    def load_templates(self) -> None:
        db, lang = self.app.db, self.app.lang
        for w in self.tpl_frame.winfo_children():
            w.destroy()
        cat_sel = self.cat_menu.get()
        cat = ""
        for key, cat_key in CATEGORY_KEYS.items():
            if cat_sel == self.app.t(cat_key):
                cat = key
        tpl_list = (templates_store.by_category(db, cat) if cat
                    else templates_store.all_templates(db))
        for tpl in tpl_list:
            card = ctk.CTkFrame(self.tpl_frame, fg_color=config.COLOR_BG, corner_radius=10)
            card.pack(fill="x", pady=4, padx=4)
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=10, pady=(8, 0))
            cat_name = self.app.t(CATEGORY_KEYS.get(tpl["category"], "tw_cat_general"))
            ctk.CTkLabel(head, text=f"{tpl['name']}  [{cat_name}]", font=F(12, "bold"),
                         anchor="w").pack(side="left")
            body = tpl["text_ar"] if lang == "ar" else tpl["text_fr"]
            txt = ctk.CTkTextbox(card, height=76, fg_color="transparent",
                                 font=F(12), wrap="word")
            txt.insert("1.0", body)
            txt.configure(state="disabled")
            txt.pack(fill="x", padx=10, pady=4)
            foot = ctk.CTkFrame(card, fg_color="transparent")
            foot.pack(fill="x", padx=10, pady=(0, 8))
            ctk.CTkButton(foot, text=self.app.t("copy"), width=90, height=28,
                          command=lambda b=body: self.copy_tpl(b)).pack(side="right")

    def copy_tpl(self, body: str) -> None:
        """Copy template with the seller's CCP/BaridiMob info substituted."""
        db = self.app.db
        ccp = settings_store.get_setting(db, "ccp_number", "")
        name = settings_store.get_setting(db, "ccp_name", "")
        rip = settings_store.get_setting(db, "baridimob_rip", "")
        info = " / ".join(x for x in [f"CCP {ccp} {name}".strip(), f"RIP {rip}"] if x)
        text = body.replace("{ccp_info}", info or "CCP")
        copy_to_clipboard(self, text)
        self.app.toast(self.app.t("copied"), "ok")

    def log_inquiry(self) -> None:
        label = self.cust_combo.get()
        cid = self.cust_labels.get(label)
        if not cid:
            self.app.toast(self.app.t("fill_required"), "warn")
            return
        inquiries_model.log(self.app.db, cid, platform=self.platform.get(),
                            converted=bool(self.converted.get()),
                            notes=self.inq_notes.get().strip())
        trust.refresh(self.app.db, cid)
        self.inq_notes.set("")
        self.converted.deselect()
        self.app.toast(self.app.t("tw_saved"), "ok")
        self.refresh()
