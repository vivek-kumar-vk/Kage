"""Study modules - Knowledge_Base notes written as numbered tasks.

WHAT THIS FILE OWNS
    The module contract and its parser. A study module is an ordinary
    note whose front matter carries `type: study-module`, optionally
    bound to a study-board topic with `topic_id:`. Its body is split by
    `## Task <n>` headings; inside each task's body, list items that
    begin `Q<task>.<num>` are that task's questions, and the question id
    is kept verbatim (`Q2.10` stays `Q2.10`). Everything here is regex
    and string work - Tier 0, no model call, no file writes.

WHY THE PARSER IS THE CONTRACT
    The format exists only because this file can read it. A note with
    `type: study-module` but no `## Task 1` heading is malformed, not
    empty - callers must say so plainly rather than render a module with
    zero tasks and pretend it was meant to be that way. A note without
    the type marker is an ordinary note and never appears as a module,
    no matter how its body happens to look.

WHY MARKDOWN IS ONLY READ THROUGH match_notes_to_topics
    That file already validates names against the notes directory -
    traversal-proof, extension-checked. Opening a second door into the
    shared Knowledge_Base would be two places to get security wrong
    instead of one (C8's spirit applied to a sibling tab).

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Study_Tab\\read_study_modules.py
"""

from __future__ import annotations

import re
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

import manage_recall_schedule as recall          # noqa: E402  (note list)
import match_notes_to_topics as matcher          # noqa: E402  (the only door)

MODULE_TYPE = "study-module"

# A task starts here: "## Task 3 — Monitor inputs and the fishbucket".
# The number is the identity (task-3); whatever follows the number on
# the line is the title, separators included so nothing is rewritten.
TASK_HEADING_RE = re.compile(r"^##\s+Task\s+(\d+)\s*:?\s*(.*)$")

# A question line: "- Q3.2 Which file records what Splunk has read?".
# Group 1 is the id, verbatim - Q2.10 must not become Q2.1 + a zero.
QUESTION_LINE_RE = re.compile(r"^\s*[-*]\s+(Q\d+\.\d+)\b\.?:?\s*(.*)$")


def frontmatter_of(text: str) -> dict:
    """The key: value lines of the note's front matter block, the same
    simple shape manage_recall_schedule reads - title/added_at there,
    type/topic_id here."""
    parts = text.split("---", 2)
    block = parts[1] if len(parts) >= 3 else ""
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip()
    return out


def is_module(note_file: str) -> bool:
    """True when the note's front matter carries the module type.
    Nothing else about the body matters for this answer."""
    text = matcher.read_note_markdown(note_file)
    return frontmatter_of(text).get("type") == MODULE_TYPE


def parse_module(note_file: str) -> dict:
    """One module, parsed. Raises ValueError for a note that is not a
    module at all; reports malformed=True for one that claims to be but
    has no Task 1 to start from."""
    text = matcher.read_note_markdown(note_file)
    meta = frontmatter_of(text)
    if meta.get("type") != MODULE_TYPE:
        raise ValueError(f"'{note_file}' is not a {MODULE_TYPE} note")

    # Body only - everything after the closing front-matter fence.
    parts = text.split("---", 2)
    body = parts[2] if len(parts) >= 3 else text

    tasks: list[dict] = []
    current: dict | None = None
    for line in body.splitlines():
        heading = TASK_HEADING_RE.match(line)
        if heading:
            current = {"id": f"task-{heading.group(1)}",
                       "number": int(heading.group(1)),
                       "title": heading.group(2).strip(" \t—-"),
                       "questions": []}
            tasks.append(current)
        elif current is not None:
            question = QUESTION_LINE_RE.match(line)
            if question:
                current["questions"].append(
                    {"id": question.group(1),
                     "text": question.group(2).strip()})

    return {
        "note_file": note_file,
        "topic_id": meta.get("topic_id") or None,
        "malformed": not any(t["number"] == 1 for t in tasks),
        "tasks": tasks,
    }


def all_modules() -> list[dict]:
    """Every real note that parses as a module, malformed ones included
    (flagged). Empty list today, honestly - no module notes exist yet."""
    out = []
    for note in recall.all_notes():
        try:
            if is_module(note["note_file"]):
                out.append(parse_module(note["note_file"]))
        except ValueError:
            continue
    return out


def find_module_for_topic(topic: dict) -> dict | None:
    """Which module serves one study-board topic, in this order and no
    other: an explicit `topic_id` binding first; then the token-overlap
    best note, but only if it really is a module - a topic must never
    claim an ordinary note just because the words line up."""
    explicit = [m for m in all_modules() if m["topic_id"] == topic.get("id")]
    if explicit:
        return explicit[0]

    best = matcher.best_note_for(topic.get("topic", ""))
    if best and is_module(best["note_file"]):
        return parse_module(best["note_file"])
    return None


def main() -> None:
    print("STUDY MODULES")
    print("=" * 50)
    modules = all_modules()
    notes = recall.all_notes()
    print(f"  {len(notes)} note(s) in the knowledge base, "
          f"{len(modules)} study module(s)")
    for m in modules:
        state = ("malformed - no Task 1"
                 if m["malformed"]
                 else f"{len(m['tasks'])} task(s)"
                      + (f", bound to {m['topic_id']}" if m["topic_id"] else ""))
        print(f"  {m['note_file']}: {state}")
    if not modules:
        print("  No module notes yet. The Modules list will say 0 of 32 -")
        print("  that gap is the to-do list, not something to fill with samples.")


if __name__ == "__main__":
    main()
