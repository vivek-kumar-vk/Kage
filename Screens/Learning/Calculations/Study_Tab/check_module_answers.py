"""Answer checking for study-module questions - right, wrong, or no key.

WHAT THIS FILE OWNS
    `Saved_Records/module_answer_keys.json`, one object per note file,
    keyed by question id:

        {"splunk_inputs.md": {
            "Q1.1": {"answer": "8089",
                     "accept": ["port 8089"],
                     "why": "one line shown after a correct answer"}}}

    check_one_answer() compares a typed string against the key. It
    returns correct / not-correct / no-key. It NEVER returns the stored
    answer - the reader page calls this and shows only the verdict.

WHY THE KEY LIVES HERE AND NOT IN THE NOTE
    If the answer sat under the heading in the markdown, the reader
    would render it and the answer box would be theatre. Keeping keys
    server-side means the page source never carries them either.

WHY THE COMPARISON IS THIS DUMB
    Lowercase both sides, collapse whitespace runs, strip surrounding
    punctuation, compare against `answer` plus every string in `accept`.
    That is the whole algorithm - Tier 0 (Rule 3), predictable, and
    honest about being a spelling-level check rather than understanding.
    A question with no entry in the key is NOT wrong: the reply says
    there is no key, because an honest "cannot check" beats a confident
    "wrong".

WHY JSON, NOT CSV
    Hand-editable, nested per question, no second reader promising
    columns. Same reasoning as manage_week_plans.py.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Study_Tab\\check_module_answers.py
"""

from __future__ import annotations

import json
import string
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
        sys.path.insert(0, str(_group))         # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAVED_RECORDS = SCREEN / "Saved_Records"
KEYS_FILE = SAVED_RECORDS / "module_answer_keys.json"


def _read_all() -> dict:
    if not KEYS_FILE.exists():
        return {}
    return json.loads(KEYS_FILE.read_text(encoding="utf-8"))


def normalize(typed: str) -> str:
    """Lowercase, collapse whitespace runs, strip surrounding
    punctuation. Inner punctuation stays - '8089/tcp' and 'port 8089'
    are different strings, and the accept list is how variants are
    blessed, not a smarter matcher."""
    collapsed = " ".join((typed or "").lower().split())
    return collapsed.strip(string.punctuation + "\\u201c\\u201d\\u2018\\u2019")


def key_for(note_file: str, question_id: str) -> dict | None:
    """The stored key for one question, or None. Reading it directly is
    for maintenance tools only - anything serving the page must go
    through check_one_answer(), which never echoes it back."""
    return _read_all().get(note_file, {}).get(question_id)


def check_one_answer(note_file: str, question_id: str, typed: str) -> dict:
    """The only verdict the page gets. Shapes:
      {has_key: false, correct: null}          - no key, cannot check
      {has_key: true,  correct: false}         - wrong, no hints
      {has_key: true,  correct: true, why: ..} - right, explain why
    """
    question_id = (question_id or "").strip()
    typed = (typed or "").strip()
    if not note_file or not question_id:
        raise ValueError("checking needs a note file and a question id")
    if not typed:
        raise ValueError("an empty answer cannot be checked")

    key = key_for(note_file, question_id)
    if not key:
        return {"has_key": False, "correct": None}

    candidates = [key.get("answer", "")] + list(key.get("accept", []))
    wanted = {normalize(c) for c in candidates if c}
    if normalize(typed) in wanted:
        return {"has_key": True, "correct": True,
                "why": key.get("why") or None}
    return {"has_key": True, "correct": False}


def main() -> None:
    keys = _read_all()
    print("MODULE ANSWER KEYS")
    print("=" * 50)
    if not keys:
        print(f"  {KEYS_FILE.name} is empty - no question has a key yet.")
        print("  Keys are typed by hand into that file, one object per note.")
        return
    for note_file, questions in sorted(keys.items()):
        print(f"  {note_file}: {len(questions)} keyed question(s)")


if __name__ == "__main__":
    main()
