"""The Pixel Office event backbone (D12).

One append-only events table + one SSE endpoint. Everything the stage renders
(pops, typing, bubbles, glows) is driven by these events, and every event has a
real producer: an OmniRoute run (source=run) or a board edit (source=board).
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

import settings_for_agents as cfg
from db import connect
from services import office

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))
REPLAY_LIMIT = 25
HEARTBEAT_SECONDS = 15.0
KEEP_EVENTS = 3000

_subscribers: set = set()
_real_active: set = set()  # agents with a live real (source=run) run right now


def _now():
    return datetime.now(IST).replace(microsecond=0).isoformat()


def emit(source, type_, text="", agent_name=None, department=None, artifact=None, sim=False):
    """Record one event and push it to every SSE subscriber. Sync + non-blocking."""
    event = {
        "id": None,
        "ts": _now(),
        "source": source,
        "sim": 1 if sim else 0,
        "agent_name": agent_name,
        "department": department,
        "type": type_,
        "text": (text or "")[:400],
        "artifact": artifact,
    }

    conn = connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO events (ts, source, sim, agent_name, department, type, text, artifact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["ts"],
                source,
                event["sim"],
                agent_name,
                department,
                type_,
                event["text"],
                artifact,
            ),
        )
        conn.commit()
        event["id"] = cursor.lastrowid

        if event["id"] and event["id"] % 400 == 0:
            conn.execute(
                """
                DELETE FROM events
                WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT ?)
                """,
                (KEEP_EVENTS,),
            )
            conn.commit()
    finally:
        conn.close()

    if source == "run" and agent_name:
        if type_ == "started":
            _real_active.add(agent_name)
        elif type_ in {"done", "error"}:
            _real_active.discard(agent_name)

    for queue in list(_subscribers):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    return event


@router.get(cfg.API_PREFIX + "/events")
async def stream_events(request: Request):
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (REPLAY_LIMIT,)
        ).fetchall()
    finally:
        conn.close()
    replay = [dict(row) for row in reversed(rows)]

    queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    async def generator():
        for event in replay:
            yield f"data: {json.dumps(event)}\n\n"

        _subscribers.add(queue)
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            _subscribers.discard(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
