import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import settings_for_agents as cfg
from db import connect
from services import events, office, runs
from services.omni import OmniError, ask_omni_detailed, list_models as omni_list_models

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))

# D17.4 — profile files the Agent Deck may read/write. Name only, no
# separators, known extension: the path can never leave the profile folder.
SAFE_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}\.(md|txt|json)$")
MAX_FILE_BYTES = 100_000
MAX_MESSAGE_CHARS = 2000


class AskBody(BaseModel):
    message: Optional[str] = None


class MessageBody(BaseModel):
    body: Optional[str] = None


class NoteBody(BaseModel):
    body: Optional[str] = None


class FileBody(BaseModel):
    content: Optional[str] = None


def _now():
    return datetime.now(IST).replace(microsecond=0).isoformat()


def _read_description(description_path):
    try:
        return description_path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def _profile_path(agent_dir):
    """identity.md is the roster-facing profile when an agent keeps one
    (its own multi-file identity/context/goal/memory split); description.txt
    is the plain fallback every other agent under AI_Agents/ still uses."""
    identity_path = agent_dir / "identity.md"
    if identity_path.exists():
        return identity_path
    description_path = agent_dir / "description.txt"
    if description_path.exists():
        return description_path
    return None


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
    """Roster from every AI_AGENTS_DIRS root + office.json, each with its
    own DM room (D12). A screen whose agent is real code keeps everything
    about it in one folder under its own Backend/Agent/ (no copy here);
    other agents still live entirely under AI_Agents/."""
    agents = []

    for root in cfg.AI_AGENTS_DIRS:
        if not (root.exists() and root.is_dir()):
            continue
        for path in sorted(root.iterdir()):
            if not path.is_dir():
                continue

            description_path = _profile_path(path)
            if description_path is None:
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
                    "model": meta.get("model"),
                    "models": meta.get("models"),
                    "description": description,
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


@router.get(cfg.API_PREFIX + "/unread")
async def unread_summary():
    """Per-agent-room unread counts: messages the owner has not seen yet.
    Unread = rows past the room's read marker that the owner did not author
    (agent replies and system failure notes count; the owner's own lines do
    not). No marker row yet means everything is unread."""
    conn = connect()
    try:
        markers = {
            row["room_id"]: row["last_rowid"]
            for row in conn.execute("SELECT room_id, last_rowid FROM message_reads")
        }
        rooms = {
            row["id"]: row["agent_name"]
            for row in conn.execute(
                "SELECT id, agent_name FROM rooms WHERE kind = 'agent'"
            )
        }

        agents = {}
        for room_id, agent_name in rooms.items():
            last = markers.get(room_id, 0)
            row = conn.execute(
                """
                SELECT COUNT(*) AS c FROM messages
                WHERE room_id = ? AND rowid > ? AND author != 'user'
                """,
                (room_id, last),
            ).fetchone()
            agents[agent_name] = row["c"]

        return {
            "state": "ok",
            "agents": agents,
            "rooms": {
                room_id: agents.get(agent_name, 0)
                for room_id, agent_name in rooms.items()
            },
            "total": sum(agents.values()),
        }
    finally:
        conn.close()


