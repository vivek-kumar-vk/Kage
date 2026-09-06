"""K-19: the watchdog — verdicts only, cannot_tell when a source does not
answer, marker-file budget, audit file (EV-WATCH-01..04)."""

import json
import socket
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import watchdog  # noqa: E402

_IST = timezone(timedelta(hours=5, minutes=30))
_NOW = datetime(2026, 9, 7, 20, 31, 5, tzinfo=_IST)


@pytest.fixture(autouse=True)
def spine_dir(tmp_path, monkeypatch):
    target = tmp_path / "spine"
    target.mkdir()
    monkeypatch.setenv("KAGE_SPINE_DIR", str(target))
    monkeypatch.setattr(watchdog, "_storage_port", lambda: None)  # storage down
    return target


def test_ev_watch_01_storage_unreachable_is_cannot_tell(spine_dir, monkeypatch):
    monkeypatch.setattr(watchdog, "discover", lambda: ([], []))
    results = watchdog.run(_NOW)
    by_check = {r["check"]: r for r in results}
    assert by_check["source:*"]["verdict"] == "cannot_tell"
    assert by_check["source:*"]["detail"].startswith("unreachable")
    assert by_check["llm_spend"]["verdict"] == "cannot_tell"
    assert by_check["projector_lag"]["verdict"] == "cannot_tell"
    assert by_check["backup"]["verdict"] == "cannot_tell"
    assert by_check["complexity"]["verdict"] == "cannot_tell"


def _fake_screen(tmp_path, name, port):
    folder = tmp_path / name / "Backend"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"settings_for_{name.lower()}.py").write_text(f"PORT = {port}\n",
                                                            encoding="utf-8")
    return SimpleNamespace(SCREEN_FOLDER=folder.parent)


def test_ev_watch_02_screens_up_and_down(spine_dir, monkeypatch, tmp_path):
    screens = [
        _fake_screen(tmp_path, "Alpha", 65531),
        _fake_screen(tmp_path, "Beta", 65532),
        _fake_screen(tmp_path, "Gamma", 65533),
    ]
    monkeypatch.setattr(watchdog, "discover", lambda: (screens, []))

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 65531))
    server.listen(1)

    def _serve():
        try:
            conn, _ = server.accept()
            conn.recv(1024)
            conn.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: 0\r\n\r\n")
            conn.close()
        except OSError:
            pass

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    results = watchdog.run(_NOW)
    thread.join(timeout=5)
    server.close()

    by_check = {r["check"]: r for r in results}
    assert by_check["screen:Alpha"]["verdict"] == "up"
    assert by_check["screen:Beta"]["verdict"] == "down"
    assert by_check["screen:Gamma"]["verdict"] == "down"


def test_ev_watch_03_backup_overdue_and_audit_file(spine_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(watchdog, "_storage_port", lambda: 8009)

    def _get_json(url, timeout):
        if "type=backup_completed" in url:
            return 200, {"state": "ok", "projected_at": "x",
                         "projector_lag_bytes": 0,
                         "events": [{"ts": "2026-08-29T03:30:00+05:30",
                                     "payload": {"verified": True}}]}
        return 0, None

    monkeypatch.setattr(watchdog, "_get_json", _get_json)
    monkeypatch.setattr(watchdog, "discover", lambda: ([], []))
    results = watchdog.run(_NOW)
    by_check = {r["check"]: r for r in results}
    assert by_check["backup"]["verdict"] == "stale"
    assert by_check["backup"]["detail"].startswith("backup_overdue")

    path = watchdog.write_audit_md(results, _NOW)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# watchdog 2026-09-07T20:31:05+05:30"
    assert any(line.startswith("- backup: stale — backup_overdue") for line in lines)


def test_ev_watch_04_run_if_due_respects_the_marker(spine_dir, monkeypatch):
    monkeypatch.setattr(watchdog, "discover", lambda: ([], []))
    first = watchdog.run_if_due(_NOW)
    assert first is not None
    assert (spine_dir / "_watchdog_last_run").is_file()
    second = watchdog.run_if_due(_NOW + timedelta(minutes=10))
    assert second is None
    third = watchdog.run_if_due(_NOW + timedelta(minutes=31))
    assert third is not None
