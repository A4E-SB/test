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


# ---------------------------------------------------------------------------
# Performance timings (v1.7.5): the lag hunt needed real numbers from the
# user's machine. Every timed operation lands here; anything slow (>150ms)
# is also appended to error.log. Settings → Diagnostics shows the report.
# ---------------------------------------------------------------------------

from collections import deque

SLOW_MS = 150
timings: dict[str, deque] = {}


def timeit(name: str):
    """Context manager: `with timeit("orders.refresh"): ...`"""
    import contextlib, time as _t
    @contextlib.contextmanager
    def _cm():
        t0 = _t.perf_counter()
        try:
            yield
        finally:
            add_timing(name, (_t.perf_counter() - t0) * 1000)
    return _cm()


def add_timing(name: str, ms: float) -> None:
    buf = timings.setdefault(name, deque(maxlen=20))
    buf.append(round(ms, 1))
    if ms > SLOW_MS:
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            import datetime as _dt
            with open(config.DATA_DIR / "error.log", "a", encoding="utf-8") as fh:
                fh.write(f"[{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                         f"SLOW {name}: {ms:.0f} ms\n")
        except Exception:
            pass


_footer: list[str] = []      # v1.7.12: environment facts appended to the
                              # report (db size, index presence, sqlite build)


def set_report_footer(*lines_: str) -> None:
    """Attach environment facts to every future report()."""
    global _footer
    _footer = list(lines_)


def report() -> str:
    """Human-readable timing report (last 20 samples per operation)."""
    if not timings:
        return "no samples yet"
    lines = ["Himaya performance report (ms, last samples):"]
    for name, buf in timings.items():
        avg = sum(buf) / len(buf)
        lines.append(f"  {name:<28} last={buf[-1]:>7.1f}  avg={avg:>7.1f}  "
                     f"max={max(buf):>7.1f}  n={len(buf)}")
    if _footer:
        lines.append("")
        lines.extend(_footer)
    return "\n".join(lines)
