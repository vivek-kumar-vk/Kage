"""Start and stop a study block, and keep the honest record of it.

WHAT THIS FILE OWNS
    `Saved_Records/study_sessions.csv` - one row per block, written only
    when the block is STOPPED. A block you start and never stop leaves no
    row. That is correct: an unfinished session is not a lie half-told,
    it simply has not happened yet as far as the record is concerned.

WHY "IN PROGRESS" LIVES IN ITS OWN FILE, NOT THE CSV
    The CSV is a frozen column contract (Column_Contracts) - a promise
    about finished rows. A session that has started but not stopped has
    no `minutes` yet, so it does not belong in that file. It lives in
    `study_session_in_progress.json` instead, which holds at most one
    session and is deleted the moment that session stops.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Study_Tab\\track_study_sessions.py
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IST = timezone(timedelta(hours=5, minutes=30), "IST")

SAVED_RECORDS = SCREEN / "Saved_Records"
SESSIONS_FILE = SAVED_RECORDS / "study_sessions.csv"
IN_PROGRESS_FILE = SAVED_RECORDS / "study_session_in_progress.json"

COLUMNS = ["date", "started_at", "minutes", "topic", "notes",
           "recall_note_file", "capture"]
# `capture` joined the frozen contract at v14 - the work-capture line,
# one line on what day-job work taught or produced today. It is last
# and always written (default ""), so older readers see an empty cell
# rather than a missing column.


class ASessionIsAlreadyRunning(Exception):
    """Raised by start_a_session() when one is already in progress.

    Two running sessions would mean stop_the_session() cannot know which
    one it is closing, so this is refused rather than silently overwriting
    the first one's start time.
    """


class NoSessionIsRunning(Exception):
    """Raised by stop_the_session() and current_session() when there is
    nothing to stop or report."""


def _now() -> datetime:
    return datetime.now(IST)


@dataclass(frozen=True)
class RunningSession:
    topic: str
    started_at: datetime
    elapsed_minutes: int


def start_a_session(topic: str) -> RunningSession:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("a study block needs a topic")
    if IN_PROGRESS_FILE.exists():
        running = current_session()
        raise ASessionIsAlreadyRunning(
            f"'{running.topic}' has been running since "
            f"{running.started_at.isoformat(timespec='minutes')} - stop it "
            "before starting another one."
        )

    started_at = _now()
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    IN_PROGRESS_FILE.write_text(
        json.dumps({"topic": topic, "started_at": started_at.isoformat()}),
        encoding="utf-8",
    )
    return RunningSession(topic=topic, started_at=started_at, elapsed_minutes=0)


def current_session() -> RunningSession | None:
    """None when nothing is running - not an exception, because callers
    like the Today tab just want to know either way."""
    if not IN_PROGRESS_FILE.exists():
        return None
    data = json.loads(IN_PROGRESS_FILE.read_text(encoding="utf-8"))
    started_at = datetime.fromisoformat(data["started_at"])
    elapsed = int((_now() - started_at).total_seconds() // 60)
    return RunningSession(topic=data["topic"], started_at=started_at,
                          elapsed_minutes=max(0, elapsed))


def stop_the_session(notes: str = "", recall_note_file: str = "",
                     capture: str = "") -> dict:
    """Close the running session and write exactly one row.

    Minutes are rounded to the nearest whole minute, never up - a block
    stopped 40 seconds in is 0 minutes studied, not 1, because rounding up
    would let a habit tracker be gamed by starting and immediately
    stopping.

    `capture` is the work-capture line (frozen contract v14): one line on
    what day-job work taught or produced today. It defaults to "" so old
    callers keep working and every row still carries all seven columns.
    """
    running = current_session()
    if running is None:
        raise NoSessionIsRunning("nothing is running - start a block first")

    ended_at = _now()
    minutes = int((ended_at - running.started_at).total_seconds() // 60)

    row = {
        "date": running.started_at.date().isoformat(),
        "started_at": running.started_at.isoformat(timespec="seconds"),
        "minutes": minutes,
        "topic": running.topic,
        "notes": (notes or "").strip(),
        "recall_note_file": (recall_note_file or "").strip(),
        "capture": (capture or "").strip(),
    }
    _append_row(row)
    IN_PROGRESS_FILE.unlink()
    return row


def _append_row(row: dict) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    is_new = not SESSIONS_FILE.exists() or SESSIONS_FILE.stat().st_size == 0
    with SESSIONS_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if is_new:
            w.writeheader()
        w.writerow(row)


def read_sessions() -> list[dict]:
    """Every finished block, oldest first. Empty when nothing has been
    logged yet - not an error, the honest starting state of this screen."""
    if not SESSIONS_FILE.exists():
        return []
    with SESSIONS_FILE.open(newline="", encoding="utf-8") as f:
        return [
            {**row, "minutes": int(row["minutes"])}
            for row in csv.DictReader(f)
        ]


def main() -> None:
    sessions = read_sessions()
    running = current_session()

    print("STUDY SESSIONS")
    print()
    if running:
        print(f"  RUNNING NOW: {running.topic!r}, "
              f"{running.elapsed_minutes} minute(s) so far")
    else:
        print("  Nothing running right now.")
    print()
    if not sessions:
        print("  No finished blocks logged yet.")
        return
    for row in sessions[-10:]:
        print(f"  {row['date']}  {row['minutes']:>4} min  {row['topic']}")
    print(f"\n  {len(sessions)} block(s) total.")


if __name__ == "__main__":
    main()
