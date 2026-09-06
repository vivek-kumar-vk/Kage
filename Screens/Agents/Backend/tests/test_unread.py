"""Unread-badge spine (2026-09-06): message_reads markers + the /unread and
/read routes. Offline: a temp agents.db, the real schema, the real router —
no live gateway, no AI_Agents walk (the routes read the rooms table directly).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import settings_for_agents as cfg   # noqa: E402
from db import connect, init_db     # noqa: E402
from services.agents import router  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "agents.db")
    init_db()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _room(client, name="Time_Analyst_Agent"):
    room_id = f"room-{uuid.uuid4().hex[:10]}"
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO rooms (id, kind, name, agent_name, created_at) "
            "VALUES (?, 'agent', ?, ?, '2026-09-06T00:00:00+05:30')",
            (room_id, f"DM · {name}", name),
        )
        conn.commit()
    finally:
        conn.close()
    return room_id


def _msg(room_id, author, created="2026-09-06T01:00:00+05:30"):
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO messages (id, room_id, author, agent_name, body, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (f"msg-{uuid.uuid4().hex[:10]}", room_id, author, "x", "body", created),
        )
        conn.commit()
    finally:
        conn.close()


def test_no_marker_means_everything_agent_authored_is_unread(client):
    room = _room(client)
    _msg(room, "agent")
    _msg(room, "system")
    _msg(room, "user")
    body = client.get("/api/agents/unread").json()
    assert body["state"] == "ok"
    assert body["rooms"][room] == 2  # agent + system count, owner's own line does not


def test_marker_clears_count_until_new_agent_message(client):
    room = _room(client)
    _msg(room, "agent")
    assert client.post(f"/api/agents/rooms/{room}/read").json()["state"] == "ok"
    assert client.get("/api/agents/unread").json()["rooms"][room] == 0

    _msg(room, "agent", created="2026-09-06T02:00:00+05:30")
    assert client.get("/api/agents/unread").json()["rooms"][room] == 1


def test_mark_read_is_idempotent_and_never_rewinds(client):
    room = _room(client)
    _msg(room, "agent")
    first = client.post(f"/api/agents/rooms/{room}/read").json()["last_rowid"]
    again = client.post(f"/api/agents/rooms/{room}/read").json()["last_rowid"]
    assert again == first
    assert client.get("/api/agents/unread").json()["rooms"][room] == 0


def test_unknown_room_is_404(client):
    assert client.post("/api/agents/rooms/room-nope/read").status_code == 404


def test_per_agent_map_and_total(client):
    room_a = _room(client, "A_Main_Agent")
    room_b = _room(client, "B_Sub_Agent")
    _msg(room_a, "agent")
    _msg(room_a, "agent")
    _msg(room_b, "agent")
    client.post(f"/api/agents/rooms/{room_b}/read")
    body = client.get("/api/agents/unread").json()
    assert body["agents"]["A_Main_Agent"] == 2
    assert body["agents"]["B_Sub_Agent"] == 0
    assert body["total"] == 2
