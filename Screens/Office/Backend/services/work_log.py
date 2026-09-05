"""WORK LOG - daily office entries, tagged by tech (free text). Entries
become suggested real-world examples for Learning's recall cards (part 4),
fetched by Quizmaster later (M8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_office as cfg
from services.common import get_db, today_str

router = APIRouter()


class LogIn(BaseModel):
    summary: str
    log_date: str | None = None             # defaults to today
    tech: str | None = None
    detail: str | None = None
    minutes: int | None = None


class LogPatch(BaseModel):
    summary: str | None = None
    log_date: str | None = None
    tech: str | None = None
    detail: str | None = None
    minutes: int | None = None


@router.get(cfg.API_PREFIX + "/work-log")
def list_work_log(conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT * FROM work_log ORDER BY log_date DESC, id DESC"
    ).fetchall()
    techs = sorted({r["tech"] for r in rows if (r["tech"] or "").strip()})
    return {
        "today": today_str(),
        "known_techs": techs,               # datalist suggestions, not a fixed set
        "entries": [dict(r) for r in rows],
        "empty": len(rows) == 0,
    }


@router.post(cfg.API_PREFIX + "/work-log")
def create_entry(body: LogIn, conn=Depends(get_db)):
    cur = conn.execute(
        """INSERT INTO work_log (log_date, tech, summary, detail, minutes)
           VALUES (?,?,?,?,?)""",
        (body.log_date or today_str(), body.tech, body.summary,
         body.detail, body.minutes),
    )
    conn.commit()
    return {"id": cur.lastrowid}


@router.patch(cfg.API_PREFIX + "/work-log/{entry_id}")
def update_entry(entry_id: int, body: LogPatch, conn=Depends(get_db)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(422, "nothing to update")
    if not conn.execute("SELECT 1 FROM work_log WHERE id=?", (entry_id,)).fetchone():
        raise HTTPException(404, "no such entry")
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE work_log SET {sets} WHERE id=?", (*fields.values(), entry_id)
    )
    conn.commit()
    return {"ok": True}


@router.delete(cfg.API_PREFIX + "/work-log/{entry_id}")
def delete_entry(entry_id: int, conn=Depends(get_db)):
    conn.execute("DELETE FROM work_log WHERE id=?", (entry_id,))
    conn.commit()
    return {"ok": True}
