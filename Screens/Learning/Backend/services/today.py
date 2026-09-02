"""TODAY — the focus cockpit. One hero next-step, a 3-item shortlist,
honest stats. The greeting line is Warden's job (deterministic for now;
the LLM pass will re-word it, the numbers stay computed)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

import settings_for_learning as cfg
from services.common import (
    get_db, today_str, room_mastery, short_name, streak_and_grace, get_setting,
)

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))


def _week_start() -> str:
    now = datetime.now(IST)
    return (now.date() - timedelta(days=now.weekday())).isoformat()


def _pick_hero(conn):
    """The current step: latest-touched learning room's current/first pending
    step; fall back to the first todo room."""
    room = conn.execute(
        """SELECT r.id, r.name, r.est_minutes, m.name module, m.track_id,
                  t.name track, t.color
           FROM rooms r
           JOIN modules m ON m.id = r.module_id
           JOIN tracks t ON t.id = m.track_id
           WHERE r.status='learning' AND r.archived=0
           ORDER BY (SELECT MAX(started_at) FROM sessions s WHERE s.room_id=r.id) DESC
           LIMIT 1"""
    ).fetchone()
    if not room:
        room = conn.execute(
            """SELECT r.id, r.name, r.est_minutes, m.name module, m.track_id,
                      t.name track, t.color
               FROM rooms r
               JOIN modules m ON m.id = r.module_id
               JOIN tracks t ON t.id = m.track_id
               WHERE r.status='todo' AND r.archived=0
               ORDER BY t.position, r.position LIMIT 1"""
        ).fetchone()
    if not room:
        return None, None, None

    step = conn.execute(
        """SELECT * FROM steps WHERE room_id=?
           ORDER BY (status='current') DESC, (status='todo') DESC, position
           LIMIT 1""",
        (room["id"],),
    ).fetchone()
    counts = conn.execute(
        "SELECT COUNT(*) total, COALESCE(SUM(status='done'),0) done "
        "FROM steps WHERE room_id=?",
        (room["id"],),
    ).fetchone()
    return room, step, counts


@router.get(cfg.API_PREFIX + "/today")
def today(conn=Depends(get_db)):
    room, step, counts = _pick_hero(conn)

    hero = None
    greeting = {"headline": "Nothing queued — add a room in Path.", "agent": "warden"}
    if room and step:
        left = counts["total"] - counts["done"]
        short = short_name(room["name"])
        if left > 0 and counts["done"] > 0:
            greeting = {
                "headline": (f"You're {left} step{'s' if left != 1 else ''} from "
                             f"finishing {short}."),
                "agent": "warden",
            }
        elif left > 0:
            greeting = {"headline": f"Fresh start: {short}, step 1 of {counts['total']}.",
                        "agent": "warden"}
        hero = {
            "room_id": room["id"], "room": short, "room_full": room["name"],
            "module": room["module"], "track": room["track"],
            "track_id": room["track_id"], "color": room["color"],
            "step_id": step["id"], "step_title": step["title"],
            "step_no": step["position"] + 1, "minutes": step["minutes"],
            "mastery": room_mastery(conn, room["id"]),
        }

    due = conn.execute(
        """SELECT COUNT(*) n FROM reviews
           WHERE due_date<=? AND status IN ('new','active')""",
        (today_str(),),
    ).fetchone()["n"]

    # weak spot: a learning room with bad checkpoint accuracy
    weak = conn.execute(
        """SELECT r.id, r.name, COUNT(a.id) n,
                  CAST(SUM(a.correct) AS REAL)/COUNT(a.id) acc
           FROM rooms r
           JOIN steps s ON s.room_id=r.id
           JOIN checkpoints ck ON ck.step_id=s.id
           JOIN attempts a ON a.checkpoint_id=ck.id AND a.correct IS NOT NULL
           WHERE r.status='learning'
           GROUP BY r.id HAVING n>=2 AND acc<0.5
           ORDER BY acc ASC LIMIT 1"""
    ).fetchone()

    # rhythm: last 14 days
    by_date = {r["d"]: r["m"] or 0 for r in conn.execute(
        "SELECT substr(started_at,1,10) d, SUM(actual_minutes) m FROM sessions "
        "WHERE substr(started_at,1,10)>=? GROUP BY d", (today_str(-13),)
    ).fetchall()}
    rhythm = []
    for i in range(14):
        d = (datetime.now(IST).date() - timedelta(days=13 - i)).isoformat()
        m = by_date.get(d, 0)
        rhythm.append({"day": d, "minutes": m, "done": m >= 5})

    # shortlist: hero + the other track's next thing + recall sweep
    plan = []
    if hero:
        plan.append({"kind": "step", "label": hero["step_title"],
                     "meta": f"{hero['room']} · step {hero['step_no']}",
                     "minutes": hero["minutes"], "room_id": hero["room_id"],
                     "color": hero["color"], "first": True})
    other = conn.execute(
        """SELECT r.id, r.name, s.title, s.minutes, t.color
           FROM rooms r
           JOIN modules m ON m.id=r.module_id
           JOIN tracks t ON t.id=m.track_id
           JOIN steps s ON s.room_id=r.id AND s.status!='done'
           WHERE r.status='learning' AND r.archived=0 AND r.id != COALESCE(?, -1)
           ORDER BY (t.color != COALESCE(?, '')) DESC, t.position, r.position
           LIMIT 1""",
        (hero["room_id"] if hero else None, hero["color"] if hero else None),
    ).fetchone()
    if other:
        plan.append({"kind": "step", "label": other["title"],
                     "meta": short_name(other["name"]),
                     "minutes": other["minutes"], "room_id": other["id"],
                     "color": other["color"], "first": False})
    if due:
        plan.append({"kind": "recall", "label": f"Recall sweep — {due} cards",
                     "meta": "interleaved", "minutes": max(5, round(due * 0.75)),
                     "room_id": None, "color": None, "first": False})

    # crew line (Warden): track balance over the week
    bal = conn.execute(
        """SELECT t.color, t.name, COALESCE(SUM(s.actual_minutes),0) m
           FROM sessions s JOIN rooms r ON r.id=s.room_id
           JOIN modules m2 ON m2.id=r.module_id
           JOIN tracks t ON t.id=m2.track_id
           WHERE substr(s.started_at,1,10)>=?
           GROUP BY t.color ORDER BY m DESC""",
        (today_str(-6),),
    ).fetchall()
    crew_line = "No sessions logged yet — the first one starts the story."
    if bal:
        if len(bal) > 1:
            share = round(100 * bal[0]["m"] / max(1, bal[0]["m"] + bal[1]["m"]))
            crew_line = (f"Recent minutes lean toward “{bal[0]['name']}” "
                         f"({share}%). One proposal is waiting in Crew.")
        else:
            crew_line = f"Only “{bal[0]['name']}” is moving — Planner says touch the other."

    return {
        "greeting": greeting,
        "hero": hero,
        "plan": plan,
        "rhythm": rhythm,
        "streak": streak_and_grace(conn),
        "due_cards": due,
        "weak_spot": ({"room_id": weak["id"], "room": short_name(weak["name"]),
                       "accuracy": round(weak["acc"] * 100), "misses": weak["n"]}
                      if weak else None),
        "crew_line": crew_line,
        "week_minutes": conn.execute(
            "SELECT COALESCE(SUM(actual_minutes),0) m FROM sessions "
            "WHERE substr(started_at,1,10)>=?", (_week_start(),)
        ).fetchone()["m"],
        "week_budget": int(get_setting(conn, "weekly_budget_minutes", "300")),
    }
