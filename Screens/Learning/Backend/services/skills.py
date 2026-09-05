"""SKILLS — the resume-defensibility read the Office screen (M7) consumes.

Not a tab (Learning is already at the 5-tab cap). One endpoint, same
role as /context/: another localhost screen reads it over HTTP (Rule 5).

THE RULE (D17.5)
    A skill is resume-defensible only at >=2 Good/Easy card ratings across
    the rooms tagged with it. This endpoint reports the count and the
    boolean; Office mirrors it and never sets the flag by hand.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

import settings_for_learning as cfg
from services.common import get_db

router = APIRouter()

DEFENSIBLE_MIN = 2


@router.get(cfg.API_PREFIX + "/skills")
def skills(conn=Depends(get_db)):
    """One row per skill_tag set on a live room. Honest empty when no
    room carries a tag yet."""
    rows = conn.execute(
        """SELECT r.skill_tag AS skill,
                  COUNT(DISTINCT r.id) AS rooms_tagged,
                  COALESCE(SUM(CASE WHEN rv.last_result IN ('good','easy')
                                    THEN 1 ELSE 0 END), 0) AS good_easy
           FROM rooms r
           LEFT JOIN cards c   ON c.room_id = r.id
           LEFT JOIN reviews rv ON rv.card_id = c.id
           WHERE r.skill_tag IS NOT NULL AND TRIM(r.skill_tag) <> ''
             AND r.archived = 0
           GROUP BY r.skill_tag
           ORDER BY r.skill_tag""",
    ).fetchall()

    return {
        "rule": f">={DEFENSIBLE_MIN} Good/Easy card ratings",
        "skills": [
            {
                "skill": r["skill"],
                "rooms_tagged": r["rooms_tagged"],
                "good_easy": r["good_easy"],
                "defensible": r["good_easy"] >= DEFENSIBLE_MIN,
            }
            for r in rows
        ],
    }
