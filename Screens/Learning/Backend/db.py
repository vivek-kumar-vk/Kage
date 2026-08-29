import sqlite3
import pathlib
import settings_for_learning as cfg


def connect():
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as c:
        schema_path = pathlib.Path(__file__).parent / "schema.sql"
        exists = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='topics'"
        ).fetchone()

        if not exists:
            c.executescript(schema_path.read_text(encoding="utf-8"))

        cols = [row["name"] for row in c.execute("PRAGMA table_info(topics)").fetchall()]
        if "group" not in cols:
            c.execute('ALTER TABLE topics ADD COLUMN "group" TEXT')
