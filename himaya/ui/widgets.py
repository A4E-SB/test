"""
Reusable widgets: stat cards, tag pills, dark ttk.Treeview styling,
a canvas bar-chart and the scam-alert popup.
"""

from __future__ import annotations

import sys
import functools
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from .. import config
from ..services.diagnostics import log_crash
from ..i18n import t

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
# v1.6 type scale: three weights only — 400 regular, 600 semibold (card
# numbers, active nav), 800 extrabold (page titles, hero number). Windows
# ships real families for each; when Inter TTFs are bundled later the
# families simply switch here (drop-in).
LATIN_FONT_FAMILY = "Segoe UI"
LATIN_FAMILY_SEMIBOLD = "Segoe UI Semibold"
LATIN_FAMILY_EXTRABOLD = "Segoe UI Black"
ARABIC_FONT_FAMILY = "Tajawal"        # bundled (OFL) in assets/fonts
FONT_FAMILY = LATIN_FONT_FAMILY       # swapped by set_ui_font() on language

_arabic_font_loaded = None            # cached result of load_arabic_font()


def load_arabic_font() -> bool:
    """
    Register the bundled Tajawal TTFs privately (session-only, no install)
    so Arabic renders with a real Arabic-native typeface instead of the
    OS fallback. Windows-only API; anywhere else the app keeps the Latin
    family (Arabic then falls back to the system Arabic font).
    """
    global _arabic_font_loaded
    if _arabic_font_loaded is not None:
        return _arabic_font_loaded
    fonts_dir = config.ASSETS_DIR / "fonts"
    files = sorted(fonts_dir.glob("Tajawal-*.ttf")) if fonts_dir.exists() else []
    ok = False
    if files and sys.platform == "win32":
        try:
            import ctypes
            for f in files:
                # FR_PRIVATE = 0x10: available to this process only
                ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)
            ok = True
        except Exception:
            ok = False
    _arabic_font_loaded = ok
    return ok


def set_ui_font(arabic: bool) -> None:
    """
    Point every NEWLY created widget at the right family. Called on launch
    and on language switch (the UI is fully rebuilt then, so one global is
    enough). Tajawal also covers Latin glyphs, so mixed FR/AR strings stay
    consistent.
    """
    global FONT_FAMILY
    if arabic and load_arabic_font():
        FONT_FAMILY = ARABIC_FONT_FAMILY
    else:
        FONT_FAMILY = LATIN_FONT_FAMILY


