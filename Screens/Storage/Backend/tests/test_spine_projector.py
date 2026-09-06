"""K-04: spine projection, migrations, freshness arithmetic, idempotent replay."""

import json
import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import spine_projector as sp  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def spine_db(tmp_path, monkeypatch):
    monkeypatch.setenv("KAGE_SPINE_DIR", str(tmp_path / "spine"))
    (tmp_path / "spine").mkdir()
    shutil.copy(FIXTURES / "spine_fresh_01.jsonl", tmp_path / "spine" / "events_2026-09.jsonl")
    conn = sp.connect()
    sp.apply_migrations(conn)
    sp.load_thresholds(conn, FIXTURES / "_freshness_thresholds.json")
    sp.load_prices(conn, FIXTURES / "_model_prices.json")
    yield conn
    conn.close()


def _fixed_now_view(conn):
    """The production view with 'now' pinned, per the ticket's test-time rule."""
    view_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='v_source_freshness'"
    ).fetchone()[0]
    body = re.sub(r"^CREATE VIEW \w+ AS\s*", "", view_sql)
    conn.execute(
        f"CREATE TEMP VIEW v_fresh_fixed AS {body.replace(chr(39)+'now'+chr(39), chr(39)+'2026-09-07T09:00:00+05:30'+chr(39))}"
    )


def test_migrations_are_idempotent_and_ordered(spine_db):
    assert spine_db.execute("PRAGMA user_version").fetchone()[0] == 1
    assert sp.apply_migrations(spine_db) == 1
    tables = {
        row["name"]
        for row in spine_db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"events", "projector_state", "freshness_thresholds", "model_prices"} <= tables


def test_project_is_idempotent_and_ignores_duplicate_ids(spine_db):
    result = sp.project()
    assert result["rows_added"] == 2  # the duplicate id line is ignored, not an error
    assert result["files"] == 1
    assert result["bad_lines"] == 0
    assert spine_db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2
    again = sp.project()
    assert again["rows_added"] == 0
    assert sp.projector_lag_bytes() == 0


def test_freshness_arithmetic_at_pinned_now(spine_db):
    sp.project()
    _fixed_now_view(spine_db)
    row = spine_db.execute(
        "SELECT * FROM v_fresh_fixed WHERE source='amfi_nav'"
    ).fetchone()
    assert row["last_ok_at"] == "2026-09-04T18:00:00+05:30"
    assert row["data_as_of"] == "2026-09-04"
    assert row["stale"] == 1
    assert row["age_hours"] == 63.0
    # SQLite renders the instant in UTC: 2026-09-06T18:00+05:30 == 12:30 UTC
    assert row["stale_since"].startswith("2026-09-06 12:30:00")
    assert row["lagging"] == 0
    youtube = spine_db.execute(
        "SELECT * FROM v_fresh_fixed WHERE source='youtube'"
    ).fetchone()
    assert youtube["last_ok_at"] is None
    assert youtube["stale"] == 1  # Rule 22: no success is never synthesised


def test_bad_line_skipped_and_partial_line_held_back(spine_db, tmp_path):
    target = tmp_path / "spine" / "events_2026-09.jsonl"
    good = json.loads(target.read_text(encoding="utf-8").splitlines()[1])
    target.write_text(
        "{this is not json\n" + json.dumps(good, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    conn = sp.connect()  # fresh projector state
    sp.apply_migrations(conn)
    result = sp.project()
    assert result["bad_lines"] == 1
    assert result["rows_added"] == 1
    assert sp.projector_lag_bytes() == 0
    conn.close()

    with open(target, "a", encoding="utf-8") as fh:  # a torn trailing line
        fh.write('{"v":1,"id":"ff')  # no newline: must not be projected
    partial = sp.project()
    assert partial["rows_added"] == 0
    assert sp.projector_lag_bytes() > 0  # bytes held back until the line completes


def test_loaders_replace_whole_table_and_reject_malformed_json(spine_db):
    assert spine_db.execute("SELECT COUNT(*) FROM model_prices").fetchone()[0] == 2
    prices = FIXTURES / "_model_prices.json"
    bad = FIXTURES.parent / "_malformed_prices.json"
    bad.write_text("{not json", encoding="utf-8")
    try:
        with pytest.raises(Exception):
            sp.load_prices(spine_db, bad)
        assert spine_db.execute("SELECT COUNT(*) FROM model_prices").fetchone()[0] == 2
    finally:
        bad.unlink(missing_ok=True)
    assert sp.load_prices(spine_db, prices) == 2


def test_unfinished_and_spend_views(spine_db):
    sp.project()
    unfinished = spine_db.execute("SELECT count FROM v_unfinished_count").fetchone()
    assert unfinished["count"] == 0
    spend = spine_db.execute("SELECT * FROM v_llm_spend_day").fetchall()
    assert spend == []
