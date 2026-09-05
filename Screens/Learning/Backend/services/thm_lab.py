"""TryHackMe standing lab helpers: schema migration, tagging, THM-only streak, and listing."""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def ensure_schema(conn) -> None:
    """Idempotent: adds rooms.lab_url and rooms.source if not already present."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(rooms)").fetchall()}
    if "lab_url" not in columns:
        conn.execute("ALTER TABLE rooms ADD COLUMN lab_url TEXT")
    if "source" not in columns:
        conn.execute("ALTER TABLE rooms ADD COLUMN source TEXT")
    conn.commit()


def set_lab(conn, room_id: int, lab_url: str, source: str = "thm") -> None:
    """Set lab_url + source on one room. Commits."""
    if not lab_url or not lab_url.strip():
        raise ValueError("lab_url must not be empty or blank")
    row = conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if row is None:
        raise ValueError(f"room_id {room_id} does not exist in rooms")
    conn.execute(
        "UPDATE rooms SET lab_url = ?, source = ? WHERE id = ?",
        (lab_url.strip(), source, room_id),
    )
    conn.commit()


def thm_streak_and_grace(conn) -> dict:
    """Same consecutive-day/grace logic as streak_and_grace, but counting only sessions whose room has source='thm'. Returns {"count": int, "grace": int}. No sessions on a thm room -> {"count": 0, "grace": grace}."""
    dates = [
        r["d"]
        for r in conn.execute(
            "SELECT DISTINCT substr(s.started_at, 1, 10) AS d "
            "FROM sessions s JOIN rooms r ON r.id = s.room_id "
            "WHERE r.source = 'thm' AND s.started_at IS NOT NULL "
            "ORDER BY d DESC"
        ).fetchall()
    ]

    grace_row = conn.execute(
        "SELECT value FROM settings WHERE key = ?", ("grace_days",)
    ).fetchone()
    grace = int(grace_row["value"]) if grace_row else 1

    if not dates:
        return {"count": 0, "grace": grace}

    today = datetime.now(IST).date()

    def to_date(s: str):
        return datetime.fromisoformat(s).date()

    count, prev = 0, None
    for d in dates:
        dd = to_date(d)
        if prev is None:
            if (today - dd).days > 1 + grace:
                break
        elif (prev - dd).days > 1 + grace:
            break
        count += 1
        prev = dd

    return {"count": count, "grace": grace}


def list_thm_rooms(conn) -> list[dict]:
    """All non-archived rooms with source='thm': id, name, lab_url, status. Ordered by name."""
    rows = conn.execute(
        "SELECT id, name, lab_url, status FROM rooms "
        "WHERE source = 'thm' AND archived = 0 ORDER BY name"
    ).fetchall()
    return [dict(row) for row in rows]