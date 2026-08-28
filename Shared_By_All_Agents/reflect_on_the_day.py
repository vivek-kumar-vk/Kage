"""The nightly loop: read the day's traces, think locally, write a plan.

THE LOOP THIS FILE CLOSES
    1. Everything INKY did today landed in Trace_Ledger/traces_<date>.jsonl.
    2. This file gathers that record, plus yesterday's plan and a tail of
       each agent's run history, into one prompt.
    3. qwen3:8b - on this laptop, through Ollama, costing nothing and
       sending nothing anywhere (call_the_local_model.ask) - reads it and
       writes: what happened, what went well, what got in the way, and a
       checklist plan for tomorrow.
    4. The note lands in Documentation/Daily_Notes/<date>.md, next to the
       Daily Notes folder the project already kept empty for exactly this.
    5. TOMORROW, step 2 reads step 4's checklist and scores follow-through
       against tomorrow's traces. That score goes back into the prompt.
       That is the self-improvement loop: plan, act, measure, replan.

WHY THE LOCAL MODEL AND NOT THE ROUTER
    call_the_local_model.py's own docstring is the authority: a local
    model costs nothing, has no quota, never leaves this machine. The
    toggle (local_model_toggle.json) switches the whole thing off.

HONESTY RULES
    If Ollama is down, toggled off, or the model is not pulled, the note
    still gets written - carrying the traces and the reason no reflection
    was produced. A day without a model answer must not become a day
    with no record. Follow-through is labelled an estimate everywhere it
    appears; keyword overlap cannot truly know why a planned thing
    didn't happen.
"""

from __future__ import annotations

import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Shared_By_All_Agents
PROJECT_ROOT = HERE.parent                      # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import call_the_local_model                       # noqa: E402
import local_model_settings                       # noqa: E402
from Shared_By_All_Screens.trace_every_action import (   # noqa: E402
    brief_for_the_model, estimated_follow_through,
    plan_items_from_note, trace,
)

DAILY_NOTES = PROJECT_ROOT / "Documentation" / "Daily_Notes"


def _yesterdays_plan(day: date) -> tuple[list[dict], str]:
    """Yesterday's note's checklist, for follow-through scoring."""
    note = DAILY_NOTES / f"{day.isoformat()}.md"
    if not note.exists():
        return [], ""
    text = note.read_text(encoding="utf-8")
    return plan_items_from_note(text), text


def _agent_run_tails(last: int = 5) -> str:
    """One line per recent agent run, from each agent's own memory."""
    try:
        from remember_and_recall import recent_runs               # noqa: E402
        lines = []
        agents_dir = PROJECT_ROOT / "Agents"
        for folder in sorted(agents_dir.iterdir()):
            if not folder.is_dir():
                continue
            for row in recent_runs(folder.name, last=last):
                lines.append(f"- {folder.name}: {row['outcome']} "
                             f"({row['job_shape']}) at {row['timestamp']}")
        return "\n".join(lines) or "- no agent runs recorded yet"
    except Exception as trouble:                                  # noqa: BLE001
        return f"- agent run history unavailable ({trouble})"

def build_the_prompt(day: date, trace_brief: str,
                     follow_through: dict | None) -> str:
    """Everything the model sees, in one block. Deliberately factual."""
    parts = [
        "You are INKY's day planner. Below is a factual record of everything",
        "that happened in the system today, followed by yesterday's plan and",
        "how much of it shows evidence of being done.",
        "",
        "=== TODAY'S TRACE RECORD ===",
        trace_brief,
        "",
        "=== AGENT RUNS ===",
        _agent_run_tails(),
    ]
    if follow_through and follow_through.get("planned"):
        parts += ["",
                  "=== YESTERDAY'S PLAN FOLLOW-THROUGH (estimate) ===",
                  f"{follow_through['evidenced']} of {follow_through['planned']} "
                  f"planned items have evidence in today's activity "
                  f"(~{follow_through['estimated_follow_through_pct']}%)."]
    parts += ["",
              "=== YOUR TASK ===",
              "Write exactly these four sections, markdown, no preamble:",
              "## What happened today",
              "  3-5 bullet points of facts from the record above.",
              "## What went well",
              "  1-3 bullets.",
              "## Frictions and gaps",
              "  1-3 bullets - errors, stalls, things measured but not acted on.",
              "## Plan for tomorrow",
              "  3-6 checklist items, each '- [ ] <specific action>', grounded",
              "  in the frictions above. Concrete and checkable, not vague."]
    return "\n".join(parts)


