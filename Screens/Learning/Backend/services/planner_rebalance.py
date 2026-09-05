"""M6 slice 3: Sunday-cadence Planner rebalance. Reads the ledger's actual
minutes per track over the past 7 days against the day-template's declared
minutes, plus THM-slot skips and session completion, and files one
`proposals` row (agent='planner', kind='rebalance') per calendar week.
No LLM call — pure ledger arithmetic (D12.1: LLM last)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.common import jdump, today_str
from services.day_template import get_template

IST = timezone(timedelta(hours=5, minutes=30))


def _week_bounds(today: "datetime.date") -> tuple[str, str]:
    start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=6)                  # Sunday
    return start.isoformat(), end.isoformat()


def compute_rebalance(conn, today=None) -> dict:
    """Pure computation, no writes. `today` overridable for tests."""
    today = today or datetime.now(IST).date()
    week_start, week_end = _week_bounds(today)

    tracks = conn.execute(
        "SELECT id, name FROM tracks WHERE archived=0 ORDER BY position"
    ).fetchall()

    actual_by_track = {
        r["track_id"]: r["m"]
        for r in conn.execute(
            """SELECT t.id track_id, COALESCE(SUM(s.actual_minutes),0) m
               FROM tracks t
               LEFT JOIN modules mo ON mo.track_id=t.id AND mo.archived=0
               LEFT JOIN rooms r ON r.module_id=mo.id AND r.archived=0
               LEFT JOIN sessions s ON s.room_id=r.id
                    AND substr(s.started_at,1,10) BETWEEN ? AND ?
               WHERE t.archived=0
               GROUP BY t.id""",
            (week_start, week_end),
        ).fetchall()
    }

    template = get_template(conn)
    weekday_minutes = sum(b["minutes"] for b in template["weekday"] if b["key"] in ("core", "drip"))
    weekend_minutes = sum(b["minutes"] for b in template["weekend"] if b["key"] in ("core", "drip"))
    week_target_total = weekday_minutes * 5 + weekend_minutes * 2
    # No per-track split is recorded anywhere — split evenly across active
    # tracks until the owner records one (Rule 22: don't invent a finer split).
    target_per_track = round(week_target_total / len(tracks)) if tracks else 0

    track_rows = []
    neglected = []
    for t in tracks:
        actual = actual_by_track.get(t["id"], 0)
        track_rows.append({"track_id": t["id"], "track": t["name"],
                            "actual_minutes": actual, "target_minutes": target_per_track})
        if target_per_track and actual < 0.5 * target_per_track:
            neglected.append(t["name"])

    thm_days = {
        r["d"] for r in conn.execute(
            """SELECT DISTINCT substr(s.started_at,1,10) d
               FROM sessions s JOIN rooms r ON r.id=s.room_id
               WHERE r.source='thm' AND substr(s.started_at,1,10) BETWEEN ? AND ?""",
            (week_start, week_end),
        ).fetchall()
    }
    days_elapsed = min(7, (today - datetime.fromisoformat(week_start).date()).days + 1)
    thm_skips = max(0, days_elapsed - len(thm_days))

    session_stats = conn.execute(
        """SELECT COUNT(*) started,
                  COALESCE(SUM(actual_minutes IS NOT NULL AND actual_minutes > 0), 0) finished
           FROM sessions WHERE substr(started_at,1,10) BETWEEN ? AND ?""",
        (week_start, week_end),
    ).fetchone()
    completion_rate = (round(100 * session_stats["finished"] / session_stats["started"])
                        if session_stats["started"] else None)

    return {
        "week_start": week_start, "week_end": week_end,
        "tracks": track_rows, "neglected": neglected,
        "thm_skips": thm_skips, "thm_days_covered": len(thm_days),
        "days_elapsed": days_elapsed,
        "sessions_started": session_stats["started"],
        "sessions_finished": session_stats["finished"],
        "completion_rate": completion_rate,
    }


def _summary_line(r: dict) -> str:
    bits = []
    if r["neglected"]:
        bits.append(f"{', '.join(r['neglected'])} under half its weekly target")
    if r["thm_skips"]:
        bits.append(f"THM slot missed {r['thm_skips']}/{r['days_elapsed']} days")
    if r["completion_rate"] is not None and r["completion_rate"] < 70:
        bits.append(f"only {r['completion_rate']}% of started sessions finished")
    if not bits:
        return f"Week of {r['week_start']}: on track, nothing to rebalance."
    return f"Week of {r['week_start']}: " + "; ".join(bits) + "."


def run_weekly_rebalance(conn, today=None) -> dict | None:
    """Fires only on Sunday (IST), once per calendar week. Returns the created
    proposal row, or None if it isn't Sunday or this week already ran."""
    today = today or datetime.now(IST).date()
    if today.weekday() != 6:  # Sunday
        return None

    week_start, _ = _week_bounds(today)
    marker = f"[week {week_start}]"
    existing = conn.execute(
        "SELECT id FROM proposals WHERE kind='rebalance' AND summary LIKE ?",
        (f"%{marker}%",),
    ).fetchone()
    if existing:
        return None

    result = compute_rebalance(conn, today)
    summary = f"{marker} {_summary_line(result)}"
    conn.execute(
        "INSERT INTO proposals (agent, kind, summary, detail, status) "
        "VALUES ('planner', 'rebalance', ?, ?, 'pending')",
        (summary, jdump(result)),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM proposals WHERE kind='rebalance' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return dict(row)
