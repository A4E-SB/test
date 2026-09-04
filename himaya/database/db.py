"""
SQLite access layer.

One connection per Database instance, a threading.Lock for safety, and a tiny
migration system based on PRAGMA user_version. All models receive this object.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, Optional

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SCHEMA_VERSION = 1


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
            if current < SCHEMA_VERSION:
                # Future ALTER TABLE migrations go here, in order.
                self.conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self.conn.commit()

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
