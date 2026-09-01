"""The Enhancement board: a running note so an idea that shows up mid-task
does not get lost before there is time to act on it.

WHY THIS IS ITS OWN SCREEN AND NOT JUST A MARKDOWN FILE
    An idea worth keeping usually arrives while looking at something else
    entirely - partway through a different screen, a different task, a
    different conversation. A door that is always one click away from the
    main menu gets used; a file that has to be found and opened does not.

    Started 2026-08-20 as a tab inside Learning (ADR-064). Promoted to its
    own screen 2026-08-22 (ADR-067) at the user's request - ideas about
    Finance, Models and Learning alike were living one level inside
    Learning, which made it look like a Learning-only feature when it
    never was. Same module, same data, moved rather than duplicated.

WHY SQLITE NOW AND NOT THE JSON LIST ANY MORE
    A flat list answers "what ideas are there" well enough, but a Kanban
    board asks harder questions all day long - which column, what position
    inside the column, who commented and when - and answering those by
    rewriting a whole JSON file on every drag is both slow and fragile
    (two tabs dragging at once lose one drag entirely). SQLite keeps every
    write down to one row, orders columns and positions with a single
    ORDER BY, and stays a single local file, so storage never leaves this
    machine (C1). The old `enhancement_ideas.json` is kept untouched as
    the migration source: the first time this module opens a fresh
    database it copies every idea across in place - same ids, same
    timestamps, nothing invented.

WHAT AN ENTRY IS
    A title, an optional note, an optional `area` naming which screen and
    tab it is about (free text - "Finance / Chat", "Models / Log" - never
    validated against a fixed list, because an idea about a screen that
    does not exist yet is exactly the kind of idea worth keeping), and a
    `source`: "user" for what was typed in, "ai" for a suggestion a model
    wrote in. Rule 7 says AI-generated content carries a distinct marker
    and human-entered does not - `source` is that marker, and the page
    renders it with the same violet edge (.ai-generated) already used
    everywhere else in INKY for the same reason.

THE BOARD SHAPE
    Four columns - "ideas" (fresh capture), "todo", "in_progress",
    "done" - and a REAL `order_index` per idea for its slot inside its
    column. A float, not an integer, on purpose: dropping one idea between
    two others then costs no renumbering at all, just a midpoint. Every
    idea also carries an ENH-n key, handed out in sequence by
    next_enh_key(), because "move ENH-7 to done" is easier to say out loud
    than a 12-hex id ever is.

RUN IT
    cd <repo root>
    python Screens\\Enhancement\\Calculations\\manage_enhancement_ideas.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IST = timezone(timedelta(hours=5, minutes=30), "IST")

SAVED_RECORDS = SCREEN / "Saved_Records"
IDEAS_FILE = SAVED_RECORDS / "enhancement_ideas.json"   # migration source, never rewritten
SEED_FILE = SCREEN / "enhancement_ideas_starter_seed.json"  # tracked; loaded once on a fresh board
DB_PATH = SAVED_RECORDS / "enhancement_board.db"

STATUSES = ("ideas", "todo", "in_progress", "done")
PRIORITIES = ("low", "medium", "high", "critical")


# =====================================================================
# SCHEMA AND FIRST OPEN
# =====================================================================

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ideas (
    id          TEXT PRIMARY KEY,
    enh_key     TEXT UNIQUE,
    title       TEXT NOT NULL,
    note        TEXT DEFAULT '',
    area        TEXT DEFAULT '',
    source      TEXT CHECK (source IN ('user','ai')) DEFAULT 'user',
    status      TEXT CHECK (status IN ('ideas','todo','in_progress','done')) DEFAULT 'ideas',
    priority    TEXT CHECK (priority IN ('low','medium','high','critical')) DEFAULT 'medium',
    order_index REAL,
    added_at    TEXT,
    updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS comments (
    id         TEXT PRIMARY KEY,
    idea_id    TEXT REFERENCES ideas(id),
    text       TEXT NOT NULL,
    author     TEXT CHECK (author IN ('user','ai')) DEFAULT 'user',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def _connect() -> sqlite3.Connection:
    """Open the database, making sure the schema and the one-time
    migration both happened before anything reads or writes."""
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate_if_first_open(conn)
    return conn


def _migrate_if_first_open(conn: sqlite3.Connection) -> None:
    """Copy every idea from enhancement_ideas.json across, once, in place.

    WHY A FLAG AND NOT "TABLE IS EMPTY": a user is allowed to delete
    every idea off the board - that must not look like a fresh install
    and pull the deleted ones back out of the JSON on the next open. One
    row in `meta` says the migration ran, and after that the JSON is
    history, never re-read and never rewritten.

    Order matters here: ids stay exactly as they were, `done: true`
    becomes status 'done', everything else lands back in the capture
    column, and ENH keys go out oldest-first so ENH-1 is genuinely the
    first idea ever captured, not whichever one happened to sort last.
    """
    already = conn.execute(
        "SELECT value FROM meta WHERE key = 'migrated'"
    ).fetchone()
    if already:
        return

    if IDEAS_FILE.exists():
        old_items = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
        # Oldest first; Python's stable sort keeps the file's own order
        # inside identical timestamps, of which this file has plenty.
        ordered = sorted(old_items, key=lambda i: i.get("added_at", ""))
        per_column_count: dict[str, int] = {}
        for item in ordered:
            status = "done" if item.get("done") else "ideas"
            position = per_column_count.get(status, 0)
            per_column_count[status] = position + 1
            conn.execute(
                """INSERT INTO ideas
                   (id, enh_key, title, note, area, source,
                    status, priority, order_index, added_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["id"],
                    next_enh_key(conn),
                    item["title"],
                    item.get("note", ""),
                    item.get("area", ""),
                    item.get("source", "user"),
                    status,
                    "medium",
                    float(position),
                    item["added_at"],
                    item["added_at"],
                ),
            )
        conn.commit()

    conn.execute("INSERT INTO meta (key, value) VALUES ('migrated', 'yes')")
    conn.commit()


