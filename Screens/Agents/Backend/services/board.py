import re
import uuid
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import settings_for_agents as cfg
from db import connect

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))
STATUSES = ["ideas", "todo", "in_progress", "done"]
PRIORITIES = ["low", "medium", "high", "critical"]
WORD_RE = re.compile(r"[a-z0-9]+")


class IdeaCreate(BaseModel):
    title: str
    note: Optional[str] = ""
    area: Optional[str] = ""
    source: Optional[str] = "user"
    priority: Optional[str] = "medium"


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    note: Optional[str] = None
    area: Optional[str] = None
    priority: Optional[str] = None


class StatusMove(BaseModel):
    status: str
    order_index: Optional[float] = None


class CommentCreate(BaseModel):
    text: str
    author: Optional[str] = "user"


def _now():
    return datetime.now(IST).replace(microsecond=0).isoformat()


def _fail(problem, status_code=400):
    return JSONResponse(status_code=status_code, content={"ok": False, "problem": problem})


def _clean(value, default=""):
    if value is None:
        return default
    return str(value)


def _validate_title(title):
    title = _clean(title).strip()
    if not title:
        raise ValueError("title is required")
    return title


def _validate_choice(value, choices, field):
    value = _clean(value).strip()
    if value not in choices:
        raise ValueError(f"{field} must be one of: {', '.join(choices)}")
    return value


def _words(text):
    return WORD_RE.findall(_clean(text).lower())


def _ngrams(words, size=4):
    if len(words) < size:
        return set()
    return {tuple(words[index:index + size]) for index in range(len(words) - size + 1)}


def _near_duplicate(candidate_title, existing_title):
    candidate = _clean(candidate_title).lower().strip()
    existing = _clean(existing_title).lower().strip()

    candidate_words = _words(candidate)
    existing_words = _words(existing)

    if len(candidate_words) >= 4 and len(existing_words) >= 4:
        if _ngrams(candidate_words) & _ngrams(existing_words):
            return True, "four consecutive shared words"

    ratio = SequenceMatcher(None, candidate, existing).ratio()
    if ratio >= 0.75:
        return True, f"similarity ratio {ratio:.2f}"

    return False, ""


def _next_enh_key(conn):
    rows = conn.execute("SELECT enh_key FROM ideas").fetchall()
    max_n = 0

    for row in rows:
        key = _clean(row["enh_key"]).strip()
        if key.startswith("ENH-"):
            try:
                max_n = max(max_n, int(key.split("-", 1)[1]))
            except ValueError:
                pass

    return f"ENH-{max_n + 1}"


def _bottom_order_index(conn, status):
    row = conn.execute(
        "SELECT MAX(order_index) AS max_order FROM ideas WHERE status = ?",
        (status,),
    ).fetchone()

    max_order = row["max_order"]
    if max_order is None:
        return 1.0

    return float(max_order) + 1.0


def _get_idea_row(conn, idea_id):
    return conn.execute("SELECT * FROM ideas WHERE id = ?", (idea_id,)).fetchone()