def F(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    """
    weight: "normal" (400) | "bold"/"semibold" (600) | "extrabold" (800).
    Latin mode maps weights to the real Windows families (Tk only knows
    normal/bold flags); Arabic keeps Tajawal with a bold flag.
    """
    fam, flag = _font_choice(weight)
    return ctk.CTkFont(family=fam, size=size, weight=flag)


def _font_choice(weight: str) -> tuple[str, str]:
    """Map a spec weight to (family, tk-weight-flag) for the current lang."""
    if FONT_FAMILY == ARABIC_FONT_FAMILY:
        flag = "bold" if weight in ("bold", "semibold", "extrabold") else "normal"
        return ARABIC_FONT_FAMILY, flag
    fam = {"semibold": LATIN_FAMILY_SEMIBOLD,
           "bold": LATIN_FAMILY_SEMIBOLD,
           "extrabold": LATIN_FAMILY_EXTRABOLD}.get(weight, LATIN_FONT_FAMILY)
    return fam, "normal"          # the family IS the weight


# ---------------------------------------------------------------------------
# Card surface (single source of truth for elevated containers)
# ---------------------------------------------------------------------------

def card(master, **kwargs) -> ctk.CTkFrame:
    """
    Elevated panel: lighter surface + thin 1px outline so cards read as
    cards on the page background (v1.2 UX pass — was same shade as page).
    """
    kwargs.setdefault("corner_radius", 12)
    return ctk.CTkFrame(master, fg_color=config.COLOR_CARD,
                        border_width=1, border_color=config.COLOR_BORDER,
                        **kwargs)


def _blend(base: str, tint: str, alpha: float) -> str:
    """Blend `tint` into `base` at `alpha` (0..1) -> #rrggbb (hex math)."""
    b = tuple(int(base[i:i + 2], 16) for i in (1, 3, 5))
    t = tuple(int(tint[i:i + 2], 16) for i in (1, 3, 5))
    mix = tuple(round(bt + (tn - bt) * alpha) for bt, tn in zip(b, t))
    return "#{:02x}{:02x}{:02x}".format(*mix)


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
        # minwidth = declared width: extra window space stretches the last
        # columns, but a smaller window NEVER squeezes a column under its
        # content width (hard clipping was the v1.1 bug). ttk's option is
        # MINWIDTH — 'minsize' is a grid option and raises TclError.
        tree.column(cid, width=width, minwidth=width, anchor="w", stretch=True)
    # row color tags (generic severity — used by e.g. blacklist rows)
    tree.tag_configure("danger", foreground=config.COLOR_RED)
    tree.tag_configure("caution", foreground=config.COLOR_YELLOW)
    tree.tag_configure("good", foreground=config.COLOR_GREEN)
    tree.tag_configure("dim", foreground=config.COLOR_FG_DIM)
    # STATUS badge tags (v1.3): one shared implementation — every status gets
    # a row tag with the status foreground + a subtle tinted background
    # (blend of the status color into the row surface). ttk tags style whole
    # rows, so the tint is kept faint to read as a badge, not a highlight.
    for status, color in config.STATUS_COLORS.items():
        tree.tag_configure(f"row_{status}",
                           foreground=color,
                           background=config.tint(color, 0.13,
                                                  base=config.COLOR_BG_2))
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
        super().__init__(master, fg_color=config.COLOR_CARD, corner_radius=12,
                         border_width=1, border_color=config.COLOR_BORDER)
        self._on_click = on_click
        self.grid_columnconfigure(0, weight=1)
        bar = ctk.CTkFrame(self, fg_color=color, width=4, corner_radius=2)
        bar.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(8, 0), pady=10)
        self.title_lbl = ctk.CTkLabel(self, text=title, text_color=config.COLOR_FG_DIM,
                                      font=F(11), justify="left", anchor="w",
                                      wraplength=200)
        self.title_lbl.grid(row=0, column=1, sticky="ew", padx=(10, 12), pady=(12, 0))
        # wraplength: a long amount wraps to a second line instead of being
        # clipped mid-number (v1.2 UX pass)
        self.value_lbl = ctk.CTkLabel(self, text=value, text_color=color,
                                      font=F(20, "semibold"), justify="left",
                                      anchor="w", wraplength=210)
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
# Unified STATUS badge system (v1.2): ONE component everywhere a status
# appears. Widget contexts use StatusPill; table cells (ttk.Treeview cannot
# host widgets) use the same token source rendered as "●  Label" text.
# ---------------------------------------------------------------------------

TAG_COLORS = config.TAG_COLORS
STATUS_COLORS = config.STATUS_COLORS


def status_badge_text(status: str, lang: str) -> str:
    """Status for a TABLE cell: colored-dot form of the same badge."""
    return f"●  {t(f'st_{status}', lang)}"


class TagPill(ctk.CTkLabel):
    """Small colored rounded tag."""

    def __init__(self, master, text: str, color: str):
        super().__init__(master, text=text, fg_color=color, text_color="#101216",
                         corner_radius=10, font=F(10, "bold"), height=22, padx=2)
        self.configure(anchor="center")


class StatusPill(ctk.CTkLabel):
    """
    The status badge as a real pill (v1.6): SEMANTIC-TINTED background,
    semantic-colored text, fully rounded (999px), never a solid fill.
    Same colors/labels as the table row tints — one system.
    """

    def __init__(self, master, status: str, lang: str):
        color = STATUS_COLORS.get(status, config.COLOR_FG_DIM)
        super().__init__(master, text=t(f"st_{status}", lang),
                         fg_color=config.tint(color, base=config.COLOR_BG_3),
                         text_color=color, corner_radius=11,
                         font=F(10, "semibold"), height=22,
                         padx=6, pady=0)
        self.configure(anchor="center")


# ---------------------------------------------------------------------------
# Unified TRUST indicator (v1.2): the Labels icon set everywhere —
#   ✓ ≥80 (trusted)   ⚠ 40-79 (caution)   🔒 <40 (risk)
# ---------------------------------------------------------------------------

