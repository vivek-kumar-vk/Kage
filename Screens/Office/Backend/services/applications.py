"""APPLICATIONS - the pipeline: saved -> applied -> screen -> interview ->
offer / reject. Plain CRUD, one stage field, honest empty."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_office as cfg
from services.common import get_db, now_str

router = APIRouter()


class AppIn(BaseModel):
    company: str
    role: str
    portal: str | None = None
    link: str | None = None
    stage: str = "saved"
    notes: str | None = None


class AppPatch(BaseModel):
    company: str | None = None
    role: str | None = None
    portal: str | None = None
    link: str | None = None
    stage: str | None = None
    notes: str | None = None


def _check_stage(stage: str) -> None:
    if stage not in cfg.STAGES:
        raise HTTPException(422, f"stage must be one of {cfg.STAGES}")


@router.get(cfg.API_PREFIX + "/applications")
def list_applications(conn=Depends(get_db)):
    rows = conn.execute(
        "SELECT * FROM applications ORDER BY updated_at DESC, id DESC"
    ).fetchall()
    funnel = {s: 0 for s in cfg.STAGES}
    for r in rows:
        funnel[r["stage"]] = funnel.get(r["stage"], 0) + 1
    return {
        "stages": cfg.STAGES,
        "funnel": funnel,
        "applications": [dict(r) for r in rows],
        "empty": len(rows) == 0,
    }


@router.post(cfg.API_PREFIX + "/applications")
def create_application(body: AppIn, conn=Depends(get_db)):
    _check_stage(body.stage)
    cur = conn.execute(
        """INSERT INTO applications (company, role, portal, link, stage, notes,
                                     created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (body.company, body.role, body.portal, body.link, body.stage,
         body.notes, now_str(), now_str()),
    )
    conn.commit()
    return {"id": cur.lastrowid}


@router.patch(cfg.API_PREFIX + "/applications/{app_id}")
def update_application(app_id: int, body: AppPatch, conn=Depends(get_db)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(422, "nothing to update")
    if "stage" in fields:
        _check_stage(fields["stage"])
    exists = conn.execute(
        "SELECT 1 FROM applications WHERE id=?", (app_id,)
    ).fetchone()
    if not exists:
        raise HTTPException(404, "no such application")
    fields["updated_at"] = now_str()
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE applications SET {sets} WHERE id=?",
        (*fields.values(), app_id),
    )
    conn.commit()
    return {"ok": True}


@router.delete(cfg.API_PREFIX + "/applications/{app_id}")
def delete_application(app_id: int, conn=Depends(get_db)):
    conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
    conn.commit()
    return {"ok": True}
