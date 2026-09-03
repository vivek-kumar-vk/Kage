"""The Email card's local store - SQLite under Backend/Email_Data/.

Everything the card shows is computed from these tables; Gmail is never
asked anything at page-render time. The folder is gitignored - it holds
your mail metadata (CLAUDE.md Rule 7: nothing personal in git).

D22. The categorizer writes `category`/`reason` back here, so a window
count is one GROUP BY, not a re-fetch.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import settings_for_main_menu as cfg

DB_PATH = cfg.EMAIL_DATA_DIR / "email.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    gmail_id     TEXT PRIMARY KEY,
    sender_email TEXT DEFAULT '',
    sender_name  TEXT DEFAULT '',
    subject      TEXT DEFAULT '',
    snippet      TEXT DEFAULT '',
    list_id      TEXT DEFAULT '',
    received_at  TEXT,              -- ISO UTC, from Gmail internalDate
    category     TEXT,              -- newsletters|finance|jobs|priority|other|NULL
    reason       TEXT DEFAULT '',   -- the brain's one-line why
    summarized   INTEGER DEFAULT 0, -- already folded into a digest
    categorized_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_state (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS digests (
    id           TEXT PRIMARY KEY,
    created_at   TEXT,
    span_start   TEXT,
    span_end     TEXT,
    mail_count   INTEGER DEFAULT 0,
    body         TEXT,
    delivered    INTEGER DEFAULT 0,
    delivered_at TEXT,
    error        TEXT DEFAULT ''
);
"""


def connect():
    cfg.EMAIL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------
# messages
# ---------------------------------------------------------------------
def upsert_messages(rows):
    """Insert newly fetched mail; anything already stored is left exactly
    as it is (its category survives re-syncs). Returns how many were new."""
    conn = connect()
    try:
        new = 0
        for r in rows:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO messages
                (gmail_id, sender_email, sender_name, subject,
                 snippet, list_id, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (r["gmail_id"], r["sender_email"], r["sender_name"],
                 r["subject"], r["snippet"], r["list_id"], r["received_at"]),
            )
            new += cur.rowcount
        conn.commit()
        return new
    finally:
        conn.close()


def messages_since(epoch_seconds):
    conn = connect()
    try:
        cutoff = datetime.fromtimestamp(epoch_seconds, timezone.utc)
        return conn.execute(
            "SELECT * FROM messages WHERE received_at >= ? ORDER BY received_at",
            (cutoff.isoformat(),),
        ).fetchall()
    finally:
        conn.close()


def uncategorized(limit=40):
    conn = connect()
    try:
        return conn.execute(
            """SELECT gmail_id, sender_email, sender_name, subject, snippet
               FROM messages WHERE category IS NULL
               ORDER BY received_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    finally:
        conn.close()


def apply_categories(mapping):
    """mapping: gmail_id -> (category, reason). Unknown ids are skipped."""
    conn = connect()
    try:
        for gmail_id, (category, reason) in mapping.items():
            conn.execute(
                """UPDATE messages SET category = ?, reason = ?,
                       categorized_at = ? WHERE gmail_id = ?""",
                (category, reason, _now(), gmail_id),
            )
        conn.commit()
    finally:
        conn.close()


def mark_summarized(gmail_ids):
    conn = connect()
    try:
        conn.executemany(
            "UPDATE messages SET summarized = 1 WHERE gmail_id = ?",
            [(g,) for g in gmail_ids],
        )
        conn.commit()
    finally:
        conn.close()


def newsletters_since(epoch_seconds, senders):
    """Newsletter-bucket mail from the digest sender list, not yet
    summarized. A sender matches by exact address or by domain."""
    conn = connect()
    try:
        cutoff = datetime.fromtimestamp(epoch_seconds, timezone.utc)
        rows = conn.execute(
            """SELECT * FROM messages
               WHERE category = 'newsletters' AND summarized = 0
                 AND received_at >= ? ORDER BY received_at""",
            (cutoff.isoformat(),),
        ).fetchall()
        chosen = []
        for row in rows:
            addr = (row["sender_email"] or "").lower()
            if any(addr == s or addr.endswith("@" + s) for s in senders):
                chosen.append(row)
        return chosen
    finally:
        conn.close()


# ---------------------------------------------------------------------
# sync_state - the loop's own bookkeeping, one key at a time
# ---------------------------------------------------------------------
def set_state(key, value):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO sync_state (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        conn.commit()
    finally:
        conn.close()


def get_state(key, default=None):
    conn = connect()
    try:
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def all_state():
    conn = connect()
    try:
        return {r["key"]: r["value"]
                for r in conn.execute("SELECT key, value FROM sync_state")}
    finally:
        conn.close()


# ---------------------------------------------------------------------
# digests - what was summarized, and whether the deck accepted it
# ---------------------------------------------------------------------
def record_digest(digest_id, span_start, span_end, mail_count, body):
    conn = connect()
    try:
        conn.execute(
            """INSERT INTO digests
               (id, created_at, span_start, span_end, mail_count, body,
                delivered, error)
               VALUES (?, ?, ?, ?, ?, ?, 0, '')""",
            (digest_id, _now(), span_start, span_end, mail_count, body),
        )
        conn.commit()
    finally:
        conn.close()


def mark_digest_delivered(digest_id, error=""):
    conn = connect()
    try:
        conn.execute(
            """UPDATE digests SET delivered = ?, delivered_at = ?, error = ?
               WHERE id = ?""",
            (0 if error else 1, _now() if not error else None, error, digest_id),
        )
        conn.commit()
    finally:
        conn.close()


def last_digest_created_at():
    conn = connect()
    try:
        row = conn.execute(
            "SELECT MAX(created_at) AS last FROM digests"
        ).fetchone()
        return row["last"] if row else None
    finally:
        conn.close()