def trust_glyph(score: int) -> tuple[str, str]:
    """(icon, color) for a trust score — single source of truth."""
    score = int(score or 0)
    if score >= config.TRUST_TRUSTED:
        return "✓", config.COLOR_GREEN
    if score >= config.TRUST_CAUTION:
        return "⚠", config.COLOR_YELLOW
    return "🔒", config.COLOR_RED


def trust_badge_text(score: int) -> str:
    """Trust for a TABLE cell: '✓ 85' (icon + score, no raw x/100)."""
    icon, _color = trust_glyph(score)
    return f"{icon} {int(score)}"


class TrustBadge(ctk.CTkFrame):
    """Trust header badge: big icon + score + colored label."""

    def __init__(self, master, score: int, lang: str = "fr"):
        super().__init__(master, fg_color="transparent")
        icon, color = trust_glyph(score)
        self.icon_lbl = ctk.CTkLabel(self, text=icon, font=F(24, "bold"),
                                     text_color=color)
        self.icon_lbl.grid(row=0, column=0, rowspan=2, padx=(0, 8))
        self.score_lbl = ctk.CTkLabel(self, text=f"{int(score)}/100",
                                      font=F(20, "bold"), text_color=color)
        self.score_lbl.grid(row=0, column=1, sticky="w")
        level = ("cust_trust_high" if score >= config.TRUST_TRUSTED else
                 "cust_trust_mid" if score >= config.TRUST_CAUTION else
                 "cust_trust_low")
        self.level_lbl = ctk.CTkLabel(self, text=t(level, lang), font=F(10),
                                      text_color=config.COLOR_FG_DIM)
        self.level_lbl.grid(row=1, column=1, sticky="w")


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

def bar_points(x0: float, y0: float, x1: float, y1: float, r: float = 4) -> list:
    """
    Bar outline with ONLY the top corners rounded (r px) and the baseline
    flush at y1 — the conventional bar shape (v1.7: the v1.6 smooth polygon
    rounded every corner, reading as capsules floating above the axis).
    Explicit arc samples, no Tk smoothing. Pure + unit-testable.
    """
    import math
    if y1 - y0 <= 2 * r or x1 - x0 <= 2 * r:      # too small to round
        return [x0, y0, x1, y0, x1, y1, x0, y1]
    pts = [x0, y1, x0, y0 + r]
    steps = 4                                      # samples per quarter arc
    for i in range(1, steps + 1):                  # top-left corner (180->270)
        a = math.pi + (math.pi / 2) * i / steps
        pts += [x0 + r + r * math.cos(a), y0 + r + r * math.sin(a)]
    for i in range(1, steps + 1):                  # top-right corner (270->360)
        a = (math.pi / 2) * 3 + (math.pi / 2) * i / steps
        pts += [x1 - r + r * math.cos(a), y0 + r + r * math.sin(a)]
    pts += [x1, y0 + r, x1, y1]
    return pts


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
        # gridlines + y labels (muted hairlines, no axis borders)
        for i in range(5):
            y = pad_t + plot_h * (1 - i / 4)
            self.create_line(pad_l, y, w - 12, y, fill=config.COLOR_BORDER)
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

            def rbar(bx0, by0, bx1, by1, color, r=4, _s=self):
                """Rounded-TOP bar, baseline flush (v1.7: explicit arc
                points — no smooth=, which had rounded the bottom too)."""
                _s.create_polygon(bar_points(bx0, by0, bx1, by1, r),
                                  fill=color, width=0)

            rbar(x0 - bar_w - 2, pad_t + plot_h - h1, x0 - 2,
                 pad_t + plot_h, config.COLOR_GREEN)
            rbar(x0 + 2, pad_t + plot_h - h2, x0 + bar_w + 2,
                 pad_t + plot_h, config.COLOR_RED)
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
# Funnel chart: horizontal stage bars (pending -> paid)
# ---------------------------------------------------------------------------

