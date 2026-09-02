"""RECALL — spaced repetition. SM-2-ish grading (kept from v1), the whole
due queue with the 5-part progressive reveal, forecast, honest stats, and
the Card Studio (cards without a review row are waiting to be accepted)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_learning as cfg
from services.common import get_db, today_str, ledger, now_str

router = APIRouter()

GRADES = {"again": (-0.20, 0), "hard": (-0.15, 1),
          "good": (0.10, 3), "easy": (0.15, 7)}


class GradeBody(BaseModel):
    grade: str                      # again | hard | good | easy


def _card_out(row, review_id=None, due=None):
    return {
        "review_id": review_id, "card_id": row["id"], "front": row["front"],
        "parts": [row["part1"], row["part2"], row["part3"], row["part4"],
                  row["part5"]],
        "tag": row["tag"], "tether": row["tether"], "ease": row["ease"],
        "due": due,
    }


@router.get(cfg.API_PREFIX + "/recall")
def recall(conn=Depends(get_db)):
    today = today_str()
    due_rows = conn.execute(
        """SELECT rv.id review_id, rv.due_date, c.*, rv.ease
           FROM reviews rv JOIN cards c ON c.id=rv.card_id
           WHERE rv.due_date<=? AND rv.status IN ('new','active')
           ORDER BY rv.due_date, rv.ease""",
        (today,),
    ).fetchall()

    forecast = []
    for i in range(7):
        d = today_str(i)
        n = conn.execute(
            "SELECT COUNT(*) n FROM reviews WHERE due_date=? AND status IN ('new','active')",
            (d,),
        ).fetchone()["n"]
        forecast.append({"day": d, "due": n})

    graded = conn.execute(
        """SELECT COUNT(*) n, CAST(SUM(last_result IN ('good','easy')) AS REAL) ok
           FROM reviews WHERE last_graded_date>=? AND last_result IS NOT NULL""",
        (today_str(-30),),
    ).fetchone()
    ease_avg = conn.execute(
        "SELECT AVG(ease) e FROM reviews WHERE status IN ('new','active')"
    ).fetchone()["e"]
    leeches = conn.execute(
        """SELECT c.front, rv.ease, rv.id review_id FROM reviews rv
           JOIN cards c ON c.id=rv.card_id
           WHERE rv.ease<2.0 AND rv.status='active' ORDER BY rv.ease LIMIT 5"""
    ).fetchall()

    studio = conn.execute(
        """SELECT c.* FROM cards c
           WHERE NOT EXISTS (SELECT 1 FROM reviews rv WHERE rv.card_id=c.id)
           ORDER BY c.id DESC LIMIT 10"""
    ).fetchall()

    current = _card_out(due_rows[0], due_rows[0]["review_id"],
                        due_rows[0]["due_date"]) if due_rows else None
    return {
        "due_count": len(due_rows),
        "current": current,
        "queue": len(due_rows),
        "done_today": conn.execute(
            """SELECT COUNT(*) n FROM reviews
               WHERE last_graded_date=? AND last_result IS NOT NULL""",
            (today,),
        ).fetchone()["n"],
        "forecast": forecast,
        "accuracy": round(100 * graded["ok"] / graded["n"]) if graded["n"] else None,
        "ease_avg": round(ease_avg, 2) if ease_avg else None,
        "leeches": [{"front": l["front"], "ease": l["ease"],
                     "review_id": l["review_id"]} for l in leeches],
        "studio": [_card_out(s) for s in studio],
    }


@router.post(cfg.API_PREFIX + "/review/{review_id}/grade")
def grade(review_id: int, body: GradeBody, conn=Depends(get_db)):
    if body.grade not in GRADES:
        raise HTTPException(422, "grade must be again|hard|good|easy")
    row = conn.execute(
        """SELECT rv.*, c.front FROM reviews rv JOIN cards c ON c.id=rv.card_id
           WHERE rv.id=?""",
        (review_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "no such review")

    d_ease, days = GRADES[body.grade]
    ease = min(2.8, max(1.3, row["ease"] + d_ease))
    from datetime import datetime, timedelta, timezone
    IST = timezone(timedelta(hours=5, minutes=30))
    due = (datetime.now(IST) + timedelta(days=days)).date().isoformat()
    conn.execute(
        """UPDATE reviews SET ease=?, due_date=?, last_result=?,
           last_graded_date=?, status='active' WHERE id=?""",
        (ease, due, body.grade, today_str(), review_id),
    )
    ledger(conn, "review", f"card graded {body.grade} → due {due}",
           ref=f"card:{row['card_id']}")
    conn.commit()
    return {"ok": True, "next_due": due, "ease": round(ease, 2)}


@router.post(cfg.API_PREFIX + "/studio/{card_id}/accept")
def accept(card_id: int, conn=Depends(get_db)):
    card = conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if not card:
        raise HTTPException(404, "no such card")
    conn.execute(
        "INSERT INTO reviews (card_id, due_date, ease, status) VALUES (?,?,2.5,'new')",
        (card_id, today_str()),
    )
    ledger(conn, "review", f"studio card accepted — {card['front'][:60]}")
    conn.commit()
    return {"ok": True}


@router.post(cfg.API_PREFIX + "/studio/{card_id}/discard")
def discard(card_id: int, conn=Depends(get_db)):
    card = conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if not card:
        raise HTTPException(404, "no such card")
    conn.execute("DELETE FROM cards WHERE id=?", (card_id,))
    ledger(conn, "review", f"studio card discarded — {card['front'][:60]}")
    conn.commit()
    return {"ok": True}


@router.post(cfg.API_PREFIX + "/cards")
def add_card(conn=Depends(get_db)):
    """Manual quick-add: a bare card the user fills in the UI later."""
    cur = conn.execute(
        """INSERT INTO cards (room_id, front, part1, tag) VALUES (?,?,?,'core')""",
        (None, "New card — edit me", "the answer, in one line"),
    )
    conn.commit()
    return {"id": cur.lastrowid}
