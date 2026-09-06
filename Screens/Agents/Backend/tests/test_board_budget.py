"""K-18: board one-in-one-out at 12, closes, and ticket events on the spine."""

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import settings_for_agents as cfg  # noqa: E402
from db import init_db  # noqa: E402
from services.board import router  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "agents.db")
    init_db()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(tmp_path / "spine"))
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), tmp_path / "spine"


def _body(n):
    return {"title": f"idea {n:02d}", "note": "", "area": "plan",
            "source": "user", "priority": "medium"}


def test_budget_409_closes_and_ticket_events(client):
    test_client, spine_dir = client
    opened = []
    for n in range(1, 13):
        r = test_client.post("/api/agents/ideas", json=_body(n))
        assert r.status_code == 200, r.text
        opened.append(r.json()["item"]["id"])
    events_file = next(spine_dir.glob("events_*.jsonl"))
    lines = events_file.read_text(encoding="utf-8").splitlines()
    opened_events = [line for line in lines if '"ticket_opened"' in line]
    assert len(opened_events) == 12

    r = test_client.post("/api/agents/ideas", json=_body(13))
    assert r.status_code == 409
    body = r.json()
    assert body == {
        "ok": False,
        "problem": "12 open ideas; close one first or pass closes:<id>",
        "open": 12,
        "budget": 12,
    }

    r = test_client.post(
        "/api/agents/ideas", json={**_body(13), "closes": opened[0]}
    )
    assert r.status_code == 200, r.text
    closed = test_client.get("/api/agents/ideas").json()
    first = next(item for item in closed["ideas"] if item["id"] == opened[0])
    assert first["status"] == "done"

    lines = events_file.read_text(encoding="utf-8").splitlines()
    closed_events = [line for line in lines if '"ticket_closed"' in line]
    assert len(closed_events) == 1
    assert opened[0] in closed_events[0]

    listing = test_client.get("/api/agents/ideas").json()
    assert listing["open"] == 12 and listing["budget"] == 12


def test_done_ideas_do_not_count_toward_budget(client):
    test_client, _ = client
    first = test_client.post("/api/agents/ideas", json=_body(1)).json()["item"]["id"]
    for n in range(2, 14):
        r = test_client.post("/api/agents/ideas", json=_body(n))
        if r.status_code == 409:
            break
    else:
        pytest.fail("expected the budget 409 within 13 ideas")
    test_client.patch(
        f"/api/agents/ideas/{first}/status", json={"status": "done"}
    )
    r = test_client.post("/api/agents/ideas", json=_body(14))
    assert r.status_code == 200, r.text  # a done idea freed a slot
