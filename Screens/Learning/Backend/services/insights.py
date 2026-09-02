"""INSIGHTS — the miss-nothing tab. Everything is computed from the ledger,
attempts, reviews and sessions; nothing here is hand-entered."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends

import settings_for_learning as cfg
from services.common import (
    get_db, today_str, room_mastery, level_for, short_name, streak_and_grace,
)

router = APIRouter()


def _rooms(conn):
    return conn.execute(
        """SELECT r.*, m.name module, m.track_id, t.name track, t.color
           FROM rooms r JOIN modules m ON m.id=r.module_id
           JOIN tracks t ON t.id=m.track_id
           WHERE r.archived=0 ORDER BY t.position, m.position, r.position"""
    ).fetchall()


def _room_accuracy(conn, room_id):
    row = conn.execute(
        """SELECT COUNT(*) n, CAST(COALESCE(SUM(a.correct),0) AS REAL) ok
           FROM attempts a JOIN checkpoints ck ON ck.id=a.checkpoint_id
           JOIN steps s ON s.id=ck.step_id
           WHERE s.room_id=? AND a.correct IS NOT NULL""",
        (room_id,),
    ).fetchone()
    return (row["ok"] / row["n"]) if row["n"] else None


@router.get(cfg.API_PREFIX + "/insights")
def insights(conn=Depends(get_db)):
    rooms = _rooms(conn)

    # ---- mastery map -------------------------------------------------------
    tracks_map = {}
    for r in rooms:
        pct = room_mastery(conn, r["id"])
        tracks_map.setdefault(
            (r["track_id"], r["track"], r["color"], r["module"]), []
        ).append({"id": r["id"], "name": short_name(r["name"]),
                  "mastery": pct, "level": level_for(pct), "status": r["status"]})
    mastery = []
    seen = {}
    for (tid, tname, color, module), items in tracks_map.items():
        key = (tid, tname, color)
        if key not in seen:
            seen[key] = {"track_id": tid, "track": tname, "color": color,
                         "modules": []}
        seen[key]["modules"].append({"module": module, "rooms": items})
    mastery = list(seen.values())

    # ---- retention: per-room current holding %, decayed by idle days -------
    retention = []
    for r in rooms:
        acc = _room_accuracy(conn, r["id"])
        last = conn.execute(
            "SELECT MAX(ended_at) e FROM sessions WHERE room_id=?", (r["id"],)
        ).fetchone()["e"]
        if acc is None or not last:
            continue
        idle = max(0, (today_str_as_date() - _d(last)).days)
        holding = round(100 * acc * (0.97 ** idle))
        retention.append({"room_id": r["id"], "room": short_name(r["name"]),
                          "color": r["color"], "holding": max(holding, 15),
                          "accuracy": round(acc * 100), "idle_days": idle})
    retention.sort(key=lambda x: x["holding"])
    decaying = [x for x in retention if x["holding"] < 60]

    # ---- weak spots ---------------------------------------------------------
    weak = []
    for x in retention:
        if x["holding"] < 60:
            weak.append({"kind": "decay", "room_id": x["room_id"],
                         "title": x["room"],
                         "why": f"retention decayed to {x['holding']}%",
                         "fix": "relearn"})
    for c in conn.execute(
        """SELECT c.front, c.id card_id, rv.ease, rv.id review_id FROM reviews rv
           JOIN cards c ON c.id=rv.card_id
           WHERE rv.ease<2.0 AND rv.status='active' ORDER BY rv.ease"""
    ).fetchall():
        weak.append({"kind": "leech", "card_id": c["card_id"],
                     "review_id": c["review_id"], "title": c["front"],
                     "why": f"ease {c['ease']:.1f} — you keep grading it low",
                     "fix": "reword"})
    for r in rooms:
        if r["status"] != "learning":
            continue
        last = conn.execute(
            "SELECT MAX(ended_at) e FROM sessions WHERE room_id=?", (r["id"],)
        ).fetchone()["e"]
        idle = (today_str_as_date() - _d(last)).days if last else 99
        if idle >= 5:
            weak.append({"kind": "stalled", "room_id": r["id"],
                         "title": short_name(r["name"]),
                         "why": f"no session for {idle} days",
                         "fix": "resume"})

    # ---- confidence vs reality ----------------------------------------------
    conf = []
    for r in rooms:
        c_row = conn.execute(
            """SELECT AVG(confidence) c, COUNT(*) n FROM sessions
               WHERE room_id=? AND confidence IS NOT NULL""",
            (r["id"],),
        ).fetchone()
        acc = _room_accuracy(conn, r["id"])
        if not c_row["n"] or acc is None:
            continue
        self_r = c_row["c"]                      # 1-5
        actual = acc * 5                          # 0-5
        flag = ("match" if abs(self_r - actual) < 1.2
                else "illusion" if self_r > actual else "humble")
        conf.append({"room_id": r["id"], "room": short_name(r["name"]),
                     "self": round(self_r, 1), "actual": round(actual, 1),
                     "flag": flag})

    # ---- rhythm & time -------------------------------------------------------
    by_date = defaultdict(int)
    hour_count = defaultdict(int)
    track_minutes = defaultdict(int)
    total_minutes, session_n = 0, 0
    for row in conn.execute(
        """SELECT s.started_at, s.actual_minutes, s.ended_at, t.color
           FROM sessions s
           LEFT JOIN rooms r ON r.id=s.room_id
           LEFT JOIN modules m ON m.id=r.module_id
           LEFT JOIN tracks t ON t.id=m.track_id
           WHERE s.actual_minutes IS NOT NULL"""
    ).fetchall():
        d = row["started_at"][:10]
        by_date[d] += row["actual_minutes"] or 0
        hour_count[row["started_at"][11:13]] += 1
        if row["color"]:
            track_minutes[row["color"]] += row["actual_minutes"] or 0
        total_minutes += row["actual_minutes"] or 0
        session_n += 1
    heat = []
    for i in range(27, -1, -1):
        d = today_str(-i)
        heat.append({"day": d, "minutes": by_date.get(d, 0)})
    best_hour = max(hour_count, key=hour_count.get) + ":00" if hour_count else None

    # ---- coverage ------------------------------------------------------------
    coverage = []
    track_rows = conn.execute(
        "SELECT * FROM tracks WHERE archived=0 ORDER BY position"
    ).fetchall()
    for t in track_rows:
        counts = conn.execute(
            """SELECT COUNT(*) total,
                      SUM(r.status='done') done,
                      SUM(r.status='learning') learning,
                      SUM(r.status='todo') todo
               FROM rooms r JOIN modules m ON m.id=r.module_id
               WHERE m.track_id=?""",
            (t["id"],),
        ).fetchone()
        coverage.append({"track_id": t["id"], "track": t["name"],
                         "color": t["color"], "total": counts["total"],
                         "done": counts["done"] or 0,
                         "learning": counts["learning"] or 0,
                         "todo": counts["todo"] or 0})

    ledger_rows = conn.execute(
        "SELECT * FROM ledger ORDER BY id DESC LIMIT 30"
    ).fetchall()

    return {
        "retention": retention,
        "decaying_count": len(decaying),
        "mastery": mastery,
        "weak_spots": weak[:8],
        "confidence": conf[:6],
        "rhythm": {"days": heat, "streak": streak_and_grace(conn),
                   "best_hour": best_hour,
                   "avg_session": round(total_minutes / session_n) if session_n else 0,
                   "balance": dict(track_minutes)},
        "coverage": coverage,
        "recall_health": {
            "accuracy": conn.execute(
                """SELECT CAST(SUM(last_result IN ('good','easy')) AS REAL)/COUNT(*) a
                   FROM reviews WHERE last_result IS NOT NULL"""
            ).fetchone()["a"],
            "ease_avg": conn.execute(
                "SELECT AVG(ease) e FROM reviews WHERE status IN ('new','active')"
            ).fetchone()["e"],
        },
        "ledger": [{"ts": l["ts"], "kind": l["kind"], "text": l["text"]}
                   for l in ledger_rows],
    }


def _d(s: str):
    from datetime import datetime
    return datetime.fromisoformat(s).date()


def today_str_as_date():
    from services.common import today_str
    from datetime import datetime
    return datetime.fromisoformat(today_str()).date()
