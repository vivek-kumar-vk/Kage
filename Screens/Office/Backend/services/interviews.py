"""INTERVIEW PREP - one row per scheduled interview, each with a free
markdown prep pack. Calendar order; honest empty."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_office as cfg
from services.common import get_db, today_str

router = APIRouter()

OUTCOMES = ["pending", "passed", "failed", "withdrawn"]


class IvIn(BaseModel):
    company: str
    role: str | None = None
    round: str | None = None
    scheduled_at: str                       # 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'
    mode: str | None = None
    prep_pack: str | None = None
    application_id: int | None = None


class IvPatch(BaseModel):
    company: str | None = None
    role: str | None = None
    round: str | None = None
    scheduled_at: str | None = None
    mode: str | None = None
    prep_pack: str | None = None
    outcome: str | None = None
    application_id: int | None = None


@router.get(cfg.API_PREFIX + "/interviews")
def list_interviews(conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT * FROM interviews ORDER BY scheduled_at ASC, id ASC"
    ).fetchall()
    today = today_str()
    out = []
    for r in rows:
        d = dict(r)
        day = (r["scheduled_at"] or "")[:10]
        d["is_today"] = day == today
        d["is_upcoming"] = day >= today
        d["prep_missing"] = not (r["prep_pack"] or "").strip()
        out.append(d)
    return {"outcomes": OUTCOMES, "interviews": out, "empty": len(rows) == 0}


@router.post(cfg.API_PREFIX + "/interviews")
def create_interview(body: IvIn, conn=Depends(get_db)):
    cur = conn.execute(
        """INSERT INTO interviews (application_id, company, role, round,
                                   scheduled_at, mode, prep_pack)
           VALUES (?,?,?,?,?,?,?)""",
        (body.application_id, body.company, body.role, body.round,
         body.scheduled_at, body.mode, body.prep_pack),
    )
    conn.commit()
    return {"id": cur.lastrowid}


@router.patch(cfg.API_PREFIX + "/interviews/{iv_id}")
def update_interview(iv_id: int, body: IvPatch, conn=Depends(get_db)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(422, "nothing to update")
    if fields.get("outcome") and fields["outcome"] not in OUTCOMES:
        raise HTTPException(422, f"outcome must be one of {OUTCOMES}")
    if not conn.execute("SELECT 1 FROM interviews WHERE id=?", (iv_id,)).fetchone():
        raise HTTPException(404, "no such interview")
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE interviews SET {sets} WHERE id=?", (*fields.values(), iv_id)
    )
    conn.commit()
    return {"ok": True}


@router.delete(cfg.API_PREFIX + "/interviews/{iv_id}")
def delete_interview(iv_id: int, conn=Depends(get_db)):
    conn.execute("DELETE FROM interviews WHERE id=?", (iv_id,))
    conn.commit()
    return {"ok": True}
