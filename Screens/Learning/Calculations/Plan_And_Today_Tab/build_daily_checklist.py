"""The Today tab's three checkboxes - core study, Track B, work capture.

WHAT THIS FILE OWNS
    `Saved_Records/daily_checklist.json` - a map of date -> which of
    the three daily boxes were ticked. Three boxes, no more, because
    a checklist that grows stops being checked.

HONEST DEFAULTS
    A day with no entry means none of the boxes were ticked - that is
    read as three False values, not as an error and not as an invented
    "all done". Ticks are only ever written by toggle(), never assumed.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\build_daily_checklist.py
"""

from __future__ import annotations

import json
import sys
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

SAVED_RECORDS = SCREEN / "Saved_Records"
CHECKLIST_FILE = SAVED_RECORDS / "daily_checklist.json"

KEYS = ("core", "trackb", "capture")


def _read_book() -> dict:
    if not CHECKLIST_FILE.exists():
        return {}
    return json.loads(CHECKLIST_FILE.read_text(encoding="utf-8"))


def _write_book(book: dict) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    CHECKLIST_FILE.write_text(json.dumps(book, indent=2), encoding="utf-8")


def read_day(date_str: str) -> dict:
    """The three boxes for one date. A missing day is all False - it
    simply has not been ticked yet, and is never read as 'done'."""
    day = _read_book().get(date_str, {})
    return {key: bool(day.get(key, False)) for key in KEYS}


def toggle(date_str: str, key: str) -> bool:
    """Flip one box for one date and return its new value. An unknown
    box name is refused rather than quietly created."""
    if key not in KEYS:
        raise ValueError(f"key must be one of {KEYS}, got {key!r}")
    book = _read_book()
    day = book.setdefault(date_str, {})
    day[key] = not bool(day.get(key, False))
    _write_book(book)
    return day[key]


def main() -> None:
    from datetime import datetime, timedelta, timezone
    IST = timezone(timedelta(hours=5, minutes=30), "IST")
    today = datetime.now(IST).date().isoformat()
    print("DAILY CHECKLIST")
    print("=" * 50)
    for key in KEYS:
        print(f"  [{'x' if read_day(today)[key] else ' '}] {key}")


if __name__ == "__main__":
    main()
