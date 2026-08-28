"""Rewrites one agent card from an edit made on the Models screen.

WHY THE UI EDITS THE .py FILE ITSELF
    An agent card is pure data on purpose (ADR-056): "a card that can
    compute is a card that can lie about what it is". Giving the edit
    form a second home - a JSON overlay the card reader merges in -
    would mean every fact about an agent lives in two places, and the
    day they disagree nobody knows which one is true. So the form edits
    the card itself: this module turns the posted fields back into the
    same pure-data file a person would have written by hand, validates
    it with read_agent_cards' own rules BEFORE anything is replaced,
    and swaps it in atomically. A bad edit never lands.

LIVE PICKUP
    There is no cache to clear and no server to restart:
    read_agent_cards.every_agent() re-imports each card from disk on
    every request, so the moment the file is replaced the next page
    load shows the new behaviour. Tests pin this.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Shared_By_All_Agents
PROJECT_ROOT = HERE.parent                      # the inky folder
sys.path.insert(0, str(HERE))

import read_agent_cards as cards                 # noqa: E402

# Overridable in tests so a round-trip edit never touches real agents.
AGENTS_FOLDER = PROJECT_ROOT / "Agents"

_IST = timezone(timedelta(hours=5, minutes=30), "IST")

REQUIRED_FIELDS = (
    "WHAT_I_AM_FOR", "SHAPES_I_HANDLE", "TOOLS_I_MAY_USE",
    "MOST_STEPS", "MOST_MODEL_CALLS", "LONGEST_JOB_MINUTES",
    "MAY_TOUCH_MONEY",
)
LIST_FIELDS = ("SHAPES_I_HANDLE", "TOOLS_I_MAY_USE", "WHAT_I_WILL_NEVER_DO")
NUMBER_FIELDS = ("MOST_STEPS", "MOST_MODEL_CALLS", "LONGEST_JOB_MINUTES")


class ThatEditIsWrong(ValueError):
    """The posted fields cannot make a trustworthy card."""


def _check_fields(folder_name: str, fields: dict) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in fields]
    if missing:
        raise ThatEditIsWrong(f"the edit is missing: {', '.join(missing)}")
    for field in LIST_FIELDS:
        if field in fields and not isinstance(fields[field], list):
            raise ThatEditIsWrong(f"{field} must be a list")
    if not isinstance(fields["WHAT_I_AM_FOR"], str) \
            or not fields["WHAT_I_AM_FOR"].strip():
        raise ThatEditIsWrong("WHAT_I_AM_FOR must say what the agent is for")
    for field in NUMBER_FIELDS:
        try:
            int(fields[field])
        except (TypeError, ValueError):
            raise ThatEditIsWrong(                                # noqa: B904
                f"{field} must be a whole number")


def _card_source(folder_name: str, fields: dict,
                 kept_home_sections: list | None) -> str:
    """The pure-data file, shaped exactly like a hand-written card."""
    purpose = fields["WHAT_I_AM_FOR"].replace('"', "'").strip()
    lines = [
        f'"""{folder_name} - who I am.',
        "",
        "This card was rewritten from the Models screen's edit form on "
        f"{datetime.now(_IST).date().isoformat()}.",
        "It stays pure data: no logic, no imports, nothing that could",
        'compute a lie about what this agent is.',
        '"""',
        "",
        f"AGENT_NAME = {folder_name!r}",
        "",
        "WHAT_I_AM_FOR = (",
        f'    "{purpose}"',
        ")",
        "",
        "# Shapes this agent claims. No two agents may claim the same shape;",
        "# read_agent_cards.py refuses to start if they do.",
        "SHAPES_I_HANDLE = [",
    ]
    lines += [f"    {shape!r}," for shape in fields["SHAPES_I_HANDLE"]]
    lines += [
        "]",
        "",
        "# Names from Shared_By_All_Agents/Tools/. The supervisor refuses a job",
        "# that would need a tool not listed here.",
        "TOOLS_I_MAY_USE = [",
    ]
    lines += [f"    {tool!r}," for tool in fields["TOOLS_I_MAY_USE"]]
    lines += [
        "]",
        "",
        "# Caps for ONE job. Reached means stop and tell a person (ADR-056).",
    ]
    for field in NUMBER_FIELDS:
        lines.append(f"{field} = {int(fields[field])}")
    lines += [
        "",
        "# True only for agents allowed to work on questions that could",
        "# influence money. Enforced three times over; see CLAUDE.md Rule 5.",
        f"MAY_TOUCH_MONEY = {bool(fields['MAY_TOUCH_MONEY'])!r}",
    ]
    never = fields.get("WHAT_I_WILL_NEVER_DO") or []
    if never:
        lines += [
            "",
            "# Shown on the Agents tab: what this agent will never do. Honesty,",
            "# not enforcement - the enforcement is above.",
            "WHAT_I_WILL_NEVER_DO = [",
        ]
        lines += [f"    {line!r}," for line in never]
        lines.append("]")
    if kept_home_sections:
        lines += [
            "",
            "# Which discovered part of the home page this agent belongs to.",
            "HOME_SECTIONS = [",
        ]
        lines += [f"    {section!r}," for section in kept_home_sections]
        lines.append("]")
    return "\n".join(lines) + "\n"