def seed_ideas_if_empty() -> bool:
    """Load the tracked starter cards from enhancement_ideas_starter_seed.json,
    once, only when the board has no cards yet.

    Mirrors the Learning screen's seed_topics_if_empty / seed_cards_if_empty:
    a fresh clone starts with the project's planned work already on the board.
    A `meta` flag records that the seed ran, so deleting every card does not
    pull them back on the next start. Returns True when it seeded, else False.
    """
    if not SEED_FILE.exists():
        return False

    conn = _connect()
    try:
        if conn.execute("SELECT value FROM meta WHERE key = 'seeded'").fetchone():
            return False
        if conn.execute("SELECT 1 FROM ideas LIMIT 1").fetchone():
            conn.execute("INSERT INTO meta (key, value) VALUES ('seeded', 'yes')")
            conn.commit()
            return False

        payload = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        stamp = _now()
        for position, card in enumerate(payload.get("ideas", [])):
            title = (card.get("title") or "").strip()
            if not title:
                continue
            priority = card.get("priority", "medium")
            if priority not in PRIORITIES:
                priority = "medium"
            conn.execute(
                """INSERT INTO ideas
                   (id, enh_key, title, note, area, source,
                    status, priority, order_index, added_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'ai', 'ideas', ?, ?, ?, ?)""",
                (uuid.uuid4().hex[:12], next_enh_key(conn), title,
                 (card.get("note") or "").strip(), (card.get("area") or "").strip(),
                 priority, float(position), stamp, stamp),
            )
        conn.execute("INSERT INTO meta (key, value) VALUES ('seeded', 'yes')")
        conn.commit()
        return True
    finally:
        conn.close()


def next_enh_key(conn: sqlite3.Connection) -> str:
    """The next free ENH-n number, one past whatever exists now.

    Reads the numbers rather than counting rows on purpose - deleting an
    idea must never let its number get recycled onto a different idea.
    """
    row = conn.execute(
        """SELECT MAX(CAST(SUBSTR(enh_key, 5) AS INTEGER)) AS biggest
           FROM ideas WHERE enh_key LIKE 'ENH-%'"""
    ).fetchone()
    return f"ENH-{(row['biggest'] or 0) + 1}"

VALID_SOURCES = ("user", "ai")


class NoSuchIdea(Exception):
    """Raised by set_status(), update_idea() and remove_idea() for an id not on the board."""


class DuplicateIdea(Exception):
    """Raised by add_idea() when the exact same idea is already on the
    board (Phase-1 CS-2): a double-post - a retry, a stale form, a
    double click - must never become a second row. `.existing` carries
    the row already stored, so the caller can answer with it instead.

    Exact match only, on (title, note, area, source) with surrounding
    whitespace stripped. Near-duplicates stay the job of
    find_similar_ideas.py, which warns without blocking."""
    def __init__(self, existing: dict):
        super().__init__(
            f"identical idea already on the board as {existing['key']}")
        self.existing = existing


def _now() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


# =====================================================================
# SHAPING
# =====================================================================

_IDEA_COLUMNS = ("id, enh_key, title, note, area, source, "
                 "status, priority, order_index, added_at, updated_at")


