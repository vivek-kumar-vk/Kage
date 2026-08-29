import os
import sqlite3
import pathlib
import contextlib

HERE = pathlib.Path(__file__).resolve().parent
DB_PATH = pathlib.Path(os.environ.get("FINANCE_DB") or (HERE.parent / "data" / "finance.db"))
SCHEMA_PATH = HERE.parent / "scripts" / "schema.sql"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        has = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
        ).fetchone()
        if not has:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.commit()


@contextlib.contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