class FunnelChart(ctk.CTkCanvas):
    """Order funnel drawn on a canvas: one bar per lifecycle stage."""

    def __init__(self, master, lang: str = "fr", bg: str = config.COLOR_BG,
                 height: int = 220):
        super().__init__(master, bg=bg, highlightthickness=0, height=height)
        self.lang = lang
        self.stages: list[dict] = []
        self.bind("<Configure>", lambda e: self._draw())

    def set_data(self, stages: list[dict]) -> None:
        self.stages = stages or []
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 80 or h < 60 or not self.stages:
            return
        n = len(self.stages)
        row_h = h / n
        label_w = 118
        max_n = max((s["count"] for s in self.stages), default=1) or 1
        # semantic tokens only (v1.6): pipeline stages are informational,
        # the money stages are success — no stray hues anywhere
        colors = [config.COLOR_INFO, config.COLOR_INFO, config.COLOR_INFO,
                  config.COLOR_GREEN, config.COLOR_GREEN]
        for i, s in enumerate(self.stages):
            y = i * row_h + 4
            bh = row_h - 10
            self.create_text(4, y + bh / 2, anchor="w",
                             text=t(f"st_{s['stage']}", self.lang),
                             fill=config.COLOR_FG_DIM, font=(FONT_FAMILY, 10))
            bar_max = w - label_w - 90
            bw = max(4, int(bar_max * s["count"] / max_n))
            self.create_rectangle(label_w, y, label_w + bw, y + bh,
                                  fill=colors[i % len(colors)], width=0)
            self.create_text(label_w + bw + 8, y + bh / 2, anchor="w",
                             text=f"{s['count']}  ({s['pct']:.0f}%)",
                             fill=config.COLOR_FG, font=(FONT_FAMILY, 10, "bold"))


# ---------------------------------------------------------------------------
# Screen-aware window sizing (v1.4.2)
# ---------------------------------------------------------------------------

def fit_geometry(win, w: int, h: int, margin: int = 90):
    """
    Size a window so it ALWAYS fits the screen.

    CustomTkinter multiplies geometry by the Windows display-scaling factor:
    on a 150% laptop, "480x730" is really 720x1095 px — taller than the
    screen, so the bottom buttons (Save/Cancel) sit below the visible area
    and no amount of scrolling can reach them (v1.4.2 bug). Returns the
    fitted (w, h) in CTk units, or None if even the screen query failed.
    """
    try:
        scale = ctk.ScalingTracker.get_window_scaling(win)
        max_w = int(win.winfo_screenwidth() / scale) - 40
        max_h = int(win.winfo_screenheight() / scale) - margin
        fitted = (max(280, min(w, max_w)), max(300, min(h, max_h)))
        win.geometry(f"{fitted[0]}x{fitted[1]}")
        return fitted
    except Exception:
        try:
            win.geometry(f"{w}x{h}")
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# HimayaDialog (v1.3.1): ONE safe base for every popup in the app.
#
# Two Windows-specific failure modes it kills:
#  1. grab_set() in __init__ can race the window mapping -> TclError
#     mid-construction -> a half-built ("empty") dialog with dead buttons.
#     -> grab is DEFERRED until the window exists, and never fatal.
#  2. destroy() on a window that holds the modal grab can leave the grab
#     stuck -> the app ignores every click ("window won't close, app
#     bugged"). -> close() releases the grab BEFORE destroying, and is
#     idempotent (X then Cancel, double-clicks, Esc, all safe).
# ---------------------------------------------------------------------------

class HimayaDialog(ctk.CTkToplevel):
    """Modal popup base: deferred safe grab + explicit safe close."""

    def __init_subclass__(cls, **kwargs):
        # Wrap EVERY dialog's __init__ with a crash guard: a constructor
        # exception is logged, the half-built window is closed (never a
        # zombie), and the error re-raises for the app-level handler.
        super().__init_subclass__(**kwargs)
        original = cls.__init__
        if getattr(original, "_himaya_crash_guard", False):
            return

        @functools.wraps(original)
        def guarded(self, *args, **kw):
            try:
                original(self, *args, **kw)
            except Exception:
                log_crash(f"{cls.__name__}.__init__")
                try:
                    self.close()
                except Exception:
                    pass
                raise

        guarded._himaya_crash_guard = True
        cls.__init__ = guarded

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._closed = False
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", lambda _e: self.close())
        self.after(120, self._safe_grab)

    def _safe_grab(self) -> None:
        try:
            if self.winfo_exists():
                self.grab_set()
        except Exception:
            pass   # grab is a convenience, never a crash

    def close(self) -> None:
        """The ONE exit path: release grab, destroy, NEVER leave a zombie.

        A destroy() can fail when a child widget was only half-built by a
        crashed constructor — so we escalate: CTk destroy -> raw Tk
        destroy -> withdraw (at least take it off screen)."""
        try:
            alive = bool(self.winfo_exists())
        except Exception:
            alive = False                    # widget already gone
        if not alive:
            self._closed = True
            return
        try:
            self.grab_release()
        except Exception:
            pass
        self._closed = True
        try:
            self.destroy()
            return
        except Exception:
            pass
        try:
            tk.Toplevel.destroy(self)        # skip the CTk destroy chain
            return
        except Exception:
            pass
        try:
            self.withdraw()                  # last resort: hide it
        except Exception:
            pass