def _item_from_row(row: sqlite3.Row) -> dict:
    """Shape one database row into what the page and the API speak -
    `key`, not `enh_key`, because the board calls it that everywhere."""
    return {
        "id": row["id"],
        "key": row["enh_key"],
        "title": row["title"],
        "note": row["note"],
        "area": row["area"],
        "source": row["source"],
        "status": row["status"],
        "priority": row["priority"],
        "order_index": row["order_index"],
        "added_at": row["added_at"],
        "updated_at": row["updated_at"],
        "comments": [],
    }


def _attach_comments(conn: sqlite3.Connection, items: list[dict]) -> list[dict]:
    """Group every comment under its own idea, oldest first - a comment
    thread read out of order is not a thread."""
    by_idea: dict[str, list[dict]] = {}
    for row in conn.execute(
        "SELECT * FROM comments ORDER BY created_at ASC, rowid ASC"
    ):
        by_idea.setdefault(row["idea_id"], []).append({
            "id": row["id"],
            "text": row["text"],
            "author": row["author"],
            "created_at": row["created_at"],
        })
    for item in items:
        item["comments"] = by_idea.get(item["id"], [])
    return items


# =====================================================================
# READS
# =====================================================================

def read_ideas() -> list[dict]:
    """Every idea, column by column, top to bottom inside each column.

    The column order follows STATUSES (capture first, done last) rather
    than the alphabet, because 'done' landing between 'in_progress' and
    'ideas' would read as nonsense on a board drawn left to right.
    """
    conn = _connect()
    try:
        case = " ".join(
            f"WHEN '{s}' THEN {n}" for n, s in enumerate(STATUSES)
        )
        rows = conn.execute(
            f"SELECT {_IDEA_COLUMNS} FROM ideas "
            f"ORDER BY CASE status {case} ELSE 99 END ASC, order_index ASC"
        )
        items = [_item_from_row(row) for row in rows]
        return _attach_comments(conn, items)
    finally:
        conn.close()


