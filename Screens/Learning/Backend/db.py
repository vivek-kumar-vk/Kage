import sqlite3
import pathlib
import settings_for_learning as cfg

LEGACY = ("reviews", "cards", "week_plans", "sessions", "topics")


def connect():
    # check_same_thread=False: FastAPI runs the dependency and the endpoint in
    # different threadpool threads; each request still gets its own connection.
    conn = sqlite3.connect(cfg.DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the v2 schema. If the D8 legacy tables are here, rename them
    aside first (seed.migrate moves the data, then drops them)."""
    with connect() as c:
        legacy = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='topics'"
        ).fetchone()
        if legacy:
            for t in LEGACY:
                c.execute(f"ALTER TABLE {t} RENAME TO {t}_d8")
        schema_path = pathlib.Path(__file__).parent / "schema.sql"
        c.executescript(schema_path.read_text(encoding="utf-8"))
        # light live migrations
        s_cols = {r["name"] for r in c.execute("PRAGMA table_info(sessions)").fetchall()}
        if "confidence" not in s_cols:
            c.execute("ALTER TABLE sessions ADD COLUMN confidence INTEGER")
