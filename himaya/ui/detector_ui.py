"""
Fake BaridiMob receipt detector page: drop zone (optional tkinterdnd2),
analysis, verdict banner with reasons, evidence saving, one-click blacklist.
"""

from __future__ import annotations

import threading
from pathlib import Path

import customtkinter as ctk
from tkinter import filedialog

from .. import config
from ..models import blacklist as blacklist_model
from ..models import settings_store
from ..services import detector
from .widgets import F

try:  # optional native drag & drop (strictly optional, never crash)
    from tkinterdnd2 import DND_FILES
except Exception:
    DND_FILES = None


class DetectorPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=config.COLOR_BG)
        self.app = app
        self.analysis: dict | None = None
        self.image_path: str | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text=app.t("det_title"), font=F(22, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 0))
        ctk.CTkLabel(self, text=app.t("det_desc"), font=F(12),
                     text_color=config.COLOR_FG_DIM, anchor="w", justify="left",
                     wraplength=900).grid(row=1, column=0, sticky="ew", padx=16)

        # ---- drop zone -----------------------------------------------------
        self.drop = ctk.CTkButton(
            self, text=app.t("det_drop"), font=F(16), height=150,
            fg_color=config.COLOR_BG_2, hover_color=config.COLOR_BG_3,
            border_width=2, border_color=config.COLOR_ACCENT, corner_radius=14,
            text_color=config.COLOR_FG, command=self.browse)
        self.drop.grid(row=2, column=0, sticky="ew", padx=16, pady=10)
        if DND_FILES is not None and getattr(app, "dnd_enabled", False):
            try:
                self.drop.drop_target_register(DND_FILES)
                self.drop.dnd_bind("<<Drop>>", self.on_drop)
            except Exception:
                pass

        # ---- result panel ------------------------------------------------------
        self.result = ctk.CTkScrollableFrame(self, fg_color=config.COLOR_BG_2,
                                             corner_radius=12)
        self.result.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.result.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.result, text="—", text_color=config.COLOR_FG_DIM
                     ).pack(pady=40)

        # actions bar
        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkButton(self.actions, text=app.t("det_analyze"), width=140,
                      command=self.run_analysis).pack(side="left", padx=(0, 8))
        self.save_btn = ctk.CTkButton(self.actions, text=app.t("det_save_evidence"),
                                      width=170, fg_color=config.COLOR_ORANGE,
                                      hover_color="#d35400",
                                      command=self.save_evidence, state="disabled")
        self.save_btn.pack(side="left", padx=4)
        self.blacklist_btn = ctk.CTkButton(self.actions,
                                           text=app.t("det_blacklist_from_result"),
                                           width=180, fg_color=config.COLOR_RED,
                                           hover_color="#c0392b",
                                           command=self.blacklist_from_result,
                                           state="disabled")
        self.blacklist_btn.pack(side="left", padx=4)

    # ------------------------------------------------------------------

    def browse(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All", "*.*")])
        if path:
            self.set_image(path)

    def on_drop(self, event) -> None:
        # tkinterdnd2 gives {path with spaces} or multiple paths
        path = event.data.strip().strip("{}")
        if path:
            self.set_image(path.split("} {")[0])

    def set_image(self, path: str) -> None:
        self.image_path = path
        name = Path(path).name
        self.drop.configure(text=f"📄 {name}")

    # ------------------------------------------------------------------

    def run_analysis(self) -> None:
        if not self.image_path:
            self.app.toast(self.app.t("det_no_image"), "warn")
            return
        tesseract = settings_store.get_setting(self.app.db, "tesseract_path", "")

        # clear panel + busy state
        for w in self.result.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.result, text=self.app.t("det_analyzing"),
                     text_color=config.COLOR_FG_DIM, font=F(14)).pack(pady=40)

        def work() -> None:
            res = detector.analyze(self.image_path, self.app.db,
                                   tesseract_cmd=tesseract)
            self.after(0, lambda: self.render_result(res))

        threading.Thread(target=work, daemon=True).start()

    def render_result(self, res: dict) -> None:
        self.analysis = res
        for w in self.result.winfo_children():
            w.destroy()

        verdict = res["verdict"]
        color = {"real": config.COLOR_GREEN, "fake": config.COLOR_RED,
                 "suspicious": config.COLOR_ORANGE}[verdict]
        banner = ctk.CTkFrame(self.result, fg_color=color, corner_radius=10)
        banner.pack(fill="x", pady=(8, 8), padx=10)
        ctk.CTkLabel(banner, text=self.app.t(f"det_{verdict}"), text_color="#101216",
                     font=F(18, "bold")).pack(pady=(10, 0))
        ctk.CTkLabel(banner,
                     text=f"{self.app.t('det_confidence')} : {res['confidence']}%",
                     text_color="#101216", font=F(12, "bold")).pack(pady=(0, 10))

        # extracted data
        ex = res.get("extracted", {})
        exbox = ctk.CTkFrame(self.result, fg_color=config.COLOR_BG, corner_radius=10)
        exbox.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(exbox, text=self.app.t("det_extracted"), font=F(13, "bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        rows = [(self.app.t("amount"), ex.get("amount") or "—"),
                (self.app.t("det_ocr_date"), ex.get("date") or "—"),
                (self.app.t("det_ref"), ex.get("ref") or "—"),
                (self.app.t("phone"), ex.get("phone") or "—"),
                (self.app.t("det_hash"), res.get("hash", "—"))]
        for label, value in rows:
            r = ctk.CTkFrame(exbox, fg_color="transparent")
            r.pack(fill="x", padx=12)
            ctk.CTkLabel(r, text=label, font=F(11), text_color=config.COLOR_FG_DIM,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(r, text=str(value), font=F(12), anchor="e").pack(side="right")
        ctk.CTkLabel(exbox, text="").pack()

        # reasons
        ctk.CTkLabel(self.result, text=self.app.t("det_reasons"), font=F(13, "bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        for code, detail in res.get("reasons", []):
            base = code.split("::")[0]
            txt = self.app.t(f"r_{base}", d=detail)
            rcol = config.COLOR_RED if base in detector._RED_FLAGS else (
                config.COLOR_YELLOW if base in detector._YELLOW_FLAGS else config.COLOR_FG_DIM)
            ctk.CTkLabel(self.result, text=f"• {txt}", font=F(12), text_color=rcol,
                         anchor="w", justify="left").pack(fill="x", padx=14, pady=1)

        self.save_btn.configure(state="normal")
        self.blacklist_btn.configure(state="normal")

        # learning: the seller's verdict tunes the local reason weights
        fb = ctk.CTkFrame(self.result, fg_color="transparent")
        fb.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(fb, text="🧠", font=F(13)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(fb, text=self.app.t("det_fb_real"), height=28,
                      fg_color=config.COLOR_GREEN, hover_color="#27ae60",
                      command=lambda: self.give_feedback("real")
                      ).pack(side="left", padx=4)
        ctk.CTkButton(fb, text=self.app.t("det_fb_fake"), height=28,
                      fg_color=config.COLOR_RED, hover_color="#c0392b",
                      command=lambda: self.give_feedback("fake")
                      ).pack(side="left", padx=4)

    def give_feedback(self, verdict: str) -> None:
        """Remember the human verdict for the reasons that fired (local)."""
        if not self.analysis:
            return
        detector.record_feedback(self.app.db,
                                 self.analysis.get("reasons", []), verdict)
        self.app.toast(self.app.t("det_learned"), "ok")

    # ------------------------------------------------------------------

    def save_evidence(self) -> None:
        if not self.analysis:
            return
        detector.save_evidence(self.app.db, self.analysis)
        self.app.toast(self.app.t("det_evidence_saved"), "ok")

    def blacklist_from_result(self) -> None:
        if not self.analysis:
            return
        phone = (self.analysis.get("extracted") or {}).get("phone", "") or ""
        reason = (f"Faux reçu détecté ({self.analysis['confidence']}%) — "
                  f"{Path(self.analysis['path']).name}")
        if phone:
            blacklist_model.add(self.app.db, phone, reason=reason, severity=3)
            self.app.toast("🚨 " + phone, "err")
        else:
            self.app.toast(self.app.t("det_no_image"), "warn")
