"""The shared knowledge base: real documents, saved locally, searchable
by meaning - not by fine-tuning a model on them.

WHY THIS EXISTS RATHER THAN FINE-TUNING
    A fine-tuned model can be asked what it "learned" and answer with
    something that sounds right and is not - it blends and paraphrases
    training data rather than quoting it. This project's whole ethos is
    "every number traces to a source file" (C4). Retrieval does that
    directly: a search returns the actual passage that was actually
    read, with the actual source it came from, every time.

HOW IT WORKS, IN THREE STEPS
    1. Something gets fetched (a web page, a document from Dump/) and
       broken into chunks - a few paragraphs each.
    2. Each chunk is turned into a vector by the local embedding model
       (call_the_local_model.embed) and stored next to its text.
    3. A search turns the query into the same kind of vector and
       returns the chunks whose vectors are closest to it - cosine
       similarity, computed in plain Python. No vector database, no
       new dependency: a personal knowledge base is a few thousand
       rows at most, and SQLite already holds records elsewhere in
       this project (C1 allows it explicitly).

WHERE THINGS LIVE
    Knowledge_Base/Notes/<topic>.md    the source material, human-
                                       readable, one file per topic,
                                       Obsidian-valid (C7)
    Knowledge_Base/chunks.sqlite        the search index over those
                                       notes - chunk text, its vector,
                                       and which note and source it
                                       came from

NEVER FABRICATED
    add_a_note() always requires at least one source URL or file path.
    A note with no source is not knowledge, it is a guess with a
    heading, and this file refuses to write one.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Shared_By_All_Screens
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "Shared_By_All_Agents"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from call_the_local_model import embed                                # noqa: E402

STORE = HERE / "Knowledge_Base"
NOTES = STORE / "Notes"
DB = STORE / "chunks.sqlite"

CHUNK_WORDS = 180   # a few paragraphs - small enough for a sharp match,
                    # big enough to still make sense read on its own


class NoSourceGiven(Exception):
    """Raised when a note is about to be written with nothing behind it."""


def _connect() -> sqlite3.Connection:
    STORE.mkdir(parents=True, exist_ok=True)
    NOTES.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            note_file TEXT NOT NULL,
            topic TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            source TEXT NOT NULL,
            added_at TEXT NOT NULL,
            vector TEXT NOT NULL
        )
    """)
    return conn


def _slug(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", topic.strip().lower()).strip("_")
    return slug or "untitled"


def _extract_list_field(frontmatter_text: str, field: str) -> list[str]:
    """Read a YAML `field:\n  - item` block back out of a frontmatter
    string this same function wrote, so an append can merge into it
    instead of overwriting it (only the first entry survived before).
    """
    values: list[str] = []
    in_field = False
    for line in frontmatter_text.splitlines():
        if line.strip() == f"{field}:":
            in_field = True
            continue
        if in_field:
            if line.startswith("  - "):
                values.append(line[4:].strip())
            else:
                break
    return values


def _extract_scalar_field(frontmatter_text: str, field: str) -> str | None:
    for line in frontmatter_text.splitlines():
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return None


def _split_into_chunks(text: str, words_per_chunk: int = CHUNK_WORDS) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + words_per_chunk])
           for i in range(0, len(words), words_per_chunk)] if words else []


