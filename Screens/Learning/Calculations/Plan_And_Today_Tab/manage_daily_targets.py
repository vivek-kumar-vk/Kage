"""Per-day allocated study minutes, declared by the person, not invented.

WHAT THIS FILE OWNS
    `Saved_Records/daily_targets.json` - one line per date: how many
    minutes of study that day was allocated. The Today tab's
    "Today's study schedule" card shows it and lets the user change it
    inline.

WHY THE USER TYPES THE NUMBER
    Nothing in this project can know how long a study day "should" be -
    any automatic default would be a made-up number wearing a badge.
    An empty value is shown as a dash, never as 0 (C7: blank means not
    set). Once real sessions exist, minutes studied come from
    study_sessions.csv and can be compared against the target honestly.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\manage_daily_targets.py
"""

from __future__ import annotations

import json
import sys
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
        sys.path.insert(0, str(_group))         # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

IST = timezone(timedelta(hours=5, minutes=30), "IST")

SAVED_RECORDS = SCREEN / "Saved_Records"
TARGETS_FILE = SAVED_RECORDS / "daily_targets.json"

MAX_MINUTES = 24 * 60   # a target beyond a whole day is a typo


def _read_all() -> dict:
    if not TARGETS_FILE.exists():
        return {}
    return json.loads(TARGETS_FILE.read_text(encoding="utf-8"))


def _write_all(data: dict) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    TARGETS_FILE.write_text(json.dumps(data, indent=2, sort_keys=True),
                            encoding="utf-8")


def target_for(day: str) -> int | None:
    """Allocated minutes for one YYYY-MM-DD date, or None when never set."""
    value = _read_all().get(day)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def set_target(day: str, minutes: int | None) -> int | None:
    """Set (or clear, with None) the allocated minutes for one date.
    Zero and negatives are refused: a target of nothing is cleared with
    None, not faked with a 0 that would read as 'studied enough'."""
    data = _read_all()
    if minutes is None:
        data.pop(day, None)
        _write_all(data)
        return None
    minutes = int(minutes)
    if minutes <= 0 or minutes > MAX_MINUTES:
        raise ValueError(f"minutes must be 1..{MAX_MINUTES}, got {minutes}")
    data[day] = minutes
    _write_all(data)
    return minutes


def main() -> None:
    today = datetime.now(IST).date().isoformat()
    print("DAILY STUDY TARGETS")
    print("=" * 50)
    data = _read_all()
    if not data:
        print("  No targets set yet.")
        return
    for day in sorted(data):
        marker = "  <- today" if day == today else ""
        print(f"  {day}: {data[day]} min{marker}")


if __name__ == "__main__":
    main()
