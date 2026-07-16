import os
from pathlib import Path

try:
    import pysqlite3 as sqlite3
except ImportError:
    import sqlite3

DB_PATH = os.environ.get("DB_PATH", "state/ads.db")
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str | None = None) -> sqlite3.Connection:
    conn = get_connection(db_path)
    conn.executescript(SCHEMA_PATH.read_text())
    return conn