def get_idea(item_id: str) -> dict | None:
    """One idea by its 12-hex id, or None if it is not on the board."""
    conn = _connect()
    try:
        row = conn.execute(
            f"SELECT {_IDEA_COLUMNS} FROM ideas WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            return None
        return _attach_comments(conn, [_item_from_row(row)])[0]
    finally:
        conn.close()



# =====================================================================
# WRITES
# =====================================================================

def add_idea(title: str, note: str = "", area: str = "",
             source: str = "user", priority: str = "medium") -> dict:
    """Put a new idea at the bottom of the capture column."""
    title = (title or "").strip()
    if not title:
        raise ValueError("an idea needs a title")
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {VALID_SOURCES}, not '{source}'")
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {PRIORITIES}, not '{priority}'")

    conn = _connect()
    try:
        # Retry-safety (Phase-1 CS-2): the exact same idea - same
        # stripped title, note, area and source - already on the board
        # means this POST is a retry, so refuse to file it twice.
        existing = conn.execute(
            "SELECT id FROM ideas WHERE title = ? AND note = ? "
            "AND area = ? AND source = ?",
            (title, (note or "").strip(), (area or "").strip(), source),
        ).fetchone()
        if existing:
            row = conn.execute(
                f"SELECT {_IDEA_COLUMNS} FROM ideas WHERE id = ?",
                (existing["id"],)
            ).fetchone()
            raise DuplicateIdea(
                _attach_comments(conn, [_item_from_row(row)])[0])

        bottom = conn.execute(
            "SELECT COALESCE(MAX(order_index), -1) AS bottom "
            "FROM ideas WHERE status = 'ideas'"
        ).fetchone()["bottom"]
        stamp = _now()
        item_id = uuid.uuid4().hex[:12]
        enh_key = next_enh_key(conn)
        conn.execute(
            """INSERT INTO ideas
               (id, enh_key, title, note, area, source,
                status, priority, order_index, added_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'ideas', ?, ?, ?, ?)""",
            (item_id, enh_key, title, (note or "").strip(), (area or "").strip(),
             source, priority, bottom + 1, stamp, stamp),
        )
        conn.commit()
        return {
            "id": item_id, "key": enh_key, "title": title,
            "note": (note or "").strip(), "area": (area or "").strip(),
            "source": source, "status": "ideas", "priority": priority,
            "order_index": bottom + 1, "added_at": stamp,
            "updated_at": stamp, "comments": [],
        }
    finally:
        conn.close()


def update_idea(item_id: str, title: str | None = None,
                note: str | None = None, area: str | None = None,
                priority: str | None = None) -> dict:
    """Edit what an idea says. Only the fields actually passed change;
    touching any of them stamps updated_at so a card can show staleness."""
    conn = _connect()
    try:
        row = conn.execute(
            f"SELECT {_IDEA_COLUMNS} FROM ideas WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            raise NoSuchIdea(f"no idea with id '{item_id}'")
        if priority is not None and priority not in PRIORITIES:
            raise ValueError(f"priority must be one of {PRIORITIES}, not '{priority}'")

        new_title = (title or "").strip() if title is not None else row["title"]
        if not new_title:
            raise ValueError("an idea needs a title")

        conn.execute(
            """UPDATE ideas SET title = ?, note = ?, area = ?, priority = ?,
               updated_at = ? WHERE id = ?""",
            (new_title,
             (note or "").strip() if note is not None else row["note"],
             (area or "").strip() if area is not None else row["area"],
             priority if priority is not None else row["priority"],
             _now(), item_id),
        )
        conn.commit()
        fresh = conn.execute(
            f"SELECT {_IDEA_COLUMNS} FROM ideas WHERE id = ?", (item_id,)
        ).fetchone()
        return _attach_comments(conn, [_item_from_row(fresh)])[0]
    finally:
        conn.close()



def set_status(item_id: str, status: str,
               order_index: float | None = None) -> dict:
    """Move an idea to a column, either to a stated slot or to the very
    bottom of that column when no slot was given."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}, not '{status}'")

    conn = _connect()
    try:
        row = conn.execute(
            f"SELECT {_IDEA_COLUMNS} FROM ideas WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            raise NoSuchIdea(f"no idea with id '{item_id}'")

        if order_index is None:
            # Append: one past wherever the target column currently ends.
            bottom = conn.execute(
                "SELECT COALESCE(MAX(order_index), -1) AS bottom "
                "FROM ideas WHERE status = ?", (status,)
            ).fetchone()["bottom"]
            order_index = bottom + 1

        conn.execute(
            "UPDATE ideas SET status = ?, order_index = ?, updated_at = ? WHERE id = ?",
            (status, float(order_index), _now(), item_id),
        )
        conn.commit()
        fresh = conn.execute(
            f"SELECT {_IDEA_COLUMNS} FROM ideas WHERE id = ?", (item_id,)
        ).fetchone()
        return _attach_comments(conn, [_item_from_row(fresh)])[0]
    finally:
        conn.close()


def add_comment(item_id: str, text: str, author: str = "user") -> dict:
    """Pin a comment under an idea. Comments belong to their idea - they
    ride along through column moves and die with it on delete."""
    text = (text or "").strip()
    if not text:
        raise ValueError("a comment needs some text")
    if author not in VALID_SOURCES:
        raise ValueError(f"author must be one of {VALID_SOURCES}, not '{author}'")

    conn = _connect()
    try:
        if not conn.execute(
            "SELECT 1 FROM ideas WHERE id = ?", (item_id,)
        ).fetchone():
            raise NoSuchIdea(f"no idea with id '{item_id}'")
        comment = {
            "id": uuid.uuid4().hex[:12],
            "text": text,
            "author": author,
            "created_at": _now(),
        }
        conn.execute(
            """INSERT INTO comments (id, idea_id, text, author, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (comment["id"], item_id, comment["text"],
             comment["author"], comment["created_at"]),
        )
        conn.commit()
        return comment
    finally:
        conn.close()


def remove_idea(item_id: str) -> None:
    """Take an idea off the board, comments included - an orphaned
    comment pointing at a gone idea helps nobody."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM comments WHERE idea_id = ?", (item_id,))
        gone = conn.execute("DELETE FROM ideas WHERE id = ?", (item_id,))
        if gone.rowcount == 0:
            raise NoSuchIdea(f"no idea with id '{item_id}'")
        conn.commit()
    finally:
        conn.close()


# =====================================================================
# COMMAND LINE VIEW
# =====================================================================

def main() -> None:
    ideas = read_ideas()
    print("ENHANCEMENT BOARD")
    print("=" * 50)
    if not ideas:
        print("  Nothing captured yet.")
        return
    column_seen = None
    for idea in ideas:
        if idea["status"] != column_seen:
            column_seen = idea["status"]
            print(f"\n  -- {column_seen.upper()} --")
        tag = "AI" if idea["source"] == "ai" else "you"
        area = f" ({idea['area']})" if idea["area"] else ""
        print(f"  [{tag}] {idea['key']} {idea['title']}{area}")
        for c in idea["comments"]:
            who = "AI" if c["author"] == "ai" else "you"
            print(f"       - {who}: {c['text'][:60]}")


if __name__ == "__main__":
    main()

