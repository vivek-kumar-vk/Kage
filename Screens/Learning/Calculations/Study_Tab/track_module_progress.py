"""Progress a reader has made inside one study module.

WHAT THIS FILE OWNS
    `Saved_Records/module_progress.json` - one object per module note:

        {"<note_file>.md": {
            "tasks":   {"task-1": {"done": true, "done_at": "2026-09-01"}},
            "answers": {"Q1.1": {"attempts": 2, "correct": true,
                                 "first_correct_at": "2026-09-01"}}}}

    toggle_task() flips a task's done state; record_attempt() logs one
    answer attempt; counts_for() reports tasks done against a total.

WHY THE PERCENTAGE IS NEVER STORED
    The total comes from the note, counted live by whoever calls
    counts_for(). If the note gains a task tomorrow, a stored percentage
    would quietly become a lie - a live division cannot (C4).

WHY JSON, NOT CSV
    Hand-editable, nested per task/question, no second reader promising
    columns. Same reasoning as manage_week_plans.py. Starts as {} and
    nothing is pre-ticked - empty progress is the truth on day one.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Study_Tab\\track_module_progress.py
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
PROGRESS_FILE = SAVED_RECORDS / "module_progress.json"


class NoSuchModule(Exception):
    """Raised for progress calls naming a note with no entry yet -
    callers decide whether that is fine or worth surfacing."""


def _today() -> str:
    return datetime.now(IST).date().isoformat()


def _read_all() -> dict:
    if not PROGRESS_FILE.exists():
        return {}
    return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))


def _write_all(data: dict) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _entry_for(data: dict, note_file: str) -> dict:
    """The per-note bucket, created honestly empty when absent."""
    return data.setdefault(note_file, {"tasks": {}, "answers": {}})


def progress_for(note_file: str) -> dict:
    """One module's stored progress, normalized so callers never get a
    half-shaped dict back."""
    raw = _read_all().get(note_file, {})
    return {"tasks": raw.get("tasks", {}), "answers": raw.get("answers", {})}


def toggle_task(note_file: str, task_id: str) -> dict:
    """Flip one task's done state. Un-ticking also clears the date - a
    done_at on something not done would be a record of nothing."""
    task_id = (task_id or "").strip()
    if not note_file or not task_id:
        raise ValueError("toggling needs a note file and a task id")

    data = _read_all()
    entry = _entry_for(data, note_file)
    now_done = not entry["tasks"].get(task_id, {}).get("done", False)
    entry["tasks"][task_id] = (
        {"done": True, "done_at": _today()} if now_done else {"done": False})
    _write_all(data)
    return {"task_id": task_id, "done": now_done}


def record_attempt(note_file: str, question_id: str,
                   correct: bool) -> dict:
    """Log one answer attempt. first_correct_at is stamped once and
    never moved - when it was first solved is a fact about the past."""
    question_id = (question_id or "").strip()
    if not note_file or not question_id:
        raise ValueError("recording needs a note file and a question id")

    data = _read_all()
    entry = _entry_for(data, note_file)
    record = entry["answers"].setdefault(question_id,
                                         {"attempts": 0, "correct": False})
    record["attempts"] += 1
    record["correct"] = bool(correct) or bool(record.get("correct"))
    if correct and not record.get("first_correct_at"):
        record["first_correct_at"] = _today()
    _write_all(data)
    return record


def counts_for(note_file: str, tasks_in_note: int) -> dict:
    """Done over total, both computed now - the caller passes how many
    tasks the note actually has, so the count can never drift from it."""
    tasks = progress_for(note_file)["tasks"]
    done = sum(1 for t in tasks.values() if t.get("done"))
    return {"done": done, "total": int(tasks_in_note)}


def main() -> None:
    data = _read_all()
    print("MODULE PROGRESS")
    print("=" * 50)
    if not data:
        print(f"  {PROGRESS_FILE.name} holds nothing yet - nothing "
              "pre-ticked, which is the honest state.")
        return
    for note_file, entry in sorted(data.items()):
        done = sum(1 for t in entry.get("tasks", {}).values()
                   if t.get("done"))
        answered = sum(1 for a in entry.get("answers", {}).values()
                       if a.get("correct"))
        print(f"  {note_file}: {done} task(s) ticked, "
              f"{answered} question(s) answered correctly")


if __name__ == "__main__":
    main()