"""Who is busy, who is waiting, and who may start.

One agent does one job at a time. That is the whole rule, and everything
here exists to enforce it without ever interrupting work already in
progress.

WHY A FILE AND NOT AN IN-MEMORY LOCK
    The screens are four separate processes (ADR-055), and a scheduled
    morning run is a fifth. A lock object lives inside one process and
    is invisible to the other four. A file created with
    os.O_CREAT | os.O_EXCL is atomic on POSIX and on Windows, needs no
    daemon, and survives a crash in a way you can open with a text
    editor.

Standard library only.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Shared_By_All_Agents
PROJECT_ROOT = HERE.parent                       # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BOARD = HERE / "Lease_Board"
TAKEOVERS = BOARD / "leases_taken_over.csv"

TAKEOVER_COLUMNS = [
    "timestamp", "agent", "abandoned_job_shape", "abandoned_started_at",
    "abandoned_process_id",
]


def _lease_file(agent_name: str) -> Path:
    BOARD.mkdir(parents=True, exist_ok=True)
    return BOARD / f"{agent_name}.lease"


def _queue_file(agent_name: str) -> Path:
    BOARD.mkdir(parents=True, exist_ok=True)
    return BOARD / f"{agent_name}.queue.jsonl"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WhatHappened:
    """The answer to "can this agent start now". Exactly four states.

    started    you hold the lease; go
    queued     someone else holds it; your job is written down and will run
    refused    the queue is full; nothing was written
    took_over  the previous holder is presumed dead; you hold the lease now
    """

    def __init__(self, state: str, agent_name: str, ticket: str = "",
                holder: dict | None = None, reason: str = ""):
        self.state = state
        self.agent_name = agent_name
        self.ticket = ticket
        self.holder = holder
        self.reason = reason

    @property
    def may_run(self) -> bool:
        return self.state in ("started", "took_over")

    def as_plain_dict(self) -> dict:
        return {"state": self.state, "agent": self.agent_name,
               "ticket": self.ticket, "holder": self.holder, "reason": self.reason}


def try_to_start(agent_name: str, job_shape: str, job_summary: str, *,
                 longest_job_minutes: float = 15, queue_limit: int = 20) -> WhatHappened:
    """Ask for the lease. Never blocks and never sleeps.

    A caller that waits is a caller that can deadlock; a caller told
    'queued' can get on with something else.
    """
    lease = _lease_file(agent_name)
    mine = {
        "agent": agent_name, "job_shape": job_shape,
        "job_summary": job_summary[:200],
        "started_at": _now().isoformat(timespec="seconds"),
        "process_id": os.getpid(),
        "longest_job_minutes": longest_job_minutes,
    }

    try:
        # Atomic - whoever wins this call holds the lease. No window
        # between checking and creating for a second caller to slip in.
        handle = os.open(str(lease), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(mine, out, indent=2)
        return WhatHappened("started", agent_name)
    except FileExistsError:
        pass

    holder = _read_lease(lease)

    if _is_stale(holder):
        _write_lease(lease, mine)
        _note_a_takeover(agent_name, holder)
        return WhatHappened("took_over", agent_name, holder=holder, reason=(
            f"the previous job claimed to need at most "
            f"{holder.get('longest_job_minutes', '?')} minutes and has been "
            "running longer, so it is presumed dead"
        ))

    waiting = how_many_are_waiting(agent_name)
    if waiting >= queue_limit:
        return WhatHappened("refused", agent_name, holder=holder, reason=(
            f"{agent_name} already has {waiting} jobs waiting, which is its "
            "limit. Nothing was written down; a job that silently never runs "
            "is worse than a refusal."
        ))

    ticket = _join_the_queue(agent_name, job_shape, job_summary)
    return WhatHappened("queued", agent_name, ticket=ticket, holder=holder, reason=(
        f"{agent_name} is busy with '{holder.get('job_shape', '?')}' since "
        f"{holder.get('started_at', '?')}. Your job is number {waiting + 1} "
        "in the queue."
    ))


def finish(agent_name: str) -> bool:
    """Give the lease back. Safe to call twice; safe to call when not held.

    Always called from a finally block - a lease left behind blocks the
    agent until it goes stale.
    """
    try:
        _lease_file(agent_name).unlink()
        return True
    except FileNotFoundError:
        return False


def who_is_busy() -> list[dict]:
    """Every held lease, for the Agents tab. Reads only."""
    busy = []
    for lease in sorted(BOARD.glob("*.lease")) if BOARD.exists() else []:
        holder = _read_lease(lease)
        if not holder:
            continue
        started = _parse(holder.get("started_at"))
        busy.append({
            "agent": holder.get("agent", lease.stem),
            "job_shape": holder.get("job_shape", ""),
            "job_summary": holder.get("job_summary", ""),
            "started_at": holder.get("started_at", ""),
            "running_for_seconds": int((_now() - started).total_seconds()) if started else None,
            "looks_stuck": _is_stale(holder),
        })
    return busy


def what_is_waiting(agent_name: str | None = None) -> list[dict]:
    """Every queued job, oldest first."""
    if not BOARD.exists():
        return []
    waiting = []
    pattern = f"{agent_name}.queue.jsonl" if agent_name else "*.queue.jsonl"
    for queue in sorted(BOARD.glob(pattern)):
        waiting.extend(_read_queue(queue))
    waiting.sort(key=lambda job: job.get("queued_at", ""))
    return waiting


def how_many_are_waiting(agent_name: str) -> int:
    return len(_read_queue(_queue_file(agent_name)))


def take_the_next_job(agent_name: str) -> dict | None:
    """Pop the oldest queued job. Only ever called by the agent itself,
    after it finishes one job, while it still holds nothing."""
    queue = _queue_file(agent_name)
    jobs = _read_queue(queue)
    if not jobs:
        return None
    first, rest = jobs[0], jobs[1:]
    if rest:
        with queue.open("w", encoding="utf-8") as out:
            for job in rest:
                out.write(json.dumps(job) + "\n")
    else:
        queue.unlink(missing_ok=True)
    return first


def drop_a_queued_job(agent_name: str, ticket: str) -> bool:
    """Cancel one waiting job from the UI. Returns True if it was there."""
    queue = _queue_file(agent_name)
    jobs = _read_queue(queue)
    kept = [job for job in jobs if job.get("ticket") != ticket]
    if len(kept) == len(jobs):
        return False
    if kept:
        with queue.open("w", encoding="utf-8") as out:
            for job in kept:
                out.write(json.dumps(job) + "\n")
    else:
        queue.unlink(missing_ok=True)
    return True


def recent_takeovers(days: int = 30) -> list[dict]:
    if not TAKEOVERS.exists():
        return []
    since = _now() - timedelta(days=days)
    out = []
    with TAKEOVERS.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            when = _parse(row.get("timestamp"))
            if when and when >= since:
                out.append(row)
    return out


# --------------------------------------------------------------- internals
def _join_the_queue(agent_name: str, job_shape: str, job_summary: str) -> str:
    queue = _queue_file(agent_name)
    ticket = _now().strftime("%Y%m%dT%H%M%S") + "-" + str(os.getpid())
    job = {"ticket": ticket, "agent": agent_name, "job_shape": job_shape,
          "job_summary": job_summary[:200],
          "queued_at": _now().isoformat(timespec="seconds")}
    with queue.open("a", encoding="utf-8") as out:
        out.write(json.dumps(job) + "\n")
    return ticket


def _read_queue(queue: Path) -> list[dict]:
    if not queue.exists():
        return []
    jobs = []
    with queue.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                jobs.append(json.loads(line))
            except ValueError:
                continue          # a torn line is skipped, never guessed at
    return jobs


def _read_lease(lease: Path) -> dict:
    try:
        return json.loads(lease.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _write_lease(lease: Path, payload: dict) -> None:
    lease.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _parse(stamp) -> datetime | None:
    try:
        when = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def _is_stale(holder: dict) -> bool:
    if not holder:
        return True
    started = _parse(holder.get("started_at"))
    if started is None:
        return True
    limit = timedelta(minutes=float(holder.get("longest_job_minutes", 15)))
    return _now() - started > limit


def _note_a_takeover(agent_name: str, holder: dict) -> None:
    """A takeover means something died mid-job. Its own file, because it
    should be rare and a pile of these is a real signal."""
    BOARD.mkdir(parents=True, exist_ok=True)
    new_file = not TAKEOVERS.exists()
    with TAKEOVERS.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(TAKEOVER_COLUMNS)
        writer.writerow([
            _now().isoformat(timespec="seconds"), agent_name,
            holder.get("job_shape", ""), holder.get("started_at", ""),
            holder.get("process_id", ""),
        ])
