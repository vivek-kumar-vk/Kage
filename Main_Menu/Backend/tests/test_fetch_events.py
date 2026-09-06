"""K-13: calendar/WakaTime/Gmail syncs emit spine fetch events."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Agent" / "Calendar_Agent"))

import calendar_pipeline  # noqa: E402
import email_pipeline  # noqa: E402


@pytest.fixture
def spine_dir(tmp_path, monkeypatch):
    target = tmp_path / "spine"
    monkeypatch.setenv("KAGE_SPINE_DIR", str(target))
    return target


def _sequence(spine_dir):
    files = sorted(spine_dir.glob("events_*.jsonl"))
    assert len(files) == 1
    return [
        (event["type"], event["subject"], event["payload"])
        for event in (json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines())
    ]


def test_calendar_sync_emits_attempted_then_succeeded(spine_dir, monkeypatch):
    monkeypatch.setattr(calendar_pipeline, "connection_state", lambda: ("ok", ""))
    monkeypatch.setattr(calendar_pipeline.google, "list_events", lambda *a, **k: [])
    monkeypatch.setattr(calendar_pipeline.store, "replace_events", lambda *a, **k: None)
    monkeypatch.setattr(calendar_pipeline.store, "set_meta", lambda *a, **k: None)
    monkeypatch.setattr(calendar_pipeline.cfg, "WAKATIME_SNAPSHOT_ENABLED", False)

    result = calendar_pipeline.sync_cycle()

    assert result["state"] == "ok"
    events = _sequence(spine_dir)
    assert [(kind, subject) for kind, subject, _ in events] == [
        ("fetch_attempted", "google_calendar"),
        ("fetch_succeeded", "google_calendar"),
    ]
    assert events[1][2]["items"] == 0
    assert events[1][2]["data_as_of"].endswith("+05:30")


def test_calendar_not_connected_emits_failed_with_state_sentence(spine_dir, monkeypatch):
    monkeypatch.setattr(
        calendar_pipeline, "connection_state",
        lambda: ("not_connected", "Google Calendar has not been authorised yet"),
    )
    monkeypatch.setattr(calendar_pipeline.store, "set_meta", lambda *a, **k: None)

    result = calendar_pipeline.sync_cycle()

    assert result["state"] == "not_connected"
    events = _sequence(spine_dir)
    assert [(kind, subject) for kind, subject, _ in events] == [
        ("fetch_attempted", "google_calendar"),
        ("fetch_failed", "google_calendar"),
    ]
    assert events[1][2]["error"] == "Google Calendar has not been authorised yet"


def test_email_sync_without_client_libs_emits_attempted_then_failed(spine_dir, monkeypatch):
    monkeypatch.setattr(email_pipeline.email_store, "init_db", lambda: None)
    monkeypatch.setattr(email_pipeline.email_store, "set_state", lambda *a, **k: None)
    monkeypatch.setattr(email_pipeline.email_store, "get_state", lambda *a, **k: None)
    monkeypatch.setattr(
        email_pipeline.email_gmail, "libs_missing",
        lambda: ["google-api-python-client"],
    )

    result = email_pipeline._sync_cycle_inner()

    assert result["state"] == "needs_install"
    events = _sequence(spine_dir)
    assert [(kind, subject) for kind, subject, _ in events] == [
        ("fetch_attempted", "gmail"),
        ("fetch_failed", "gmail"),
    ]
    assert events[1][2]["error"].startswith("Google client libraries missing")
