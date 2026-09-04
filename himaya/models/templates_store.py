"""Reply templates + settings key/value store."""

from __future__ import annotations

from ..database.db import Database


# --- templates --------------------------------------------------------------

def all_templates(db: Database) -> list:
    return db.query("SELECT * FROM templates ORDER BY category, name")


def by_category(db: Database, category: str) -> list:
    return db.query("SELECT * FROM templates WHERE category = ? ORDER BY name", (category,))


def categories(db: Database) -> list:
    return [r["category"] for r in db.query("SELECT DISTINCT category FROM templates")]


def get(db: Database, template_id: int):
    return db.query_one("SELECT * FROM templates WHERE id = ?", (template_id,))


def save_template(db: Database, name: str, category: str, text_ar: str, text_fr: str,
                  template_id: int | None = None) -> int:
    if template_id:
        db.execute("UPDATE templates SET name=?, category=?, text_ar=?, text_fr=? WHERE id=?",
                   (name, category, text_ar, text_fr, template_id))
        return template_id
    cur = db.execute("INSERT INTO templates(name, category, text_ar, text_fr) VALUES(?,?,?,?)",
                     (name, category, text_ar, text_fr))
    return cur.lastrowid


def delete(db: Database, template_id: int) -> None:
    db.execute("DELETE FROM templates WHERE id = ?", (template_id,))


# --- settings ---------------------------------------------------------------

def get_setting(db: Database, key: str, default: str = "") -> str:
    row = db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row and row["value"] is not None else default


def set_setting(db: Database, key: str, value: str) -> None:
    db.execute("INSERT INTO settings(key, value) VALUES(?,?) "
               "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
