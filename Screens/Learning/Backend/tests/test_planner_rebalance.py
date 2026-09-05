"""M6 slice 3: planner rebalance, tested only against synthetic ledger
fixtures in a throwaway temp DB — never the real learning.db (D17 M6.3 gate).

Run from Screens/Learning/Backend:  python -m pytest tests/ -q
"""

import sys
from datetime import date
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import settings_for_learning as cfg  # noqa: E402
import db as db_mod                  # noqa: E402
from services.planner_rebalance import compute_rebalance, run_weekly_rebalance  # noqa: E402


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", str(tmp_path / "learning.db"))
    db_mod.init_db()
    conn = db_mod.connect()
    yield conn
    conn.close()


def _seed_tracks_and_rooms(conn):
    conn.execute("INSERT INTO tracks (name, color, position) VALUES ('Track A','ember',0)")
    conn.execute("INSERT INTO tracks (name, color, position) VALUES ('Track B','jade',1)")
    conn.execute("INSERT INTO modules (track_id, name, position) VALUES (1,'Mod A',0)")
    conn.execute("INSERT INTO modules (track_id, name, position) VALUES (2,'Mod B',0)")
    conn.execute("INSERT INTO rooms (module_id, name, position, status) VALUES (1,'Room A',0,'learning')")
    conn.execute("INSERT INTO rooms (module_id, name, position, status) VALUES (2,'Room B',0,'learning')")
    conn.execute("UPDATE rooms SET lab_url='https://tryhackme.com/room/x', source='thm' WHERE id=2")
    conn.commit()


def test_neglected_track_and_thm_skips_detected(fresh_db):
    conn = fresh_db
    _seed_tracks_and_rooms(conn)
    # Sunday 2026-09-06 (IST week starting Monday 2026-08-31)
    sunday = date(2026, 9, 6)
    # Track A gets plenty of minutes all week; Track B (the THM room) gets none.
    for d in ["2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]:
        conn.execute(
            "INSERT INTO sessions (room_id, started_at, actual_minutes) VALUES (1,?,60)",
            (f"{d} 10:00:00",),
        )
    conn.commit()

    result = compute_rebalance(conn, today=sunday)
    assert result["week_start"] == "2026-08-31"
    by_name = {t["track"]: t for t in result["tracks"]}
    assert by_name["Track B"]["actual_minutes"] == 0
    assert "Track B" in result["neglected"]
    assert "Track A" not in result["neglected"]
    assert result["thm_skips"] == result["days_elapsed"]  # never touched all week
    assert result["completion_rate"] == 100  # every seeded session had actual_minutes


def test_on_track_week_has_no_neglect_and_no_skips(fresh_db):
    conn = fresh_db
    _seed_tracks_and_rooms(conn)
    sunday = date(2026, 9, 6)
    for d in ["2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06"]:
        conn.execute("INSERT INTO sessions (room_id, started_at, actual_minutes) VALUES (1,?,60)", (f"{d} 09:00:00",))
        conn.execute("INSERT INTO sessions (room_id, started_at, actual_minutes) VALUES (2,?,20)", (f"{d} 20:00:00",))
    conn.commit()

    result = compute_rebalance(conn, today=sunday)
    assert result["neglected"] == []
    assert result["thm_skips"] == 0


def test_run_weekly_rebalance_only_fires_on_sunday_and_once(fresh_db):
    conn = fresh_db
    _seed_tracks_and_rooms(conn)

    saturday = date(2026, 9, 5)
    assert run_weekly_rebalance(conn, today=saturday) is None

    sunday = date(2026, 9, 6)
    created = run_weekly_rebalance(conn, today=sunday)
    assert created is not None
    assert created["kind"] == "rebalance"
    assert created["agent"] == "planner"

    # same week, called again (e.g. a second page load that day) — no duplicate
    again = run_weekly_rebalance(conn, today=sunday)
    assert again is None
    count = conn.execute("SELECT COUNT(*) n FROM proposals WHERE kind='rebalance'").fetchone()["n"]
    assert count == 1
