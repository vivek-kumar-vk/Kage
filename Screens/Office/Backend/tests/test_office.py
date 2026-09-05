"""OFFICE screen tests - CRUD across the four record tabs plus the D17.5
resume-defensibility computation.

Run from Screens/Office/Backend:  python -m pytest tests/ -q

Every test runs against a throwaway office.db in tmp_path - never the
real one. The Learning screen is never contacted: learning_client.fetch_skills
is monkeypatched.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import settings_for_office as cfg          # noqa: E402
import db as db_mod                        # noqa: E402
import seed as seed_mod                    # noqa: E402
from services import (                     # noqa: E402
    overview, applications, interviews, work_log, resume_readiness,
    learning_client,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    for r in (overview, applications, interviews, work_log, resume_readiness):
        app.include_router(r.router)
    return app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "office.db")
    db_mod.init_db()
    # default: Learning reachable, nothing tagged
    monkeypatch.setattr(learning_client, "fetch_skills",
                        lambda: (learning_client.OK, []))
    seed_mod.run()                         # tracked skills + example rows
    return TestClient(_build_app())


# --------------------------------------------------------------------- #
# APPLICATIONS
# --------------------------------------------------------------------- #
def test_application_crud(client):
    r = client.post(f"{cfg.API_PREFIX}/applications",
                    json={"company": "Testco", "role": "SRE"})
    assert r.status_code == 200
    app_id = r.json()["id"]

    listed = client.get(f"{cfg.API_PREFIX}/applications").json()
    assert any(a["id"] == app_id and a["company"] == "Testco"
               for a in listed["applications"])
    assert listed["empty"] is False

    r = client.patch(f"{cfg.API_PREFIX}/applications/{app_id}",
                     json={"stage": "interview"})
    assert r.status_code == 200
    got = client.get(f"{cfg.API_PREFIX}/applications").json()
    row = next(a for a in got["applications"] if a["id"] == app_id)
    assert row["stage"] == "interview"

    assert client.delete(f"{cfg.API_PREFIX}/applications/{app_id}").status_code == 200
    after = client.get(f"{cfg.API_PREFIX}/applications").json()
    assert all(a["id"] != app_id for a in after["applications"])


def test_application_bad_stage_rejected(client):
    r = client.post(f"{cfg.API_PREFIX}/applications",
                    json={"company": "X", "role": "Y", "stage": "hired"})
    assert r.status_code == 422


# --------------------------------------------------------------------- #
# INTERVIEWS
# --------------------------------------------------------------------- #
def test_interview_pack_flips_prep_missing(client):
    iv_id = client.post(f"{cfg.API_PREFIX}/interviews", json={
        "company": "Testco", "scheduled_at": "2099-01-01 10:00"}).json()["id"]

    before = client.get(f"{cfg.API_PREFIX}/interviews").json()
    row = next(i for i in before["interviews"] if i["id"] == iv_id)
    assert row["prep_missing"] is True

    client.patch(f"{cfg.API_PREFIX}/interviews/{iv_id}",
                 json={"prep_pack": "likely questions: ..."})
    after = client.get(f"{cfg.API_PREFIX}/interviews").json()
    row = next(i for i in after["interviews"] if i["id"] == iv_id)
    assert row["prep_missing"] is False


def test_interview_bad_outcome_rejected(client):
    iv_id = client.post(f"{cfg.API_PREFIX}/interviews", json={
        "company": "Z", "scheduled_at": "2099-01-01"}).json()["id"]
    r = client.patch(f"{cfg.API_PREFIX}/interviews/{iv_id}",
                     json={"outcome": "ghosted"})
    assert r.status_code == 422


# --------------------------------------------------------------------- #
# WORK LOG
# --------------------------------------------------------------------- #
def test_work_log_crud_and_tech_suggestions(client):
    client.post(f"{cfg.API_PREFIX}/work-log",
                json={"summary": "did a thing", "tech": "Bindplane"})
    d = client.get(f"{cfg.API_PREFIX}/work-log").json()
    assert "Bindplane" in d["known_techs"]
    assert any(e["summary"] == "did a thing" for e in d["entries"])


# --------------------------------------------------------------------- #
# RESUME READINESS  (D17.5)
# --------------------------------------------------------------------- #
def test_defensible_only_at_two_good_easy(client, monkeypatch):
    monkeypatch.setattr(learning_client, "fetch_skills", lambda: (
        learning_client.OK,
        [
            {"skill": "sigma", "rooms_tagged": 1, "good_easy": 2, "defensible": True},
            {"skill": "terraform", "rooms_tagged": 1, "good_easy": 1, "defensible": False},
        ],
    ))
    d = client.get(f"{cfg.API_PREFIX}/resume-readiness").json()
    by_name = {s["name"]: s for s in d["skills"]}
    assert by_name["Sigma"]["defensible"] is True
    assert by_name["Sigma"]["good_easy"] == 2
    assert by_name["Terraform"]["defensible"] is False
    assert by_name["KQL"]["defensible"] is False        # absent upstream => 0


def test_inflated_when_claimed_but_not_earned(client, monkeypatch):
    monkeypatch.setattr(learning_client, "fetch_skills",
                        lambda: (learning_client.OK, []))
    # claim Sigma on the resume without earning it
    sid = next(s["id"] for s in
               client.get(f"{cfg.API_PREFIX}/resume-readiness").json()["skills"]
               if s["name"] == "Sigma")
    client.patch(f"{cfg.API_PREFIX}/skills/{sid}?on_resume=true")
    d = client.get(f"{cfg.API_PREFIX}/resume-readiness").json()
    sigma = next(s for s in d["skills"] if s["name"] == "Sigma")
    assert sigma["on_resume"] is True
    assert sigma["defensible"] is False
    assert sigma["inflated"] is True
    assert d["inflated_count"] >= 1


def test_learning_down_keeps_last_numbers_and_says_so(client, monkeypatch):
    # first, a good sync writes real numbers + fetched_at
    monkeypatch.setattr(learning_client, "fetch_skills", lambda: (
        learning_client.OK,
        [{"skill": "sigma", "rooms_tagged": 1, "good_easy": 2, "defensible": True}],
    ))
    d1 = client.get(f"{cfg.API_PREFIX}/resume-readiness").json()
    sigma1 = next(s for s in d1["skills"] if s["name"] == "Sigma")
    assert sigma1["good_easy"] == 2 and sigma1["fetched_at"]
    stamp = sigma1["fetched_at"]

    # now Learning goes dark
    monkeypatch.setattr(learning_client, "fetch_skills",
                        lambda: (learning_client.UNREACHABLE, []))
    d2 = client.get(f"{cfg.API_PREFIX}/resume-readiness").json()
    assert d2["learning_state"] == learning_client.UNREACHABLE
    sigma2 = next(s for s in d2["skills"] if s["name"] == "Sigma")
    assert sigma2["good_easy"] == 2                 # last-known kept
    assert sigma2["fetched_at"] == stamp           # not refreshed
    assert sigma2["learning_state"] == learning_client.UNREACHABLE


def test_endpoint_missing_is_its_own_state(client, monkeypatch):
    monkeypatch.setattr(learning_client, "fetch_skills",
                        lambda: (learning_client.ENDPOINT_MISSING, []))
    d = client.get(f"{cfg.API_PREFIX}/resume-readiness").json()
    assert d["learning_state"] == learning_client.ENDPOINT_MISSING


# --------------------------------------------------------------------- #
# OVERVIEW
# --------------------------------------------------------------------- #
def test_overview_counts_are_measured(client):
    o = client.get(f"{cfg.API_PREFIX}/overview").json()
    assert o["apply_target"] == cfg.APPLY_TARGET_PER_DAY
    assert set(o["funnel"]) == set(cfg.STAGES)
    # example seed has 3 applications across saved/applied/screen
    assert sum(o["funnel"].values()) == 3
