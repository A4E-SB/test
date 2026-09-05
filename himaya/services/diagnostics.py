"""
Diagnostics: crash log. Windowed (noconsole) builds have no stderr, so
unhandled exceptions used to vanish silently. Everything lands in
DATA_DIR/error.log — the file users can send back with a bug report.
"""

from __future__ import annotations

import datetime
import traceback

from .. import config


def log_crash(origin: str) -> None:
    """Append the current traceback to error.log. Never raises."""
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(config.DATA_DIR / "error.log", "a", encoding="utf-8") as fh:
            fh.write(f"[{stamp}] {origin}\n" + traceback.format_exc() + "\n")
    except Exception:
        pass   # logging must never crash the app
