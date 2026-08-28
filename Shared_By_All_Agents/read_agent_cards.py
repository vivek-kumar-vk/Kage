"""Finds every agent by walking Agents/ and reading its card.

Discovery, not registration - the same shape as
Main_Menu/Backend/find_every_screen.py. There is no list of agents
anywhere. Adding an agent costs exactly one folder.

A half-filled card stops startup rather than half-drawing an Agents
tab, the same reasoning as the screen definitions: a menu that shows an
agent which cannot run is worse than a menu that refuses to load.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AGENTS_FOLDER = PROJECT_ROOT / "Agents"

REQUIRED_FIELDS = [
    "AGENT_NAME", "WHAT_I_AM_FOR", "SHAPES_I_HANDLE", "TOOLS_I_MAY_USE",
    "MOST_STEPS", "MOST_MODEL_CALLS", "LONGEST_JOB_MINUTES", "MAY_TOUCH_MONEY",
]

CARD_FILENAME = "agent_card.py"
ABILITIES_FILENAME = "what_i_can_do.py"

BANNED_WORDS_IN_A_NAME = (
    "utils", "helpers", "misc", "common", "manager", "handler",
    "service", "core", "base", "engine", "processor", "generic",
)


class ThatAgentCardIsWrong(Exception):
    """Raised when a card cannot be trusted. Never caught quietly."""


def every_agent() -> list[dict]:
    """One dict per agent, sorted by name.

    An agent folder with no card is "not_built" - a normal, planned
    state, exactly like a screen with no Backend/. A card with no
    abilities file is "broken", reported loudly.
    """
    if not AGENTS_FOLDER.exists():
        return []

    found = []
    for folder in sorted(AGENTS_FOLDER.iterdir()):
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue

        card_path = folder / CARD_FILENAME
        abilities_path = folder / ABILITIES_FILENAME

        if not card_path.exists():
            found.append({
                "agent_name": folder.name, "state": "not_built",
                "what_i_am_for": "",
                "note": (f"there is a folder but no {CARD_FILENAME} yet, "
                        "a normal way for a planned agent to look"),
            })
            continue

        card = _load_the_card(card_path, folder.name)

        if not abilities_path.exists():
            found.append({
                "agent_name": folder.name, "state": "broken",
                "what_i_am_for": card.get("WHAT_I_AM_FOR", ""),
                "note": (f"has {CARD_FILENAME} but no {ABILITIES_FILENAME}, so "
                        "it declares things it cannot do"),
            })
            continue

        found.append({
            "agent_name": card["AGENT_NAME"], "state": "ready",
            "what_i_am_for": card["WHAT_I_AM_FOR"],
            "shapes_i_handle": list(card["SHAPES_I_HANDLE"]),
            "tools_i_may_use": list(card["TOOLS_I_MAY_USE"]),
            "most_steps": int(card["MOST_STEPS"]),
            "most_model_calls": int(card["MOST_MODEL_CALLS"]),
            "longest_job_minutes": int(card["LONGEST_JOB_MINUTES"]),
            "may_touch_money": bool(card["MAY_TOUCH_MONEY"]),
            "what_i_will_never_do": list(card.get("WHAT_I_WILL_NEVER_DO", [])),
            # Optional, pure-data extra: which discovered part of the
            # home page this agent belongs to. Present only when the
            # card declares it - an absent field is a fact, not a
            # default to fill in.
            **({"home_sections": [str(s) for s in card["HOME_SECTIONS"]]}
               if "HOME_SECTIONS" in card else {}),
            "folder": str(folder),
        })

    _complain_if_two_agents_claim_one_shape(found)
    return found


def _load_the_card(card_path: Path, folder_name: str) -> dict:
    spec = importlib.util.spec_from_file_location(f"agent_card_of_{folder_name}", card_path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as trouble:                                     # noqa: BLE001
        raise ThatAgentCardIsWrong(f"Could not read {card_path}: {trouble}")

    card, missing = {}, []
    for field in REQUIRED_FIELDS:
        if not hasattr(module, field):
            missing.append(field)
        else:
            card[field] = getattr(module, field)
    if hasattr(module, "WHAT_I_WILL_NEVER_DO"):
        card["WHAT_I_WILL_NEVER_DO"] = module.WHAT_I_WILL_NEVER_DO
    # Optional pure-data extra, read the same way: present on cards
    # that declare it, absent from every card that does not.
    if hasattr(module, "HOME_SECTIONS"):
        card["HOME_SECTIONS"] = module.HOME_SECTIONS

    if missing:
        raise ThatAgentCardIsWrong(
            f"{card_path} is missing: {', '.join(missing)}. A half-filled "
            "card would draw an agent that cannot run."
        )

    if card["AGENT_NAME"] != folder_name:
        raise ThatAgentCardIsWrong(
            f"The folder is called '{folder_name}' but its card says "
            f"AGENT_NAME is '{card['AGENT_NAME']}'. They must match, because "
            "the folder name is how everything else finds this agent."
        )

    _check_the_name_reads_like_a_name(folder_name)

    if not card["SHAPES_I_HANDLE"]:
        raise ThatAgentCardIsWrong(
            f"{card_path} handles no shapes, so nothing could ever be sent "
            "to it. Give it a shape or delete the folder."
        )

    for number_field in ("MOST_STEPS", "MOST_MODEL_CALLS", "LONGEST_JOB_MINUTES"):
        try:
            value = int(card[number_field])
        except (TypeError, ValueError):
            raise ThatAgentCardIsWrong(f"{card_path}: {number_field} must be a whole number")
        # MOST_MODEL_CALLS may be zero: a Tier-0 job of pure tool calls
        # is the cheapest kind there is and the only kind that cannot
        # hallucinate. Steps and minutes must stay at one or more -
        # a cap below those means the agent can never do anything.
        floor = 0 if number_field == "MOST_MODEL_CALLS" else 1
        if value < floor:
            raise ThatAgentCardIsWrong(
                f"{card_path}: {number_field} is {value}. A cap below "
                f"{floor} means the agent can never do anything."
            )

    return card


def _check_the_name_reads_like_a_name(folder_name: str) -> None:
    """ADR-034 applied to agents. A name must tell a non-technical reader
    what the agent is for: Finance_MF_Agent, Learning_Splunk_Agent."""
    lowered = folder_name.lower()
    for word in BANNED_WORDS_IN_A_NAME:
        if word in lowered:
            raise ThatAgentCardIsWrong(
                f"The agent folder '{folder_name}' contains the category-word "
                f"'{word}'. Name it for what it does."
            )
    if not folder_name.endswith("_Agent"):
        raise ThatAgentCardIsWrong(
            f"The agent folder '{folder_name}' should end in _Agent, so a "
            "person reading Agents/ can see at a glance what each folder is."
        )
    if "_" not in folder_name[:-6]:
        raise ThatAgentCardIsWrong(
            f"The agent folder '{folder_name}' needs at least two words "
            "before _Agent, like Finance_MF_Agent. One word is a category, "
            "not a job."
        )


def _complain_if_two_agents_claim_one_shape(found: list[dict]) -> None:
    """The supervisor dispatches by shape. Two agents claiming one shape
    means the supervisor would have to guess, which this design refuses
    to do."""
    claimed = {}
    for agent in found:
        if agent["state"] != "ready":
            continue
        for shape in agent["shapes_i_handle"]:
            if shape in claimed:
                raise ThatAgentCardIsWrong(
                    f"Both {claimed[shape]} and {agent['agent_name']} say "
                    f"they handle '{shape}'. The supervisor dispatches by "
                    "shape and will not guess between them."
                )
            claimed[shape] = agent["agent_name"]


def the_agent_for(shape: str) -> dict | None:
    """Which agent handles this shape? Returns the card, or None."""
    for agent in every_agent():
        if agent["state"] == "ready" and shape in agent["shapes_i_handle"]:
            return agent
    return None


def load_what_it_can_do(agent: dict):
    """Import an agent's abilities module. Only the supervisor calls this."""
    path = Path(agent["folder"]) / ABILITIES_FILENAME
    spec = importlib.util.spec_from_file_location(f"abilities_of_{agent['agent_name']}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
