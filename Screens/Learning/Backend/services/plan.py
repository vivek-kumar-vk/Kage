from typing import Optional, Literal

import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_learning as cfg
from db import connect

router = APIRouter()


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


class TopicCreate(BaseModel):
    name: str
    stack_area: Literal["core", "drip", "capture"]
    track: Literal["A", "B"]
    target_date: Optional[str] = None
    group: Optional[str] = None


class TopicUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[Literal["todo", "learning", "done"]] = None
    progress: Optional[float] = None
    position: Optional[int] = None
    group: Optional[str] = None


class SessionCreate(BaseModel):
    topic_id: int
    minutes: int
    confidence: Optional[int] = None
    notes: Optional[str] = None


def _topic_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "stack_area": row["stack_area"],
        "status": row["status"],
        "track": row["track"],
        "position": row["position"],
        "progress": row["progress"],
        "target_date": row["target_date"],
        "source_doc": row["source_doc"],
        "group": row["group"],
    }


@router.get(cfg.API_PREFIX + "/plan")
def get_plan(db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    c.execute(
        'SELECT id, name, stack_area, status, track, position, progress, target_date, source_doc, "group" '
        "FROM topics WHERE track = 'A' ORDER BY position, id"
    )
    track_a = [_topic_dict(row) for row in c.fetchall()]

    c.execute(
        'SELECT id, name, stack_area, status, track, position, progress, target_date, source_doc, "group" '
        "FROM topics WHERE track = 'B' ORDER BY position, id"
    )
    track_b = [_topic_dict(row) for row in c.fetchall()]

    c.execute("SELECT week_start, focus_a, focus_b, note FROM week_plans ORDER BY week_start DESC LIMIT 1")
    week = c.fetchone()

    return {
        "state": "ok",
        "tracks": {
            "A": track_a,
            "B": track_b,
        },
        "week": dict(week) if week else None,
    }


@router.post(cfg.API_PREFIX + "/topics")
def create_topic(topic: TopicCreate, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    c.execute("SELECT COALESCE(MAX(position), 0) AS max_pos FROM topics WHERE track = ?", (topic.track,))
    position = c.fetchone()["max_pos"] + 1

    c.execute(
        'INSERT INTO topics (name, stack_area, status, track, position, progress, target_date, source_doc, "group") '
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            topic.name,
            topic.stack_area,
            "todo",
            topic.track,
            position,
            0.0,
            topic.target_date,
            None,
            topic.group,
        ),
    )
    db.commit()

    topic_id = c.lastrowid
    c.execute(
        'SELECT id, name, stack_area, status, track, position, progress, target_date, source_doc, "group" '
        "FROM topics WHERE id = ?",
        (topic_id,),
    )
    row = c.fetchone()
    return _topic_dict(row)


@router.put(cfg.API_PREFIX + "/topics/{topic_id}")
def update_topic(topic_id: int, body: TopicUpdate, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    c.execute("SELECT id FROM topics WHERE id = ?", (topic_id,))
    if not c.fetchone():
        raise HTTPException(status_code=404, detail="Topic not found")

    updates = []
    values = []

    if body.name is not None:
        updates.append("name = ?")
        values.append(body.name)

    if body.status is not None:
        updates.append("status = ?")
        values.append(body.status)

    if body.progress is not None:
        updates.append("progress = ?")
        values.append(body.progress)

    if body.position is not None:
        updates.append("position = ?")
        values.append(body.position)

    if body.group is not None:
        updates.append('"group" = ?')
        values.append(body.group)

    if updates:
        values.append(topic_id)
        sql = "UPDATE topics SET " + ", ".join(updates) + " WHERE id = ?"
        c.execute(sql, values)
        db.commit()

    c.execute(
        'SELECT id, name, stack_area, status, track, position, progress, target_date, source_doc, "group" '
        "FROM topics WHERE id = ?",
        (topic_id,),
    )
    row = c.fetchone()
    return _topic_dict(row)


@router.delete(cfg.API_PREFIX + "/topics/{topic_id}")
def delete_topic(topic_id: int, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    c.execute(
        "DELETE FROM reviews WHERE card_id IN (SELECT id FROM cards WHERE topic_id = ?)",
        (topic_id,),
    )
    c.execute("DELETE FROM cards WHERE topic_id = ?", (topic_id,))
    c.execute("DELETE FROM sessions WHERE topic_id = ?", (topic_id,))
    c.execute("DELETE FROM topics WHERE id = ?", (topic_id,))

    db.commit()
    return {"deleted": topic_id}


@router.get(cfg.API_PREFIX + "/sessions")
def get_sessions(topic_id: int, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    c.execute(
        "SELECT id, topic_id, session_date, minutes, confidence, notes "
        "FROM sessions WHERE topic_id = ? ORDER BY session_date DESC, id DESC",
        (topic_id,),
    )
    sessions = [dict(row) for row in c.fetchall()]

    return {
        "state": "ok",
        "sessions": sessions,
    }


@router.post(cfg.API_PREFIX + "/sessions")
def create_session(session: SessionCreate, db: sqlite3.Connection = Depends(get_db)):
    c = db.cursor()

    c.execute("SELECT id, progress FROM topics WHERE id = ?", (session.topic_id,))
    topic = c.fetchone()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    from datetime import datetime, timezone, timedelta

    IST = timezone(timedelta(hours=5, minutes=30))
    session_date = datetime.now(IST).strftime("%Y-%m-%d")

    c.execute(
        "INSERT INTO sessions (topic_id, session_date, minutes, confidence, notes) VALUES (?, ?, ?, ?, ?)",
        (
            session.topic_id,
            session_date,
            session.minutes,
            session.confidence,
            session.notes,
        ),
    )

    new_progress = min(1.0, float(topic["progress"] or 0.0) + 0.1)
    c.execute("UPDATE topics SET progress = ? WHERE id = ?", (new_progress, session.topic_id))

    db.commit()

    session_id = c.lastrowid
    c.execute(
        "SELECT id, topic_id, session_date, minutes, confidence, notes FROM sessions WHERE id = ?",
        (session_id,),
    )
    return dict(c.fetchone())
