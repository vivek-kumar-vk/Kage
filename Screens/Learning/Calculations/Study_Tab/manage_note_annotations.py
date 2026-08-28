"""Annotations a reader leaves on a Knowledge_Base note.

WHAT THIS FILE OWNS
    `Saved_Records/note_annotations.json` - one entry per highlighted
    passage: which note, the exact quoted text, and what the reader
    wanted to say about it. Created from the Learning screen's markdown
    reader (select text -> right-click -> Add note).

WHY THE QUOTE IS STORED, NOT AN OFFSET
    Markdown renders differently as the renderer improves; character
    offsets would silently drift and start highlighting the wrong words.
    The exact quoted string is stable across re-renders, so the page can
    always find the same words again. A quote that appears more than
    once is disambiguated by `occurrence` (0-based index of the match),
    decided at save time by whoever saw the selection.

WHY JSON, NOT CSV
    One note can carry many annotations, each with a free-text body;
    there is no second reader promising columns. Same reasoning as
    manage_week_plans.py.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Study_Tab\\manage_note_annotations.py
"""

from __future__ import annotations

import json
import sys
import uuid
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
ANNOTATIONS_FILE = SAVED_RECORDS / "note_annotations.json"

MAX_NOTE_CHARS = 2000
MAX_QUOTE_CHARS = 600


class NoSuchAnnotation(Exception):
    """Raised by delete_annotation() for an id that is not in the file."""


class DuplicateAnnotation(Exception):
    """Raised by add_annotation() when the exact same annotation - same
    note, quote, occurrence and text - is already stored (Phase-1 CS-2).
    `.existing` carries the entry already on file, so the caller can
    answer with it instead of filing a second identical highlight."""
    def __init__(self, existing: dict):
        super().__init__(
            "identical annotation already stored "
            f"(id {existing.get('id')})")
        self.existing = existing


def _read_all() -> list[dict]:
    if not ANNOTATIONS_FILE.exists():
        return []
    return json.loads(ANNOTATIONS_FILE.read_text(encoding="utf-8"))


def _write_all(items: list[dict]) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    ANNOTATIONS_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def annotations_for(note_file: str) -> list[dict]:
    """Every annotation on one note, oldest first."""
    return [a for a in _read_all() if a.get("note_file") == note_file]


def add_annotation(note_file: str, quote: str, note: str,
                   occurrence: int = 0) -> dict:
    """Attach `note` to `quote` (the exact selected text) on `note_file`.
    Empty quotes or notes are refused - an annotation pointing at
    nothing, or saying nothing, is not worth storing.

    An EXACT repeat of an annotation already stored raises
    DuplicateAnnotation carrying that entry (Phase-1 CS-2): a retried
    save must never leave two identical highlights on one passage."""
    quote = (quote or "").strip()
    note = (note or "").strip()
    if not quote:
        raise ValueError("an annotation needs the selected text")
    if not note:
        raise ValueError("an annotation needs a note")
    kept_quote = quote[:MAX_QUOTE_CHARS]
    kept_note = note[:MAX_NOTE_CHARS]
    kept_occurrence = max(0, int(occurrence or 0))
    items = _read_all()
    for a in items:
        if ((a.get("note_file") or "").strip() == (note_file or "").strip()
                and a.get("quote") == kept_quote
                and int(a.get("occurrence") or 0) == kept_occurrence
                and a.get("note") == kept_note):
            raise DuplicateAnnotation(a)
    entry = {
        "id": uuid.uuid4().hex[:12],
        "note_file": note_file,
        "quote": kept_quote,
        "occurrence": kept_occurrence,
        "note": kept_note,
        "created_at": datetime.now(IST).isoformat(timespec="seconds"),
    }
    items.append(entry)
    _write_all(items)
    return entry


def delete_annotation(annotation_id: str) -> None:
    items = _read_all()
    kept = [a for a in items if a.get("id") != annotation_id]
    if len(kept) == len(items):
        raise NoSuchAnnotation(f"no annotation with id '{annotation_id}'")
    _write_all(kept)


def main() -> None:
    items = _read_all()
    print("NOTE ANNOTATIONS")
    print("=" * 50)
    if not items:
        print("  No annotations yet - highlight something in the reader.")
        return
    by_note: dict[str, int] = {}
    for a in items:
        by_note[a["note_file"]] = by_note.get(a["note_file"], 0) + 1
    for note_file, count in sorted(by_note.items()):
        print(f"  {note_file}: {count} annotation(s)")


if __name__ == "__main__":
    main()
