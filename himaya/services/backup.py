"""Database backup / restore (single .db file copy)."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from ..config import BACKUP_DIR
from ..database.db import Database


def backup(db: Database, dest_dir: Path | str | None = None) -> str:
    """Hot-copy the SQLite file to a timestamped backup. Returns the new path."""
    dest_dir = Path(dest_dir) if dest_dir else BACKUP_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"himaya_backup_{stamp}.db"
    # ensure pending writes are flushed to disk before copying
    db.execute("PRAGMA wal_checkpoint(FULL)")
    shutil.copy2(db.path, dest)
    return str(dest)


def restore(backup_path: Path | str, current_db_path: Path | str) -> None:
    """
    Replace the current database with a backup.
    The app must reopen (usually restart) the database afterwards.
    """
    src, dst = Path(backup_path), Path(current_db_path)
    if not src.exists():
        raise FileNotFoundError(backup_path)
    shutil.copy2(src, dst)
