"""The Pixel Office event backbone (D12).

One append-only events table + one SSE endpoint. Everything the stage renders
(pops, typing, bubbles, glows) is driven by these events, and every event has a
real producer: an OmniRoute run (source=run), a board edit (source=board), or
the ambient demo generator (source=demo, sim=1 — always labeled as simulated).
"""

import asyncio
import json
import random
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
_demo_active: set = set()  # agents mid demo-burst, so bursts can overlap
_bg_tasks: set = set()  # keep fire-and-forget burst tasks referenced
_demo_task = None


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


# --- ambient demo generator (sim=1, clearly labeled client-side) ---

DEMO_ACTIONS = {
    "model": [
        "routing a completion through the gateway",
        "checking model quotas",
        "timing a latency probe",
        "refreshing the model roster",
    ],
    "finance": [
        "reconciling today's numbers",
        "sweeping the ledger for stale rows",
        "pricing a watchlist row",
        "drafting the money brief",
    ],
    "learning": [
        "rescheduling a recall card",
        "summarizing a finance primer",
        "drafting a 3-question quiz",
        "tidying the week plan",
    ],
    "deck": [
        "triaging the idea board",
        "drafting an enhancement card",
        "running a UI sweep",
        "watching for drifted screens",
    ],
    "anime": [
        "refreshing the seasonal list",
        "checking watch-list availability",
        "tagging new episodes",
        "pruning dead links",
    ],
    "lobby": [
        "watching the board",
        "collecting status from the floor",
    ],
}


def _demo_roster():
    entries = []

    for root in cfg.AI_AGENTS_DIRS:
        if not (root.exists() and root.is_dir()):
            continue
        for path in sorted(root.iterdir()):
            if not path.is_dir():
                continue
            if not (path / "identity.md").exists() and not (path / "description.txt").exists():
                continue
            meta = office.read_office(path)
            entries.append((path.name, meta["department"], meta["tier"]))

    return entries


async def _demo_burst():
    roster = _demo_roster()
    candidates = [
        (name, dept)
        for name, dept, tier in roster
        if tier != "head" and name not in _real_active and name not in _demo_active
    ]
    if not candidates:
        return

    name, dept = random.choice(candidates)
    actions = DEMO_ACTIONS.get(dept) or DEMO_ACTIONS["deck"]
    _demo_active.add(name)
    try:
        emit(source="demo", type_="started", agent_name=name, department=dept, sim=True)
        await asyncio.sleep(random.uniform(0.8, 1.6))
        emit(
            source="demo",
            type_="output",
            text=random.choice(actions),
            agent_name=name,
            department=dept,
            sim=True,
        )
        await asyncio.sleep(random.uniform(1.2, 2.4))

        if random.random() < 0.25 and dept != "lobby":
            emit(
                source="demo",
                type_="output",
                text=random.choice(actions),
                agent_name=name,
                department=dept,
                sim=True,
            )
            await asyncio.sleep(random.uniform(1.0, 2.0))

        emit(source="demo", type_="done", agent_name=name, department=dept, sim=True)
    finally:
        _demo_active.discard(name)


async def _demo_loop():
    # Keep the stage alive for reviews: up to 3 overlapping bursts so two or
    # three agents are usually mid-task somewhere. Still sim=1 throughout.
    await asyncio.sleep(2.0)
    while True:
        try:
            if len(_demo_active) < 3:
                task = asyncio.create_task(_demo_burst())
                _bg_tasks.add(task)
                task.add_done_callback(_bg_tasks.discard)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(random.uniform(2.0, 5.0))


def start_demo():
    global _demo_task
    if cfg.DEMO_EVENTS and (_demo_task is None or _demo_task.done()):
        _demo_task = asyncio.create_task(_demo_loop())


def stop_demo():
    global _demo_task
    if _demo_task is not None:
        _demo_task.cancel()
        _demo_task = None
