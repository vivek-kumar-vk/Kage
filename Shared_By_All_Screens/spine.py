"""Event spine write path (K-03): schema-checked, locked, append-only JSONL.

Every event is one JSON line in kage-data/spine/events_<YYYY-MM>.jsonl.
Failure is loud (SpineWriteError); a bad event is rejected before any I/O
(SpineSchemaError). Idempotency is the projector's concern, not ours.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


class SpineSchemaError(ValueError): ...
class SpineWriteError(OSError): ...

PRODUCERS: frozenset = frozenset({
    "main_menu", "agents", "finance", "storage", "learning", "office",
    "launcher", "ingest", "anime",
})
TYPES = {
    "fetch_attempted": (),
    "fetch_succeeded": ("data_as_of", "items"),
    "fetch_failed": ("error",),
    "llm_call": ("task_class", "tier", "rung_used", "chain", "schema_valid",
                 "latency_ms", "degraded", "unresolved_tokens"),
    "agent_run": ("run_id", "status"),
    "number_set": ("value",),
    "decision_proposed": ("rank", "kind", "source", "severity", "score",
                          "data_as_of", "text", "status"),
    "decision_taken": ("by",),
    "decision_dismissed": ("by",),
    "watchdog_verdict": ("verdict", "detail"),
    "ticket_opened": ("key", "title"),
    "ticket_closed": ("key",),
    "ingest_received": ("source",),
    "backup_completed": ("destination", "files", "bytes", "verified"),
    "screen_started": ("port", "pid"),
    "screen_stopped": ("exit_code", "restarted"),
}
MAX_PAYLOAD_BYTES: int = 4096
MAX_SUBJECT_CHARS: int = 80
LOCK_ATTEMPTS: int = 50
LOCK_SLEEP_S: float = 0.02
STALE_LOCK_S: float = 5.0
IST = timezone(timedelta(hours=5, minutes=30))

_HEX32 = re.compile(r"[0-9a-f]{32}")


def spine_dir() -> Path:
    """The spine directory; KAGE_SPINE_DIR overrides (tests, phone migration)."""
    override = os.environ.get("KAGE_SPINE_DIR")
    directory = Path(override) if override else Path(__file__).resolve().parents[1] / "kage-data" / "spine"
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SpineWriteError(f"{directory}: {exc}") from exc
    return directory


def current_file(now: datetime | None = None) -> Path:
    return spine_dir() / f"events_{_as_ist(now or datetime.now(IST)):%Y-%m}.jsonl"


def _as_ist(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=IST)
    return now.astimezone(IST)


def _check_int_or_none(name: str, value) -> None:
    if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
        raise SpineSchemaError(f"{name}: expected int or null")


def emit(producer: str, type: str, subject: str, payload: dict, *,
         model: str | None = None, tokens_in: int | None = None,
         tokens_out: int | None = None, cost_usd: float | None = None,
         correlation_id: str | None = None, event_id: str | None = None,
         now: datetime | None = None) -> str:
    # Schema before I/O: no lock is touched and no file opened on a bad event.
    if producer not in PRODUCERS:
        raise SpineSchemaError(f"producer: unknown {producer!r}")
    if type not in TYPES:
        raise SpineSchemaError(f"type: unknown {type!r}")
    if not isinstance(subject, str) or not subject or len(subject) > MAX_SUBJECT_CHARS:
        raise SpineSchemaError(f"subject: expected 1..{MAX_SUBJECT_CHARS} chars")
    if not isinstance(payload, dict):
        raise SpineSchemaError("payload: expected an object")
    missing = [key for key in TYPES[type] if key not in payload]
    if missing:
        raise SpineSchemaError(f"payload: missing required keys {missing} for type {type!r}")
    if len(json.dumps(payload, ensure_ascii=False).encode()) > MAX_PAYLOAD_BYTES:
        raise SpineSchemaError(f"payload: larger than {MAX_PAYLOAD_BYTES} bytes")
    _check_int_or_none("tokens_in", tokens_in)
    _check_int_or_none("tokens_out", tokens_out)
    if cost_usd is not None and (not isinstance(cost_usd, (int, float)) or isinstance(cost_usd, bool)):
        raise SpineSchemaError("cost_usd: expected number or null")
    if event_id is not None and not _HEX32.fullmatch(event_id):
        raise SpineSchemaError("event_id: expected 32 lowercase hex chars")

    ts = _as_ist(now or datetime.now(IST)).isoformat(timespec="seconds")
    event_id = event_id or uuid.uuid4().hex
    line = json.dumps(
        {"v": 1, "id": event_id, "ts": ts, "producer": producer, "type": type,
         "subject": subject, "payload": payload, "model": model,
         "tokens_in": tokens_in, "tokens_out": tokens_out, "cost_usd": cost_usd,
         "correlation_id": correlation_id},
        ensure_ascii=False, separators=(",", ":"),
    )
    data = (line + "\n").encode("utf-8")

    directory = spine_dir()
    lock_path = directory / "events.lock"
    lock_fd = None
    for _attempt in range(LOCK_ATTEMPTS):
        try:
            lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > STALE_LOCK_S:
                    lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(LOCK_SLEEP_S)
        except OSError as exc:
            raise SpineWriteError(f"{lock_path}: {exc}") from exc
    if lock_fd is None:
        raise SpineWriteError(
            f"{lock_path}: lock not acquired after {LOCK_ATTEMPTS} attempts"
        )
    os.close(lock_fd)

    target = current_file(now)
    try:
        fd = os.open(target, os.O_CREAT | os.O_WRONLY | os.O_APPEND)
        try:
            view = memoryview(data)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise SpineWriteError(f"{target}: {exc}") from exc
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
    return event_id
