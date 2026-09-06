"""K-12: finance freshness events, dated cache, no silent re-stamping
(EV-FRESH-02, EV-FRESH-04). Offline: every request primitive is faked."""

import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from services import db as finance_db  # noqa: E402
from services import market_data  # noqa: E402


@pytest.fixture
def env(tmp_path, monkeypatch):
    spine_root = tmp_path / "spine"
    spine_root.mkdir()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(spine_root))
    monkeypatch.setattr(finance_db, "DB_PATH", tmp_path / "finance.db")
    finance_db.init_db()
    conn = finance_db.connect()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS data_health "
        "(id INTEGER PRIMARY KEY, price_last_refresh TEXT)"
    )
    conn.execute(
        "INSERT OR IGNORE INTO data_health (id, price_last_refresh) VALUES (1, 'seeded')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO price_history (symbol, date, price, source, currency) "
        "VALUES ('ABC', '2026-09-01', 100.0, 'mfapi', 'INR')"
    )
    conn.commit()
    seeded = conn.execute(
        "SELECT price_last_refresh FROM data_health WHERE id = 1"
    ).fetchone()[0]
    conn.close()

    monkeypatch.setattr(market_data, "_get", lambda address: (False, "down"))
    monkeypatch.setattr(market_data, "_bse_get", lambda address: (False, "down"))
    monkeypatch.setattr(market_data, "stock_history",
                        lambda *a, **k: {"has_data": False, "note": "no history"})
    monkeypatch.setattr(market_data, "get_stock_price",
                        lambda *a, **k: {"has_data": False, "note": "no history"})

    def _no_network(request, timeout=None):
        raise OSError("network unplugged")

    monkeypatch.setattr(urllib.request, "urlopen", _no_network)
    return {"spine": spine_root, "seeded": seeded}


def test_ev_san_batch_failure_events_and_dated_cache(env):
    result = market_data.batch_refresh(["ABC"])
    assert result["prices"] == {"ABC": None}

    files = sorted(env["spine"].glob("events_*.jsonl"))
    assert len(files) == 1
    events = [json.loads(line)
              for line in files[0].read_text(encoding="utf-8").splitlines()]
    assert events[0]["type"] == "fetch_attempted"
    assert events[0]["subject"] == "mfapi"
    assert events[-1]["type"] == "fetch_failed"
    assert events[-1]["subject"] == "mfapi"
    assert events[-1]["payload"]["error"].startswith("down")
    # Every touched source keeps its 1:1 attempted/terminal pairing.
    attempted = [e["subject"] for e in events if e["type"] == "fetch_attempted"]
    terminal = [e["subject"] for e in events if e["type"] != "fetch_attempted"]
    assert sorted(attempted) == sorted(terminal)

    cached = market_data.get_last_cached_price("ABC", now=date(2026, 9, 7))
    assert cached == {
        "has_data": True, "symbol": "ABC", "price": 100.0, "currency": "INR",
        "source": "mfapi", "cached": True, "as_of": "2026-09-01",
        "age_days": 6, "stale": True,
    }

    conn = finance_db.connect()
    value = conn.execute(
        "SELECT price_last_refresh FROM data_health WHERE id = 1"
    ).fetchone()[0]
    conn.close()
    assert value == env["seeded"]  # never re-stamped by batch_refresh
