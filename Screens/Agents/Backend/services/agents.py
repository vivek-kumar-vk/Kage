import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import settings_for_agents as cfg
from db import connect
from services import office

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))


class AskBody(BaseModel):
    message: Optional[str] = None


def _now():
    return datetime.now(IST).replace(microsecond=0).isoformat()


def _read_description(description_path):
    try:
        return description_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _ensure_agent_room(conn, name, position):
    row = conn.execute(
        "SELECT id FROM rooms WHERE kind = 'agent' AND agent_name = ?",
        (name,),
    ).fetchone()

    if row:
        return row["id"]

    room_id = "room-" + uuid.uuid4().hex[:10]
    conn.execute(
        """
        INSERT INTO rooms (id, kind, name, agent_name, position, created_at)
        VALUES (?, 'agent', ?, ?, ?, ?)
        """,
        (room_id, f"DM · {name}", name, position, _now()),
    )
    conn.commit()
    return room_id


def _dept_position(department, index):
    dept_order = {dept["id"]: i for i, dept in enumerate(office.DEPARTMENTS)}
    return float(dept_order.get(department, 99) * 1000 + index)


def _agent_entries(conn):
    """Roster from AI_Agents/ + office.json, each with its own DM room (D12)."""
    agents = []
    root = cfg.AI_AGENTS_DIR

    if root.exists() and root.is_dir():
        for path in sorted(root.iterdir()):
            if not path.is_dir():
                continue

            description_path = path / "description.txt"
            if not description_path.exists():
                continue

            meta = office.read_office(path)
            description = _read_description(description_path)
            agents.append(
                {
                    "name": path.name,
                    "role": description.splitlines()[0] if description else "",
                    "department": meta["department"],
                    "tier": meta["tier"],
                    "parent": meta.get("parent"),
                }
            )

    agents.sort(
        key=lambda agent: (
            agent["tier"] != "head",
            agent["tier"] != "main",
            agent["name"].casefold(),
        )
    )

    for index, agent in enumerate(agents):
        agent["room_id"] = _ensure_agent_room(
            conn, agent["name"], _dept_position(agent["department"], index)
        )

    return agents


def _get_agents():
    conn = connect()
    try:
        return _agent_entries(conn)
    finally:
        conn.close()


@router.get(cfg.API_PREFIX + "/workspace")
async def get_workspace():
    conn = connect()
    try:
        rooms = [
            {
                "id": row["id"],
                "kind": row["kind"],
                "name": row["name"],
                "agent_name": row["agent_name"],
            }
            for row in conn.execute(
                """
                SELECT id, kind, name, agent_name
                FROM rooms
                ORDER BY COALESCE(position, 999999.0), id
                """
            ).fetchall()
        ]

        counts = {"ideas": 0, "todo": 0, "in_progress": 0, "done": 0}
        for row in conn.execute(
            "SELECT status, COUNT(*) AS c FROM ideas GROUP BY status"
        ).fetchall():
            if row["status"] in counts:
                counts[row["status"]] = row["c"]

        return {
            "state": "ok",
            "departments": office.DEPARTMENTS,
            "rooms": rooms,
            "agents": _agent_entries(conn),
            "counts": {"ideas": counts},
        }
    finally:
        conn.close()


@router.get(cfg.API_PREFIX + "/agents")
async def list_agents():
    return {"state": "ok", "agents": _get_agents()}


@router.get(cfg.API_PREFIX + "/rooms")
async def list_rooms():
    conn = connect()
    try:
        rooms = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, kind, name, agent_name, position, created_at
                FROM rooms
                ORDER BY COALESCE(position, 999999.0), id
                """
            ).fetchall()
        ]
        return {"state": "ok", "rooms": rooms}
    finally:
        conn.close()


@router.get(cfg.API_PREFIX + "/rooms/{room_id}/messages")
async def list_room_messages(room_id: str):
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT id, room_id, author, agent_name, body, created_at
            FROM messages
            WHERE room_id = ?
            ORDER BY COALESCE(created_at, ''), rowid
            LIMIT 300
            """,
            (room_id,),
        ).fetchall()
        return {"state": "ok", "messages": [dict(row) for row in rows]}
    finally:
        conn.close()


@router.get(cfg.API_PREFIX + "/agents/{name}/messages")
async def list_agent_messages(name: str):
    conn = connect()
    try:
        agents = {agent["name"]: agent for agent in _agent_entries(conn)}
        if name not in agents:
            return JSONResponse(
                status_code=404,
                content={"state": "error", "problem": "unknown agent"},
            )

        room_id = agents[name]["room_id"]
        rows = conn.execute(
            """
            SELECT id, room_id, author, agent_name, body, created_at
            FROM messages
            WHERE room_id = ?
            ORDER BY COALESCE(created_at, ''), rowid
            LIMIT 300
            """,
            (room_id,),
        ).fetchall()
        return {
            "state": "ok",
            "room_id": room_id,
            "messages": [dict(row) for row in rows],
        }
    finally:
        conn.close()


@router.post(cfg.API_PREFIX + "/agents/{name}/ask")
async def ask_agent(name: str, payload: Optional[AskBody] = Body(default=None)):
    # Live OmniRoute wiring is deferred to PLAN.md item 3 (LLM last). Until
    # then this stays a stub — the Pixel Office shell + SSE run without it.
    _ = payload

    known_names = {agent["name"] for agent in _get_agents()}

    if name not in known_names:
        return JSONResponse(
            status_code=404,
            content={"state": "error", "problem": "unknown agent"},
        )

    return {
        "state": "pending",
        "reply": None,
        "note": "agent wiring lands in PLAN.md item 3",
    }


# --- dev loop helper (Claude-added; not in the Qwen spec) ---
# The bootstrap placeholder page polls this every 2s and hard-reloads when files
# under Screens/Agents/ change, so Stage_agents turns show live without a browser
# extension. Harmless once the real next_app UI is served. Preserve across rewrites.
@router.get(cfg.API_PREFIX + "/_stamp")
async def build_stamp():
    newest = 0.0
    for p in cfg.SCREEN.rglob("*"):
        if p.is_file() and "node_modules" not in p.parts and ".git" not in p.parts:
            try:
                newest = max(newest, p.stat().st_mtime)
            except OSError:
                pass
    return {"stamp": round(newest, 3)}
