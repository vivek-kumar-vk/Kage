"""run_headless_cli - one ladder, walked bottom-up, for agent jobs that
may need more than pure Python.

THE LADDER (cheapest rung first, CLI last - ADR-056's deterministic-first
order, extended one rung):

    Tier 0   a plain Python callable the job carries (a lookup, a formula)
    Tier 1   the LOCAL model, qwen3:8b through call_the_local_model.ask
             - costs nothing, sends nothing off this laptop
    Tier 2   a headless CLI (`agy --print`, `gemini -p`, `claude -p`) -
             real money and unverified billing, so it is GATED by
             ../cli_orchestration_settings.json. Resting state per
             ADR-132: agy ON (first CLI rung), claude ON but locked
             behind the owner's explicit approval on each job, gemini
             OFF until the owner says otherwise.

run_headless(job, tier) walks up from Tier 0 and stops at the first rung
that actually answers. `tier` is a CEILING, never a target: asking for
tier=2 cannot make the ladder skip Tier 1. When the gate is off, or the
CLI errors, times out, or exits nonzero, the attempt is recorded and
traced and the walk continues - nothing depends on Tier 2 ever answering.

NOT registered in the_tool_registry, on purpose: the registry's own
definition of a tool is "deterministic, never calls a model". This file
is called directly, exactly like call_the_local_model.py next door.

NO DAEMON MODE. NO KEY ADAPTERS. Gemini is reached only through its
official subscription login; _command_for refuses to build any command
carrying a daemon flag or an API-key flag, whatever the settings say.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent              # Shared_By_All_Agents/Tools
_SHARED = _HERE.parent                              # Shared_By_All_Agents
_PROJECT_ROOT = _SHARED.parent                      # the inky folder
for _folder in (_PROJECT_ROOT, _SHARED, _SHARED / "Tools"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

SETTINGS_FILE = _SHARED / "cli_orchestration_settings.json"

# Flags that would turn a one-shot headless ask into something that
# lingers, listens, or authenticates with a key instead of a login.
# Refused in code, whatever the settings file says.
_BANNED_FLAG_PIECES = ("daemon", "--api-key", "api_key",
                       "service_account", "credentials")
_BANNED_SHORT_FLAGS = {"-k", "-d"}

# Escalation order among the CLIs (ADR-132): agy first - it rides the
# owner's Google AI Pro subscription with no visible per-call cost;
# gemini second for the same reason; claude LAST - it is the strongest
# model in the chain (claude-sonnet-5, measured $0.0078 for one hello)
# and therefore the one rung an agent may only touch with the owner's
# explicit approval on that job.
PROVIDER_ORDER = ["agy", "gemini", "claude"]

# The key a job must carry (True) before the claude rung will be built.
# Set by whoever recorded the owner's yes - no yes, no Claude.
OWNER_APPROVAL_KEY = "owner_approved"

# How each CLI is asked to print one answer and exit. Everything here is
# the one-shot form of the CLI - never a serve/daemon mode.
_PROMPT_FLAG = {"claude": "-p", "gemini": "-p", "agy": "--print"}


def load_the_gate() -> dict:
    """Read the settings fresh on every call - flipping the owner's flag
    takes effect on the next job, with no restart and no cache."""
    if not SETTINGS_FILE.exists():
        return {"enabled": False}
    try:
        gate = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except ValueError:
        return {"enabled": False}   # unreadable gate reads as closed gate
    return gate if isinstance(gate, dict) else {"enabled": False}


def _trace_attempt(subject: str, outcome: str, detail: dict,
                   duration_ms: int) -> None:
    """One row in the trace ledger per ladder attempt. Kept behind a tiny
    function so tests can watch it without writing real ledger rows."""
    try:
        from Shared_By_All_Screens.trace_every_action import trace
        trace("run_headless_cli", "skill", subject, target=str(detail)[:120],
              outcome=outcome, duration_ms=duration_ms)
    except Exception:                                              # noqa: BLE001
        pass    # the ledger must never be the thing that breaks a job


def _command_for(provider_name: str, provider: dict, prompt: str,
                 gate: dict) -> list[str] | None:
    """The exact argv for one CLI attempt, or None if the settings ask
    for something this file refuses to build."""
    if provider.get("enabled") is not True:
        return None
    if provider.get("requires_owner_approval") is True:
        # ADR-132: the claude rung answers only jobs that carry the
        # owner's explicit yes. Without it the rung is skipped and the
        # skip is traced - an agent can never spend the owner's Claude
        # money on its own initiative.
        if provider.get(OWNER_APPROVAL_KEY) is not True:
            return None
    command = str(provider.get("command") or "").strip()
    if not command:
        return None
    argv = [command, _PROMPT_FLAG.get(provider_name, "-p"), prompt]
    for extra in provider.get("args") or []:
        argv.append(str(extra))
    if provider_name == "claude":
        argv += ["--max-turns", str(int(gate.get("max_turns", 1)))]
    lowered = [part.lower() for part in argv]
    joined = " ".join(lowered)
    if any(banned in joined for banned in _BANNED_FLAG_PIECES):
        return None
    # Short flags get an exact match too - "-d" contains no long word.
    for part in lowered:
        if part in _BANNED_SHORT_FLAGS:
            return None
    return argv


def run_headless(job, tier: int = 2) -> dict:
    """Walk the ladder for one job. job is a dict:

        prompt   the ask itself (required)
        tier0    optional zero-argument callable returning a dict with
                 has_data - pure Python, tried first when present

    tier is the ceiling this call may climb to. Returns has_data plus
    tier_used (the rung that answered), the text, and attempts - one
    entry per rung that was tried and did not answer. An honest failure
    after every allowed rung is has_data: False with the trail attached.
    """
    started = time.time()
    prompt = str((job or {}).get("prompt") or "").strip()
    if not prompt:
        return {"has_data": False, "note": "run_headless was given no prompt.",
                "attempts": []}
    tier = max(0, min(int(tier), 2))
    attempts: list[dict] = []

    # ---- Tier 0: the job's own Python ---------------------------------
    zero = (job or {}).get("tier0")
    if callable(zero):
        try:
            answer = zero()
        except Exception as problem:                           # noqa: BLE001
            attempts.append({"tier": 0, "outcome": f"raised: {problem}"})
        else:
            if isinstance(answer, dict) and answer.get("has_data"):
                _trace_attempt("tier0", "ok",
                               {"tier_used": 0}, int((time.time() - started) * 1000))
                return {**answer, "tier_used": 0, "attempts": attempts}
            attempts.append({"tier": 0, "outcome": "answered without data"})

    # ---- Tier 1: the local model --------------------------------------
    if tier >= 1:
        from call_the_local_model import ask as local_ask
        local_answer = local_ask(prompt)
        if local_answer.get("has_data") and str(local_answer.get("text", "")).strip():
            _trace_attempt("tier1", "ok", {"model": local_answer.get("model")},
                           int((time.time() - started) * 1000))
            return {"has_data": True, "tier_used": 1,
                    "text": local_answer["text"], "model": local_answer.get("model"),
                    "tokens_in": local_answer.get("tokens_in"),
                    "tokens_out": local_answer.get("tokens_out"),
                    "attempts": attempts}
        attempts.append({"tier": 1,
                         "outcome": local_answer.get("note") or "no usable answer"})

    # ---- Tier 2: headless CLIs, gated ---------------------------------
    if tier >= 2:
        gate = load_the_gate()
        if not gate.get("enabled"):
            attempts.append({"tier": 2, "outcome": "gate off by settings"})
            _trace_attempt("tier2_gate", "skipped", {}, 0)
        else:
            for provider_name in PROVIDER_ORDER:
                entry = dict(gate.get("providers", {}).get(
                    provider_name, {}))
                needs_owner_ok = (entry.get("requires_owner_approval")
                                  is True)
                if needs_owner_ok:
                    entry[OWNER_APPROVAL_KEY] = ((job or {}).get(
                        OWNER_APPROVAL_KEY) is True)
                argv = _command_for(provider_name, entry, prompt, gate)
                if argv is None:
                    if needs_owner_ok:
                        attempts.append(
                            {"tier": 2, "provider": provider_name,
                             "outcome": ("skipped: owner approval "
                                         "required (ADR-132)")})
                        _trace_attempt(f"tier2_{provider_name}",
                                       "owner_approval_required", {}, 0)
                    continue          # provider off or refused
                attempt_started = time.time()
                try:
                    finished = subprocess.run(
                        argv, capture_output=True, text=True,
                        timeout=float(gate.get("timeout_s", 300)))
                    seconds_ms = int((time.time() - attempt_started) * 1000)
                    if finished.returncode == 0 and finished.stdout.strip():
                        _trace_attempt(f"tier2_{provider_name}", "ok",
                                       {"exit_code": 0}, seconds_ms)
                        return {"has_data": True, "tier_used": 2,
                                "provider": provider_name,
                                "text": finished.stdout.strip(),
                                "attempts": attempts}
                    reason = (f"exited {finished.returncode}: "
                              f"{(finished.stderr or '')[:200]}")
                except subprocess.TimeoutExpired:
                    reason = f"timed out past {gate.get('timeout_s', 300)}s"
                    seconds_ms = int(gate.get("timeout_s", 300) * 1000)
                except OSError as problem:
                    reason = f"could not start the CLI: {problem}"
                    seconds_ms = int((time.time() - attempt_started) * 1000)
                attempts.append({"tier": 2, "provider": provider_name,
                                 "outcome": reason})
                _trace_attempt(f"tier2_{provider_name}", "fail",
                               {"reason": reason[:120]}, seconds_ms)

    return {"has_data": False,
            "note": ("every rung of the ladder up to Tier "
                     f"{tier} came back empty - see attempts for which "
                     "rung said what"),
            "attempts": attempts}

