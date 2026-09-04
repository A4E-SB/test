"""Database package: SQLite engine + first-run seeding."""

from .db import Database
from .seed import seed

__all__ = ["Database", "seed"]
