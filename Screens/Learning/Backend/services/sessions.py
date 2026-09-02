"""FOCUS SESSIONS — start/finish a real timed session; everything is logged
to the ledger. The UI runs the timer; the backend owns the record."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import settings_for_learning as cfg
from services.common import get_db, now_str, ledger, short_name

router = APIRouter()


class StartBody(BaseModel):
    room_id: int | None = None
    planned_minutes: int = 25


class FinishBody(BaseModel):
    actual_minutes: int
    note: str | None = None
    confidence: int | None = None   # 1-5 self-rating, feeds Insights


@router.post(cfg.API_PREFIX + "/session/start")
def start_session(body: StartBody, conn=Depends(get_db)):
    room = None
    if body.room_id:
        room = conn.execute("SELECT * FROM rooms WHERE id=?", (body.room_id,)).fetchone()
    cur = conn.execute(
        """INSERT INTO sessions (room_id, started_at, planned_minutes)
           VALUES (?,?,?)""",
        (room["id"] if room else None, now_str(), body.planned_minutes),
    )
    conn.execute(
        "UPDATE rooms SET status='learning' WHERE id=? AND status='todo'",
        (room["id"],),
    ) if room else None
    ledger(conn, "session",
           f"focus session started — {body.planned_minutes} min"
           + (f" · {short_name(room['name'])}" if room else ""),
           ref=f"session:{cur.lastrowid}")
    conn.commit()
    return {"session_id": cur.lastrowid, "room_id": room["id"] if room else None,
            "planned_minutes": body.planned_minutes, "started_at": now_str()}


@router.post(cfg.API_PREFIX + "/session/{session_id}/finish")
def finish_session(session_id: int, body: FinishBody, conn=Depends(get_db)):
    row = conn.execute(
        "SELECT * FROM sessions WHERE id=?", (session_id,)
    ).fetchone()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(404, "no such session")
    conn.execute(
        """UPDATE sessions SET ended_at=?, actual_minutes=?, notes=?, confidence=?
           WHERE id=?""",
        (now_str(), body.actual_minutes, body.note, body.confidence, session_id),
    )
    room = conn.execute("SELECT name FROM rooms WHERE id=?",
                        (row["room_id"],)).fetchone() if row["room_id"] else None
    ledger(conn, "session",
           f"focus session logged — {body.actual_minutes} min"
           + (f" · {short_name(room['name'])}" if room else ""),
           ref=f"session:{session_id}")
    conn.commit()
    return {"ok": True, "session_id": session_id,
            "actual_minutes": body.actual_minutes}


@router.get(cfg.API_PREFIX + "/sessions")
def list_sessions(limit: int = 20, conn=Depends(get_db)):
    rows = conn.execute(
        """SELECT s.*, r.name room FROM sessions s
           LEFT JOIN rooms r ON r.id=s.room_id
           WHERE s.ended_at IS NOT NULL
           ORDER BY s.started_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [{"id": r["id"], "room": r["room"], "started_at": r["started_at"],
             "ended_at": r["ended_at"], "actual_minutes": r["actual_minutes"],
             "confidence": r["confidence"], "note": r["notes"]} for r in rows]
