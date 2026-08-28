"""The only writer to any agent's Memory/ folder.

Two kinds of memory, deliberately separate, because they answer
different questions and rot at different speeds:

    what_i_learned.md   durable facts, in English, appended, that a
                        person can read and correct with a text editor.
    what_happened.csv   one row per run. Counts, not prose - what a
                        future counting tool would read to see which
                        agent is struggling.

Both live inside the agent's own folder. C8 for agents: an agent may
not read or write another agent's memory. Enforced here in code, and
by a test that reads source.

NO VECTOR STORE, ON PURPOSE
    One user, a few hundred facts. A markdown file is diffable in git,
    correctable by hand, readable in the UI, and impossible to corrupt
    invisibly. Reach for embeddings when recall genuinely fails and a
    log proves it - not before.
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Shared_By_All_Agents
PROJECT_ROOT = HERE.parent                       # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AGENTS = PROJECT_ROOT / "Agents"

HAPPENED_FILE = "what_happened.csv"


def _learned_file_name(agent_name: str) -> str:
    """Agent-prefixed, so every agent's note carries a name Obsidian's
    graph (and test_no_two_notes_share_a_name) can tell apart - a bare
    'what_i_learned.md' collided the moment a second agent wrote one."""
    return f"{agent_name}_what_i_learned.md"


HAPPENED_COLUMNS = [
    "timestamp", "ticket", "job_shape", "outcome", "steps_taken",
    "model_calls", "seconds", "notes",
    # Appended at the tail (2026-08-26, Phase-1 5.4): token counts for the
    # run, the agent-memory half of what CS-3 did for trace rows. Older
    # memory files keep their eight-column headers - a new column is added
    # by writing wider rows, never by rewriting history. A blank cell means
    # nothing was counted, which is a different fact from zero.
    "tokens_in", "tokens_out",
]

# Not a technical limit - a memory file longer than this stops being
# something a person will actually read, and unread memory is not memory.
MOST_LEARNINGS_BEFORE_CURATING = 200


class ThatIsNotYourMemory(Exception):
    """Raised when an agent reaches into another agent's folder."""


def _memory_folder(agent_name: str) -> Path:
    where = AGENTS / agent_name / "Memory"
    where.mkdir(parents=True, exist_ok=True)
    return where


def _check_it_is_your_own(calling_agent: str, target_agent: str) -> None:
    if calling_agent != target_agent:
        raise ThatIsNotYourMemory(
            f"{calling_agent} tried to touch {target_agent}'s memory. Agents "
            "do not share memory (C8). If a fact needs to cross between "
            "agents, it goes through the noticeboard and nothing else."
        )


# ---------------------------------------------------------------- remember
def remember(calling_agent: str, agent_name: str, learning: str, *,
            because: str = "", confidence: str = "observed") -> bool:
    """Write down one durable fact.

    confidence is one of:
        corrected  a human told me this directly. Highest trust.
        observed   I saw it happen in a run. Normal.
        guessed    I inferred it. Shown differently in the UI and never
                   used to skip a check.
    """
    _check_it_is_your_own(calling_agent, agent_name)

    if confidence not in ("corrected", "observed", "guessed"):
        raise ValueError(f"confidence must be corrected, observed or guessed, not {confidence}")

    learning = " ".join((learning or "").split())
    if not learning:
        raise ValueError("an empty learning is not a learning")

    where = _memory_folder(agent_name) / _learned_file_name(agent_name)
    if not where.exists():
        where.write_text(
            f"# What {agent_name} has learned\n\n"
            "Newest at the top. Written by the agent, correctable by hand. "
            "Delete anything wrong; nothing here is sacred.\n\n",
            encoding="utf-8",
        )

    existing = where.read_text(encoding="utf-8")
    if _already_said(existing, learning):
        return False

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = f"- **{stamp}** ({confidence}) {learning}"
    if because:
        entry += f"\n  - why: {' '.join(because.split())}"

    lines = existing.splitlines()
    insert_at = _where_the_list_starts(lines)
    lines.insert(insert_at, entry)
    where.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _already_said(existing: str, learning: str) -> bool:
    tidy = re.sub(r"[^a-z0-9 ]", "", learning.lower())
    for line in existing.splitlines():
        if not line.startswith("- **"):
            continue
        said = re.sub(r"[^a-z0-9 ]", "", line.lower())
        if tidy and tidy in said:
            return True
    return False


def _where_the_list_starts(lines: list[str]) -> int:
    for number, line in enumerate(lines):
        if line.startswith("- **"):
            return number
    return len(lines)


