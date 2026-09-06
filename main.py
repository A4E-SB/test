#!/usr/bin/env python3
"""
Himaya (حماية) — entry point.

Usage:
    python main.py                 # launch the app (default local database)
    python main.py --db PATH       # use a specific .db file (e.g. on a USB key)
    python main.py --init-only     # just create/seed the database, then exit
"""

from __future__ import annotations

import argparse
import sys

from himaya import config
from himaya.database import Database, seed


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="Himaya")
    p.add_argument("--db", help="Path to the SQLite database file")
    p.add_argument("--init-only", action="store_true",
                   help="Create + seed the database and exit (no GUI)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    db_path = args.db or config.DB_PATH

    from himaya.services.diagnostics import timeit
    with timeit("startup:database"):
        db = Database(db_path)   # creates schema + runs migrations
        seed(db)                 # default settings + reply templates (idempotent)

    if args.init_only:
        print(f"Database ready: {db_path}")
        db.close()
        return 0

    # GUI imports are kept lazy so --init-only works on headless machines.
    from himaya.ui.app import HimayaApp
    with timeit("startup:window"):
        app = HimayaApp(db)   # includes the first page build (dashboard)

    def on_close() -> None:
        """Rotating auto-backup (5 copies) before quitting, if enabled."""
        try:
            from himaya.services.security import auto_backup_enabled, backup_on_close
            if auto_backup_enabled(db):
                backup_on_close(db)
        except Exception:
            pass   # never block closing because of a backup hiccup
        db.close()
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
