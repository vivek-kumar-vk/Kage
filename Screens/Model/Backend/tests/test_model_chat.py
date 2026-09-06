"""Tests for the Model screen's orchestrator chat forward (plan 5.3).

No gateway and no Agent Deck are needed: the roster fetch and the ask
forward are monkeypatched at the module boundary, so what's under test
is the routing - plain text -> orchestrator, /-command -> the named
agent, /all -> every main-tier agent bounded - plus the honest states.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import server_for_model as srv  # noqa: E402

ROSTER = {
    "state": "ok",
    "agents": [
        {"name": "Agent_Head", "tier": "head"},
        {"name": "Deck_Main_Agent", "tier": "main"},
        {"name": "Finance_Main_Agent", "tier": "main"},
        {"name": "Finance_MF_Agent", "tier": "sub"},
    ],
}


@pytest.fixture()
def asks(monkeypatch):
    """A recording stand-in for the deck's ask path."""
    calls = []

    def fake_ask(name, message):
        calls.append((name, message))
        return {"agent": name, "state": "ok", "reply": f"echo:{message}", "problem": None}

    monkeypatch.setattr(srv, "_ask_agent", fake_ask)
    return calls


@pytest.fixture()
def client(monkeypatch, asks):
    monkeypatch.setattr(srv, "_fetch_roster", lambda: dict(ROSTER))
    return TestClient(srv.app)


def test_plain_message_goes_to_the_orchestrator(client, asks):
    response = client.post("/api/model/chat", json={"message": "status?"})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ok"
    assert asks == [("Deck_Main_Agent", "status?")]


def test_slash_command_resolves_the_suffix_less_name(client, asks):
    response = client.post("/api/model/chat", json={"message": "/finance_main holdings?"})
    assert response.status_code == 200
    assert asks == [("Finance_Main_Agent", "holdings?")]


def test_explicit_target_beats_the_command(client, asks):
    response = client.post(
        "/api/model/chat", json={"message": "/deck_main hi", "target": "finance_mf"}
    )
    assert response.status_code == 200
    assert asks == [("Finance_MF_Agent", "/deck_main hi")]


def test_all_broadcasts_to_mains_only_and_caps_replies(client, monkeypatch, asks):
    monkeypatch.setattr(srv.cfg, "BROADCAST_REPLY_CAP", 10)
    response = client.post("/api/model/chat", json={"message": "/all roll call"})
    assert response.status_code == 200
    body = response.json()
    assert body["broadcast"] is True
    # Head and subs stay out; the two mains answer in roster order.
    assert [row["agent"] for row in body["replies"]] == [
        "Deck_Main_Agent",
        "Finance_Main_Agent",
    ]
    # The reply cap is applied structurally, not by dropping the row.
    assert body["replies"][0]["reply"] == "echo:roll call"[:10]


def test_unknown_command_agent_is_an_honest_422(client, asks):
    response = client.post("/api/model/chat", json={"message": "/nosuch hi"})
    assert response.status_code == 422
    assert "unknown agent" in response.json()["problem"]
    assert asks == []


def test_empty_message_is_422(client):
    response = client.post("/api/model/chat", json={"message": "   "})
    assert response.status_code == 422


def test_command_without_a_message_is_422(client):
    assert client.post("/api/model/chat", json={"message": "/finance_main"}).status_code == 422
    assert client.post("/api/model/chat", json={"message": "/all"}).status_code == 422


def test_deck_offline_is_an_honest_state_not_a_crash(monkeypatch):
    monkeypatch.setattr(
        srv,
        "_fetch_roster",
        lambda: srv._agents_offline("URLError: connection refused"),
    )
    client = TestClient(srv.app)
    response = client.post("/api/model/chat", json={"message": "hello?"})
    assert response.status_code == 200  # D27.1: a failed ask is a result
    body = response.json()
    assert body["state"] == "agents offline"
    assert "connection refused" in body["problem"]


def test_agents_passthrough_lists_names_for_the_autocomplete(monkeypatch):
    monkeypatch.setattr(srv, "_fetch_roster", lambda: dict(ROSTER))
    client = TestClient(srv.app)
    body = client.get("/api/model/agents").json()
    assert body["state"] == "ok"
    assert {row["name"] for row in body["agents"]} == {
        "Agent_Head",
        "Deck_Main_Agent",
        "Finance_Main_Agent",
        "Finance_MF_Agent",
    }


def test_agents_passthrough_reports_offline(monkeypatch):
    monkeypatch.setattr(
        srv, "_fetch_roster", lambda: srv._agents_offline("boom")
    )
    client = TestClient(srv.app)
    body = client.get("/api/model/agents").json()
    assert body["state"] == "agents offline"
