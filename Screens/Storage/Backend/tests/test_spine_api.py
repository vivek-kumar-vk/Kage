"""K-05: spine read endpoints — seven GET routes over the projected spine."""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def client(tmp_path, monkeypatch):
    spine_root = tmp_path / "spine"
    spine_root.mkdir()
    shutil.copy(FIXTURES / "spine_fresh_01.jsonl", spine_root / "events_2026-09.jsonl")
    monkeypatch.setenv("KAGE_SPINE_DIR", str(spine_root))
    import server_for_storage  # noqa: F401
    from services import spine_projector as sp

    conn = sp.connect()
    sp.apply_migrations(conn)
    sp.load_thresholds(conn, FIXTURES / "_freshness_thresholds.json")
    sp.load_prices(conn, FIXTURES / "_model_prices.json")
    conn.close()
    return TestClient(server_for_storage.app)


def test_all_seven_routes_return_ok_envelopes(client):
    r = client.get("/api/storage/spine/freshness")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "ok"
    assert "projected_at" in body and "projector_lag_bytes" in body
    sources = {row["source"]: row for row in body["sources"]}
    assert set(sources) == {"amfi_nav", "youtube"}  # one row per threshold
    assert sources["youtube"]["stale"] == 1  # never a success: stale

    r = client.get("/api/storage/spine/spend")
    assert r.status_code == 200
    body = r.json()
    for key in ("day", "calls", "tokens_in", "tokens_out", "cost_usd", "calls_t2", "by_agent"):
        assert key in body
    assert body["calls"] == 0 and body["by_agent"] == []

    r = client.get("/api/storage/spine/numbers")
    assert r.status_code == 200 and r.json()["numbers"] == []

    r = client.get("/api/storage/spine/decisions")
    assert r.status_code == 200 and r.json()["decisions"] == []

    r = client.get("/api/storage/spine/watchdog")
    assert r.status_code == 200 and r.json()["checks"] == []

    r = client.get("/api/storage/spine/unfinished")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 0 and body["budget"] == 12

    r = client.get("/api/storage/spine/events")
    assert r.status_code == 200
    body = r.json()
    assert len(body["events"]) == 2  # the fixture's duplicate-id line is ignored
    assert all(isinstance(event["payload"], dict) for event in body["events"])
    assert body["events"][0]["type"] in {"fetch_attempted", "fetch_succeeded"}


def test_events_limit_is_clamped(client):
    r = client.get("/api/storage/spine/events", params={"limit": 9999})
    assert r.status_code == 200
    assert len(r.json()["events"]) <= 500
    r = client.get("/api/storage/spine/events", params={"type": "fetch_succeeded", "subject": "amfi_nav"})
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) == 1 and all(e["type"] == "fetch_succeeded" for e in events)


def test_failing_projection_is_503_error(tmp_path, monkeypatch):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("KAGE_SPINE_DIR", str(blocker))
    import server_for_storage  # already imported; env is read per request

    client = TestClient(server_for_storage.app)
    r = client.get("/api/storage/spine/freshness")
    assert r.status_code == 503
    body = r.json()
    assert body["state"] == "error"
    assert "problem" in body
