"""D17 tests: the honest zero and the v3 board.

Run from Screens/Learning/Backend:  python -m pytest tests/ -q

These run against a throwaway temp database — never the real learning.db.
"""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import settings_for_learning as cfg  # noqa: E402
import db as db_mod                  # noqa: E402
import seed                          # noqa: E402


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """A temp learning.db with the v2-era shape + fake demo rows in it."""
    monkeypatch.setattr(cfg, "DB_PATH", str(tmp_path / "learning.db"))
    db_mod.init_db()
    with db_mod.connect() as conn:
        cur = conn.cursor()
        # simulate what D17 must wipe: the old two-track board + demo history
        cur.execute("INSERT INTO tracks (name, color, position) VALUES ('Splunk Admin','ember',0)")
        cur.execute("INSERT INTO tracks (name, color, position) VALUES ('Detection Engineering & Cloud Security','jade',1)")
        cur.execute("INSERT INTO modules (track_id, name, position) VALUES (1,'Architecture & pipeline',0)")
        cur.execute("INSERT INTO rooms (module_id, name, position) VALUES (1,'Architecture + component roles (SH, Indexer, UF, HF, DS, CM, LM)',0)")
        cur.execute("INSERT INTO steps (room_id, position, title, minutes) VALUES (1,0,'Foundations — what it is and why it exists',6)")
        cur.execute("INSERT INTO checkpoints (step_id, position, kind, question, options) VALUES (1,0,'mcq','q?','[]')")
        cur.execute("INSERT INTO attempts (checkpoint_id, answer, correct, ts) VALUES (1,'demo',1,'2026-09-01 21:00:00')")
        cur.execute("INSERT INTO sessions (room_id, started_at, ended_at, actual_minutes) VALUES (1,'2026-09-01 20:30:00','2026-09-01 21:10:00',25)")
        cur.execute("INSERT INTO cards (room_id, front, part1, tag, tether) VALUES (1,'demo front','demo p1','core','trackA')")
        cur.execute("INSERT INTO reviews (card_id, due_date, ease, status) VALUES (1,'2026-09-01',2.5,'active')")
        cur.execute("INSERT INTO notes (room_id, body) VALUES (1,'demo note')")
        cur.execute("INSERT INTO proposals (agent, kind, summary) VALUES ('planner','reorder','demo proposal')")
        cur.execute("INSERT INTO agent_runs (agent, text, source) VALUES ('warden','sample run','sample')")
        cur.execute("INSERT INTO ledger (kind, text) VALUES ('system','Demo history seeded — 20 sessions')")
        cur.execute("INSERT INTO settings (key, value) VALUES ('weekly_budget_minutes','300')")
        conn.commit()
    yield tmp_path / "learning.db"


def _counts(path):
    with db_mod.connect() as conn:
        conn.row_factory = None
        tables = ("sessions", "attempts", "reviews", "cards", "notes",
                  "proposals", "agent_runs", "ledger", "tracks", "modules",
                  "rooms", "steps", "checkpoints")
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in tables}


def test_d17_zero_wipes_every_demo_row(fresh_db):
    assert any(v > 0 for v in _counts(fresh_db).values())
    with db_mod.connect() as conn:
        assert seed.d17_zero(conn.cursor())
        conn.commit()
    c = _counts(fresh_db)
    for t in ("sessions", "attempts", "reviews", "cards", "notes",
              "proposals", "agent_runs", "steps", "checkpoints"):
        assert c[t] == 0, f"{t} still holds {c[t]} demo rows"
    assert c["ledger"] == 1          # only the D17 honest-zero entry
    assert c["tracks"] == 2 and c["rooms"] > 0


def test_d17_zero_is_idempotent(fresh_db):
    with db_mod.connect() as conn:
        cur = conn.cursor()
        assert seed.d17_zero(cur)
        conn.commit()
        assert not seed.d17_zero(cur)   # marker set: never wipes again
        conn.commit()


def test_board_seeds_two_ground0_tracks(fresh_db):
    with db_mod.connect() as conn:
        seed.run()
        cur = conn.cursor()
        tracks = cur.execute(
            "SELECT name, color FROM tracks ORDER BY position").fetchall()
        assert [t["name"] for t in tracks] == [
            "Project → DevOps", "Observability (job-driven)"]
        # every track opens with a Ground Zero module
        first_modules = cur.execute(
            """SELECT t.name track, m.name module FROM modules m
               JOIN tracks t ON t.id = m.track_id
               WHERE m.position = 0 ORDER BY t.position""").fetchall()
        assert all(m["module"].startswith("Ground Zero") for m in first_modules)
        # detection parks archived inside track 2, never deleted
        parked = cur.execute(
            "SELECT archived FROM modules WHERE name='Detection (parked)'"
        ).fetchone()
        assert parked and parked["archived"] == 1
        # the old dissolved tracks are gone
        old = cur.execute(
            "SELECT COUNT(*) c FROM tracks WHERE name LIKE '%Detection Engineering%'"
        ).fetchone()["c"]
        assert old == 0
        # DQL/DPL now exist as real rooms
        dql = cur.execute(
            "SELECT COUNT(*) c FROM rooms WHERE name LIKE 'DQL%' OR name LIKE 'DPL%'"
        ).fetchone()["c"]
        assert dql == 2


def test_no_steps_no_checkpoints_anywhere(fresh_db):
    """Nothing records work that has not happened: rooms seed as skeletons."""
    with db_mod.connect() as conn:
        seed.run()
        conn.commit()
    c = _counts(fresh_db)
    assert c["steps"] == 0 and c["checkpoints"] == 0
    assert c["rooms"] == 68          # 20 project-side + 48 observability-side


def test_fresh_install_path(fresh_db):
    """A brand-new install (no wipe needed) gets the same D17 board."""
    with db_mod.connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM rooms"); cur.execute("DELETE FROM modules")
        cur.execute("DELETE FROM tracks"); cur.execute("DELETE FROM ledger")
        cur.execute("INSERT INTO settings (key, value) VALUES ('d17_zero_done','1')")
        conn.commit()
        assert seed.board(cur)
        conn.commit()
        assert cur.execute("SELECT COUNT(*) c FROM tracks").fetchone()["c"] == 2


def test_settings_reset_to_real_defaults(fresh_db):
    with db_mod.connect() as conn:
        seed.run()
        cur = conn.cursor()
        vals = {r["key"]: r["value"] for r in
                cur.execute("SELECT key, value FROM settings").fetchall()}
    assert vals["weekly_budget_minutes"] == "450"
    assert vals["default_session_minutes"] == "25"
    assert vals["grace_days"] == "1"