def write_the_note(day: date, body: str, *, reflected: bool,
                   model_name: str = "", seconds: float = 0.0) -> Path:
    """The day's note, whatever happened - even a no-reflection day."""
    DAILY_NOTES.mkdir(parents=True, exist_ok=True)
    path = DAILY_NOTES / f"{day.isoformat()}.md"
    header = (f"---\ntitle: Daily Note {day.isoformat()}\n"
              f"type: daily-note\nreflected: {str(reflected).lower()}\n"
              f"model: {model_name or '—'}\n---\n\n"
              f"# Daily Note — {day.isoformat()}\n\n")
    footer = (f"\n\n---\n*Reflected by {model_name} in {seconds:.0f}s.*\n"
              if reflected else
              "\n\n---\n*No local-model reflection was produced for this note - "
              "the traces are still here, so a later reflection can use them.*\n")
    path.write_text(header + body + footer, encoding="utf-8")
    return path


def reflect_on_the_day(day: date | None = None) -> dict:
    """The whole loop for one day. Returns what happened, honestly."""
    day = day or date.today()
    trace("day_planner", "agent", "start_reflection", target=str(day))

    trace_brief = brief_for_the_model(day)
    plan_items, _ = _yesterdays_plan(day - timedelta(days=1))
    follow_through = estimated_follow_through(plan_items, trace_brief)

    if not local_model_settings.is_enabled():
        body = ("## Skipped\n\nThe local-model toggle is OFF, so no "
                f"reflection was generated.\n\n{trace_brief}")
        path = write_the_note(day, body, reflected=False)
        trace("day_planner", "agent", "reflection_skipped", outcome="escalated")
        return {"has_data": False, "note": "local model toggle is off",
                "note_path": str(path)}

    if not call_the_local_model.is_ollama_running():
        body = ("## Skipped\n\nOllama was not reachable, so no reflection "
                f"was generated.\n\n{trace_brief}")
        path = write_the_note(day, body, reflected=False)
        trace("day_planner", "agent", "reflection_skipped", outcome="escalated")
        return {"has_data": False, "note": "ollama not reachable",
                "note_path": str(path)}

    started = time.time()
    answer = call_the_local_model.ask(build_the_prompt(day, trace_brief,
                                                       follow_through))
    seconds = time.time() - started

    if not answer.get("has_data"):
        body = (f"## Skipped\n\nThe local model did not answer: "
                f"{answer.get('note')}\n\n{trace_brief}")
        path = write_the_note(day, body, reflected=False)
        trace("day_planner", "agent", "reflection_failed", outcome="fail")
        return {"has_data": False, "note": answer.get("note"),
                "note_path": str(path)}

    # Strip reasoning-model scratchpad, same as the Finance chat door.
    text = re.sub(r"<think>.*?</think>\s*", "", answer["text"],
                  flags=re.DOTALL)
    text = re.sub(r"<think>.*$", "", text, flags=re.DOTALL).strip()

    path = write_the_note(day, text, reflected=True,
                          model_name=answer.get("model", ""),
                          seconds=seconds)
    trace("day_planner", "agent", "reflection_written",
          target=path.name, duration_ms=int(seconds * 1000))
    return {"has_data": True, "note_path": str(path),
            "model": answer.get("model"), "seconds_taken": seconds,
            "follow_through": follow_through}


def main() -> None:
    result = reflect_on_the_day()
    print("REFLECT ON THE DAY")
    print("=" * 50)
    print(f"  reflected : {result['has_data']}")
    print(f"  note      : {result.get('note_path')}")
    if result["has_data"]:
        print(f"  model     : {result.get('model')} "
              f"({result.get('seconds_taken', 0):.0f}s)")
    else:
        print(f"  reason    : {result.get('note')}")


if __name__ == "__main__":
    main()

