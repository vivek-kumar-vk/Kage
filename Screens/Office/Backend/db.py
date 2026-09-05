"""office.db - this screen's own store. Data of record (unlike a RAG
cache); gitignored because it holds real company names and notes.
"""

from __future__ import annotations

import sqlite3

import settings_for_office as cfg


def connect() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI runs the dependency and the endpoint
    # on different threadpool threads; each request still opens its own.
    conn = sqlite3.connect(cfg.DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(cfg.SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