@router.post(cfg.API_PREFIX + "/rooms/{room_id}/read")
async def mark_room_read(room_id: str):
    """Mark an agent room read up to now (the Slack 'open the channel'
    primitive). Idempotent: re-reading sets the same or a higher cursor."""
    conn = connect()
    try:
        room = conn.execute(
            "SELECT id, agent_name FROM rooms WHERE id = ? AND kind = 'agent'",
            (room_id,),
        ).fetchone()
        if not room:
            return JSONResponse(
                status_code=404,
                content={"state": "error", "problem": "unknown room"},
            )

        row = conn.execute(
            "SELECT COALESCE(MAX(rowid), 0) AS m FROM messages WHERE room_id = ?",
            (room_id,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO message_reads (room_id, last_rowid, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(room_id) DO UPDATE SET
                last_rowid = MAX(last_rowid, excluded.last_rowid),
                updated_at = excluded.updated_at
            """,
            (room_id, row["m"], _now()),
        )
        conn.commit()
        return {
            "state": "ok",
            "room_id": room_id,
            "agent_name": room["agent_name"],
            "last_rowid": row["m"],
        }
    finally:
        conn.close()


def _department_label(department_id):
    for dept in office.DEPARTMENTS:
        if dept["id"] == department_id:
            return dept["label"]
    return department_id


def _build_system_prompt(agent, all_agents):
    role = agent["role"] or "agent"
    dept_label = _department_label(agent["department"])
    lines = [
        f"You are {agent['name']}, the {role} in the {dept_label} department of "
        "AGENT DECK, the agent console of a private personal-dashboard system called Kage.",
    ]

    description = (agent.get("description") or "").strip()
    if description:
        lines += ["", "Your brief, in the operator's own words:", description]

    tier = agent["tier"]
    tier_line = f"You are a {tier} agent."
    if tier == "sub" and agent.get("parent"):
        tier_line += f" You report to {agent['parent']}."
    elif tier == "main":
        subs = sorted(a["name"] for a in all_agents if a.get("parent") == agent["name"])
        if subs:
            tier_line += f" Your sub-agents are: {', '.join(subs)}."
    lines += ["", tier_line]

    lines += [
        "",
        "Answer in plain text. Be concrete and brief. If you do not have the data "
        "to answer, say exactly what is missing — never guess a number, a file "
        "path, or a status.",
    ]
    return "\n".join(lines)


def _resolve_model_pref(agent):
    if agent.get("model"):
        return agent["model"]
    models = agent.get("models")
    if models:
        return models[0]
    return None


async def _run_ask(name: str, message: Optional[str]):
    """The one ask code path — used by /agents/{name}/ask, the DM composer at
    /agents/{name}/messages, and agent-kind rooms at /rooms/{room_id}/messages.
    Returns (status_code, body_dict)."""
    conn = connect()
    try:
        all_agents = _agent_entries(conn)
        agents_by_name = {agent["name"]: agent for agent in all_agents}
        if name not in agents_by_name:
            return 404, {"state": "error", "problem": "unknown agent"}

        text = (message or "").strip()
        if not text:
            return 422, {"state": "error", "problem": "empty message"}

        agent = agents_by_name[name]
        department = agent["department"]
        room_id = agent["room_id"]

        user_message_id = "msg-" + uuid.uuid4().hex[:10]
        created = _now()
        conn.execute(
            """
            INSERT INTO messages (id, room_id, author, agent_name, body, created_at)
            VALUES (?, ?, 'user', ?, ?, ?)
            """,
            (user_message_id, room_id, name, text[:MAX_MESSAGE_CHARS], created),
        )
        conn.commit()
        user_message = {
            "id": user_message_id,
            "room_id": room_id,
            "author": "user",
            "agent_name": name,
            "body": text[:MAX_MESSAGE_CHARS],
            "created_at": created,
        }
        run_id = runs.open_run(conn, name, department, room_id, text[:MAX_MESSAGE_CHARS])
    finally:
        conn.close()

    events.emit(
        source="run", type_="started", text=text[:120],
        agent_name=name, department=department, sim=False,
    )
    events.emit(
        source="run", type_="thinking",
        agent_name=name, department=department, sim=False,
    )

    system = _build_system_prompt(agent, all_agents)
    model_pref = _resolve_model_pref(agent)

    try:
        result = await ask_omni_detailed(system, text, model=model_pref)
    except OmniError as exc:
        problem = str(exc)
        return _fail_run(run_id, room_id, name, department, problem, user_message)
    except Exception as exc:  # narrated, never swallowed (Rule 8)
        problem = f"{type(exc).__name__}: {exc}"
        return _fail_run(run_id, room_id, name, department, problem, user_message)

    reply = result["text"]

    conn = connect()
    try:
        runs.close_run(
            conn, run_id, status="ok", reply=reply,
            model=result["model"], usage=result["usage"],
        )
        reply_message_id = "msg-" + uuid.uuid4().hex[:10]
        reply_created = _now()
        conn.execute(
            """
            INSERT INTO messages (id, room_id, author, agent_name, body, created_at)
            VALUES (?, ?, 'agent', ?, ?, ?)
            """,
            (reply_message_id, room_id, name, reply[:MAX_MESSAGE_CHARS], reply_created),
        )
        conn.commit()
        reply_message = {
            "id": reply_message_id,
            "room_id": room_id,
            "author": "agent",
            "agent_name": name,
            "body": reply[:MAX_MESSAGE_CHARS],
            "created_at": reply_created,
        }
    finally:
        conn.close()

    events.emit(
        source="run", type_="output", text=reply[:160],
        agent_name=name, department=department, sim=False,
    )
    events.emit(
        source="run", type_="done",
        agent_name=name, department=department, sim=False,
    )

    return 200, {
        "state": "ok",
        "reply": reply,
        "run_id": run_id,
        "model": result["model"],
        "message": user_message,
        "reply_message": reply_message,
    }


def _fail_run(run_id, room_id, name, department, problem, user_message):
    conn = connect()
    try:
        runs.close_run(conn, run_id, status="error", problem=problem)
        system_message_id = "msg-" + uuid.uuid4().hex[:10]
        conn.execute(
            """
            INSERT INTO messages (id, room_id, author, agent_name, body, created_at)
            VALUES (?, ?, 'system', ?, ?, ?)
            """,
            (system_message_id, room_id, name, problem, _now()),
        )
        conn.commit()
    finally:
        conn.close()

    events.emit(
        source="run", type_="error", text=problem,
        agent_name=name, department=department, sim=False,
    )

    # HTTP 200 with state=error: the gateway's specific sentence is the payload
    # the UI shows inline; a 5xx would surface as a generic network error and
    # lose it (D27).
    return 200, {
        "state": "error",
        "reply": None,
        "problem": problem,
        "run_id": run_id,
        "message": user_message,
    }


@router.post(cfg.API_PREFIX + "/agents/{name}/ask")
async def ask_agent(name: str, payload: Optional[AskBody] = Body(default=None)):
    status, body = await _run_ask(name, payload.message if payload else None)
    if status == 200:
        return body
    return JSONResponse(status_code=status, content=body)


@router.post(cfg.API_PREFIX + "/agents/{name}/messages")
async def post_agent_message(name: str, payload: Optional[MessageBody] = Body(default=None)):
    """The DM composer's send path — same ask flow as /ask (D27), so a DM to an
    agent gets a real reply, narrated on the office stage like any other run."""
    status, body = await _run_ask(name, payload.body if payload else None)
    if status == 200:
        return body
    return JSONResponse(status_code=status, content=body)


@router.post(cfg.API_PREFIX + "/rooms/{room_id}/messages")
async def post_room_message(room_id: str, payload: Optional[MessageBody] = Body(default=None)):
    text = (payload.body or "").strip() if payload else ""
    if not text:
        return JSONResponse(
            status_code=422,
            content={"state": "error", "problem": "empty message"},
        )

    conn = connect()
    try:
        room = conn.execute(
            "SELECT id, kind, agent_name FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()
    finally:
        conn.close()

    if not room:
        return JSONResponse(
            status_code=404,
            content={"state": "error", "problem": "unknown room"},
        )

    if room["kind"] == "agent" and room["agent_name"]:
        status, body = await _run_ask(room["agent_name"], text)
        if status == 200:
            return body
        return JSONResponse(status_code=status, content=body)

    conn = connect()
    try:
        message_id = "msg-" + uuid.uuid4().hex[:10]
        created = _now()
        conn.execute(
            """
            INSERT INTO messages (id, room_id, author, body, created_at)
            VALUES (?, ?, 'user', ?, ?)
            """,
            (message_id, room_id, text[:MAX_MESSAGE_CHARS], created),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "state": "ok",
        "message": {
            "id": message_id,
            "room_id": room_id,
            "author": "user",
            "agent_name": None,
            "body": text[:MAX_MESSAGE_CHARS],
            "created_at": created,
        },
        "note": "stored — only agent rooms think",
    }


@router.get(cfg.API_PREFIX + "/models")
async def get_models():
    try:
        models = await omni_list_models()
        return {"state": "ok", "models": models, "gateway": cfg.OMNIROUTE_URL}
    except OmniError as exc:
        return {
            "state": "error",
            "models": [],
            "gateway": cfg.OMNIROUTE_URL,
            "problem": str(exc),
        }


@router.post(cfg.API_PREFIX + "/agents/{name}/notes")
async def post_agent_note(name: str, payload: Optional[NoteBody] = Body(default=None)):
    """Persist a note authored BY the agent itself, mirroring the D19.5
    user-DM route above. First writer is the Email card's newsletter
    digest (AGENTS.md D22): the menu's email pipeline summarizes new
    newsletters and POSTs the digest here, so it lands in the agent's DM
    room and on the office stage as a real (sim=0) agent output."""
    body = (payload.body or "").strip() if payload else ""
    if not body:
        return JSONResponse(
            status_code=422,
            content={"state": "error", "problem": "empty note"},
        )

    conn = connect()
    try:
        agents = {agent["name"]: agent for agent in _agent_entries(conn)}
        if name not in agents:
            return JSONResponse(
                status_code=404,
                content={"state": "error", "problem": "unknown agent"},
            )

        room_id = agents[name]["room_id"]
        message_id = "msg-" + uuid.uuid4().hex[:10]
        created = _now()
        conn.execute(
            """
            INSERT INTO messages (id, room_id, author, agent_name, body, created_at)
            VALUES (?, ?, 'agent', ?, ?, ?)
            """,
            (message_id, room_id, name, body[:MAX_MESSAGE_CHARS], created),
        )
        conn.commit()
        message = {
            "id": message_id,
            "room_id": room_id,
            "author": "agent",
            "agent_name": name,
            "body": body[:MAX_MESSAGE_CHARS],
            "created_at": created,
        }
        department = agents[name]["department"]
    finally:
        conn.close()

    events.emit(
        "agent",
        "output",
        f"note: {body[:80]}",
        agent_name=name,
        department=department,
        sim=False,
    )

    return {"state": "ok", "message": message}


def _known_agent_dir(name: str):
    known = {agent["name"] for agent in _get_agents()}
    if name not in known:
        return None
    for root in cfg.AI_AGENTS_DIRS:
        candidate = root / name
        if candidate.is_dir():
            return candidate
    return None


@router.get(cfg.API_PREFIX + "/agents/{name}/files")
async def list_agent_files(name: str):
    agent_dir = _known_agent_dir(name)
    if agent_dir is None:
        return JSONResponse(
            status_code=404,
            content={"state": "error", "problem": "unknown agent"},
        )

    files = []
    if agent_dir.is_dir():
        for path in sorted(agent_dir.iterdir()):
            if not path.is_file() or not SAFE_FILE.match(path.name):
                continue
            stat = path.stat()
            files.append(
                {
                    "name": path.name,
                    "size": stat.st_size,
                    "updated": datetime.fromtimestamp(stat.st_mtime, IST)
                    .replace(microsecond=0)
                    .isoformat(),
                }
            )
    return {"state": "ok", "files": files}


@router.get(cfg.API_PREFIX + "/agents/{name}/files/{filename}")
async def read_agent_file(name: str, filename: str):
    agent_dir = _known_agent_dir(name)
    if agent_dir is None:
        return JSONResponse(
            status_code=404,
            content={"state": "error", "problem": "unknown agent"},
        )
    if not SAFE_FILE.match(filename):
        return JSONResponse(
            status_code=422,
            content={"state": "error", "problem": "bad filename"},
        )

    path = agent_dir / filename
    if not path.is_file():
        return JSONResponse(
            status_code=404,
            content={"state": "error", "problem": "no such file"},
        )

    stat = path.stat()
    return {
        "state": "ok",
        "file": {
            "name": filename,
            "content": path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_BYTES],
            "size": stat.st_size,
            "updated": datetime.fromtimestamp(stat.st_mtime, IST)
            .replace(microsecond=0)
            .isoformat(),
        },
    }


@router.put(cfg.API_PREFIX + "/agents/{name}/files/{filename}")
async def write_agent_file(
    name: str, filename: str, payload: Optional[FileBody] = Body(default=None)
):
    agent_dir = _known_agent_dir(name)
    if agent_dir is None:
        return JSONResponse(
            status_code=404,
            content={"state": "error", "problem": "unknown agent"},
        )
    if not SAFE_FILE.match(filename):
        return JSONResponse(
            status_code=422,
            content={"state": "error", "problem": "bad filename"},
        )

    content = payload.content if payload and payload.content is not None else ""
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        return JSONResponse(
            status_code=413,
            content={"state": "error", "problem": "file too large"},
        )

    path = agent_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    stat = path.stat()

    return {
        "state": "ok",
        "file": {
            "name": filename,
            "size": stat.st_size,
            "updated": datetime.fromtimestamp(stat.st_mtime, IST)
            .replace(microsecond=0)
            .isoformat(),
        },
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
