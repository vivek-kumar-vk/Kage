"""Tests for the Context Engine collector (PLAN item 16 A).

Offline unit tests: the HTTP and git layers are monkeypatched, so the
suite never touches a live screen, the real git history, or the Storage
library. What is under test is the honest-state shaping - each source
maps every failure mode to its own named state, never a fabricated value
(Rule 8).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services import context_engine as ce          # noqa: E402


@pytest.fixture()
def fake_roots(tmp_path, monkeypatch):
    """Two fake screen settings files, so discovery has something to read."""
    menu = tmp_path / "menu_backend"
    storage = tmp_path / "storage_backend"
    menu.mkdir()
    storage.mkdir()
    (menu / "settings_for_main_menu.py").write_text(
        'SCREEN_NAME = "main_menu"\nHOST = "127.0.0.1"\nPORT = 8000\n',
        encoding="utf-8")
    (storage / "settings_for_storage.py").write_text(
        'SCREEN_NAME = "storage"\nHOST = "127.0.0.1"\nPORT = 8009\n',
        encoding="utf-8")
    roots = [menu, storage]
    monkeypatch.setattr(ce, "_screen_roots", lambda: roots)
    return roots


# ---------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------
def test_discover_reads_port_and_name_from_settings(fake_roots):
    screens = ce.discover_screens(fake_roots)
    by_name = {s["name"]: s for s in screens}
    assert by_name["main_menu"]["port"] == 8000
    assert by_name["storage"]["port"] == 8009
    assert by_name["storage"]["host"] == "127.0.0.1"


def test_port_of_resolves_storage_from_its_own_settings(fake_roots):
    assert ce._port_of("storage", fake_roots) == 8009


def test_port_of_returns_none_for_unknown_screen(fake_roots):
    assert ce._port_of("nope", fake_roots) is None


# ---------------------------------------------------------------------
# wakatime states
# ---------------------------------------------------------------------
def test_wakatime_not_wired_when_menu_says_not_connected(fake_roots, monkeypatch):
    monkeypatch.setattr(ce, "_get_json",
                        lambda url, timeout=ce.HTTP_TIMEOUT_S: (200, {"state": "not_connected"}))
    state, lines = ce.collect_wakatime(ce.datetime.now(ce.IST))
    assert state == "not_wired"
    assert any("not wired" in line for line in lines)


def test_wakatime_unreachable_when_menu_down(fake_roots, monkeypatch):
    monkeypatch.setattr(ce, "_get_json",
                        lambda url, timeout=ce.HTTP_TIMEOUT_S: (0, None))
    state, lines = ce.collect_wakatime(ce.datetime.now(ce.IST))
    assert state == "unreachable"


def test_wakatime_ok_passes_the_real_payload_through(fake_roots, monkeypatch):
    payload = {"state": "ok", "today": "2 hrs 40 mins", "week": []}
    monkeypatch.setattr(ce, "_get_json",
                        lambda url, timeout=ce.HTTP_TIMEOUT_S: (200, payload))
    state, lines = ce.collect_wakatime(ce.datetime.now(ce.IST))
    assert state == "ok"
    assert any("2 hrs 40 mins" in line for line in lines)


# ---------------------------------------------------------------------
# git states
# ---------------------------------------------------------------------
def test_git_error_is_named_not_swallowed(monkeypatch):
    class R:
        returncode = 128
        stdout = ""
        stderr = "fatal: not a git repository"
    monkeypatch.setattr(ce.subprocess, "run", lambda *a, **k: R())
    state, lines = ce.collect_git(ce.datetime.now(ce.IST))
    assert state == "error"
    assert any("fatal" in line for line in lines)


def test_git_zero_commits_is_ok_and_says_so(monkeypatch):
    class R:
        returncode = 0
        stdout = ""
        stderr = ""
    monkeypatch.setattr(ce.subprocess, "run", lambda *a, **k: R())
    state, lines = ce.collect_git(ce.datetime.now(ce.IST))
    assert state == "ok"
    assert any("0 commits" in line for line in lines)


def test_git_lists_commits_when_there_are_any(monkeypatch):
    class R:
        returncode = 0
        stdout = "abc1234 09:10 did a thing\ndef5678 11:20 did another\n"
        stderr = ""
    monkeypatch.setattr(ce.subprocess, "run", lambda *a, **k: R())
    state, lines = ce.collect_git(ce.datetime.now(ce.IST))
    assert state == "ok"
    assert any("abc1234" in line for line in lines)
    assert any("2 commit(s)" in line for line in lines)


# ---------------------------------------------------------------------
# screens states
# ---------------------------------------------------------------------
def test_screens_down_screen_makes_state_partial(fake_roots, monkeypatch):
    monkeypatch.setattr(ce, "discover_screens",
                        lambda roots: [{"name": "main_menu", "host": "127.0.0.1", "port": 8000},
                                       {"name": "storage", "host": "127.0.0.1", "port": 8009}])
    codes = iter([200, 0])

    def fake_get(url, timeout=ce.HTTP_TIMEOUT_S):
        return next(codes), None

    monkeypatch.setattr(ce, "_get_json", fake_get)
    state, lines = ce.collect_screens(ce.datetime.now(ce.IST))
    assert state == "partial"
    assert any("DOWN" in line for line in lines)


def test_screens_all_up_is_ok(fake_roots, monkeypatch):
    monkeypatch.setattr(ce, "discover_screens",
                        lambda roots: [{"name": "main_menu", "host": "127.0.0.1", "port": 8000}])
    monkeypatch.setattr(ce, "_get_json", lambda url, timeout=ce.HTTP_TIMEOUT_S: (200, {}))
    state, lines = ce.collect_screens(ce.datetime.now(ce.IST))
    assert state == "ok"


# ---------------------------------------------------------------------
# the run itself
# ---------------------------------------------------------------------
def test_run_writes_every_snapshot_and_reports_ok(fake_roots, monkeypatch):
    now = ce.datetime.now(ce.IST)
    written = []

    def fake_post(url, payload, timeout=ce.HTTP_TIMEOUT_S):
        written.append((url, payload["content"]))
        return 200, {"state": "ok", "path": "library/context_engine/x/today/x_1.md"}

    monkeypatch.setattr(ce, "_get_json",
                        lambda url, timeout=ce.HTTP_TIMEOUT_S: (200, {"state": "ok"}))
    monkeypatch.setattr(ce, "_post_json", fake_post)
    monkeypatch.setattr(ce.subprocess, "run", lambda *a, **k: type(
        "R", (), {"returncode": 0, "stdout": "abc1234 09:10 x", "stderr": ""})())
    summary = ce.run_collection()
    assert summary["state"] == "ok"
    assert len(written) == 4
    assert all("/context_engine/" in url for url, _ in written)
    assert all("/today" in url for url, _ in written)
    for source in ce.SOURCE_ORDER:
        row = next(r for r in summary["sources"] if r["source"] == source)
        assert row["written"] is True


def test_run_reports_a_failed_library_write_instead_of_losing_it(fake_roots, monkeypatch):
    monkeypatch.setattr(ce, "_get_json",
                        lambda url, timeout=ce.HTTP_TIMEOUT_S: (200, {"state": "ok"}))
    monkeypatch.setattr(ce, "_post_json",
                        lambda url, payload, timeout=ce.HTTP_TIMEOUT_S: (0, None))
    monkeypatch.setattr(ce.subprocess, "run", lambda *a, **k: type(
        "R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    summary = ce.run_collection()
    assert summary["state"] == "error"
    for row in summary["sources"]:
        assert row["written"] is False
        assert row["problem"]


def test_read_latest_names_missing_snapshots(fake_roots, monkeypatch):
    calls = []

    def fake_get(url, timeout=ce.HTTP_TIMEOUT_S):
        calls.append(url)
        return 404, None

    monkeypatch.setattr(ce, "_get_json", fake_get)
    result = ce.read_latest()
    assert len(result["sources"]) == 4
    for row in result["sources"]:
        assert row["state"] == "no_snapshot"
