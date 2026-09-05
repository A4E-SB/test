"""
Local security: optional app password (PBKDF2, no external deps) and
rotating auto-backups on close.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path

from ..database.db import Database
from ..models import settings_store

PASSWORD_KEY = "app_password"       # json {salt, hash} — empty/absent = no lock
AUTO_BACKUP_KEY = "auto_backup"     # '1' / '0' (default '1')
KEEP_BACKUPS = 5


def hash_password(password: str, salt: bytes | None = None) -> dict:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return {"salt": salt.hex(), "hash": digest.hex()}


def set_password(db: Database, password: str) -> None:
    settings_store.set_setting(db, PASSWORD_KEY,
                               json.dumps(hash_password(password)))


def clear_password(db: Database) -> None:
    settings_store.set_setting(db, PASSWORD_KEY, "")


def has_password(db: Database) -> bool:
    return bool(settings_store.get_setting(db, PASSWORD_KEY, ""))


def verify_password(db: Database, password: str) -> bool:
    raw = settings_store.get_setting(db, PASSWORD_KEY, "")
    if not raw:
        return True
    try:
        data = json.loads(raw)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                     bytes.fromhex(data["salt"]), 120_000)
        return hmac.compare_digest(digest.hex(), data["hash"])
    except (ValueError, KeyError):
        return False


# ---------------------------------------------------------------------------
# Auto-backup (rotating, keeps the last KEEP_BACKUPS)
# ---------------------------------------------------------------------------

def auto_backup_enabled(db: Database) -> bool:
    return settings_store.get_setting(db, AUTO_BACKUP_KEY, "1") == "1"


def set_auto_backup(db: Database, enabled: bool) -> None:
    settings_store.set_setting(db, AUTO_BACKUP_KEY, "1" if enabled else "0")


def backup_on_close(db: Database) -> str | None:
    """Backup + rotate. Returns the new backup path (or None if disabled)."""
    from . import backup as backup_service
    if not auto_backup_enabled(db):
        return None
    path = backup_service.backup(db)
    _rotate(db.path.parent / "backups")
    return path


def _rotate(folder: Path) -> None:
    try:
        files = sorted(folder.glob("himaya_backup_*.db"))
        for old in files[:-KEEP_BACKUPS]:
            old.unlink(missing_ok=True)
    except Exception:
        pass