# ---------------------------------------------------------------------------
# v1.5 design kit (dense analytics): section headers, compact stats, hero
# card and a horizontal bar chart — the "bank statement" hierarchy.
# ---------------------------------------------------------------------------

def section_header(master, text: str) -> ctk.CTkFrame:
    """
    Uppercase 11px semibold muted label (the design spec's section header).
    Arabic has no uppercase — kept as-is there. +0.04em tracking is not a
    Tk capability; the uppercase + size + color carry the hierarchy.
    """
    is_latin = not any("\u0600" <= ch <= "\u06FF" for ch in text)
    row = ctk.CTkFrame(master, fg_color="transparent")
    bar = ctk.CTkFrame(row, fg_color=config.COLOR_ACCENT, width=3, height=12,
                       corner_radius=2)
    bar.pack(side="left", padx=(0, 8))
    lbl = ctk.CTkLabel(row, text=text.upper() if is_latin else text,
                       font=F(11, "semibold"),
                       text_color=config.COLOR_FG_MUTED, anchor="w")
    lbl.pack(side="left")
    return row


class CompactStat(ctk.CTkFrame):
    """Dense stat tile: small title, colored value, optional sub-line.
    Same clickable contract as StatCard, half the footprint."""

    def __init__(self, master, title: str, value: str = "—",
                 color: str = config.COLOR_ACCENT, sub: str = "",
                 icon: str = "", on_click=None):
        super().__init__(master, fg_color=config.COLOR_CARD, corner_radius=12,
                         border_width=1, border_color=config.COLOR_BORDER)
        self._on_click = on_click
        col = 0
        if icon:
            # small VECTOR icon in a colored circular chip (tinted bg,
            # semantic fg) — exact centering, one icon family everywhere
            chip = ctk.CTkFrame(self, fg_color=config.tint(color), width=32,
                                height=32, corner_radius=16)
            chip.grid(row=0, column=0, rowspan=3, padx=(10, 0), pady=10)
            chip.grid_propagate(False)
            try:
                from .icons import render as _icon_render
                img = ctk.CTkImage(light_image=_icon_render(icon, color, 18),
                                   size=(18, 18))
                ctk.CTkLabel(chip, text="", image=img).place(
                    relx=0.5, rely=0.5, anchor="center")
            except Exception:
                pass
            col = 1
        self.grid_columnconfigure(col + 1, weight=1)
        self.title_lbl = ctk.CTkLabel(self, text=title, font=F(11),
                                      text_color=config.COLOR_FG_DIM,
                                      anchor="w", justify="left",
                                      wraplength=150)
        self.title_lbl.grid(row=0, column=col + 1, sticky="ew",
                            padx=(10, 10), pady=(10, 0))
        self.value_lbl = ctk.CTkLabel(self, text=value, font=F(20, "semibold"),
                                      text_color=color, anchor="w",
                                      justify="left", wraplength=170)
        self.value_lbl.grid(row=1, column=col + 1, sticky="ew", padx=(10, 10))
        self.sub_lbl = ctk.CTkLabel(self, text=sub, font=F(10),
                                    text_color=config.COLOR_FG_MUTED, anchor="w",
                                    justify="left", wraplength=170)
        self.sub_lbl.grid(row=2, column=col + 1, sticky="ew",
                          padx=(10, 10), pady=(0, 9))
        if not sub:
            self.sub_lbl.grid_remove()
        if on_click:
            self._make_clickable()

    set = StatCard.set          # identical contract (value, sub)

    _make_clickable = StatCard._make_clickable


