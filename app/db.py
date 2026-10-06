"""SQLite helpers (plain sqlite3 - no ORM needed for a project this size)."""
import os
import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_schema(db_path):
    """Create all tables (safe to call repeatedly)."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = sqlite3.connect(db_path)
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as f:
        con.executescript(f.read())
    con.commit()
    con.close()