def _comments_for(conn, idea_id):
    rows = conn.execute(
        """
        SELECT id, text, author, created_at
        FROM comments
        WHERE idea_id = ?
        ORDER BY COALESCE(created_at, ''), id
        """,
        (idea_id,),
    ).fetchall()

    return [
        {
            "id": row["id"],
            "text": row["text"],
            "author": row["author"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _idea_api(conn, row):
    order_index = row["order_index"]
    if order_index is not None:
        order_index = float(order_index)

    return {
        "id": row["id"],
        "key": row["enh_key"],
        "title": row["title"],
        "note": row["note"] or "",
        "area": row["area"] or "",
        "source": row["source"],
        "status": row["status"],
        "priority": row["priority"],
        "order_index": order_index,
        "added_at": row["added_at"],
        "updated_at": row["updated_at"],
        "comments": _comments_for(conn, row["id"]),
    }


def _open_ideas(conn):
    return conn.execute(
        """
        SELECT id, enh_key, title, note, area, source, status
        FROM ideas
        WHERE status != 'done'
        """
    ).fetchall()


@router.get(cfg.API_PREFIX + "/ideas")
async def list_ideas():
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT *
            FROM ideas
            ORDER BY
                CASE status
                    WHEN 'ideas' THEN 0
                    WHEN 'todo' THEN 1
                    WHEN 'in_progress' THEN 2
                    WHEN 'done' THEN 3
                    ELSE 4
                END,
                COALESCE(order_index, 999999.0),
                COALESCE(added_at, ''),
                id
            """
        ).fetchall()

        return {"state": "ok", "ideas": [_idea_api(conn, row) for row in rows]}
    finally:
        conn.close()


@router.post(cfg.API_PREFIX + "/ideas")
async def create_idea(payload: IdeaCreate):
    try:
        title = _validate_title(payload.title)
        note = _clean(payload.note)
        area = _clean(payload.area)
        source = _clean(payload.source, "user") or "user"
        priority = _clean(payload.priority, "medium") or "medium"

        source = _validate_choice(source, ["user", "ai"], "source")
        priority = _validate_choice(priority, PRIORITIES, "priority")

        conn = connect()
        try:
            exact = conn.execute(
                """
                SELECT *
                FROM ideas
                WHERE title = ? AND note = ? AND area = ? AND source = ?
                """,
                (title, note, area, source),
            ).fetchone()

            if exact:
                return {"ok": True, "item": _idea_api(conn, exact), "duplicate": True}

            duplicate_warning = None
            for row in _open_ideas(conn):
                is_duplicate, reason = _near_duplicate(title, row["title"])
                if is_duplicate:
                    duplicate_warning = {
                        "idea_id": row["id"],
                        "key": row["enh_key"],
                        "title": row["title"],
                        "reason": reason,
                    }
                    break

            now = _now()
            idea_id = uuid.uuid4().hex[:12]
            enh_key = _next_enh_key(conn)
            order_index = _bottom_order_index(conn, "ideas")

            conn.execute(
                """
                INSERT INTO ideas (
                    id, enh_key, title, note, area, source, status, priority,
                    order_index, added_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'ideas', ?, ?, ?, ?)
                """,
                (
                    idea_id,
                    enh_key,
                    title,
                    note,
                    area,
                    source,
                    priority,
                    order_index,
                    now,
                    now,
                ),
            )
            conn.commit()

            row = _get_idea_row(conn, idea_id)
            response = {"ok": True, "item": _idea_api(conn, row)}

            if duplicate_warning:
                response["duplicate_warning"] = duplicate_warning

            return response
        finally:
            conn.close()
    except ValueError as exc:
        return _fail(str(exc), 400)


@router.put(cfg.API_PREFIX + "/ideas/{idea_id}")
async def update_idea(idea_id: str, payload: IdeaUpdate):
    try:
        conn = connect()
        try:
            row = _get_idea_row(conn, idea_id)
            if not row:
                return _fail("Idea not found", 404)

            updates = []
            params = []

            if payload.title is not None:
                updates.append("title = ?")
                params.append(_validate_title(payload.title))

            if payload.note is not None:
                updates.append("note = ?")
                params.append(_clean(payload.note))

            if payload.area is not None:
                updates.append("area = ?")
                params.append(_clean(payload.area))

            if payload.priority is not None:
                updates.append("priority = ?")
                params.append(_validate_choice(payload.priority, PRIORITIES, "priority"))

            if not updates:
                return {"ok": True, "item": _idea_api(conn, row)}

            updates.append("updated_at = ?")
            params.append(_now())
            params.append(idea_id)

            conn.execute(
                f"UPDATE ideas SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()

            row = _get_idea_row(conn, idea_id)
            return {"ok": True, "item": _idea_api(conn, row)}
        finally:
            conn.close()
    except ValueError as exc:
        return _fail(str(exc), 400)


@router.patch(cfg.API_PREFIX + "/ideas/{idea_id}/status")
async def move_idea(idea_id: str, payload: StatusMove):
    try:
        status = _validate_choice(payload.status, STATUSES, "status")

        conn = connect()
        try:
            row = _get_idea_row(conn, idea_id)
            if not row:
                return _fail("Idea not found", 404)

            if payload.order_index is None:
                order_index = _bottom_order_index(conn, status)
            else:
                order_index = float(payload.order_index)

            conn.execute(
                """
                UPDATE ideas
                SET status = ?, order_index = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, order_index, _now(), idea_id),
            )
            conn.commit()

            row = _get_idea_row(conn, idea_id)
            return {"ok": True, "item": _idea_api(conn, row)}
        finally:
            conn.close()
    except ValueError as exc:
        return _fail(str(exc), 400)


@router.post(cfg.API_PREFIX + "/ideas/{idea_id}/comments")
async def add_comment(idea_id: str, payload: CommentCreate):
    try:
        text = _clean(payload.text).strip()
        if not text:
            raise ValueError("comment text is required")

        author = _clean(payload.author, "user") or "user"
        author = _validate_choice(author, ["user", "ai"], "author")

        conn = connect()
        try:
            row = _get_idea_row(conn, idea_id)
            if not row:
                return _fail("Idea not found", 404)

            now = _now()
            comment_id = uuid.uuid4().hex[:12]

            conn.execute(
                """
                INSERT INTO comments (id, idea_id, text, author, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (comment_id, idea_id, text, author, now),
            )

            conn.execute(
                "UPDATE ideas SET updated_at = ? WHERE id = ?",
                (now, idea_id),
            )
            conn.commit()

            row = _get_idea_row(conn, idea_id)
            return {"ok": True, "item": _idea_api(conn, row)}
        finally:
            conn.close()
    except ValueError as exc:
        return _fail(str(exc), 400)


@router.delete(cfg.API_PREFIX + "/ideas")
async def delete_idea(id: str = Query(...)):
    conn = connect()
    try:
        row = _get_idea_row(conn, id)
        if not row:
            return _fail("Idea not found", 404)

        conn.execute("DELETE FROM comments WHERE idea_id = ?", (id,))
        conn.execute("DELETE FROM ideas WHERE id = ?", (id,))
        conn.commit()

        return {"ok": True}
    finally:
        conn.close()
