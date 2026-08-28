"""Stops before anything that cannot be undone, and asks.

NEEDS_HUMAN.csv (the router's escalation file, also used by the
supervisor) is for when an agent fails. This is the other half: what
happens when an agent is about to succeed at something it should not do
unsupervised.

Five kinds of action pass through here:

    delete_something      removing a file or a record
    overwrite_something   replacing content that existed
    speak_as_me           anything leaving the machine with my name on it
    move_money            anything touching a broker, a payment, an order
    change_many_things    a bulk operation over more than a handful of items

Nothing in Inky today can send an email or place a trade. The last
three are here anyway, because the moment one exists the gate must
already be the road it travels.

How it works: an agent calls ask_first(). If the action is reversible
and small, it returns permission immediately. If not, it writes a
pending request and raises WaitingForYou, which stops the job. A person
sees it in the Agents tab, presses approve or refuse, and the job runs
again.
"""

from __future__ import annotations

import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Above this many items, an operation is bulk and needs a person
# regardless of how safe each individual change looks.
A_HANDFUL = 5

WHAT_NEEDS_ASKING = {
    "delete_something": "removes something that existed",
    "overwrite_something": "replaces content that was already there",
    "speak_as_me": "sends something out with my name on it",
    "move_money": "touches a broker, a payment or an order",
    "change_many_things": "changes more than a handful of things at once",
}

PENDING = PROJECT_ROOT / "Shared_By_All_Screens" / "Current_Numbers" / "WAITING_FOR_YOU.csv"
PENDING_COLUMNS = [
    "asked_at", "request_id", "agent", "ticket", "kind", "what_it_would_do",
    "what_cannot_be_undone", "how_many_things", "answer", "answered_at",
]


class WaitingForYou(Exception):
    """Raised when an action needs a person. Never retried automatically -
    a retry loop around a permission request is how consent gets manufactured."""

    def __init__(self, request_id: str, message: str):
        super().__init__(message)
        self.request_id = request_id


def ask_first(agent_name: str, ticket: str, kind: str, what_it_would_do: str,
             what_cannot_be_undone: str = "", how_many_things: int = 1,
             already_approved=None) -> bool:
    """Call immediately before doing something irreversible.

    Returns True when the action may proceed. Raises WaitingForYou
    otherwise - never returns False, so a caller cannot mistake a
    refusal for an ordinary answer.

    `already_approved` is the set of request_ids a person has approved,
    passed in by the supervisor.
    """
    if kind not in WHAT_NEEDS_ASKING:
        raise ValueError(
            f"'{kind}' is not a kind of action this gate knows. It knows: "
            f"{', '.join(sorted(WHAT_NEEDS_ASKING))}"
        )

    request_id = _fingerprint(agent_name, kind, what_it_would_do)

    if already_approved and request_id in already_approved:
        _write_down(request_id, agent_name, ticket, kind, what_it_would_do,
                   what_cannot_be_undone, how_many_things, answer="proceeded")
        return True

    answer = _look_up_a_previous_answer(request_id)
    if answer == "approved":
        return True
    if answer == "refused":
        raise WaitingForYou(request_id, (
            f"You refused this before: {what_it_would_do}. It has not been "
            "asked again. Change the answer in the Agents tab if you have "
            "changed your mind."
        ))

    _write_down(request_id, agent_name, ticket, kind, what_it_would_do,
               what_cannot_be_undone, how_many_things, answer="waiting")

    raise WaitingForYou(request_id, _how_to_say_it(
        agent_name, kind, what_it_would_do, what_cannot_be_undone,
        how_many_things, request_id,
    ))


