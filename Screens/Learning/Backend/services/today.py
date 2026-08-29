from datetime import datetime, timezone, timedelta

import sqlite3
from fastapi import APIRouter, Depends

import settings_for_learning as cfg
from db import connect

router = APIRouter()
IST = timezone(timedelta(hours=5, minutes=30))


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@router.get(cfg.API_PREFIX + "/today")
def get_today(db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    c.execute("SELECT session_date FROM sessions ORDER BY session_date DESC")
    rows = c.fetchall()
    streak_days = len(set(row["session_date"] for row in rows)) if rows else 0
    last_studied = rows[0]["session_date"] if rows else None

    c.execute("SELECT COALESCE(SUM(minutes), 0) AS total FROM sessions")
    week_minutes = c.fetchone()["total"]

    c.execute("SELECT focus_a, focus_b FROM week_plans ORDER BY week_start DESC LIMIT 1")
    week_plan = c.fetchone()

    c.execute(
        "SELECT s.session_date AS date, s.minutes, t.name AS topic, s.notes "
        "FROM sessions s JOIN topics t ON s.topic_id = t.id "
        "ORDER BY s.session_date DESC, s.id DESC LIMIT 5"
    )
    recent_activity = [dict(row) for row in c.fetchall()]

    today_str = datetime.now(IST).strftime("%Y-%m-%d")
    c.execute(
        "SELECT COUNT(*) AS n FROM reviews WHERE due_date <= ? AND status = 'active'",
        (today_str,),
    )
    due_cards = c.fetchone()["n"]

    return {
        "streak": {
            "days": streak_days,
            "last_studied": last_studied,
        },
        "week": {
            "minutes": week_minutes,
            "target_minutes": 300,
        },
        "today_plan": {
            "track_a": week_plan["focus_a"] if week_plan else "",
            "track_b": week_plan["focus_b"] if week_plan else "",
            "capture": "Review flashcards",
        },
        "recent_activity": recent_activity,
        "due_cards": due_cards,
    }
