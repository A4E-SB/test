"""
Reusable widgets: stat cards, tag pills, dark ttk.Treeview styling,
a canvas bar-chart and the scam-alert popup.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from .. import config
from ..i18n import t

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"


def F(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


# ---------------------------------------------------------------------------
# Dark ttk.Treeview (used for all tables)
# ---------------------------------------------------------------------------

def make_tree(master, columns: list[tuple[str, str, int]], rid: bool = False,
              height: int = 14) -> ttk.Treeview:
    """
    columns: list of (col_id, heading, width_px). Creates a dark Treeview.
    rid: add a leading full-width '#0' column for ids.
    """
    style = ttk.Style(master)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("Himaya.Treeview", background=config.COLOR_BG_2,
                    fieldbackground=config.COLOR_BG, foreground=config.COLOR_FG,
                    rowheight=32, borderwidth=0, font=(FONT_FAMILY, 11))
    style.configure("Himaya.Treeview.Heading", background=config.COLOR_BG_3,
                    foreground=config.COLOR_FG, font=(FONT_FAMILY, 11, "bold"),
                    relief="flat", borderwidth=0)
    style.map("Himaya.Treeview", background=[("selected", config.COLOR_ACCENT)],
              foreground=[("selected", "#ffffff")])
    style.map("Himaya.Treeview.Heading", background=[("active", config.COLOR_BG_3)])

    cols = [c[0] for c in columns]
    tree = ttk.Treeview(master, columns=cols, show="headings", height=height,
                        style="Himaya.Treeview", selectmode="extended")
    for cid, heading, width in columns:
        tree.heading(cid, text=heading)
        tree.column(cid, width=width, anchor="w")
    # row color tags
    tree.tag_configure("danger", foreground=config.COLOR_RED)
    tree.tag_configure("caution", foreground=config.COLOR_YELLOW)
    tree.tag_configure("good", foreground=config.COLOR_GREEN)
    tree.tag_configure("dim", foreground=config.COLOR_FG_DIM)
    return tree


# ---------------------------------------------------------------------------
# Stat card (dashboard)
# ---------------------------------------------------------------------------

def wheel_combo(combo, values: list[str], wrap: bool = True) -> None:
    """
    Mouse-wheel cycling for CTkComboBox (e.g. the 58 wilayas).

    The native dropdown menu doesn't scroll with the wheel on Windows, so the
    widget itself cycles through its values instead: scroll up = previous,
    scroll down = next.
    """
    vals = list(values) or ["—"]

    def step(delta: int, _event=None) -> str:
        try:
            cur = combo.get()
            idx = vals.index(cur) if cur in vals else -1
        except Exception:
            idx = -1
        idx += delta
        if wrap:
            idx %= len(vals)
        else:
            idx = max(0, min(len(vals) - 1, idx))
        combo.set(vals[idx])
        return "break"

    def bind_all(widget) -> None:
        widget.bind("<MouseWheel>", lambda e: step(1 if (e.delta or 0) < 0 else -1))
        widget.bind("<Button-4>", lambda e: step(-1))   # Linux scroll up
        widget.bind("<Button-5>", lambda e: step(1))    # Linux scroll down

    bind_all(combo)
    # the combobox is a frame around an entry/button: wheel events over the
    # text field only fire on the entry, so bind it too (if present)
    entry = getattr(combo, "entry", None)
    if entry is not None:
        try:
            bind_all(entry)
        except Exception:
            pass


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str = "—",
                 color: str = config.COLOR_ACCENT, sub: str = "", on_click=None):
        super().__init__(master, fg_color=config.COLOR_BG_2, corner_radius=12)
        self._on_click = on_click
        self.grid_columnconfigure(0, weight=1)
        bar = ctk.CTkFrame(self, fg_color=color, width=4, corner_radius=2)
        bar.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(8, 0), pady=10)
        self.title_lbl = ctk.CTkLabel(self, text=title, text_color=config.COLOR_FG_DIM,
                                      font=F(11), justify="left", anchor="w")
        self.title_lbl.grid(row=0, column=1, sticky="ew", padx=(10, 12), pady=(12, 0))
        self.value_lbl = ctk.CTkLabel(self, text=value, text_color=color,
                                      font=F(24, "bold"), justify="left", anchor="w")
        self.value_lbl.grid(row=1, column=1, sticky="ew", padx=(10, 12))
        self.sub_lbl = ctk.CTkLabel(self, text=sub, text_color=config.COLOR_FG_DIM,
                                    font=F(10), justify="left", anchor="w")
        self.sub_lbl.grid(row=2, column=1, sticky="ew", padx=(10, 12), pady=(0, 10))
        if not sub:
            self.sub_lbl.grid_remove()
        if on_click:                    # labels exist now -> safe to bind
            self._make_clickable()

    def set(self, value: str, sub: str = "") -> None:
        self.value_lbl.configure(text=value)
        if sub:
            self.sub_lbl.configure(text=sub)
            self.sub_lbl.grid()
        else:
            self.sub_lbl.grid_remove()

    def _make_clickable(self) -> None:
        """Whole card reacts to the cursor + click (cards navigate the app)."""
        try:
            self.configure(cursor="hand2")
        except Exception:
            pass
        widgets = [self, self.title_lbl, self.value_lbl, self.sub_lbl]
        for w in widgets:
            w.bind("<Button-1>", lambda _e: (self._on_click or (lambda: None))())


# ---------------------------------------------------------------------------
# Tag pill + status colors (maps live in config, re-exported for convenience)
# ---------------------------------------------------------------------------

TAG_COLORS = config.TAG_COLORS
STATUS_COLORS = config.STATUS_COLORS


class TagPill(ctk.CTkLabel):
    """Small colored rounded tag."""

    def __init__(self, master, text: str, color: str):
        super().__init__(master, text=text, fg_color=color, text_color="#101216",
                         corner_radius=10, font=F(10, "bold"), height=22, padx=2)
        self.configure(anchor="center")


def tags_frame(master, tags: list[str], lang: str) -> ctk.CTkFrame:
    """Frame containing one pill per tag (auto tag keys)."""
    fr = ctk.CTkFrame(master, fg_color="transparent")
    for i, tag in enumerate(tags):
        pill = TagPill(fr, t(f"tag_{tag}", lang), TAG_COLORS.get(tag, config.COLOR_FG_DIM))
        pill.grid(row=0, column=i, padx=(0, 6))
    return fr


# ---------------------------------------------------------------------------
# Trust score bar
# ---------------------------------------------------------------------------

class TrustBar(ctk.CTkFrame):
    def __init__(self, master, score: int = 50, lang: str = "fr"):
        super().__init__(master, fg_color="transparent")
        self.lang = lang
        self.bar = ctk.CTkProgressBar(self, height=14, corner_radius=7)
        self.bar.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.lbl = ctk.CTkLabel(self, text="", font=F(12, "bold"))
        self.lbl.grid(row=0, column=1)
        self.grid_columnconfigure(0, weight=1)
        self.set(score)

    def set(self, score: int) -> None:
        score = max(0, min(100, int(score)))
        color = config.COLOR_GREEN if score >= config.TRUST_TRUSTED else (
            config.COLOR_YELLOW if score >= config.TRUST_CAUTION else config.COLOR_RED)
        self.bar.configure(progress_color=color)
        self.bar.set(score / 100.0)
        self.lbl.configure(text=f"{score}/100", text_color=color)


# ---------------------------------------------------------------------------
# Canvas bar chart (revenue vs losses) — no matplotlib, keeps the app small
# ---------------------------------------------------------------------------

class BarChart(ctk.CTkCanvas):
    """Grouped bars (two series) drawn on a canvas; redraws on resize."""

    def __init__(self, master, lang: str = "fr", bg: str = config.COLOR_BG,
                 height: int = 240):
        super().__init__(master, bg=bg, highlightthickness=0, height=height)
        self.lang = lang
        self.series: list[dict] = []
        self.legend1 = t("dash_chart_revenue", lang)
        self.legend2 = t("dash_chart_losses", lang)
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, series: list[dict]) -> None:
        self.series = series or []
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60 or h < 60 or not self.series:
            return
        pad_l, pad_b, pad_t = 56, 44, 26
        plot_w, plot_h = w - pad_l - 16, h - pad_b - pad_t
        n = len(self.series)
        max_v = max((max(s["revenue"], s["losses"]) for s in self.series), default=1) or 1
        # round up to a nice value
        mag = 10 ** len(str(int(max_v)))
        top = ((max_v // (mag / 10)) + 1) * (mag / 10)

        self.configure(bg=config.COLOR_BG)
        # gridlines + y labels
        for i in range(5):
            y = pad_t + plot_h * (1 - i / 4)
            self.create_line(pad_l, y, w - 12, y, fill="#262a33")
            v = top * i / 4
            lbl = f"{v:,.0f}".replace(",", " ")
            self.create_text(pad_l - 8, y, text=lbl, anchor="e", fill=config.COLOR_FG_DIM,
                             font=(FONT_FAMILY, 9))

        group_w = plot_w / n
        bar_w = min(34, group_w / 3.2)
        for i, s in enumerate(self.series):
            x0 = pad_l + i * group_w + group_w / 2
            h1 = plot_h * (s["revenue"] / top)
            h2 = plot_h * (s["losses"] / top)
            self.create_rectangle(x0 - bar_w - 2, pad_t + plot_h - h1, x0 - 2,
                                  pad_t + plot_h, fill=config.COLOR_ACCENT, width=0)
            self.create_rectangle(x0 + 2, pad_t + plot_h - h2, x0 + bar_w + 2,
                                  pad_t + plot_h, fill=config.COLOR_RED, width=0)
            self.create_text(x0, pad_t + plot_h + 14, text=s["label"],
                             fill=config.COLOR_FG_DIM, font=(FONT_FAMILY, 9))

        # legend
        lx = pad_l + 4
        self.create_rectangle(lx, 6, lx + 10, 16, fill=config.COLOR_ACCENT, width=0)
        self.create_text(lx + 16, 11, text=self.legend1, anchor="w",
                         fill=config.COLOR_FG_DIM, font=(FONT_FAMILY, 10))
        lx2 = lx + 100 + 24
        self.create_rectangle(lx2, 6, lx2 + 10, 16, fill=config.COLOR_RED, width=0)
        self.create_text(lx2 + 16, 11, text=self.legend2, anchor="w",
                         fill=config.COLOR_FG_DIM, font=(FONT_FAMILY, 10))


# ---------------------------------------------------------------------------
# Scam alert popup
# ---------------------------------------------------------------------------

class ScamAlert(ctk.CTkToplevel):
    """
    Red modal popup shown whenever a risky phone number is detected.
    on_block / on_continue are optional callbacks (used by the order dialog).
    """

    def __init__(self, master, app, risk: dict, on_block=None, on_continue=None,
                 show_block_btn: bool = True):
        super().__init__(master)
        from ..services.phone import DANGER
        lang = app.lang
        danger = risk["level"] == DANGER
        color = config.COLOR_RED if danger else config.COLOR_ORANGE
        self.title("Himaya")
        self.configure(fg_color=config.COLOR_BG_2)
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.grab_set()

        ctk.CTkLabel(self, text=t("scam_alert", lang), text_color=color,
                     font=F(22, "bold")).pack(pady=(18, 4))
        phone_disp = risk.get("phone", "")
        ctk.CTkLabel(self, text=phone_disp, font=F(28, "bold"),
                     text_color=config.COLOR_FG).pack()
        ctk.CTkLabel(self, text=t("scam_danger_body" if danger else "scam_caution_body", lang),
                     text_color=color, font=F(13)).pack(pady=(0, 8))

        # reasons box
        box = ctk.CTkScrollableFrame(self, fg_color=config.COLOR_BG, height=150,
                                     corner_radius=8, label_text=t("det_reasons", lang))
        box.pack(fill="both", expand=True, padx=18, pady=4)
        for code in risk.get("reasons", []):
            base = code.split("::")[0]
            detail = code.split("::", 1)[1] if "::" in code else ""
            txt = t(f"reason_{base}", lang, d=detail)
            ctk.CTkLabel(box, text=f"• {txt}", anchor="w", justify="left",
                         text_color=config.COLOR_FG, font=F(12)).pack(anchor="w", pady=2)

        if risk.get("fake_count"):
            ctk.CTkLabel(self, text=f"{t('scam_fake_count', lang)} : {risk['fake_count']}",
                         text_color=config.COLOR_RED, font=F(12, "bold")).pack()
        if risk.get("lost_money"):
            from ..config import fmt_money
            ctk.CTkLabel(self, text=f"{t('scam_lost_with_him', lang)} : "
                                    f"{fmt_money(risk['lost_money'], lang)}",
                         text_color=config.COLOR_RED, font=F(12, "bold")).pack()

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=14)
        if show_block_btn and on_block:
            ctk.CTkButton(btns, text=t("scam_block_order", lang), fg_color=config.COLOR_RED,
                          hover_color="#c0392b", command=lambda: self._close(on_block)
                          ).pack(side="left", padx=(0, 8))
        if on_continue:
            ctk.CTkButton(btns, text=t("scam_proceed", lang), fg_color=config.COLOR_BG_3,
                          text_color=config.COLOR_FG,
                          command=lambda: self._close(on_continue)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text=t("close", lang), fg_color="transparent",
                      text_color=config.COLOR_FG_DIM, border_width=1,
                      command=lambda: self._close(None)).pack(side="right")

    def _close(self, cb) -> None:
        self.grab_release()
        self.destroy()
        if cb:
            cb()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def row_tag(status: str) -> str:
    """Treeview color tag for an order status."""
    if status in ("ghosted", "fake_payment", "blocked"):
        return "danger"
    if status in ("refused", "phone_off"):
        return "caution"
    if status in ("delivered", "paid"):
        return "good"
    return "dim" if status in ("canceled", "pending") else ""


def center(win, master) -> None:
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    x = master.winfo_rootx() + (master.winfo_width() - w) // 2
    y = master.winfo_rooty() + (master.winfo_height() - h) // 3
    win.geometry(f"+{max(0, x)}+{max(0, y)}")


def copy_to_clipboard(widget: tk.Misc, text: str) -> None:
    """Copy text to the OS clipboard (for Messenger / WhatsApp Web pasting)."""
    top = widget.winfo_toplevel()
    top.clipboard_clear()
    top.clipboard_append(text)
    top.update()  # keep clipboard after app closes on Windows
