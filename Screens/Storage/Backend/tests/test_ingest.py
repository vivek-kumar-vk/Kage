"""K-23: ingestion adapter — Pomodoro, Books, YouTube inbox -> spine
(EV-INGEST-01..03, EV-BOOKS-01). All network-free."""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from services import ingest  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

POMODORO_OK = """---
kind: pomodoro
started: 2026-09-07T20:30:00+05:30
ended: 2026-09-07T20:55:00+05:30
minutes: 25
area: LEARN
label: "Splunk buckets and retention"
---
"""
POMODORO_BAD = POMODORO_OK.replace("20:55:00", "21:10:00")
YOUTUBE = [
    {"video_id": "a1", "title": "Splunk clustering deep dive",
     "channel_id": "UC1", "channel": "SplunkTV", "minutes": 42,
     "watched_at": "2026-09-07T21:00:00+05:30"},
    {"video_id": "b2", "title": "funny cats", "channel_id": "UC2",
     "channel": "Cats", "minutes": 18, "watched_at": "2026-09-07T22:00:00+05:30"},
]


@pytest.fixture
def env(tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    monkeypatch.setenv("KAGE_INBOX_DIR", str(inbox))
    monkeypatch.setenv("KAGE_SPINE_DIR", str(tmp_path / "spine"))
    (tmp_path / "spine").mkdir()
    monkeypatch.setattr(ingest.cfg, "KAGE_DATA_DIR", tmp_path / "kage-data")
    (spine := tmp_path / "spine")
    (spine / "_youtube_channels.json").write_text(json.dumps({"UC1": "deep"}),
                                                  encoding="utf-8")
    return {"inbox": inbox, "spine": spine, "data": tmp_path / "kage-data"}


def _events(spine_dir):
    files = sorted(spine_dir.glob("events_*.jsonl"))
    if not files:
        return []
    return [json.loads(line)
            for line in files[0].read_text(encoding="utf-8").splitlines()]


def test_ev_ingest_01_pomodoro_ok_and_bad(env):
    inbox = env["inbox"] / "pomodoro"
    inbox.mkdir(parents=True)
    (inbox / "pomodoro_ok.md").write_text(POMODORO_OK, encoding="utf-8")
    (inbox / "pomodoro_bad.md").write_text(POMODORO_BAD, encoding="utf-8")

    result = ingest.scan()

    assert [r["file"] for r in result["received"]] == ["pomodoro_ok.md"]
    assert [r["file"] for r in result["rejected"]] == ["pomodoro_bad.md"]
    assert result["rejected"][0]["error"] == "minutes 25 disagree with span 40"
    done = env["inbox"] / "_done" / "pomodoro"
    assert (done / "pomodoro_ok.md").is_file()
    rejected = done / "_rejected"
    assert (rejected / "pomodoro_bad.md").is_file()
    assert (rejected / "pomodoro_bad.md.error.txt").is_file()
    events = _events(env["spine"])
    types = [(e["type"], e["subject"]) for e in events]
    assert ("ingest_received", "pomodoro") in types
    assert ("fetch_succeeded", "pomodoro_inbox") in types
    assert ("fetch_failed", "pomodoro_inbox") in types


def test_ev_ingest_02_youtube_week_totals(env):
    inbox = env["inbox"] / "youtube"
    inbox.mkdir(parents=True)
    (inbox / "watch_2026-09-07.json").write_text(json.dumps(YOUTUBE), encoding="utf-8")

    result = ingest.scan()
    assert len(result["received"]) == 1
    payload = next(e for e in _events(env["spine"])
                   if e["type"] == "fetch_succeeded" and e["subject"] == "youtube_inbox")
    assert payload["payload"]["data_as_of"] == "2026-09-07"

    numbers = {e["subject"]: e["payload"]["value"] for e in _events(env["spine"])
               if e["type"] == "number_set"}
    assert numbers["youtube.week.deep_minutes"] == 42
    assert numbers["youtube.week.passive_minutes"] == 18

    # re-dropping the same day replaces it: totals do not double
    (inbox / "watch_2026-09-07.json").write_text(json.dumps(YOUTUBE), encoding="utf-8")
    (env["inbox"] / "_done" / "youtube" / "watch_2026-09-07.json").unlink()
    ingest.scan()
    numbers = {e["subject"]: e["payload"]["value"] for e in _events(env["spine"])
               if e["type"] == "number_set"}
    assert numbers["youtube.week.deep_minutes"] == 42
    assert numbers["youtube.week.passive_minutes"] == 18


def test_ev_books_01_upload_meta_and_read_cursor(env):
    import shutil
    inbox = env["inbox"] / "books"
    inbox.mkdir(parents=True)
    shutil.copy(FIXTURES / "three_pages.pdf", inbox / "Deep Systems.pdf")

    ingest.scan()
    meta_path = env["data"] / "library" / "books" / "deep-systems" / "meta.json"
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["pages"] == 3
    assert meta["quota_pages_per_day"] == 12
    assert meta["cursor_page"] == 0

    numbers = {e["subject"]: e["payload"]["value"] for e in _events(env["spine"])
               if e["type"] == "number_set"}
    assert numbers["books.deep-systems.pages"] == 3
    assert numbers["books.deep-systems.cursor_page"] == 0

    # same book again -> rejected as duplicate
    shutil.copy(FIXTURES / "three_pages.pdf", inbox / "Deep Systems.pdf")
    result = ingest.scan()
    assert result["rejected"][0]["error"].startswith("duplicate")

    from fastapi import FastAPI
    import server_for_storage
    client = TestClient(server_for_storage.app)
    r = client.post("/api/storage/books/deep-systems/read", json={"upto_page": 2})
    assert r.status_code == 200
    assert json.loads(meta_path.read_text(encoding="utf-8"))["cursor_page"] == 2
    r = client.post("/api/storage/books/deep-systems/read", json={"upto_page": 1})
    assert r.status_code == 422  # behind the cursor
    r = client.post("/api/storage/books/deep-systems/read", json={"upto_page": 9})
    assert r.status_code == 422  # past the end
    listing = client.get("/api/storage/books").json()["books"]
    assert listing[0]["slug"] == "deep-systems" and listing[0]["cursor_page"] == 2


def test_ev_ingest_03_scan_never_raises_on_garbage(env):
    inbox = env["inbox"] / "pomodoro"
    inbox.mkdir(parents=True)
    (inbox / "garbage.md").write_text("not front matter at all", encoding="utf-8")
    result = ingest.scan()
    assert result["state"] == "ok"
    assert len(result["rejected"]) == 1
