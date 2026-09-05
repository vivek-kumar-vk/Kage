"""The Calendar card's learning agent (D23).

Once a night it looks at what actually happened - coding time from
WakaTime, commits in this repo, what was already on the calendar, what
the Email card flagged - and answers two questions:

    notes      what happened on this day, in one line each. Observation.
    proposals  what should go ON the calendar next. Intention.

Notes are written to the store immediately: they describe the past, and
the day's real signals are their evidence. Proposals are not. Writing to
Google Calendar rings the owner's phone, so a proposal sits as `pending`
until it is approved (or until CALENDAR_AUTO_WRITE is deliberately
turned on). That asymmetry is the whole safety design of this file.

Two brains, one prompt:

    claude_cli  one `claude -p` per run, ends when it answers. The Email
                card's proven path - already logged in, no key in .env.
    omniroute   the same prompt POSTed to the gateway on 8010, which is
                where Hermes and DeepSeek arrive (PLAN item 3).

A brain that is not there reports "offline" and the run is skipped. It
never falls back to guessing something onto a real calendar.
"""

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import calendar_store as store
import settings_for_main_menu as cfg


class AgentError(RuntimeError):
    """A failure said in one sentence the card can print."""


# ---------------------------------------------------------------------
# THE BRAIN
# ---------------------------------------------------------------------
def _gateway_key():
    """Same lookup the Model screen uses, done locally rather than by
    importing across screens (CLAUDE.md Rule 5)."""
    if os.environ.get("GATEWAY_API_KEY"):
        return os.environ["GATEWAY_API_KEY"]
    env_file = cfg.PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("GATEWAY_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def brain_state():
    """Which brain would run, and whether it is actually reachable."""
    backend = cfg.CALENDAR_AGENT_BACKEND
    if backend == "claude_cli":
        if not shutil.which("claude"):
            return {"state": "offline", "backend": backend,
                    "model": cfg.CALENDAR_AGENT_MODEL,
                    "detail": "the claude CLI is not on PATH"}
        return {"state": "ok", "backend": backend,
                "model": cfg.CALENDAR_AGENT_MODEL, "detail": ""}
    if backend == "omniroute":
        base = cfg.OMNIROUTE_BASE_URL.rstrip("/")
        try:
            request = urllib.request.Request(
                f"{base}/v1/models",
                headers={"accept": "application/json",
                         "Authorization": f"Bearer {_gateway_key()}"})
            with urllib.request.urlopen(request, timeout=3):
                pass
        except Exception as problem:  # noqa: BLE001 - unreachable is a real state
            return {"state": "offline", "backend": backend,
                    "model": cfg.CALENDAR_AGENT_MODEL,
                    "detail": f"gateway {base} unreachable ({problem})"}
        return {"state": "ok", "backend": backend,
                "model": cfg.CALENDAR_AGENT_MODEL, "detail": ""}
    return {"state": "offline", "backend": backend,
            "model": cfg.CALENDAR_AGENT_MODEL,
            "detail": f"unknown CALENDAR_AGENT_BACKEND {backend!r}"}


def _run_claude_cli(prompt):
    path = shutil.which("claude")
    if not path:
        raise AgentError("the claude CLI is not on PATH")
    result = subprocess.run(
        [path, "-p", "--model", cfg.CALENDAR_AGENT_MODEL],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=cfg.CALENDAR_AGENT_TIMEOUT,
    )
    text = result.stdout.decode("utf-8", errors="replace").strip()
    if result.returncode != 0 or not text:
        detail = result.stderr.decode("utf-8", errors="replace")[:300]
        raise AgentError(f"claude -p failed: {detail or 'empty answer'}")
    return text


def _run_omniroute(prompt):
    """OpenAI-compatible chat completion against the gateway - the same
    shape the Model screen already reads /v1/models from."""
    base = cfg.OMNIROUTE_BASE_URL.rstrip("/")
    body = json.dumps({
        "model": cfg.CALENDAR_AGENT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/v1/chat/completions", data=body, method="POST",
        headers={"content-type": "application/json",
                 "Authorization": f"Bearer {_gateway_key()}"})
    try:
        with urllib.request.urlopen(request, timeout=cfg.CALENDAR_AGENT_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as problem:
        raise AgentError(f"gateway answered HTTP {problem.code}")
    except Exception as problem:  # noqa: BLE001
        raise AgentError(f"gateway {base} unreachable ({problem})")
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise AgentError("gateway answered without a message")


def _run(prompt):
    if cfg.CALENDAR_AGENT_BACKEND == "omniroute":
        return _run_omniroute(prompt)
    return _run_claude_cli(prompt)


def _extract_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise AgentError("no JSON object in the agent's answer")
    try:
        return json.loads(text[start:end + 1])
    except ValueError as problem:
        raise AgentError(f"the agent's JSON did not parse ({problem})")


# ---------------------------------------------------------------------
# THE SIGNALS - only things that really happened
# ---------------------------------------------------------------------
def _git_commits(day):
    """Commits authored in this repo on that day. `git` missing or this
    not being a repo is not an error - it is one fewer signal."""
    try:
        result = subprocess.run(
            ["git", "log", "--no-merges", f"--since={day} 00:00",
             f"--until={day} 23:59", "--pretty=format:%s"],
            cwd=str(cfg.PROJECT_ROOT), stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in
            result.stdout.decode("utf-8", errors="replace").splitlines() if line][:20]


def _email_signal():
    """What the Email card already knows, if it is connected. Guarded:
    the calendar must work whether or not Gmail ever gets set up."""
    try:
        import email_pipeline
        summary = email_pipeline.summary(24)
    except Exception:  # noqa: BLE001 - a card that is down is not an error here
        return None
    if summary.get("state") != "ok":
        return None
    return {"total": summary.get("total"),
            "priority": summary.get("counts", {}).get("priority")}


def gather(day):
    """Everything real that is known about one day."""
    waka = store.waka_on(day)
    return {
        "day": day,
        "weekday": date.fromisoformat(day).strftime("%A"),
        "coding_seconds": (waka or {}).get("total_seconds"),
        "top_project": (waka or {}).get("top_project"),
        "top_language": (waka or {}).get("top_language"),
        "commits": _git_commits(day),
        "events": [{"summary": e["summary"], "start": e["start_iso"],
                    "all_day": bool(e["all_day"])}
                   for e in store.events_on(day)],
        "email": _email_signal(),
    }


def has_any_signal(signals):
    """A day with nothing real in it gets no agent run at all - that is
    cheaper and it is the only way the notes stay evidence-backed."""
    return bool(signals["commits"] or signals["events"]
                or signals["coding_seconds"] or signals["email"])


# ---------------------------------------------------------------------
# THE PROFILE - identity.md / context.md / goal.md / memory.md, read fresh
# every run so editing the files changes behavior without touching code.
# ---------------------------------------------------------------------
def _read_text(path):
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _recent_memory(path, lines=10):
    text = _read_text(path)
    if not text:
        return "(no runs recorded yet)"
    body = [line for line in text.splitlines() if line and not line.startswith("#")]
    return "\n".join(body[-lines:]) or "(no runs recorded yet)"


def _load_profile():
    here = Path(__file__).resolve().parent
    return {
        "identity": _read_text(here / "identity.md"),
        "context": _read_text(here / "context.md"),
        "goal": _read_text(here / "goal.md"),
        "memory": _recent_memory(here / "memory.md"),
    }


def _append_memory(day, notes, proposals, detail):
    here = Path(__file__).resolve().parent
    line = f"- {day}: {notes} note(s), {proposals} proposal(s) - {detail}\n"
    with open(here / "memory.md", "a", encoding="utf-8") as handle:
        handle.write(line)


# ---------------------------------------------------------------------
# THE PROMPT
# ---------------------------------------------------------------------
PROFILE_BLOCK = """# Who you are
{identity}

# What you know about the system you run in
{context}

# Where this is headed
{goal}

# Your own recent runs
{memory}

---
"""

PROMPT = """Below is EVERYTHING that is known about one day. It is the only evidence
you have. You have two jobs.

1. NOTES - describe what actually happened that day, one short line each
   (max 9 words). Only from the evidence. If the evidence is thin, write
   fewer notes. Never write a note the evidence does not support.

2. PROPOSALS - calendar events worth adding to the NEXT few days, based
   on what this day shows. Propose only when there is a real reason in
   the evidence: unfinished work that has a natural follow-up, a rhythm
   worth protecting, a deadline implied by an existing event. Propose
   nothing if nothing is warranted - an empty list is the right answer
   more often than not. Never propose a meeting with another person.
   Never invent an attendee, a place or a deadline.

Every proposal needs `reason`: the specific evidence it came from.

Times are local, 24h, format YYYY-MM-DDTHH:MM:SS. Proposals must start
after {today}T00:00:00 and within the next 14 days.

Answer with ONLY this JSON object, no prose before or after:
{{"notes":[{{"kind":"code|meeting|mail|other","text":"..."}}],
  "proposals":[{{"summary":"...","start":"...","end":"...",
                "description":"...","reason":"..."}}]}}

Evidence:
{evidence}"""


def run_for_day(day, propose=True):
    """One learning run for one day. Returns a plain dict the endpoint
    hands straight to the card."""
    state = brain_state()
    if state["state"] != "ok":
        return {"state": "brain_offline", "detail": state["detail"],
                "notes": 0, "proposals": 0}

    signals = gather(day)
    if not has_any_signal(signals):
        return {"state": "no_signal",
                "detail": f"nothing recorded for {day}",
                "notes": 0, "proposals": 0}

    full_prompt = PROFILE_BLOCK.format(**_load_profile()) + PROMPT.format(
        today=date.today().isoformat(),
        evidence=json.dumps(signals, indent=2, default=str))
    answer = _extract_json(_run(full_prompt))

    written_notes = 0
    for note in answer.get("notes", []) or []:
        text = str(note.get("text", "")).strip()[:160]
        kind = str(note.get("kind", "other")).strip()[:20] or "other"
        if text:
            store.add_note(day, kind, text)
            written_notes += 1

    written_proposals = 0
    if propose:
        horizon = date.today() + timedelta(days=14)
        for item in answer.get("proposals", []) or []:
            summary = str(item.get("summary", "")).strip()[:200]
            start_iso = str(item.get("start", "")).strip()
            end_iso = str(item.get("end", "")).strip()
            if not summary or not start_iso:
                continue
            try:
                start_at = datetime.fromisoformat(start_iso)
            except ValueError:
                continue
            # A proposal outside the stated horizon is dropped rather
            # than clamped - a silently moved event is worse than none.
            if not (date.today() <= start_at.date() <= horizon):
                continue
            store.add_proposal(
                start_at.date().isoformat(), summary, start_iso, end_iso,
                str(item.get("description", ""))[:1000],
                str(item.get("reason", ""))[:300])
            written_proposals += 1

    store.set_meta("last_agent_run", datetime.now().isoformat(timespec="seconds"))
    detail = (f"from {len(signals['commits'])} commit(s), "
              f"{signals['coding_seconds'] or 0}s coding")
    _append_memory(day, written_notes, written_proposals, detail)
    return {"state": "ok", "detail": "", "notes": written_notes,
            "proposals": written_proposals}


def run_recent(days=3):
    """The nightly job: re-read the last few days, since WakaTime and
    the commit log both settle late."""
    results = {}
    for offset in range(days):
        day = (date.today() - timedelta(days=offset)).isoformat()
        try:
            results[day] = run_for_day(day)
        except AgentError as problem:
            results[day] = {"state": "error", "detail": str(problem),
                            "notes": 0, "proposals": 0}
    return results
