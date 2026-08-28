"""The Study tab's activity heatmap - pure maths, no file access.

WHAT THIS FILE OWNS
    Nothing on disk. heatmap() turns a list of already-read session
    rows into day cells for the GitHub-style grid. Reading
    `study_sessions.csv` stays with track_study_sessions.py, so this
    file can be tested with any rows at all, including none.

WHY THE GRID IS ALWAYS FULL WEEKS
    A grid that starts or ends mid-week renders as a ragged edge no
    CSS wants to draw. So the range is always exactly `weeks` blocks
    of seven Monday-first days, ending with the block that contains
    today - today's cell may be partial, the grid never is.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Study_Tab\\build_study_heatmap.py
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
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


def _level(minutes: int) -> int:
    """The colour bucket for one day's minutes: 0 none, 1 up to half an
    hour, 2 up to an hour, 3 up to two hours, 4 beyond."""
    if minutes <= 0:
        return 0
    if minutes <= 30:
        return 1
    if minutes <= 60:
        return 2
    if minutes <= 120:
        return 3
    return 4


def heatmap(sessions: list[dict], weeks: int = 26,
            today: date | None = None) -> dict:
    """Day cells covering the last `weeks` Monday-started weeks ending
    today. `sessions` is the list read_sessions() returns (or any rows
    with `date` and `minutes`); multiple blocks on one day add up.
    Zero study days are honest zeros - level 0 - never gaps or guesses.
    """
    if weeks < 1:
        raise ValueError(f"weeks must be at least 1, got {weeks}")
    today = today or date.today()

    minutes_by_date: dict[str, int] = {}
    for row in sessions:
        minutes_by_date[row["date"]] = \
            minutes_by_date.get(row["date"], 0) + int(row["minutes"])

    first_monday = (today - timedelta(days=today.weekday())) \
        - timedelta(weeks=weeks - 1)
    days = []
    for offset in range(weeks * 7):
        day = first_monday + timedelta(days=offset)
        key = day.isoformat()
        minutes = minutes_by_date.get(key, 0)
        days.append({"date": key, "minutes": minutes,
                     "level": _level(minutes)})
    return {"weeks": weeks, "days": days}


def main() -> None:
    from track_study_sessions import read_sessions
    grid = heatmap(read_sessions())
    studied = sum(1 for d in grid["days"] if d["minutes"] > 0)
    total = sum(d["minutes"] for d in grid["days"])
    print("STUDY HEATMAP")
    print("=" * 50)
    print(f"  Last {grid['weeks']} weeks: {total} minute(s) across "
          f"{studied} day(s).")


if __name__ == "__main__":
    main()