def add_a_note(topic: str, content: str, sources: list[str], *,
               tags: list[str] | None = None, written_by: str = "local model") -> dict:
    """Save real material under one topic, chunked and embedded for
    search. Every note keeps its sources in its own frontmatter, so
    opening the file answers "where did this come from" without this
    module at all.
    """
    sources = [s for s in (sources or []) if s and s.strip()]
    if not sources:
        raise NoSourceGiven(
            f"add_a_note('{topic}', ...) was given no sources. A note with "
            "no source is a guess with a heading, and this file refuses to "
            "write one."
        )

    content = (content or "").strip()
    if not content:
        raise ValueError("a note needs some content")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    slug = _slug(topic)
    NOTES.mkdir(parents=True, exist_ok=True)
    note_path = NOTES / f"{slug}.md"

    is_new = not note_path.exists()

    if is_new:
        added_at = now
        all_sources = list(sources)
        all_tags = list(tags or [])
        existing_body = ""
    else:
        existing_text = note_path.read_text(encoding="utf-8")
        parts = existing_text.split("---", 2)
        old_frontmatter, existing_body = (parts[1], parts[2]) if len(parts) == 3 else ("", existing_text)
        added_at = _extract_scalar_field(old_frontmatter, "added_at") or now
        old_sources = _extract_list_field(old_frontmatter, "sources")
        all_sources = old_sources + [s for s in sources if s not in old_sources]
        old_tags = _extract_list_field(old_frontmatter, "tags")
        all_tags = old_tags + [t for t in (tags or []) if t not in old_tags]

    frontmatter = [
        "---", f"title: {topic}", "type: knowledge-note",
        f"added_at: {added_at}", f"written_by: {written_by}",
        "sources:",
    ] + [f"  - {s}" for s in all_sources]
    if not is_new:
        frontmatter += [f"updated_at: {now}"]
    if all_tags:
        frontmatter += ["tags:"] + [f"  - {t}" for t in all_tags]
    frontmatter += ["---", ""]

    # Every entry names its own source inline, right under its heading -
    # so the note is self-describing in the body even if the frontmatter
    # list above is ever read out of context (a search hit, an export).
    source_line = "**Source:** " + "; ".join(sources)
    entry = f"\n## Added {now}\n\n{source_line}\n\n{content}\n"

    new_text = "\n".join(frontmatter) + "\n" + existing_body.lstrip("\n") + entry
    note_path.write_text(new_text, encoding="utf-8")

    conn = _connect()
    chunks_added = 0
    try:
        for chunk in _split_into_chunks(content):
            result = embed(chunk)
            if not result["has_data"]:
                continue   # Ollama unreachable - the note is still saved
                          # on disk, just not searchable until re-indexed
            conn.execute(
                "INSERT INTO chunks (note_file, topic, chunk_text, source, added_at, vector) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (note_path.name, topic, chunk, sources[0], now, json.dumps(result["vector"])),
            )
            chunks_added += 1
        conn.commit()
    finally:
        conn.close()

    # A display path only - never used to open the file again, so
    # falling back to the absolute path (a different drive on Windows,
    # or a test double outside PROJECT_ROOT) is fine rather than a
    # crash over cosmetics.
    try:
        shown_as = os.path.relpath(note_path, PROJECT_ROOT)
    except ValueError:
        shown_as = str(note_path)

    return {"has_data": True, "note_file": shown_as,
           "chunks_added": chunks_added, "is_new_note": is_new}


def search(query: str, most: int = 5) -> dict:
    """The chunks whose meaning is closest to the query, newest ties
    broken toward the highest score. has_data: False, never an empty
    list dressed up as a real "nothing found" - those are different
    facts (Ollama unreachable vs. genuinely no match).
    """
    result = embed(query)
    if not result["has_data"]:
        return {"has_data": False, "note": result["note"], "matches": []}

    query_vector = result["vector"]
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT topic, chunk_text, source, note_file, vector FROM chunks"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"has_data": True, "matches": [],
               "note": "The knowledge base is empty - nothing has been added yet."}

    scored = []
    for topic, chunk_text, source, note_file, vector_json in rows:
        score = _cosine_similarity(query_vector, json.loads(vector_json))
        scored.append({"topic": topic, "text": chunk_text, "source": source,
                       "note_file": note_file, "score": round(score, 4)})

    scored.sort(key=lambda r: r["score"], reverse=True)
    return {"has_data": True, "matches": scored[:most]}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def how_big_is_it() -> dict:
    """Counts for a dashboard, later. No model call."""
    conn = _connect()
    try:
        chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        topics = conn.execute("SELECT DISTINCT topic FROM chunks").fetchall()
    finally:
        conn.close()
    note_count = len(list(NOTES.glob("*.md"))) if NOTES.exists() else 0
    return {"notes": note_count, "chunks": chunk_count, "topics": sorted(t[0] for t in topics)}


def main() -> None:
    info = how_big_is_it()
    print("KNOWLEDGE BASE")
    print()
    print(f"  {info['notes']} note(s), {info['chunks']} searchable chunk(s)")
    if info["topics"]:
        print("  topics: " + ", ".join(info["topics"]))
    else:
        print("  empty - nothing has been added yet")


if __name__ == "__main__":
    main()
