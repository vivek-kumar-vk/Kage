"""Which Knowledge_Base note belongs to a study topic - decided by
counting shared words, never by guessing.

WHAT THIS FILE OWNS
    The Tier-0 bridge between a planned topic ("Splunk - pipeline") and
    the markdown note to open for it. Scores every note title against
    the topic with plain token overlap: shared meaningful words, weighted
    by rarity across the note titles so "architecture" counts for less
    than "dynatrace". No model call, no file writes - a lookup that can
    be explained in one sentence.

WHY THE THRESHOLD IS PUBLIC
    A best score below MATCH_THRESHOLD returns None, and the page says
    "no note found" instead of opening a half-related note. A wrong
    match reads as truth; an honest miss reads as work to do.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Study_Tab\\match_notes_to_topics.py
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

import manage_recall_schedule as recall         # noqa: E402  (owns NOTES_DIR)

NOTES_DIR = recall.NOTES_DIR

# Best-score floor. Tuned on the real library: "Dynatrace architecture"
# vs topic "Dynatrace - OneAgent" shares the rare word dynatrace and
# clears it comfortably; unrelated topics land far below it.
MATCH_THRESHOLD = 34

_STOPWORDS = frozenset("""
a an and are as at by for from in into is it of on or that the to with
what how why when which this these those their its his her
""".split())

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    """Lowercased words minus stopwords. Numbers stay - 'OneAgent v7'
    should keep its version."""
    return set(_WORD_RE.findall((text or "").lower())) - _STOPWORDS


def notes_index() -> list[dict]:
    """Every KB note's matching tokens, via the recall module's own
    front-matter reader so titles come from one place."""
    out = []
    for note in recall.all_notes():
        tokens = _tokens(note["title"]) | _tokens(Path(note["note_file"]).stem)
        out.append({**note, "_tokens": tokens})
    return out


def best_note_for(topic_text: str) -> dict | None:
    """The highest-scoring note for a topic string, or None below the
    threshold. Score = sum over shared tokens of 100 / (docs containing
    it), capped per token at 50 so one ultra-rare word cannot dominate
    three solid matches."""
    topic_tokens = _tokens(topic_text)
    if not topic_tokens:
        return None
    index = notes_index()
    if not index:
        return None

    doc_freq: dict[str, int] = {}
    for entry in index:
        for tok in entry["_tokens"]:
            doc_freq[tok] = doc_freq.get(tok, 0) + 1

    best = None
    best_score = 0
    for entry in index:
        shared = topic_tokens & entry["_tokens"]
        score = sum(min(50, 100 // max(1, doc_freq.get(tok, 1)))
                    for tok in shared)
        if score > best_score:
            best_score = score
            best = {"note_file": entry["note_file"], "title": entry["title"],
                    "score": score}
    if best is None or best_score < MATCH_THRESHOLD:
        return None
    return best


def read_note_markdown(note_file: str) -> str:
    """The raw markdown of one note. The name is validated against the
    notes directory itself - no separators, no traversal, no absolute
    paths - because a reader feature must never become a file reader."""
    candidate = (NOTE_SAFE_RE.sub("", note_file or "")).strip()
    if not candidate or candidate != note_file:
        raise ValueError("bad note name")
    path = (NOTES_DIR / candidate).resolve()
    if path.parent != NOTES_DIR.resolve() or path.suffix.lower() != ".md":
        raise ValueError("bad note name")
    if not path.exists():
        raise FileNotFoundError(f"'{candidate}' is not in {NOTES_DIR}")
    return path.read_text(encoding="utf-8")


NOTE_SAFE_RE = re.compile(r"[^A-Za-z0-9._ \-]")


def main() -> None:
    print("TOPIC -> NOTE MATCHER")
    print("=" * 50)
    samples = [
        "Splunk - parsing and indexing pipeline",
        "Dynatrace - OneAgent",
        "GitHub - how to commit",
        "something nothing nowhere",
    ]
    for topic in samples:
        match = best_note_for(topic)
        if match:
            print(f"  {topic!r} -> {match['note_file']} "
                  f"(score {match['score']})")
        else:
            print(f"  {topic!r} -> no note above the threshold")


if __name__ == "__main__":
    main()