class HeroCard(ctk.CTkFrame):
    """THE number of the page: shield icon in a soft accent-tinted circle,
    31px extrabold value, muted support line — full-width band."""

    def __init__(self, master, title: str, color: str = config.COLOR_ACCENT,
                 icon: str = "shield", on_click=None):
        super().__init__(master, fg_color=config.COLOR_CARD, corner_radius=12,
                         border_width=1, border_color=config.COLOR_BORDER)
        self._on_click = on_click
        self.grid_columnconfigure(2, weight=1)
        # soft tinted circular badge (never a solid semantic fill) holding
        # the VECTOR icon — v1.7.1: the emoji version sat off-center (emoji
        # font metrics); a CTkImage centers exactly.
        badge = ctk.CTkFrame(self, fg_color=config.tint(color), width=54,
                             height=54, corner_radius=27)
        badge.grid(row=0, column=0, rowspan=3, padx=(16, 0), pady=16)
        badge.grid_propagate(False)
        try:
            from .icons import render as _icon_render
            img = ctk.CTkImage(light_image=_icon_render(icon, color, 28),
                               size=(28, 28))
            ctk.CTkLabel(badge, text="", image=img).place(
                relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(badge, text="\U0001F6E1\uFE0F", font=F(22)).place(
                relx=0.5, rely=0.5, anchor="center")
        self.title_lbl = ctk.CTkLabel(self, text=title, font=F(12),
                                      text_color=config.COLOR_FG_DIM, anchor="w")
        self.title_lbl.grid(row=0, column=2, sticky="w", padx=(14, 16), pady=(14, 0))
        self.value_lbl = ctk.CTkLabel(self, text="—", font=F(31, "extrabold"),
                                      text_color=color, anchor="w",
                                      justify="left", wraplength=520)
        self.value_lbl.grid(row=1, column=2, sticky="w", padx=(14, 16))
        self.sub_lbl = ctk.CTkLabel(self, text="", font=F(11),
                                    text_color=config.COLOR_FG_MUTED, anchor="w",
                                    justify="left", wraplength=520)
        self.sub_lbl.grid(row=2, column=2, sticky="w", padx=(14, 16), pady=(0, 14))
        if on_click:
            self._make_clickable()

    set = StatCard.set
    _make_clickable = StatCard._make_clickable


class HBarChart(ctk.CTkFrame):
    """Horizontal bar list: label | track+fill (proportional) | amount+share.
    Tk-native: the fill is placed with place(relwidth=...) so it resizes
    with the track without any pixel math."""

    def __init__(self, master, height: int = 24):
        super().__init__(master, fg_color="transparent")
        self._row_h = height
        self._rows: list[tuple[ctk.CTkFrame, ctk.CTkFrame]] = []

    def set_data(self, items: list) -> None:
        """items: (label, value, color) sorted by importance; zeros skipped."""
        for row, _fill in self._rows:
            row.destroy()
        self._rows = []
        items = [(l, v, c) for (l, v, c) in items if v > 0]
        if not items:
            return
        peak = max(v for _l, v, _c in items) or 1.0
        for label, value, color in items:
            row = ctk.CTkFrame(self, fg_color="transparent")
            row.pack(fill="x", pady=(self._row_h - 18) // 2)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=label, font=F(11), anchor="w", width=150,
                         justify="left").grid(row=0, column=0, sticky="w")
            track = ctk.CTkFrame(row, fg_color=config.COLOR_BG_3,
                                 height=12, corner_radius=6)
            track.grid(row=0, column=1, sticky="ew", padx=8)
            fill = ctk.CTkFrame(track, fg_color=color, corner_radius=6)
            fill.place(relwidth=max(0.02, value / peak), relheight=1)
            share = f"{value / peak * 100:.0f}%"
            ctk.CTkLabel(row, text=f"{share}", font=F(10),
                         text_color=config.COLOR_FG_DIM, width=36).grid(
                             row=0, column=2, sticky="e")
            self._rows.append((row, fill))


# ---------------------------------------------------------------------------
# Empty state (v1.2): icon + short message instead of a bare dash
# ---------------------------------------------------------------------------

class EmptyState(ctk.CTkFrame):
    """Centered 'nothing here yet' block: icon, message, optional hint."""

    def __init__(self, master, icon: str, message: str, hint: str = ""):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text=icon, font=F(40)).grid(row=0, column=0, pady=(0, 4))
        ctk.CTkLabel(self, text=message, font=F(14, "bold"),
                     text_color=config.COLOR_FG_DIM).grid(row=1, column=0)
        if hint:
            # wraplength tracks the ACTUAL panel width (bind <Configure>) so
            # long hints wrap instead of being clipped by a narrow container
            lbl = ctk.CTkLabel(self, text=hint, font=F(11),
                               text_color=config.COLOR_FG_DIM, wraplength=340,
                               justify="left")
            lbl.grid(row=2, column=0, pady=(2, 0), sticky="ew")
            lbl.bind("<Configure>",
                     lambda e, l=lbl: l.configure(wraplength=max(120, e.width - 8)))


