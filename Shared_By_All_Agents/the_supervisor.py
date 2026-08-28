"""Orchestration. The supervisor takes a request, finds the one agent
whose card claims that shape, checks permissions and the lease, writes
a Briefing, and runs the agent's steps inside a Budget.

It contains no model. Dispatch is a lookup against the cards, because
putting a language model in charge of routing puts a guess in the one
position where a mistake is unrecoverable and unlogged (ADR-056).

The order is fixed and is itself the guardrail:

    THINK     the Briefing is written before the agent wakes
    REMEMBER  the agent's own memory is read into the Briefing
    ACT       steps run, each one recorded before the next begins

Nothing here knows any agent's name - enforced by a test, the same way
test_the_menu_and_launcher_never_name_a_screen works today.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "Tools"))
sys.path.insert(0, str(PROJECT_ROOT / "Screens" / "Models" / "Calculations"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from read_agent_cards import every_agent, load_what_it_can_do, the_agent_for  # noqa: E402
from remember_and_recall import as_a_paragraph_for_a_briefing, write_down_what_happened  # noqa: E402
from the_lease_board import finish, try_to_start                     # noqa: E402
from the_limits import TheJobMustStop, a_budget_for, check_the_agent_may_do_this  # noqa: E402
from the_tool_registry import describe_these                          # noqa: E402
import the_everyday_tools                        # noqa: E402,F401  registers the tools
import the_research_tools                         # noqa: E402,F401  registers search_the_web
from do_one_task import escalate_to_human                             # noqa: E402


class Briefing:
    """Everything an agent is told, written down before it starts.

    This object is the anti-hallucination mechanism. An agent is never
    asked to work out what to do; it is handed the goal, the facts
    already known, the tools it may use, the budget it may spend, and
    the exact shape of an acceptable answer. Anything outside that
    shape is rejected downstream by check_the_answer.py.
    """

    def __init__(self, agent_name, ticket, shape, goal, expectation, *,
                facts_i_already_know="", tools_available=None,
                is_money_question=False, budget=None):
        self.agent_name = agent_name
        self.ticket = ticket
        self.shape = shape
        self.goal = goal
        self.expectation = expectation
        self.facts_i_already_know = facts_i_already_know
        self.tools_available = tools_available or []
        self.is_money_question = is_money_question
        self.budget = budget
        self.written_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def as_words_for_a_model(self) -> str:
        """The briefing turned into the note a model receives.

        Written as instructions to a careful person, not incantations -
        the rules that actually bind are enforced in code; this exists
        so the model's first attempt is more likely to survive them.
        """
        lines = ["You are helping with one narrow job. Do only this job.",
                "", f"The job: {self.goal}"]
        if self.facts_i_already_know:
            lines += ["", self.facts_i_already_know]
        if self.expectation.get("wants_json"):
            keys = self.expectation.get("required_keys") or []
            lines += ["", "Answer with JSON only. No prose before or after it."]
            if keys:
                lines.append("It must contain these keys: " + ", ".join(keys))
        if self.expectation.get("one_of"):
            lines += ["", "Answer with exactly one of these words and nothing "
                     "else: " + ", ".join(self.expectation["one_of"])]
        if self.expectation.get("max_words"):
            lines.append(f"Use at most {self.expectation['max_words']} words.")
        lines += [
            "", "Two things will get your answer thrown away:",
            "- inventing a number. If a figure is not in the text above, say "
            "you do not have it. A missing number is a fine answer; a "
            "guessed one is not.",
            "- giving advice. Describe what is there. Never recommend "
            "buying, selling or holding anything.",
        ]
        return "\n".join(lines)

    def as_plain_dict(self) -> dict:
        return {
            "agent": self.agent_name, "ticket": self.ticket, "shape": self.shape,
            "goal": self.goal, "written_at": self.written_at,
            "tools_available": [t["name"] for t in self.tools_available],
            "is_money_question": self.is_money_question,
            "knows_something_already": bool(self.facts_i_already_know),
        }


class HowItWent:
    def __init__(self, state, agent_name="", ticket="", answer=None, why="",
                budget=None, briefing=None):
        self.state = state          # finished | queued | refused | needs_human
        self.agent_name = agent_name
        self.ticket = ticket
        self.answer = answer
        self.why = why
        self.budget = budget
        self.briefing = briefing

    def as_plain_dict(self) -> dict:
        return {
            "state": self.state, "agent": self.agent_name, "ticket": self.ticket,
            "answer": self.answer, "why": self.why,
            "budget": self.budget.as_plain_dict() if self.budget else None,
            "briefing": self.briefing.as_plain_dict() if self.briefing else None,
        }


def hand_this_to_someone(shape, goal, *, expectation=None, is_money_question=False,
                         remember_about=None, run_now=True) -> HowItWent:
    """The one way in. Everything the UI, the morning run and the
    screens call.

    Returns HowItWent. Never raises for an ordinary problem - a refusal
    is an answer, and an exception escaping here would take a whole
    morning run down.
    """
    expectation = expectation or {}
    started = time.time()

    agent = the_agent_for(shape)
    if agent is None:
        return HowItWent("refused", why=(
            f"No agent claims the shape '{shape}'. The agents that exist "
            f"handle: {_what_everyone_handles()}. Either use one of those "
            "shapes, or add an agent folder that claims this one."
        ))

    allowed, why_not = check_the_agent_may_do_this(
        agent, shape, is_money_question, expectation.get("tools_needed", [])
    )
    if not allowed:
        return HowItWent("refused", agent["agent_name"], why=why_not)

    lease = try_to_start(agent["agent_name"], shape, goal,
                         longest_job_minutes=agent["longest_job_minutes"])

    if lease.state == "queued":
        return HowItWent("queued", agent["agent_name"], lease.ticket, why=lease.reason)
    if lease.state == "refused":
        return HowItWent("refused", agent["agent_name"], why=lease.reason)
    if not run_now:
        finish(agent["agent_name"])
        return HowItWent("queued", agent["agent_name"], why="asked not to run now")

    ticket = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    budget = a_budget_for(agent, ticket)

    try:
        briefing = _write_the_briefing(agent, ticket, shape, goal, expectation,
                                       is_money_question, remember_about, budget)
        answer = _let_the_agent_work(agent, briefing, budget)
        _write_down_the_run(agent, ticket, shape, "finished", budget, started, "")
        return HowItWent("finished", agent["agent_name"], ticket, answer,
                         "the agent finished inside its budget", budget, briefing)

    except TheJobMustStop as stopped:
        _write_down_the_run(agent, ticket, shape, "needs_human", budget, started, str(stopped))
        escalate_to_human(agent["agent_name"], shape, str(stopped), budget.steps_taken)
        return HowItWent("needs_human", agent["agent_name"], ticket,
                         why=str(stopped), budget=budget)

    except Exception as trouble:                                     # noqa: BLE001
        # An agent's own bug must not poison the lease board or the morning.
        why = f"{agent['agent_name']} hit an unexpected problem: {trouble}"
        _write_down_the_run(agent, ticket, shape, "failed", budget, started, why)
        escalate_to_human(agent["agent_name"], shape, why, budget.steps_taken)
        return HowItWent("needs_human", agent["agent_name"], ticket, why=why, budget=budget)

    finally:
        finish(agent["agent_name"])


def _write_the_briefing(agent, ticket, shape, goal, expectation, is_money_question,
                        remember_about, budget) -> Briefing:
    """THINK, then REMEMBER. Both happen before a single step runs."""
    name = agent["agent_name"]
    facts = as_a_paragraph_for_a_briefing(name, name, about=remember_about or shape)

    briefing = Briefing(
        agent_name=name, ticket=ticket, shape=shape, goal=goal,
        expectation=expectation, facts_i_already_know=facts,
        tools_available=describe_these(agent["tools_i_may_use"]),
        is_money_question=is_money_question, budget=budget,
    )
    budget.note(f"was briefed on: {goal[:120]}")
    if facts:
        budget.note(f"recalled {facts.count(chr(10) + '- ')} things it already knew")
    return briefing


def _let_the_agent_work(agent, briefing, budget):
    """ACT. The agent's own module does the steps; the budget polices them.

    An abilities module must expose do_the_job(project_root, briefing,
    budget). That is the entire contract, and keeping it to one
    function is what stops the supervisor needing to know anything
    about any particular agent.
    """
    abilities = load_what_it_can_do(agent)
    if not hasattr(abilities, "do_the_job"):
        raise TheJobMustStop(
            f"{agent['agent_name']} has a what_i_can_do.py with no "
            "do_the_job(project_root, briefing, budget) function, so there "
            "is nothing for the supervisor to call."
        )
    return abilities.do_the_job(str(PROJECT_ROOT), briefing, budget)


def _write_down_the_run(agent, ticket, shape, outcome, budget, started, notes) -> None:
    name = agent["agent_name"]
    write_down_what_happened(name, name, ticket, shape, outcome, budget.steps_taken,
                             budget.model_calls, time.time() - started, notes,
                             tokens_in=budget.tokens_in or None,
                             tokens_out=budget.tokens_out or None)
    # Mirrored into the trace ledger, so the nightly reflection sees the
    # agent's day alongside every click and skill call. The run's ticket
    # doubles as the correlation id (Phase-1 CS-1): it is already unique
    # per run, so a second id minted here would only split the trail.
    from Shared_By_All_Screens.trace_every_action import trace
    trace(name, "agent", f"run_{shape}", target=ticket,
          detail={"outcome": outcome, "steps": budget.steps_taken,
                  "model_calls": budget.model_calls},
          outcome="ok" if outcome == "finished" else
                  ("escalated" if outcome == "needs_human" else "fail"),
          duration_ms=int((time.time() - started) * 1000),
          correlation_id=ticket)


def _what_everyone_handles() -> str:
    shapes = []
    for agent in every_agent():
        if agent["state"] == "ready":
            shapes.extend(agent["shapes_i_handle"])
    return ", ".join(sorted(set(shapes))) or "nothing yet"


def work_through_the_queue(agent_name: str, most_jobs: int = 5) -> list[dict]:
    """Called after an agent frees its lease, and by the morning run.

    Deliberately capped - an unbounded drain can run for hours and
    starve every other agent of the free-tier allowance they all share.
    """
    from the_lease_board import take_the_next_job

    done = []
    for _ in range(most_jobs):
        job = take_the_next_job(agent_name)
        if job is None:
            break
        outcome = hand_this_to_someone(job["job_shape"], job["job_summary"])
        done.append(outcome.as_plain_dict())
    return done
