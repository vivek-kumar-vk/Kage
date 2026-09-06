"""K-03: event spine write path — schema, atomic locked appends, loud failure."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from Shared_By_All_Screens import spine

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def spine_tmp(tmp_path, monkeypatch):
    target = tmp_path / "spine"
    monkeypatch.setenv("KAGE_SPINE_DIR", str(target))
    return target


def test_emit_writes_one_valid_line(spine_tmp):
    event_id = spine.emit("launcher", "screen_started", "storage", {"port": 8009, "pid": 1})
    assert len(event_id) == 32 and event_id == event_id.lower()
    files = [p for p in spine_tmp.glob("events_*.jsonl")]
    assert len(files) == 1
    raw = files[0].read_text(encoding="utf-8")
    assert raw.endswith("\n") and raw.count("\n") == 1
    event = json.loads(raw)
    assert list(event.keys()) == [
        "v", "id", "ts", "producer", "type", "subject", "payload", "model",
        "tokens_in", "tokens_out", "cost_usd", "correlation_id",
    ]
    assert event["v"] == 1 and event["id"] == event_id
    assert event["ts"].endswith("+05:30")
    assert event["model"] is None and event["correlation_id"] is None
    assert not (spine_tmp / "events.lock").exists()


def test_two_processes_append_400_lines(spine_tmp):
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "from Shared_By_All_Screens import spine\n"
        "for i in range(200):\n"
        "    spine.emit('launcher', 'screen_started', 'storage', {'port': 8009, 'pid': i})\n"
    )
    env = {**os.environ, "KAGE_SPINE_DIR": str(spine_tmp)}
    procs = [subprocess.Popen([sys.executable, "-c", code], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
             for _ in range(2)]
    for proc in procs:
        out, err = proc.communicate(timeout=120)
        assert proc.returncode == 0, err.decode()
    files = list(spine_tmp.glob("events_*.jsonl"))
    assert len(files) == 1
    lines = files[0].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 400
    assert all(json.loads(line) for line in lines)
    assert not (spine_tmp / "events.lock").exists()


def test_unknown_type_raises_before_write(spine_tmp):
    with pytest.raises(spine.SpineSchemaError):
        spine.emit("launcher", "not_a_type", "storage", {})
    assert not list(spine_tmp.glob("events_*.jsonl"))


def test_oversize_payload_raises(spine_tmp):
    with pytest.raises(spine.SpineSchemaError):
        spine.emit("finance", "fetch_attempted", "amfi_nav", {"blob": "x" * 5000})
    assert not list(spine_tmp.glob("events_*.jsonl"))


def test_stale_lock_is_recovered(spine_tmp):
    spine_tmp.mkdir(parents=True, exist_ok=True)
    stale = spine_tmp / "events.lock"
    stale.write_text("", encoding="utf-8")
    old = time.time() - spine.STALE_LOCK_S - 5
    os.utime(stale, (old, old))
    event_id = spine.emit("launcher", "screen_started", "storage", {"port": 8009, "pid": 2})
    assert len(event_id) == 32
    assert not stale.exists()
    files = list(spine_tmp.glob("events_*.jsonl"))
    assert len(files) == 1 and len(files[0].read_text(encoding="utf-8").splitlines()) == 1


def test_readonly_dir_raises_write_error(tmp_path, monkeypatch):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("", encoding="utf-8")
    monkeypatch.setenv("KAGE_SPINE_DIR", str(blocker))
    with pytest.raises(spine.SpineWriteError):
        spine.emit("launcher", "screen_started", "storage", {"port": 8009, "pid": 3})


def test_fixture_lines_roundtrip_byte_equal(spine_tmp):
    original = (FIXTURES / "spine_event_examples.jsonl").read_text(encoding="utf-8")
    for line in original.splitlines():
        event = json.loads(line)
        spine.emit(
            event["producer"], event["type"], event["subject"], event["payload"],
            model=event["model"], tokens_in=event["tokens_in"],
            tokens_out=event["tokens_out"], cost_usd=event["cost_usd"],
            correlation_id=event["correlation_id"], event_id=event["id"],
            now=datetime.fromisoformat(event["ts"]),
        )
    files = list(spine_tmp.glob("events_*.jsonl"))
    assert len(files) == 1
    written = files[0].read_text(encoding="utf-8")
    assert written == original
