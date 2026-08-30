from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import settings_for_agents as cfg
from db import connect

router = APIRouter()


class AskBody(BaseModel):
    message: Optional[str] = None


def _read_role(description_path):
    try:
        lines = description_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""

    for line in lines:
        line = line.strip()
        if line:
            return line

    return ""


def _get_agents():
    agents = []
    root = cfg.AI_AGENTS_DIR

    if root.exists() and root.is_dir():
        for path in sorted(root.iterdir()):
            if not path.is_dir():
                continue

            description_path = path / "description.txt"
            if not description_path.exists():
                continue

            agents.append(
                {
                    "name": path.name,
                    "role": _read_role(description_path),
                }
            )

    agents.sort(key=lambda agent: (agent["name"] != "Agent_Head", agent["name"].casefold()))
    return agents


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
            "rooms": rooms,
            "agents": _get_agents(),
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
    # V1 leaves messages empty. room_id will be used in V2.
    _ = room_id
    return {"state": "ok", "messages": []}


@router.post(cfg.API_PREFIX + "/agents/{name}/ask")
async def ask_agent(name: str, payload: Optional[AskBody] = Body(default=None)):
    # payload will be used in V2.
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
        "note": "agent wiring lands in V2",
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
