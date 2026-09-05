"""RESUME READINESS - the no-inflation gate (D17.5).

A skill is resume-defensible ONLY at >=2 Good/Easy recall ratings in the
Learning screen. This screen never sets that flag by hand: it fetches
Learning's /api/learning/skills, mirrors the numbers into office.db with a
fetched_at, and recomputes `defensible` locally from the same rule so a
tampered mirror still can't lie.

Learning down => every row keeps its last mirrored numbers but carries the
state string ("learning screen unreachable") and its stale fetched_at, so
the tab shows plainly that the figure is old. That is the D17.5-blessed
mirror pattern, not a silent carry-forward (Rule 22).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

import settings_for_office as cfg
from services.common import get_db, now_str
from services import learning_client

router = APIRouter()

DEFENSIBLE_MIN = 2


class SkillIn(BaseModel):
    name: str
    skill_tag: str | None = None            # defaults to name.lower()
    on_resume: bool = False


def _sync(conn) -> str:
    """Pull Learning's numbers into the skills mirror. Returns the state."""
    state, remote = learning_client.fetch_skills()
    by_tag = {(s.get("skill") or "").strip().lower(): s for s in remote}

    for row in conn.execute("SELECT * FROM skills").fetchall():
        tag = (row["skill_tag"] or row["name"]).strip().lower()
        if state == learning_client.OK and tag in by_tag:
            r = by_tag[tag]
            ge = int(r.get("good_easy") or 0)
            conn.execute(
                """UPDATE skills SET good_easy=?, rooms_tagged=?, defensible=?,
                          learning_state=?, fetched_at=? WHERE id=?""",
                (ge, int(r.get("rooms_tagged") or 0),
                 1 if ge >= DEFENSIBLE_MIN else 0,
                 learning_client.OK, now_str(), row["id"]),
            )
        elif state == learning_client.OK:
            # Learning is up but has no tagged rooms for this skill yet.
            conn.execute(
                """UPDATE skills SET good_easy=0, rooms_tagged=0, defensible=0,
                          learning_state=?, fetched_at=? WHERE id=?""",
                ("no rooms tagged in learning", now_str(), row["id"]),
            )
        else:
            # Learning unreachable / endpoint missing: keep last numbers,
            # record the state, do NOT touch fetched_at (it stays stale).
            conn.execute(
                "UPDATE skills SET learning_state=? WHERE id=?",
                (state, row["id"]),
            )
    conn.commit()
    return state


@router.get(cfg.API_PREFIX + "/resume-readiness")
def resume_readiness(conn=Depends(get_db)):
    state = _sync(conn)
    rows = conn.execute(
        "SELECT * FROM skills ORDER BY name"
    ).fetchall()
    skills = [dict(r) for r in rows]
    for s in skills:
        s["defensible"] = bool(s["defensible"])
        s["on_resume"] = bool(s["on_resume"])
        # the one that matters: claimed on the resume but not earned
        s["inflated"] = s["on_resume"] and not s["defensible"]

    return {
        "rule": f">={DEFENSIBLE_MIN} Good/Easy recall ratings in Learning",
        "learning_url": cfg.LEARNING_URL,
        "learning_state": state,
        "skills": skills,
        "inflated_count": sum(1 for s in skills if s["inflated"]),
        "empty": len(skills) == 0,
    }


@router.post(cfg.API_PREFIX + "/skills")
def add_skill(body: SkillIn, conn=Depends(get_db)):
    tag = (body.skill_tag or body.name).strip().lower()
    conn.execute(
        """INSERT INTO skills (name, skill_tag, on_resume)
           VALUES (?,?,?)
           ON CONFLICT(name) DO UPDATE SET skill_tag=excluded.skill_tag,
                                           on_resume=excluded.on_resume""",
        (body.name.strip(), tag, 1 if body.on_resume else 0),
    )
    conn.commit()
    return {"ok": True}


@router.patch(cfg.API_PREFIX + "/skills/{skill_id}")
def set_on_resume(skill_id: int, on_resume: bool, conn=Depends(get_db)):
    conn.execute(
        "UPDATE skills SET on_resume=? WHERE id=?",
        (1 if on_resume else 0, skill_id),
    )
    conn.commit()
    return {"ok": True}


@router.delete(cfg.API_PREFIX + "/skills/{skill_id}")
def delete_skill(skill_id: int, conn=Depends(get_db)):
    conn.execute("DELETE FROM skills WHERE id=?", (skill_id,))
    conn.commit()
    return {"ok": True}