def write_card(folder_name: str, fields: dict) -> dict:
    """Validate first, then replace agent_card.py atomically. Never raises."""
    folder_name = str(folder_name)
    if not folder_name.endswith("_Agent"):
        return {"ok": False, "problem":
                f"agent names end in _Agent; '{folder_name}' does not."}
    folder = AGENTS_FOLDER / folder_name
    if not folder.is_dir():
        return {"ok": False,
                "problem": f"no agent folder called '{folder_name}'"}

    try:
        _check_fields(folder_name, fields)
    except ThatEditIsWrong as wrong:
        return {"ok": False, "problem": str(wrong)}

    # HOME_SECTIONS was declared by whoever built the agent, not edited
    # here - carry it through untouched unless the edit supplies it.
    kept_home_sections = fields.get("HOME_SECTIONS")
    if kept_home_sections is None:
        live = next((a for a in cards.every_agent()
                     if a.get("agent_name") == folder_name), None)
        if live and live.get("home_sections"):
            kept_home_sections = list(live["home_sections"])

    source = _card_source(folder_name, fields, kept_home_sections)

    stamp = datetime.now(_IST).strftime("%Y%m%dT%H%M%S")
    temp_path = folder / f"agent_card_edit_{stamp}.py"
    live_path = folder / cards.CARD_FILENAME
    try:
        temp_path.write_text(source, encoding="utf-8")
        # The same validator every startup uses. If the candidate card
        # cannot be trusted, it never becomes the card.
        cards._load_the_card(temp_path, folder_name)
        others = [a for a in cards.every_agent()
                  if a.get("agent_name") != folder_name]
        claimed = {shape for other in others
                   for shape in other.get("shapes_i_handle", [])}
        clash = [shape for shape in fields["SHAPES_I_HANDLE"]
                 if shape in claimed]
        if clash:
            raise cards.ThatAgentCardIsWrong(
                f"{', '.join(map(repr, clash))} already handled by "
                "another agent")
        os.replace(temp_path, live_path)
    except cards.ThatAgentCardIsWrong as wrong:
        temp_path.unlink(missing_ok=True)
        return {"ok": False, "problem": str(wrong)}
    except OSError as trouble:
        temp_path.unlink(missing_ok=True)
        return {"ok": False, "problem": f"could not save the card: {trouble}"}

    reloaded = next((a for a in cards.every_agent()
                     if a.get("agent_name") == folder_name), None)
    return {"ok": True, "card": reloaded}


def main() -> None:
    print("This module has no command of its own - it exists so the")
    print("Models screen's PUT /api/models/agents/<name> can save edits.")


if __name__ == "__main__":
    main()


