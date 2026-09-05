"""OVERVIEW - the one-glance funnel: today's apply target, interviews this
week, prep due, pipeline snapshot. Every number here is counted from
office.db, never assumed."""

from __future__ import annotations

from fastapi import APIRouter, Depends

import settings_for_office as cfg
from services.common import get_db, today_str

router = APIRouter()


@router.get(cfg.API_PREFIX + "/overview")
def overview(conn=Depends(get_db)):
    today = today_str()
    week_end = today_str(7)

    applied_today = conn.execute(
        """SELECT COUNT(*) c FROM applications
           WHERE stage NOT IN ('saved') AND substr(updated_at,1,10)=?""",
        (today,),
    ).fetchone()["c"]

    funnel_rows = conn.execute(
        "SELECT stage, COUNT(*) c FROM applications GROUP BY stage"
    ).fetchall()
    funnel = {s: 0 for s in cfg.STAGES}
    for r in funnel_rows:
        funnel[r["stage"]] = r["c"]

    interviews_week = conn.execute(
        """SELECT COUNT(*) c FROM interviews
           WHERE substr(scheduled_at,1,10) BETWEEN ? AND ?
             AND outcome='pending'""",
        (today, week_end),
    ).fetchone()["c"]

    prep_due = conn.execute(
        """SELECT COUNT(*) c FROM interviews
           WHERE substr(scheduled_at,1,10) BETWEEN ? AND ?
             AND outcome='pending'
             AND (prep_pack IS NULL OR TRIM(prep_pack)='')""",
        (today, week_end),
    ).fetchone()["c"]

    interview_today = conn.execute(
        """SELECT COUNT(*) c FROM interviews
           WHERE substr(scheduled_at,1,10)=? AND outcome='pending'""",
        (today,),
    ).fetchone()["c"]

    total_apps = sum(funnel.values())

    return {
        "date": today,
        "apply_target": cfg.APPLY_TARGET_PER_DAY,
        "applied_today": applied_today,
        "apply_target_met": applied_today >= cfg.APPLY_TARGET_PER_DAY,
        "interviews_this_week": interviews_week,
        "interview_today": interview_today,          # M6 preemption reads this
        "prep_due": prep_due,
        "funnel": funnel,
        "stages": cfg.STAGES,
        "empty": total_apps == 0,
    }
