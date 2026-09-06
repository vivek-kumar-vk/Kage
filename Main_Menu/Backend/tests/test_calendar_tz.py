"""K-14: calendar timezone root-cause fix — IST windows, IST day/time,
honest freshness (EV-FRESH fixtures from the ticket)."""

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Agent" / "Calendar_Agent"))

import calendar_pipeline  # noqa: E402

_IST = timezone(timedelta(hours=5, minutes=30))


class _FixedNow(datetime):
    """datetime with a pinned now(), so freshness ages deterministically."""

    fixed: datetime

    @classmethod
    def now(cls, tz=None):  # noqa: N805
        moment = cls.fixed
        return moment.astimezone(tz) if tz else moment


def test_window_is_ist_days_in_utc(monkeypatch):
    monkeypatch.setattr(calendar_pipeline.cfg, "CALENDAR_DAYS_BACK", 7)
    monkeypatch.setattr(calendar_pipeline.cfg, "CALENDAR_DAYS_AHEAD", 30)
    start, end = calendar_pipeline._window(date(2026, 9, 7))
    assert start == "2026-08-30T18:30:00+00:00"
    assert end == "2026-10-07T18:29:59+00:00"


def test_day_of_uses_the_ist_instant():
    day, start_iso, all_day = calendar_pipeline._day_of(
        {"start": {"dateTime": "2026-09-07T04:30:00Z"}})
    assert (day, start_iso, all_day) == ("2026-09-07", "2026-09-07T10:00:00+05:30", False)

    # 19:30Z is 01:00 IST the next calendar day
    day, _, _ = calendar_pipeline._day_of({"start": {"dateTime": "2026-09-06T19:30:00Z"}})
    assert day == "2026-09-07"

    assert calendar_pipeline._day_of({"start": {"date": "2026-09-07"}}) \
        == ("2026-09-07", None, True)
    assert calendar_pipeline._day_of({"start": {}}) == (None, None, False)


def test_clock_converts_to_ist():
    assert calendar_pipeline._clock("2026-09-07T04:30:00Z") == "10:00am"
    assert calendar_pipeline._clock("2026-09-07T10:00:00") == "10:00am"
    assert calendar_pipeline._clock("nonsense") is None
    assert calendar_pipeline._clock(None) is None


def _spine_event(event_id, ts, type_, payload):
    return {"v": 1, "id": event_id * 32, "ts": ts, "producer": "main_menu",
            "type": type_, "subject": "google_calendar", "payload": payload,
            "model": None, "tokens_in": None, "tokens_out": None,
            "cost_usd": None, "correlation_id": None}


def _write_events(spine_root, events):
    (spine_root / "events_2026-09.jsonl").write_text(
        "\n".join(json.dumps(e, separators=(",", ":")) for e in events) + "\n",
        encoding="utf-8")


def test_month_freshness_reads_the_spine(tmp_path, monkeypatch):
    spine_root = tmp_path / "spine"
    spine_root.mkdir()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(spine_root))
    _FixedNow.fixed = datetime(2026, 9, 7, 11, 0, tzinfo=_IST)  # 3h after 08:01
    monkeypatch.setattr(calendar_pipeline, "datetime", _FixedNow)
    _write_events(spine_root, [
        _spine_event("1", "2026-09-07T08:00:00+05:30", "fetch_attempted", {}),
        _spine_event("2", "2026-09-07T08:01:00+05:30", "fetch_succeeded",
                     {"data_as_of": "2026-09-07T08:01:00+05:30", "items": 3}),
    ])

    freshness = calendar_pipeline._calendar_freshness()
    assert freshness["state"] == "fresh"
    assert freshness["last_ok_at"] == "2026-09-07T08:01:00+05:30"
    assert freshness["stale_since"] == "2026-09-07T14:01:00+05:30"
    assert freshness["last_error"] is None

    # a fetch_failed newer than the last success sets last_error only
    _FixedNow.fixed = datetime(2026, 9, 7, 15, 0, tzinfo=_IST)  # now 7h: stale
    _write_events(spine_root, [
        _spine_event("1", "2026-09-07T08:00:00+05:30", "fetch_attempted", {}),
        _spine_event("2", "2026-09-07T08:01:00+05:30", "fetch_succeeded",
                     {"data_as_of": "2026-09-07T08:01:00+05:30", "items": 3}),
        _spine_event("3", "2026-09-07T09:00:00+05:30", "fetch_failed",
                     {"error": "token expired"}),
    ])
    freshness = calendar_pipeline._calendar_freshness()
    assert freshness["state"] == "stale"
    assert freshness["last_ok_at"] == "2026-09-07T08:01:00+05:30"
    assert freshness["stale_since"] == "2026-09-07T14:01:00+05:30"
    assert freshness["last_error"] == "token expired"


def test_month_freshness_never_when_no_success(tmp_path, monkeypatch):
    spine_root = tmp_path / "spine"
    spine_root.mkdir()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(spine_root))
    freshness = calendar_pipeline._calendar_freshness()
    assert freshness["state"] == "never"
    assert freshness["last_ok_at"] is None
