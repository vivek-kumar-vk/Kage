"""Seven-day plans, one JSON file - what each half of the plan does per day.

WHAT THIS FILE OWNS
    `Saved_Records/week_plans.json` - one entry per planned week, each
    carrying its number, its Monday start date, the focus for each
    track, and seven days (Mon-Sun). Since ADR-094 a day is more than
    two lines: it carries what kind of day it is, the two topic ids it
    works on, its timed chunks (four study blocks and a recall block on
    a normal day), its Track B evening block, a free-text note and a
    done flag the user flips themselves. The fourteen-week plan those
    days were filled from lives in `seed_the_week_plans.py`, next door.

WHY WEEK NUMBERS ARE DERIVED, NOT STORED AS INPUT
    `num` is always len(existing)+1 at the moment the week is added,
    so it can never disagree with the file it sits in. Deleting a week
    leaves the remaining numbers alone - they were true when written
    and rewriting history would break nothing but trust in them.

WHY JSON, NOT A FROZEN CSV (same reasoning as manage_the_study_plan.py)
    A week gets edited and deleted by hand; there is no second reader
    to keep a column promise to.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\manage_week_plans.py
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
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
WEEK_PLANS_FILE = SAVED_RECORDS / "week_plans.json"

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

# WHAT A DAY IS FOR, not what happened on it. Saturday is off and Sunday
# consolidates - that is the learning contract, not a guess - so `kind`
# is derived from the weekday when a week is created and editable after.
# A public holiday turns a Wednesday into an off day and nothing else
# in the file has to change.
DAY_KINDS = ("study", "prep", "off", "consolidation", "buffer")

# A CHUNK is one timed block inside a study day. `kind` decides only how
# it is drawn: `lab` gets the hands-on badge, `recall` gets the card
# badge, `study` gets neither. It carries no maths.
CHUNK_KINDS = ("study", "lab", "recall")

MAX_CHUNKS_PER_DAY = 8      # four chunks then a recall is the shape; 8 is a typo guard
MAX_POINTS_PER_CHUNK = 8


class WeekPlanError(Exception):
    """Parent for every error this file raises, so a caller can catch
    the family without needing to know each member by name."""


class NoSuchWeek(WeekPlanError):
    """Raised for a week id that is not in the file - most likely
    already deleted, never silently ignored."""


def _today() -> date:
    return datetime.now(IST).date()


def read_weeks() -> list[dict]:
    """Every planned week, oldest first. Empty when none exist yet -
    not an error, the honest state before the first plan is made."""
    if not WEEK_PLANS_FILE.exists():
        return []
    data = json.loads(WEEK_PLANS_FILE.read_text(encoding="utf-8"))
    weeks = data.get("weeks", [])
    for week in weeks:
        for day in week.get("days", []):
            _fill_missing(day)
    return weeks


def _default_kind(day_name: str) -> str:
    """Saturday off, Sunday consolidation, everything else a study day.
    Straight from the contract, so it is a fact about the calendar and
    not an invented default."""
    if day_name == "Sat":
        return "off"
    if day_name == "Sun":
        return "consolidation"
    return "study"


def _fill_missing(day: dict) -> dict:
    """Weeks written before chunks existed are still valid weeks.
    Reading one fills the newer keys in memory with the empty values
    they would have had - it never rewrites the file, because a read
    that quietly edits history is worse than a missing key."""
    day.setdefault("kind", _default_kind(day.get("d", "")))
    day.setdefault("topicA", "")
    day.setdefault("topicB", "")
    day.setdefault("chunks", [])
    day.setdefault("evening", None)
    return day


def _write_weeks(weeks: list[dict]) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    WEEK_PLANS_FILE.write_text(json.dumps({"weeks": weeks}, indent=2),
                               encoding="utf-8")


def _blank_day(day_name: str, day_date: date) -> dict:
    """One empty day, in full shape. Every field a person fills in starts
    empty, because a pre-filled task would be fabricated work (Rule 12).
    `kind` is the only derived field and it comes from the weekday."""
    return {
        "d": day_name,
        "date": day_date.isoformat(),
        "kind": _default_kind(day_name),
        "a": "",
        "b": "",
        "topicA": "",
        "topicB": "",
        "chunks": [],
        "evening": None,
        "note": "",
        "done": False,
    }


def _clean_points(points) -> list[str]:
    """The bullet lines under a chunk. Blank lines are dropped rather
    than stored - an empty bullet draws as a stray dot on the page."""
    if not isinstance(points, list):
        return []
    kept = [str(point).strip() for point in points if str(point).strip()]
    return kept[:MAX_POINTS_PER_CHUNK]


def _clean_chunk(chunk) -> dict | None:
    """One timed block, or None when there is nothing in it. A chunk with
    no title is dropped, not stored empty: an empty row on the page reads
    as "planned nothing", which is not the same as "not planned"."""
    if not isinstance(chunk, dict):
        return None
    title = str(chunk.get("title", "")).strip()
    if not title:
        return None
    kind = str(chunk.get("kind", "study")).strip() or "study"
    if kind not in CHUNK_KINDS:
        raise ValueError(f"chunk kind must be one of {CHUNK_KINDS}, got {kind!r}")
    return {
        "clock": str(chunk.get("clock", "")).strip(),
        "kind": kind,
        "title": title,
        "points": _clean_points(chunk.get("points")),
    }


def _clean_evening(evening) -> dict | None:
    """The Track B hour. None when the day has no evening block at all -
    a Saturday, or a day whose evening went to interview prep instead."""
    if not isinstance(evening, dict):
        return None
    title = str(evening.get("title", "")).strip()
    if not title:
        return None
    return {"title": title, "points": _clean_points(evening.get("points"))}


def _normalise_day(day) -> dict:
    """Force one incoming day into the shape this file promises.
    Unknown keys are dropped on purpose: the page round-trips whole day
    objects back on save, so anything not named here would live in the
    file forever without a single reader knowing it was there."""
    if not isinstance(day, dict):
        raise ValueError("each day must be an object")
    kind = str(day.get("kind", "")).strip() or _default_kind(str(day.get("d", "")))
    if kind not in DAY_KINDS:
        raise ValueError(f"day kind must be one of {DAY_KINDS}, got {kind!r}")
    chunks = [c for c in (_clean_chunk(raw) for raw in (day.get("chunks") or [])) if c]
    if len(chunks) > MAX_CHUNKS_PER_DAY:
        raise ValueError(
            f"a day holds at most {MAX_CHUNKS_PER_DAY} chunks, got {len(chunks)}")
    return {
        "d": str(day.get("d", "")).strip(),
        "date": str(day.get("date", "")).strip(),
        "kind": kind,
        "a": str(day.get("a", "")).strip(),
        "b": str(day.get("b", "")).strip(),
        "topicA": str(day.get("topicA", "")).strip(),
        "topicB": str(day.get("topicB", "")).strip(),
        "chunks": chunks,
        "evening": _clean_evening(day.get("evening")),
        "note": str(day.get("note", "")).strip(),
        "done": bool(day.get("done", False)),
    }


def add_week(start: str, focus_a: str = "", focus_b: str = "") -> dict:
    """Add one week starting on `start` (YYYY-MM-DD, ideally a Monday).
    Seven days are built with real dates; every field a human fills in
    starts empty, because a pre-filled task would be fabricated work."""
    try:
        start_date = date.fromisoformat((start or "").strip())
    except ValueError:
        raise ValueError(f"start must be YYYY-MM-DD, got {start!r}") from None

    weeks = read_weeks()
    week = {
        "id": uuid.uuid4().hex[:12],
        "num": len(weeks) + 1,
        "start": start_date.isoformat(),
        "focusA": (focus_a or "").strip(),
        "focusB": (focus_b or "").strip(),
        "days": [
            _blank_day(DAY_NAMES[offset], start_date + timedelta(days=offset))
            for offset in range(7)
        ],
    }
    weeks.append(week)
    _write_weeks(weeks)
    return week


def _find_week(weeks: list[dict], week_id: str) -> dict:
    for week in weeks:
        if week["id"] == week_id:
            return week
    raise NoSuchWeek(f"no week with id '{week_id}'")


def current_week(today=None) -> dict | None:
    """The week whose Mon..Sun window contains today, or None when no
    planned week covers today. None means 'nothing planned', which is
    a fact worth showing, not a gap to fill."""
    today = today or _today()
    if isinstance(today, str):
        today = date.fromisoformat(today)
    for week in read_weeks():
        start = date.fromisoformat(week["start"])
        if start <= today <= start + timedelta(days=6):
            return week
    return None


def toggle_day(week_id: str, day_date: str) -> dict:
    """Flip one day's done flag and return the updated day. A date that
    is not one of this week's seven is refused rather than ignored -
    silently flipping the wrong day would be worse than failing."""
    weeks = read_weeks()
    week = _find_week(weeks, week_id)
    wanted = date.fromisoformat(day_date).isoformat()
    for day in week["days"]:
        if day["date"] == wanted:
            day["done"] = not day["done"]
            _write_weeks(weeks)
            return day
    raise ValueError(f"'{day_date}' is not a day of week {week_id}")


def save_week(week_id: str, days: list[dict] | None = None,
              focus_a: str | None = None,
              focus_b: str | None = None) -> dict:
    """Overwrite the editable parts of a week. Only the arguments that
    are actually passed change anything, so a caller updating just the
    focus lines cannot wipe the days by accident."""
    weeks = read_weeks()
    week = _find_week(weeks, week_id)
    if days is not None:
        week["days"] = [_normalise_day(day) for day in days]
    if focus_a is not None:
        week["focusA"] = focus_a
    if focus_b is not None:
        week["focusB"] = focus_b
    _write_weeks(weeks)
    return week


def delete_week(week_id: str) -> None:
    weeks = read_weeks()
    kept = [w for w in weeks if w["id"] != week_id]
    if len(kept) == len(weeks):
        raise NoSuchWeek(f"no week with id '{week_id}'")
    _write_weeks(kept)


def main() -> None:
    weeks = read_weeks()
    print("WEEK PLANS")
    print("=" * 50)
    if not weeks:
        print("  No weeks planned yet.")
        return
    current = current_week()
    for week in weeks:
        marker = " <- this week" if current and week["id"] == current["id"] else ""
        print(f"  Week {week['num']}: w/c {week['start']}{marker}")
        print(f"    A: {week['focusA'] or '(no focus set)'}")
        print(f"    B: {week['focusB'] or '(no focus set)'}")


if __name__ == "__main__":
    main()