# ----------------------------------------------------------------- recall
def recall(calling_agent: str, agent_name: str, about: str | None = None,
          most: int = 12) -> list[dict]:
    """Read back what this agent knows, newest first.

    `about` filters by substring - deliberately not a semantic search, so
    the same question always returns the same lines and a person can
    verify that by reading the file.
    """
    _check_it_is_your_own(calling_agent, agent_name)

    where = _memory_folder(agent_name) / _learned_file_name(agent_name)
    if not where.exists():
        return []

    found = []
    for line in where.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- **"):
            continue
        if about and about.lower() not in line.lower():
            continue
        match = re.match(r"- \*\*(.+?)\*\* \((\w+)\) (.+)", line)
        if not match:
            continue
        found.append({"when": match.group(1), "confidence": match.group(2),
                      "learning": match.group(3)})
        if len(found) >= most:
            break
    return found


def as_a_paragraph_for_a_briefing(calling_agent: str, agent_name: str,
                                  about: str | None = None, most: int = 8) -> str:
    """Memory, formatted to paste into a prompt.

    Guessed learnings are excluded - a guess must never reach a model as
    though it were a fact, which is how a hedge becomes a hallucination
    two steps downstream.
    """
    remembered = recall(calling_agent, agent_name, about, most * 2)
    trusted = [r for r in remembered if r["confidence"] != "guessed"][:most]
    if not trusted:
        return ""
    lines = ["What I already know, from previous runs:"]
    for item in trusted:
        lines.append(f"- {item['learning']} ({item['when']})")
    return "\n".join(lines)


def forget(calling_agent: str, agent_name: str, index: int) -> bool:
    """Delete one learning by its position in recall()'s newest-first list.
    Used by the "wrong memory, two-second delete" button on the Agents tab."""
    _check_it_is_your_own(calling_agent, agent_name)

    where = _memory_folder(agent_name) / _learned_file_name(agent_name)
    if not where.exists():
        return False

    lines = where.read_text(encoding="utf-8").splitlines()
    entry_starts = [i for i, line in enumerate(lines) if line.startswith("- **")]
    if index < 0 or index >= len(entry_starts):
        return False

    start = entry_starts[index]
    end = entry_starts[index + 1] if index + 1 < len(entry_starts) else len(lines)
    del lines[start:end]
    where.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def needs_curating(agent_name: str) -> bool:
    where = _memory_folder(agent_name) / _learned_file_name(agent_name)
    if not where.exists():
        return False
    count = sum(1 for line in where.read_text(encoding="utf-8").splitlines()
               if line.startswith("- **"))
    return count > MOST_LEARNINGS_BEFORE_CURATING


# ------------------------------------------------------------ what happened
def write_down_what_happened(calling_agent: str, agent_name: str, ticket: str,
                             job_shape: str, outcome: str, steps_taken: int,
                             model_calls: int, seconds: float, notes: str = "",
                             tokens_in=None, tokens_out=None) -> None:
    _check_it_is_your_own(calling_agent, agent_name)

    where = _memory_folder(agent_name) / HAPPENED_FILE
    new_file = not where.exists()
    with where.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(HAPPENED_COLUMNS)
        writer.writerow([
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ticket, job_shape, outcome, int(steps_taken), int(model_calls),
            round(float(seconds), 1), " ".join((notes or "").split())[:200],
            "" if tokens_in is None else int(tokens_in),
            "" if tokens_out is None else int(tokens_out),
        ])


def how_this_agent_has_been_doing(agent_name: str, last: int = 50) -> dict:
    """Counts for the Agents tab. No judgement, no model, just tallies.

    has_data: False rather than zeroes when there is nothing yet - an
    agent that has never run has not failed 0% of the time, it has
    simply not run. malformed: True when the file exists but its
    header row is missing or wrong - one agent's memory file breaking
    this way once took the whole Agents tab down for every agent, so
    this says so plainly instead of guessing at columns that are not
    there (the same "malformed, not empty" distinction the
    study-module reader uses for a note with no Task 1).
    """
    where = _memory_folder(agent_name) / HAPPENED_FILE
    if not where.exists():
        return {"has_data": False, "runs": 0}

    with where.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    if not rows:
        return {"has_data": False, "runs": 0}

    if "outcome" not in fieldnames:
        return {"has_data": False, "runs": len(rows), "malformed": True,
                "detail": f"{HAPPENED_FILE} is missing its header row"}

    recent = rows[-last:]
    finished = sum(1 for row in recent if row["outcome"] == "finished")
    stuck = sum(1 for row in recent if row["outcome"] == "needs_human")

    def average(column):
        values = []
        for row in recent:
            try:
                values.append(float(row[column]))
            except (KeyError, ValueError):
                pass
        return round(sum(values) / len(values), 1) if values else None

    return {
        "has_data": True, "runs": len(rows), "runs_counted_here": len(recent),
        "finished": finished, "needed_a_human": stuck,
        "average_seconds": average("seconds"),
        "average_model_calls": average("model_calls"),
        "last_run": recent[-1]["timestamp"], "last_outcome": recent[-1]["outcome"],
    }


def recent_runs(agent_name: str, last: int = 20) -> list[dict]:
    """The raw rows for the Agent detail panel's "recent runs" table."""
    where = _memory_folder(agent_name) / HAPPENED_FILE
    if not where.exists():
        return []
    with where.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return list(reversed(rows[-last:]))
