"""D38 — interview-day preemption. Today asks Office; Office down is an
honest state, never a guessed "no interview".

Run from Screens/Learning/Backend:  python -m pytest tests/ -q
Throwaway temp learning.db; Office is never really contacted.
"""

import io
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import settings_for_learning as cfg      # noqa: E402
import db as db_mod                      # noqa: E402
import seed                              # noqa: E402
from services import today as today_svc  # noqa: E402
from services import office_client       # noqa: E402
from services.common import today_str    # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", str(tmp_path / "learning.db"))
    db_mod.init_db()
    seed.run()
    app = FastAPI()
    app.include_router(today_svc.router)
    return TestClient(app)


def _office_returns(monkeypatch, value):
    monkeypatch.setattr(office_client, "fetch_interviews_today", lambda: value)


# --------------------------------------------------------------------- #
# the /today office block
# --------------------------------------------------------------------- #
def test_office_block_ok_no_interview(client, monkeypatch):
    _office_returns(monkeypatch, (office_client.OK, []))
    o = client.get("/api/learning/today").json()["office"]
    assert o["state"] == "ok"
    assert o["interview_today"] is False
    assert o["interviews"] == []


def test_interview_today_surfaces_with_pack(client, monkeypatch):
    iv = {"company": "Acme", "role": "Detection Eng", "round": "Tech 1",
          "scheduled_at": today_str() + " 15:30", "mode": "video",
          "prep_pack": "likely: sigma, ATT&CK mapping"}
    _office_returns(monkeypatch, (office_client.OK, [iv]))
    o = client.get("/api/learning/today").json()["office"]
    assert o["interview_today"] is True
    assert len(o["interviews"]) == 1
    assert o["interviews"][0]["prep_pack"] == "likely: sigma, ATT&CK mapping"


def test_office_offline_is_honest_not_no_interview(client, monkeypatch):
    _office_returns(monkeypatch, (office_client.OFFLINE, []))
    o = client.get("/api/learning/today").json()["office"]
    assert o["state"] == "office offline"      # UI says "couldn't check"
    assert o["interview_today"] is False       # never a fabricated "clear day"


# --------------------------------------------------------------------- #
# office_client filtering (Office HTTP faked)
# --------------------------------------------------------------------- #
class _FakeResp:
    status = 200

    def __init__(self, payload):
        self._b = json.dumps(payload).encode()

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_client_keeps_only_today_pending(monkeypatch):
    payload = {"interviews": [
        {"company": "Today Co", "outcome": "pending",
         "scheduled_at": today_str() + " 11:00", "prep_pack": "p"},
        {"company": "Yesterday Co", "outcome": "pending",
         "scheduled_at": today_str(-1) + " 11:00", "prep_pack": ""},
        {"company": "Done Co", "outcome": "passed",
         "scheduled_at": today_str() + " 09:00", "prep_pack": ""},
    ]}
    monkeypatch.setattr(office_client.urllib.request, "urlopen",
                        lambda *a, **k: _FakeResp(payload))
    state, rows = office_client.fetch_interviews_today()
    assert state == office_client.OK
    assert [r["company"] for r in rows] == ["Today Co"]


def test_client_offline_on_connection_error(monkeypatch):
    def boom(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(office_client.urllib.request, "urlopen", boom)
    state, rows = office_client.fetch_interviews_today()
    assert state == office_client.OFFLINE
    assert rows == []
