from datetime import datetime, timezone, timedelta

import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


class GradeRequest(BaseModel):
    grade: str


def _card_from_row(row):
    return {
        "review_id": row["review_id"],
        "id": row["id"],
        "front": row["front"],
        "parts": [row["part1"], row["part2"], row["part3"], row["part4"], row["part5"]],
        "tag": row["tag"],
        "tether": row["tether"],
    }


@router.get(cfg.API_PREFIX + "/recall")
def get_recall(db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()
    today_str = datetime.now(IST).strftime("%Y-%m-%d")

    c.execute(
        "SELECT COUNT(*) AS n FROM reviews WHERE due_date <= ? AND status = 'active'",
        (today_str,),
    )
    today_count = c.fetchone()["n"]

    c.execute(
        "SELECT COUNT(*) AS n FROM reviews WHERE due_date > ? AND status = 'active'",
        (today_str,),
    )
    pending_count = c.fetchone()["n"]

    c.execute("SELECT COUNT(*) AS n FROM reviews")
    all_count = c.fetchone()["n"]

    c.execute(
        "SELECT r.id AS review_id, c.id, c.front, c.part1, c.part2, c.part3, c.part4, c.part5, c.tag, c.tether "
        "FROM reviews r JOIN cards c ON r.card_id = c.id "
        "WHERE r.due_date <= ? AND r.status = 'active' "
        "ORDER BY r.due_date, r.id",
        (today_str,),
    )
    today_queue = [_card_from_row(row) for row in c.fetchall()]

    c.execute(
        "SELECT r.id AS review_id, c.id, c.front, c.part1, c.part2, c.part3, c.part4, c.part5, c.tag, c.tether "
        "FROM reviews r JOIN cards c ON r.card_id = c.id "
        "WHERE r.due_date > ? AND r.status = 'active' "
        "ORDER BY r.due_date, r.id",
        (today_str,),
    )
    pending_queue = [_card_from_row(row) for row in c.fetchall()]

    c.execute(
        "SELECT r.id AS review_id, c.id, c.front, c.part1, c.part2, c.part3, c.part4, c.part5, c.tag, c.tether "
        "FROM reviews r JOIN cards c ON r.card_id = c.id "
        "ORDER BY r.due_date, r.id"
    )
    all_queue = [_card_from_row(row) for row in c.fetchall()]

    return {
        "counts": {
            "today": today_count,
            "pending": pending_count,
            "all": all_count,
        },
        "queues": {
            "today": today_queue,
            "pending": pending_queue,
            "all": all_queue,
        },
    }


@router.post(cfg.API_PREFIX + "/reviews/{review_id}/grade")
def grade_review(review_id: int, body: GradeRequest, db: sqlite3.Connection = Depends(get_db)):
    grade = body.grade
    if grade not in ("again", "hard", "good", "easy"):
        raise HTTPException(status_code=422, detail="Invalid grade")

    c = db.cursor()

    c.execute("SELECT id, ease, due_date FROM reviews WHERE id = ?", (review_id,))
    review = c.fetchone()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    ease = float(review["ease"] or 2.5)
    today = datetime.now(IST).date()

    if grade == "again":
        ease = max(1.3, ease - 0.2)
        due = today
    elif grade == "hard":
        ease = max(1.3, ease - 0.15)
        due = today + timedelta(days=1)
    elif grade == "good":
        ease = min(2.8, ease + 0.10)
        due = today + timedelta(days=3)
    else:
        ease = min(2.8, ease + 0.15)
        due = today + timedelta(days=7)

    c.execute(
        "UPDATE reviews SET due_date = ?, ease = ?, last_result = ?, last_graded_date = ?, status = 'active' WHERE id = ?",
        (
            due.strftime("%Y-%m-%d"),
            ease,
            grade,
            today.strftime("%Y-%m-%d"),
            review_id,
        ),
    )

    db.commit()
    return {"state": "ok"}
