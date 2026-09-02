"""Shared helpers for the Learning OS v2 services."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def get_db():
    from db import connect
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def today_str(offset_days: int = 0) -> str:
    return (datetime.now(IST) + timedelta(days=offset_days)).date().isoformat()


def now_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def jload(text, fallback):
    try:
        return json.loads(text) if text else fallback
    except (TypeError, ValueError):
        return fallback


def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def ledger(conn, kind: str, text: str, ref: str | None = None) -> None:
    conn.execute(
        "INSERT INTO ledger (ts, kind, ref, text) VALUES (?,?,?,?)",
        (now_str(), kind, ref, text),
    )


def get_setting(conn, key: str, default: str) -> str:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def room_steps(conn, room_id: int):
    return conn.execute(
        "SELECT * FROM steps WHERE room_id=? ORDER BY position, id", (room_id,)
    ).fetchall()


def room_mastery(conn, room_id: int) -> int:
    """0-100: 55% step completion + 45% checkpoint accuracy."""
    st = conn.execute(
        """SELECT COUNT(*) total, COALESCE(SUM(status='done'),0) done
           FROM steps WHERE room_id=?""",
        (room_id,),
    ).fetchone()
    total, done = st["total"], st["done"]
    att = conn.execute(
        """SELECT COUNT(*) n, COALESCE(SUM(a.correct),0) ok
           FROM attempts a
           JOIN checkpoints ck ON ck.id = a.checkpoint_id
           JOIN steps s ON s.id = ck.step_id
           WHERE s.room_id=? AND a.correct IS NOT NULL""",
        (room_id,),
    ).fetchone()
    acc = (att["ok"] / att["n"]) if att["n"] else 0.0
    step_part = (done / total) if total else 0.0
    return round(100 * (0.55 * step_part + 0.45 * acc))


def level_for(pct: int) -> str:
    if pct >= 85:
        return "mastered"
    if pct >= 65:
        return "strong"
    if pct >= 40:
        return "familiar"
    if pct >= 15:
        return "learning"
    return "novice"


def short_name(name: str) -> str:
    """Room names carry parenthetical detail — the headline wants the short form."""
    for sep in ("(", "—"):
        if sep in name:
            name = name.split(sep)[0]
    return name.strip().rstrip(",.")


def streak_and_grace(conn) -> dict:
    """Consecutive-day streak counting any session; grace days from settings.
    A gap of up to `grace` missed days does not break the chain."""
    dates = [r["d"] for r in conn.execute(
        "SELECT DISTINCT substr(started_at,1,10) d FROM sessions "
        "WHERE started_at IS NOT NULL ORDER BY d DESC"
    ).fetchall()]
    grace = int(get_setting(conn, "grace_days", "1"))
    if not dates:
        return {"count": 0, "grace": grace}
    today = datetime.now(IST).date()

    def to_date(s: str):
        return datetime.fromisoformat(s).date()

    count, prev = 0, None
    for d in dates:
        dd = to_date(d)
        if prev is None:
            if (today - dd).days > 1 + grace:  # even grace can't save it
                break
        elif (prev - dd).days > 1 + grace:     # gap too wide mid-chain
            break
        count += 1
        prev = dd
    return {"count": count, "grace": grace}