# ---------------------------------------------------------------------------
# Cell tooltip for tables: full text on hover when a column is too narrow
# (general truncation answer — data is ellipsized by tk, tooltip restores it)
# ---------------------------------------------------------------------------

class _TreeToolTip:
    def __init__(self, tree):
        self.tree = tree
        self.win = None
        self._job = None
        tree.bind("<Motion>", self._motion, add="+")
        tree.bind("<Leave>", self._hide, add="+")

    def _motion(self, event) -> None:
        self._hide()
        try:
            row = self.tree.identify_row(event.y)
            col = self.tree.identify_column(event.x)
            if not row or not col:
                return
            idx = int(col.replace("#", "")) - 1
            values = self.tree.item(row, "values")
            if idx < 0 or idx >= len(values):
                return
            text = str(values[idx])
            width = self.tree.column(col, "width")
            # ~7 px per char at font 11 — only show when actually clipped
            if len(text) * 7 <= width:
                return
            self._job = self.tree.after(450, lambda: self._show(text, event))
        except Exception:
            pass

    def _show(self, text, event) -> None:
        self._job = None
        if self.win is not None and self.win.winfo_exists():
            self.win.destroy()
        self.win = tw = ctk.CTkToplevel(self.tree)
        tw.overrideredirect(True)
        tw.attributes("-topmost", True)
        ctk.CTkLabel(tw, text=text, font=F(11), justify="left", wraplength=320,
                     fg_color=config.COLOR_BG_3, corner_radius=6,
                     text_color=config.COLOR_FG, padx=8, pady=4).pack()
        tw.geometry(f"+{event.x_root + 12}+{event.y_root + 14}")

    def _hide(self, _event=None) -> None:
        if self._job is not None:
            try:
                self.tree.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self.win is not None and self.win.winfo_exists():
            self.win.destroy()
            self.win = None


def bind_tree_tooltips(tree) -> None:
    """Attach hover tooltips showing full cell text when clipped."""
    _TreeToolTip(tree)


# ---------------------------------------------------------------------------
# Scam alert popup
# ---------------------------------------------------------------------------

class ScamAlert(HimayaDialog):
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
        fit_geometry(self, 480, 420)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())

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
        self.close()   # HimayaDialog.close: grab released, idempotent
        if cb:
            cb()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

class Debouncer:
    """
    Coalesce rapid callbacks into one (e.g. a refresh per keystroke in a
    search box -> a single refresh 250ms after the last key). Searching
    rebuilds whole tables, so per-character refreshes are what made the
    UI feel laggy while typing.
    """

    def __init__(self, widget, delay_ms: int = 250):
        self._widget = widget
        self._delay = delay_ms
        self._job = None

    def call(self, fn, *args) -> None:
        self.cancel()
        self._job = self._widget.after(
            self._delay, lambda: self._run(fn, *args))

    def _run(self, fn, *args) -> None:
        self._job = None
        fn(*args)

    def cancel(self) -> None:
        if self._job is not None:
            try:
                self._widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None


def rtl_side(app, normal: str = "left") -> str:
    """Pack side flipped in Arabic (RTL mirror)."""
    return "right" if getattr(app, "lang", "fr") == "ar" else normal


def rtl_anchor(app) -> str:
    """Text anchor flipped in Arabic (RTL mirror)."""
    return "e" if getattr(app, "lang", "fr") == "ar" else "w"


def row_tag(status: str) -> str:
    """
    Treeview tag for an order status: the shared tinted-badge row tag.
    Unknown statuses fall back to the old severity names (still configured
    in every tree), so any caller is safe.
    """
    if status in config.STATUS_COLORS:
        return f"row_{status}"
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
