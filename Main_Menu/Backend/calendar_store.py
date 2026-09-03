"""The Calendar card's local store (D23): one SQLite file in
Calendar_Data/ (gitignored).

It holds four things, and each one is a different kind of truth, so they
never share a table:

    events      the mirror of the real Google calendar. Read-only truth.
    day_notes   what the agent OBSERVED about a day, from real signals.
    proposals   what the agent WANTS to put on the calendar. Not truth
                until the owner approves it and Google accepts the write.
    waka_days   one row per day of WakaTime totals, snapshotted nightly
                so history survives the free plan's 7-day window.

Nothing in here invents a value. A day with no row comes back as a day
with no row - the card draws that as an empty cell, never as a zero.
"""

import json
import sqlite3
from datetime import date, datetime, timedelta

import settings_for_main_menu as cfg

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    google_id    TEXT PRIMARY KEY,
    day          TEXT NOT NULL,
    start_iso    TEXT,
    end_iso      TEXT,
    all_day      INTEGER NOT NULL DEFAULT 0,
    summary      TEXT,
    description  TEXT,
    location     TEXT,
    by_agent     INTEGER NOT NULL DEFAULT 0,
    updated_at   TEXT
);
CREATE INDEX IF NOT EXISTS events_day ON events(day);

CREATE TABLE IF NOT EXISTS day_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    day        TEXT NOT NULL,
    kind       TEXT NOT NULL,
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(day, kind, text)
);
CREATE INDEX IF NOT EXISTS day_notes_day ON day_notes(day);

CREATE TABLE IF NOT EXISTS proposals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    day             TEXT NOT NULL,
    summary         TEXT NOT NULL,
    start_iso       TEXT,
    end_iso         TEXT,
    description     TEXT,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    google_event_id TEXT,
    error           TEXT,
    created_at      TEXT NOT NULL,
    decided_at      TEXT
);
CREATE INDEX IF NOT EXISTS proposals_status ON proposals(status);
CREATE INDEX IF NOT EXISTS proposals_day ON proposals(day);

CREATE TABLE IF NOT EXISTS waka_days (
    day           TEXT PRIMARY KEY,
    total_seconds INTEGER,
    top_project   TEXT,
    top_language  TEXT,
    payload       TEXT,
    captured_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def db_path():
    return cfg.CALENDAR_DATA_DIR / "calendar.sqlite"


def connect():
    cfg.CALENDAR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _now():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------
# META
# ---------------------------------------------------------------------
def get_meta(key, default=None):
    with connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(key, value):
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


# ---------------------------------------------------------------------
# EVENTS - written only by the Google mirror
# ---------------------------------------------------------------------
def replace_events(window_start, window_end, rows):
    """The mirror is authoritative for its window: anything Google no
    longer returns in that window is gone from here too, so a cancelled
    meeting stops showing on the card."""
    with connect() as conn:
        conn.execute("DELETE FROM events WHERE day>=? AND day<=?",
                     (window_start, window_end))
        conn.executemany(
            "INSERT OR REPLACE INTO events"
            "(google_id,day,start_iso,end_iso,all_day,summary,description,"
            " location,by_agent,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            [(r["google_id"], r["day"], r["start_iso"], r["end_iso"],
              int(r["all_day"]), r["summary"], r["description"],
              r.get("location"), int(r.get("by_agent", 0)), _now())
             for r in rows],
        )
    return len(rows)


def events_between(start_day, end_day):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM events WHERE day>=? AND day<=? "
            "ORDER BY all_day DESC, start_iso",
            (start_day, end_day)).fetchall()]


def events_on(day):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM events WHERE day=? ORDER BY all_day DESC, start_iso",
            (day,)).fetchall()]


def upcoming(from_iso, from_day, limit=3):
    """The WHAT'S NEXT list: what is genuinely still ahead.

    All-day events count. Filtering them out (they have no start time to
    compare against `now`) made the card say "Nothing scheduled" while a
    real birthday sat three days away - an empty list that was not true.
    A timed event sorts before an all-day one on the same date.
    """
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM events "
            "WHERE (all_day=0 AND start_iso>=?) OR (all_day=1 AND day>=?) "
            "ORDER BY day, all_day, start_iso LIMIT ?",
            (from_iso, from_day, limit)).fetchall()]


# ---------------------------------------------------------------------
# DAY NOTES - what the agent observed
# ---------------------------------------------------------------------
def add_note(day, kind, text):
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO day_notes(day,kind,text,created_at) "
            "VALUES(?,?,?,?)", (day, kind, text, _now()))


def notes_between(start_day, end_day):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM day_notes WHERE day>=? AND day<=? ORDER BY day,id",
            (start_day, end_day)).fetchall()]


def notes_on(day):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM day_notes WHERE day=? ORDER BY id", (day,)).fetchall()]


# ---------------------------------------------------------------------
# PROPOSALS - never truth until approved AND written
# ---------------------------------------------------------------------
def add_proposal(day, summary, start_iso, end_iso, description, reason):
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM proposals WHERE day=? AND summary=? "
            "AND status!='rejected'", (day, summary)).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO proposals(day,summary,start_iso,end_iso,description,"
            "reason,created_at) VALUES(?,?,?,?,?,?,?)",
            (day, summary, start_iso, end_iso, description, reason, _now()))
        return cur.lastrowid


def proposals(status=None, limit=50):
    sql = "SELECT * FROM proposals"
    args = []
    if status:
        sql += " WHERE status=?"
        args.append(status)
    sql += " ORDER BY day, id LIMIT ?"
    args.append(limit)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def proposals_on(day):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM proposals WHERE day=? AND status IN "
            "('pending','written') ORDER BY id", (day,)).fetchall()]


def get_proposal(proposal_id):
    with connect() as conn:
        row = conn.execute("SELECT * FROM proposals WHERE id=?",
                           (proposal_id,)).fetchone()
    return dict(row) if row else None


def mark_proposal(proposal_id, status, google_event_id=None, error=None):
    with connect() as conn:
        conn.execute(
            "UPDATE proposals SET status=?, "
            "google_event_id=COALESCE(?,google_event_id), error=?, "
            "decided_at=? WHERE id=?",
            (status, google_event_id, error, _now(), proposal_id))


# ---------------------------------------------------------------------
# WAKATIME - the snapshot that outlives the free plan's 7-day window
# ---------------------------------------------------------------------
def save_waka_day(day, total_seconds, top_project, top_language, payload):
    with connect() as conn:
        conn.execute(
            "INSERT INTO waka_days(day,total_seconds,top_project,top_language,"
            "payload,captured_at) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(day) DO UPDATE SET total_seconds=excluded.total_seconds,"
            " top_project=excluded.top_project,"
            " top_language=excluded.top_language,"
            " payload=excluded.payload, captured_at=excluded.captured_at",
            (day, total_seconds, top_project, top_language,
             json.dumps(payload)[:20000], _now()))


def waka_between(start_day, end_day):
    with connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT day,total_seconds,top_project,top_language FROM waka_days "
            "WHERE day>=? AND day<=? ORDER BY day",
            (start_day, end_day)).fetchall()]


def waka_on(day):
    with connect() as conn:
        row = conn.execute("SELECT * FROM waka_days WHERE day=?",
                           (day,)).fetchone()
    return dict(row) if row else None


def waka_day_count():
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) n FROM waka_days").fetchone()["n"]


# ---------------------------------------------------------------------
# HELPERS the pipeline and the card share
# ---------------------------------------------------------------------
def month_bounds(year, month):
    first = date(year, month, 1)
    last = date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)
    return first.isoformat(), last.isoformat()
