"""A tool is a plain Python function that does something deterministic
and returns a plain dict. It never calls a model. That is the whole
definition, and it is what makes tools cheap: a tool call costs nothing
and cannot hallucinate.

Every tool declares what it needs and what it gives back, so the Agents
tab can show a person exactly what an agent is permitted to do.

Registration is by decorator at import time. There is no list to maintain.
"""

from __future__ import annotations

import inspect
import time


WHAT_EXISTS: dict[str, dict] = {}


class ThereIsNoSuchTool(Exception):
    pass


class ThatToolWasUsedWrongly(Exception):
    pass


def a_tool(name: str, what_it_does: str, gives_back: str):
    """Decorator. Registers a function as a tool.

    name          plain words, lowercase with underscores, reads as an action
    what_it_does  one sentence a non-technical reader understands
    gives_back    one sentence describing the returned dict
    """
    def keep_it(function):
        if name in WHAT_EXISTS:
            raise ValueError(
                f"Two tools are both called '{name}'. Tool names are how "
                "agent cards grant permission, so they must be unique."
            )
        for word in ("utils", "helper", "misc", "manager", "handler", "process"):
            if word in name:
                raise ValueError(
                    f"The tool name '{name}' contains the category-word "
                    f"'{word}'. Name it for the action it performs."
                )

        # A parameter with a default is optional. Treating it as required
        # would force every caller to restate a default the tool already
        # knows, which is how a permission list becomes noise.
        signature = inspect.signature(function)
        must_have, may_have = [], []
        for parameter_name, parameter in signature.parameters.items():
            if parameter_name == "project_root":
                continue
            if parameter.default is inspect.Parameter.empty:
                must_have.append(parameter_name)
            else:
                may_have.append(parameter_name)

        WHAT_EXISTS[name] = {
            "name": name, "what_it_does": what_it_does, "gives_back": gives_back,
            "needs": must_have, "may_also_take": may_have, "run": function,
        }
        return function
    return keep_it


def use(name: str, project_root, **arguments):
    """Run a tool by name.

    The supervisor has already checked the agent's card permits this
    tool. This function checks the arguments, so a mistyped argument
    fails here with a readable message rather than deep inside the tool.

    Every invocation lands in the trace ledger (kind "skill") - the
    nightly reflection reads these to see which skills an agent leans
    on and which it avoids. Tracing wraps the call: if the ledger cannot
    be written, the tool still runs.
    """
    if name not in WHAT_EXISTS:
        raise ThereIsNoSuchTool(
            f"No tool called '{name}'. There are: "
            + (", ".join(sorted(WHAT_EXISTS)) or "none registered")
        )

    tool = WHAT_EXISTS[name]
    missing = [need for need in tool["needs"] if need not in arguments]
    if missing:
        raise ThatToolWasUsedWrongly(
            f"'{name}' needs {', '.join(missing)} and did not get it. It "
            f"takes: {', '.join(tool['needs'])}"
        )

    allowed = set(tool["needs"]) | set(tool["may_also_take"])
    extra = [given for given in arguments if given not in allowed]
    if extra:
        raise ThatToolWasUsedWrongly(
            f"'{name}' was given {', '.join(extra)}, which it does not take. "
            f"It takes: {', '.join(sorted(allowed))}"
        )

    from Shared_By_All_Screens.trace_every_action import trace
    started = time.time()
    try:
        result = tool["run"](project_root=project_root, **arguments)
    except Exception:
        trace("skill", "skill", name, target=tool["what_it_does"][:60],
              outcome="fail", duration_ms=int((time.time() - started) * 1000))
        raise
    trace("skill", "skill", name, target=tool["what_it_does"][:60],
          outcome="ok", duration_ms=int((time.time() - started) * 1000))
    return result


def describe_them_all() -> list[dict]:
    """Every tool, for the Agents tab and for building a briefing."""
    return [
        {"name": t["name"], "what_it_does": t["what_it_does"],
         "needs": t["needs"], "may_also_take": t["may_also_take"],
         "gives_back": t["gives_back"]}
        for t in sorted(WHAT_EXISTS.values(), key=lambda t: t["name"])
    ]


def describe_these(names) -> list[dict]:
    """The subset one agent may use, for its briefing."""
    wanted = set(names)
    return [d for d in describe_them_all() if d["name"] in wanted]
