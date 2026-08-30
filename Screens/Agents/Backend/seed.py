import json
import uuid
from datetime import datetime, timedelta, timezone

import settings_for_agents as cfg
from db import connect

IST = timezone(timedelta(hours=5, minutes=30))

VALID_STATUS = {"ideas", "todo", "in_progress", "done"}
VALID_PRIORITY = {"low", "medium", "high", "critical"}
VALID_SOURCE = {"user", "ai"}

GENERIC_IDEAS = [
    {
        "title": "Define the workspace goal",
        "note": "State what the agent deck should do in one sentence.",
        "area": "plan",
        "source": "ai",
        "status": "ideas",
        "priority": "high",
    },
    {
        "title": "List the first rooms",
        "note": "Keep Board and Runs visible before adding agent rooms.",
        "area": "plan",
        "source": "ai",
        "status": "ideas",
        "priority": "medium",
    },
    {
        "title": "Review board columns",
        "note": "Check that ideas, todo, in progress, and done still match the workflow.",
        "area": "board",
        "source": "ai",
        "status": "ideas",
        "priority": "medium",
    },
    {
        "title": "Draft agent role cards",
        "note": "Give each agent one plain role sentence for the right pane.",
        "area": "agents",
        "source": "ai",
        "status": "ideas",
        "priority": "medium",
    },
    {
        "title": "Prepare local seed examples",
        "note": "Keep the local seed file generic and safe to commit as an example.",
        "area": "data",
        "source": "ai",
        "status": "ideas",
        "priority": "low",
    },
    {
        "title": "Plan verification gate",
        "note": "List the commands that prove the screen starts cleanly.",
        "area": "quality",
        "source": "ai",
        "status": "ideas",
        "priority": "high",
    },
    {
        "title": "Collect next improvements",
        "note": "Capture small follow-up tasks after the first working pass.",
        "area": "backlog",
        "source": "ai",
        "status": "ideas",
        "priority": "low",
    },
]


def _now():
    return datetime.now(IST).replace(microsecond=0).isoformat()


def _text(value, default=""):
    if value is None:
        return default
    return str(value)


def _choice(value, valid, default):
    value = _text(value, default).strip()
    return value if value in valid else default


def _order_index(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _meta_seeded(conn):
    row = conn.execute("SELECT value FROM meta WHERE key = 'seeded'").fetchone()
    return bool(row and row["value"] == "yes")


def _mark_seeded(conn):
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('seeded', 'yes')")


def _existing_enh_numbers(conn):
    numbers = set()
    rows = conn.execute("SELECT enh_key FROM ideas").fetchall()

    for row in rows:
        key = _text(row["enh_key"]).strip()
        if key.startswith("ENH-"):
            try:
                numbers.add(int(key.split("-", 1)[1]))
            except ValueError:
                pass

    return numbers


def _next_enh_key(used_keys, used_numbers):
    n = max(used_numbers) + 1 if used_numbers else 1

    while n in used_numbers:
        n += 1

    key = f"ENH-{n}"
    used_numbers.add(n)
    used_keys.add(key)
    return key


def _assign_key(raw_key, used_keys, used_numbers):
    key = _text(raw_key).strip()

    if key and key.startswith("ENH-") and key not in used_keys:
        used_keys.add(key)
        try:
            used_numbers.add(int(key.split("-", 1)[1]))
        except ValueError:
            pass
        return key

    return _next_enh_key(used_keys, used_numbers)


def _timestamp(value, fallback):
    value = _text(value).strip()

    if not value or value == "@today":
        return fallback

    return value


def _normalize_idea(raw, fallback_order, existing_ids, used_keys, used_numbers, now):
    if not isinstance(raw, dict):
        return None

    title = _text(raw.get("title")).strip()
    if not title:
        return None

    idea_id = _text(raw.get("id")).strip()
    if not idea_id or idea_id in existing_ids:
        while True:
            idea_id = uuid.uuid4().hex[:12]
            if idea_id not in existing_ids:
                existing_ids.add(idea_id)
                break
    else:
        existing_ids.add(idea_id)

    added_at = _timestamp(raw.get("added_at"), now)
    updated_at = _timestamp(raw.get("updated_at"), added_at or now)

    return {
        "id": idea_id,
        "enh_key": _assign_key(raw.get("key") or raw.get("enh_key"), used_keys, used_numbers),
        "title": title,
        "note": _text(raw.get("note")),
        "area": _text(raw.get("area")),
        "source": _choice(raw.get("source"), VALID_SOURCE, "user"),
        "status": _choice(raw.get("status"), VALID_STATUS, "ideas"),
        "priority": _choice(raw.get("priority"), VALID_PRIORITY, "medium"),
        "order_index": _order_index(raw.get("order_index"), fallback_order),
        "added_at": added_at,
        "updated_at": updated_at,
    }


def _insert_idea(conn, idea):
    conn.execute(
        """
        INSERT INTO ideas (
            id, enh_key, title, note, area, source, status, priority,
            order_index, added_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            idea["id"],
            idea["enh_key"],
            idea["title"],
            idea["note"],
            idea["area"],
            idea["source"],
            idea["status"],
            idea["priority"],
            idea["order_index"],
            idea["added_at"],
            idea["updated_at"],
        ),
    )


def _load_local_seed():
    path = cfg.HERE / "seed_local.json"

    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return data if isinstance(data, dict) else None


def _seed_ideas(conn):
    if conn.execute("SELECT COUNT(*) AS n FROM ideas").fetchone()["n"] > 0:
        _mark_seeded(conn)
        return

    if _meta_seeded(conn):
        return

    now = _now()
    existing_ids = set()
    used_keys = set()
    used_numbers = _existing_enh_numbers(conn)
    data = _load_local_seed()

    if data is not None and isinstance(data.get("ideas"), list):
        raw_ideas = data["ideas"]
    else:
        raw_ideas = GENERIC_IDEAS

    for index, raw in enumerate(raw_ideas, start=1):
        idea = _normalize_idea(
            raw,
            float(index),
            existing_ids,
            used_keys,
            used_numbers,
            now,
        )
        if idea:
            _insert_idea(conn, idea)

    _mark_seeded(conn)


def _upsert_room(conn, room_id, kind, name, agent_name, position):
    row = conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()

    if row:
        conn.execute(
            "UPDATE rooms SET kind = ?, name = ?, agent_name = ? WHERE id = ?",
            (kind, name, agent_name, room_id),
        )
    else:
        conn.execute(
            """
            INSERT INTO rooms (id, kind, name, agent_name, position, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (room_id, kind, name, agent_name, position, _now()),
        )


def _seed_rooms(conn):
    _upsert_room(conn, "board", "board", "Board", "Agent_Head", 1.0)
    _upsert_room(conn, "runs", "system", "Runs", None, 2.0)


def run():
    conn = connect()
    try:
        _seed_rooms(conn)
        _seed_ideas(conn)
        conn.commit()
    finally:
        conn.close()
