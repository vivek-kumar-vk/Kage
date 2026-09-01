import os
import sqlite3
import pathlib
import contextlib

HERE = pathlib.Path(__file__).resolve().parent
DB_PATH = pathlib.Path(os.environ.get("FINANCE_DB") or (HERE.parent / "data" / "finance.db"))
SCHEMA_PATH = HERE.parent / "scripts" / "schema.sql"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI runs a sync generator dependency and the
    # sync endpoint it feeds on *different* threadpool threads, so the default
    # guard 500s once several requests land at once (the Overview fires nine).
    # Safe here — every request opens and closes its own connection.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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
        # migrations for DBs created before the table existed (idempotent)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS app_settings (
                   key TEXT PRIMARY KEY,
                   value TEXT NOT NULL,
                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        conn.commit()


@contextlib.contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