def _how_to_say_it(agent_name, kind, what_it_would_do, what_cannot_be_undone,
                   how_many_things, request_id) -> str:
    """The sentence a person reads: what, what is permanent, how big."""
    lines = [
        f"{agent_name} stopped before doing something that needs you.", "",
        f"What it would do: {what_it_would_do}",
        f"Why it stopped: this {WHAT_NEEDS_ASKING[kind]}.",
    ]
    if what_cannot_be_undone:
        lines.append(f"What cannot be undone: {what_cannot_be_undone}")
    if how_many_things > 1:
        lines.append(f"How many things: {how_many_things}")
    lines += ["", "Nothing has happened yet. Approve or refuse it in the "
             f"Agents tab, then run the job again. Reference: {request_id}"]
    return "\n".join(lines)


def would_this_need_asking(kind: str, how_many_things: int = 1) -> bool:
    """A cheap check an agent can make while planning, before doing work."""
    if kind in WHAT_NEEDS_ASKING:
        return True
    return how_many_things > A_HANDFUL


def _fingerprint(agent_name: str, kind: str, what_it_would_do: str) -> str:
    """Stable id for the same request, so an approval sticks across runs
    and a refusal is not re-asked every time."""
    raw = f"{agent_name}|{kind}|{' '.join(what_it_would_do.split())}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _write_down(request_id, agent_name, ticket, kind, what_it_would_do,
                what_cannot_be_undone, how_many_things, answer) -> None:
    PENDING.parent.mkdir(parents=True, exist_ok=True)
    new_file = not PENDING.exists()
    with PENDING.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(PENDING_COLUMNS)
        writer.writerow([
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            request_id, agent_name, ticket, kind, what_it_would_do[:300],
            what_cannot_be_undone[:300], how_many_things, answer, "",
        ])


def _look_up_a_previous_answer(request_id: str) -> str | None:
    """The newest decision wins, so changing your mind in the UI works."""
    if not PENDING.exists():
        return None
    decision = None
    for row in _all_rows():
        if row.get("request_id") != request_id:
            continue
        if row.get("answer") in ("approved", "refused"):
            decision = row["answer"]
    return decision


def what_is_waiting() -> list[dict]:
    """Everything still unanswered, newest first. For the Agents tab."""
    if not PENDING.exists():
        return []
    newest = {}
    for row in _all_rows():
        newest[row["request_id"]] = row
    waiting = [row for row in newest.values() if row.get("answer") == "waiting"]
    waiting.sort(key=lambda row: row.get("asked_at", ""), reverse=True)
    return waiting


def answer_it(request_id: str, approved: bool, who: str = "me") -> bool:
    """Record a decision from the UI. Appends rather than editing, so the
    history of what you approved and when survives."""
    if not PENDING.exists():
        return False

    original = None
    for row in _all_rows():
        if row["request_id"] == request_id:
            original = row
    if original is None:
        return False

    with PENDING.open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow([
            original["asked_at"], request_id, original["agent"], original["ticket"],
            original["kind"], original["what_it_would_do"],
            original["what_cannot_be_undone"], original["how_many_things"],
            "approved" if approved else "refused",
            datetime.now(timezone.utc).isoformat(timespec="seconds") + f" by {who}",
        ])
    return True


def what_i_have_approved() -> set[str]:
    """The set of approved request_ids, for the supervisor to pass down."""
    if not PENDING.exists():
        return set()
    newest = {}
    for row in _all_rows():
        newest[row["request_id"]] = row.get("answer")
    return {rid for rid, answer in newest.items() if answer == "approved"}


def _all_rows() -> list[dict]:
    with PENDING.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def show_the_plan(steps: list[str], what_is_permanent: set[str]) -> str:
    """Format a multi-step plan for a person to read before approving."""
    lines = ["Here is the whole plan before anything runs:", ""]
    for number, step in enumerate(steps, start=1):
        permanent = step in what_is_permanent
        lines.append(f"{number}. {step}" + ("   [CANNOT BE UNDONE]" if permanent else ""))
    lines += ["", f"{len(what_is_permanent)} of {len(steps)} steps cannot be undone.",
             "Nothing has happened yet."]
    return "\n".join(lines)
