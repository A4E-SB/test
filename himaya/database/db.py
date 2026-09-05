"""
SQLite access layer.

One connection per Database instance, a threading.Lock for safety, and a tiny
migration system based on PRAGMA user_version. All models receive this object.
"""

from __future__ import annotations

import sqlite3
import sys
import threading
from pathlib import Path
from typing import Any, Iterable, Optional


def _find_schema() -> Path:
    """
    Locate schema.sql in dev AND frozen (PyInstaller) builds.

    Frozen layout: <_MEIPASS>/himaya/database/schema.sql, where _MEIPASS is
    the bundle root (one-folder: ...\_internal). The module dir usually
    matches, but we fall back to explicit _MEIPASS locations for safety.
    """
    here = Path(__file__).resolve().parent / "schema.sql"
    if here.exists():
        return here
    base = getattr(sys, "_MEIPASS", None)
    if base:
        for cand in (Path(base) / "himaya" / "database" / "schema.sql",
                     Path(base) / "schema.sql"):
            if cand.exists():
                return cand
    return here  # let the caller raise a clear FileNotFoundError


SCHEMA_PATH = _find_schema()
SCHEMA_VERSION = 2


class Database:
    """Thin, explicit wrapper around sqlite3 used by every model/service."""

    def __init__(self, db_path: Path | str):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.init_schema()

    # -- schema / migrations -------------------------------------------------

    def init_schema(self) -> None:
        """Create tables (idempotent) and run pending migrations."""
        with self._lock:
            self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            current = self.conn.execute("PRAGMA user_version").fetchone()[0]
            if current < 2:
                self._migrate_v2()          # orders: product_id + deposit
            if current < SCHEMA_VERSION:
                # Future ALTER TABLE migrations go here, in order.
                self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self.conn.commit()

    def _migrate_v2(self) -> None:
        """v1 -> v2: add orders.product_id / orders.deposit (existing DBs)."""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(orders)")}
        if "product_id" not in cols:
            self.conn.execute(
                "ALTER TABLE orders ADD COLUMN product_id INTEGER "
                "REFERENCES products(id) ON DELETE SET NULL")
        if "deposit" not in cols:
            self.conn.execute(
                "ALTER TABLE orders ADD COLUMN deposit REAL NOT NULL DEFAULT 0")

    # -- helpers --------------------------------------------------------------

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self.conn.execute(sql, tuple(params))
            self.conn.commit()
            return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, tuple(params)).fetchall()

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, tuple(params)).fetchone()

    def scalar(self, sql: str, params: Iterable[Any] = ()) -> Any:
        row = self.query_one(sql, params)
        return row[0] if row is not None else None

    def close(self) -> None:
        with self._lock:
            self.conn.close()
