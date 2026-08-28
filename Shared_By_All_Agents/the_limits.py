"""The guardrails that stop a job running away.

check_the_answer.py guards the content of one answer; this file guards
the shape of a whole job. Three things go wrong with agent loops, and
each has a counter here:

    1. It never stops.       -> MOST_STEPS and LONGEST_JOB_MINUTES
    2. It spends everything. -> MOST_MODEL_CALLS, checked before each call
    3. It goes in circles.   -> the same step twice with the same input
                                is refused - a loop, not persistence

Every refusal is a plain English sentence, because these end up in
NEEDS_HUMAN.csv where a person reads them later.
"""

from __future__ import annotations

import time


class TheJobMustStop(Exception):
    """Raised when a limit is reached. Caught by the supervisor, which
    writes the reason to NEEDS_HUMAN.csv and stops. Never retried."""


class Budget:
    """One job's allowance. Created by the supervisor, passed to the
    agent, checked before every step.

    Deliberately not a decorator or context manager: an agent author
    should see spend() written out at the point of spending, because an
    invisible guardrail is one people stop believing in.
    """

    def __init__(self, agent_name: str, ticket: str, most_steps: int,
                most_model_calls: int, longest_job_minutes: float):
        self.agent_name = agent_name
        self.ticket = ticket
        self.most_steps = int(most_steps)
        self.most_model_calls = int(most_model_calls)
        self.longest_job_seconds = float(longest_job_minutes) * 60
        self.started = time.time()

        self.steps_taken = 0
        self.model_calls = 0
        # Token spend, filled in by record_tokens() after each real model
        # answer. Zero here is a true zero - a job that never calls a
        # model genuinely used no tokens (Phase-1 CS-3, agent-memory half).
        self.tokens_in = 0
        self.tokens_out = 0
        self.steps_done: list[tuple[str, str]] = []
        self.what_i_did: list[str] = []

    def about_to_take_a_step(self, step_name: str, fingerprint: str = "") -> bool:
        """Call before every step. Raises TheJobMustStop if it may not run.

        `fingerprint` is whatever makes this step's input unique - a
        scheme code, a URL, a date. Two steps with the same name and the
        same fingerprint is a loop.
        """
        self._check_the_clock()

        if self.steps_taken >= self.most_steps:
            raise TheJobMustStop(
                f"{self.agent_name} has taken all {self.most_steps} steps it "
                f"is allowed for one job and has not finished. Last steps: "
                f"{self._recent_steps()}. Either the job is bigger than the "
                "cap, or it is going in circles. A person should look before "
                "the cap is raised."
            )

        if fingerprint and (step_name, fingerprint) in self.steps_done:
            raise TheJobMustStop(
                f"{self.agent_name} tried to run '{step_name}' twice with "
                f"exactly the same input ({str(fingerprint)[:80]}). That is "
                "a loop."
            )

        self.steps_taken += 1
        self.steps_done.append((step_name, fingerprint))
        return True

    def about_to_call_a_model(self, why: str = "") -> bool:
        """Call immediately before do_one_task. Raises, or returns True."""
        self._check_the_clock()

        if self.model_calls >= self.most_model_calls:
            raise TheJobMustStop(
                f"{self.agent_name} has used all {self.most_model_calls} "
                "model calls allowed for one job. "
                + (f"It wanted another for: {why}. " if why else "")
                + "Before raising the cap, check whether one of those calls "
                "should have been ordinary code."
            )

        self.model_calls += 1
        return True

    def record_tokens(self, tokens_in, tokens_out) -> None:
        """Add one model answer's token counts to this job's total.

        Takes whatever the caller has and tolerates a missing count -
        Ollama always reports both today, but a provider that answers
        without counts must degrade to 'not counted', never to a guess.
        """
        for attribute, value in (("tokens_in", tokens_in), ("tokens_out", tokens_out)):
            if value is None:
                continue
            try:
                setattr(self, attribute, getattr(self, attribute) + int(value))
            except (TypeError, ValueError):
                continue

    def _check_the_clock(self) -> None:
        running_for = time.time() - self.started
        if running_for > self.longest_job_seconds:
            raise TheJobMustStop(
                f"{self.agent_name} has been working for {int(running_for)} "
                f"seconds, past the {int(self.longest_job_seconds)} it "
                "declared as its longest job. Stopping so the lease frees "
                "and the queue moves."
            )

    def note(self, sentence) -> None:
        """One plain sentence about what just happened. Shown in the UI."""
        self.what_i_did.append(" ".join(str(sentence).split())[:200])

    def seconds_so_far(self) -> float:
        return round(time.time() - self.started, 1)

    def _recent_steps(self) -> str:
        return ", ".join(name for name, _ in self.steps_done[-4:]) or "none"

    def as_plain_dict(self) -> dict:
        return {
            "agent": self.agent_name, "ticket": self.ticket,
            "steps_taken": self.steps_taken, "of_most_steps": self.most_steps,
            "model_calls": self.model_calls,
            "of_most_model_calls": self.most_model_calls,
            "seconds": self.seconds_so_far(), "what_i_did": list(self.what_i_did),
        }


def a_budget_for(agent: dict, ticket: str) -> Budget:
    """Build a Budget from an agent card. The card is the only source."""
    return Budget(
        agent_name=agent["agent_name"], ticket=ticket,
        most_steps=agent["most_steps"], most_model_calls=agent["most_model_calls"],
        longest_job_minutes=agent["longest_job_minutes"],
    )


def check_the_agent_may_do_this(agent: dict, shape: str, is_money_question: bool,
                                tool_names) -> tuple[bool, str]:
    """Before a job starts: is this agent allowed to do it at all?

    Checked by the supervisor, in code, before the agent is woken. An
    agent never decides its own permissions.
    """
    if shape not in agent["shapes_i_handle"]:
        return False, (
            f"{agent['agent_name']} does not handle '{shape}'. Its card "
            f"lists: {', '.join(agent['shapes_i_handle'])}"
        )

    if is_money_question and not agent["may_touch_money"]:
        return False, (
            f"{agent['agent_name']} is not marked MAY_TOUCH_MONEY, and this "
            "job could influence money. The card is the authority, not the job."
        )

    not_allowed = [name for name in tool_names if name not in agent["tools_i_may_use"]]
    if not_allowed:
        return False, (
            f"{agent['agent_name']} would need tools its card does not list: "
            f"{', '.join(not_allowed)}. Add them to TOOLS_I_MAY_USE if that "
            "is genuinely intended."
        )

    return True, ""
