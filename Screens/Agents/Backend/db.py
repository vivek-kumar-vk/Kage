import sqlite3

import settings_for_agents as cfg


def connect():
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # schema.sql is entirely `CREATE TABLE IF NOT EXISTS`, so run it on every
    # startup — that way a schema addition (e.g. the events table, D12) lands on
    # an already-created agents.db instead of only on a fresh one.
    conn = connect()
    try:
        schema_path = cfg.SCREEN / "Backend" / "schema.sql"
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
