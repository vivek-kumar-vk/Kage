"""Spaced repetition over real material - the notes Overnight_Research_Agent
already wrote into the shared Knowledge_Base, each one traced to a source
(C4). This file invents no content of its own; it only decides, from what
is actually there, what is due today.

WHY A LEITNER SYSTEM, NOT SOMETHING FANCIER
    Five boxes, one interval each. A note that is remembered moves up a
    box and is asked about less often; a note that is forgotten drops
    back to the shortest interval. It is the same idea as a proper SM-2
    algorithm with the "ease factor" removed - simple enough to read in
    one sitting, and there is no real cost to that simplicity yet because
    nothing has been reviewed even once.

WHY THIS FILE OWNS THE REVIEW STATE, NOT THE KNOWLEDGE BASE
    Knowledge_Base/ is shared - Overnight_Research_Agent writes notes into
    it too, and a screen only ever owns its own Saved_Records (C8's spirit
    applied to a shared folder). So `recall_reviews.csv` lives here, in
    Learning, and the notes themselves are read but never edited.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Recall_Tab\\manage_recall_schedule.py
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
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

NOTES_DIR = PROJECT_ROOT / "Shared_By_All_Screens" / "Knowledge_Base" / "Notes"
SAVED_RECORDS = SCREEN / "Saved_Records"
REVIEWS_FILE = SAVED_RECORDS / "recall_reviews.csv"
COLUMNS = ["date", "note_file", "topic", "remembered", "box_before", "box_after", "next_due"]

# Box 0 is "never reviewed" and is not in this table - it is always due.
# Box 5 is not a ceiling on remembering, it is where the interval stops
# growing; nothing here claims a note is "mastered forever".
BOX_INTERVAL_DAYS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}
MAX_BOX = 5


class NoSuchNote(Exception):
    """Raised when mark_reviewed() is given a note_file that is not
    actually sitting in Knowledge_Base/Notes."""


def _today() -> date:
    return datetime.now(IST).date()


def _read_note_frontmatter(path: Path) -> dict:
    """title and added_at only - the two fields this screen actually
    needs. Notes are written by add_and_search_the_knowledge_base.py in a
    fixed, simple shape (see that file), so a small local reader is
    enough; it does not need that file's own chunking/embedding machinery."""
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = text.split("---", 2)
    frontmatter = parts[1] if len(parts) >= 3 else ""
    out = {"title": path.stem.replace("_", " "), "added_at": None}
    for line in frontmatter.splitlines():
        if line.startswith("title:"):
            out["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("added_at:"):
            out["added_at"] = line.split(":", 1)[1].strip()
    return out


def all_notes() -> list[dict]:
    """Every real note on file, title + filename. Empty list, honestly,
    if Overnight_Research_Agent has not written any yet."""
    if not NOTES_DIR.exists():
        return []
    notes = []
    for path in sorted(NOTES_DIR.glob("*.md")):
        meta = _read_note_frontmatter(path)
        notes.append({"note_file": path.name, "title": meta["title"],
                      "added_at": meta["added_at"]})
    return notes


def _latest_review_by_note() -> dict[str, dict]:
    if not REVIEWS_FILE.exists():
        return {}
    latest: dict[str, dict] = {}
    with REVIEWS_FILE.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing = latest.get(row["note_file"])
            if existing is None or row["date"] >= existing["date"]:
                latest[row["note_file"]] = row
    return latest


@dataclass(frozen=True)
class RecallStatus:
    note_file: str
    title: str
    box: int                # 0 = never reviewed
    last_reviewed: str | None
    next_due: str | None    # None for box 0 - it has always been due
    is_due: bool


def schedule(today: date | None = None) -> list[RecallStatus]:
    """One entry per note, due-soonest first, so the Recall tab can just
    render the list top to bottom."""
    today = today or _today()
    latest = _latest_review_by_note()

    out = []
    for note in all_notes():
        review = latest.get(note["note_file"])
        if review is None:
            out.append(RecallStatus(note["note_file"], note["title"], 0,
                                     None, None, True))
            continue
        box = int(review["box_after"])
        next_due = review["next_due"]
        out.append(RecallStatus(
            note["note_file"], note["title"], box,
            review["date"], next_due,
            date.fromisoformat(next_due) <= today,
        ))

    out.sort(key=lambda r: (not r.is_due, r.next_due or "0000-00-00"))
    return out


def notes_due(today: date | None = None) -> list[RecallStatus]:
    return [r for r in schedule(today) if r.is_due]


def mark_reviewed(note_file: str, remembered: bool, today: date | None = None) -> dict:
    if not (NOTES_DIR / note_file).exists():
        raise NoSuchNote(f"'{note_file}' is not in {NOTES_DIR}")

    today = today or _today()
    latest = _latest_review_by_note()
    previous = latest.get(note_file)
    box_before = int(previous["box_after"]) if previous else 0

    box_after = min(MAX_BOX, box_before + 1) if remembered else 1
    next_due = today + timedelta(days=BOX_INTERVAL_DAYS[box_after])
    meta = _read_note_frontmatter(NOTES_DIR / note_file)

    row = {
        "date": today.isoformat(), "note_file": note_file,
        "topic": meta["title"], "remembered": remembered,
        "box_before": box_before, "box_after": box_after,
        "next_due": next_due.isoformat(),
    }
    _append_row(row)
    return row


def _append_row(row: dict) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    is_new = not REVIEWS_FILE.exists() or REVIEWS_FILE.stat().st_size == 0
    with REVIEWS_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if is_new:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    due = notes_due()
    total = len(all_notes())
    print("RECALL")
    print("=" * 50)
    print(f"  {total} note(s) in the knowledge base, {len(due)} due today")
    print()
    for r in due[:15]:
        state = "never reviewed" if r.box == 0 else f"box {r.box}, due {r.next_due}"
        print(f"  {r.title:<50} {state}")
    if not due:
        print("  Nothing due. Nothing to fabricate here either.")


if __name__ == "__main__":
    main()
