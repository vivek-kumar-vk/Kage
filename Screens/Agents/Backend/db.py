import sqlite3

import settings_for_agents as cfg


def connect():
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    try:
        has = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ideas'"
        ).fetchone()
        if not has:
            schema_path = cfg.SCREEN / "Backend" / "schema.sql"
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            conn.commit()
    finally:
        conn.close()
