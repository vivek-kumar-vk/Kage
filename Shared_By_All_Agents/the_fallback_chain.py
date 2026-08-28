"""the_fallback_chain - the Orchestrator seat's quality-first call chain.

THE CHAIN (Phase H step 4.1, seat per ADR-132)

    rung 1   claude CLI      - the Orchestrator seat. Only built when the
                               gate in cli_orchestration_settings.json is
                               enabled AND this job carries
                               owner_approved=True. Everything the ladder
                               refuses (daemon flags, key flags) is refused
                               here too, because the argv is built by the
                               ladder's own _command_for.
    rung 2   Model B  8081   - the deep local MoE model
    rung 3   Model A  8080   - the fast local workhorse model
    rung 4   free Groq, then free OpenRouter - via ask_the_free_providers

WHY THE ORDER DIFFERS FROM THE LADDER NEXT DOOR
    run_headless_cli.py walks cheapest-first because an ordinary agent
    job should cost nothing. The Orchestrator seat exists precisely for
    the jobs where cheap-and-wrong is the expensive outcome (Validation
    Contracts, DAG plans), so this chain walks strongest-first and
    degrades honestly rung by rung instead.

WHY THE MODEL NAMES ARE NOWHERE IN THIS FILE
    Working rule: never hardcode a model name. Each local rung asks its
    server's /v1/models what it serves and takes the first chat model -
    exactly what Tests/test_the_local_models.py does live.

TRACING
    One correlation_id ties every row of one walk together. Each rung
    attempted leaves a kind="model" row (actor "orchestrator",
    action "fallback_chain_rung") and the walk ends with an
    action="fallback_chain_result" row saying which rung answered.

RUN IT
    cd <repo root>
    python Shared_By_All_Agents\\the_fallback_chain.py "plan this" ^
        [--owner-approved]

    --owner-approved is a claim that the owner said yes for THIS job;
    the claude rung still will not move unless the settings gate agrees.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent              # Shared_By_All_Agents
_PROJECT_ROOT = _HERE.parent                        # the inky folder
for _folder in (_PROJECT_ROOT, _PROJECT_ROOT / "Shared_By_All_Screens"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

try:
    from Shared_By_All_Agents.Tools.run_headless_cli import (
        OWNER_APPROVAL_KEY, _command_for, load_the_gate)
except ImportError:                                # pragma: no cover
    sys.path.insert(0, str(_HERE / "Tools"))
    from Tools.run_headless_cli import (
        OWNER_APPROVAL_KEY, _command_for, load_the_gate)

try:
    from Shared_By_All_Screens.trace_every_action import (
        new_correlation_id, trace)
except ImportError:                                # pragma: no cover
    from trace_every_action import new_correlation_id, trace   # noqa: E402

try:
    import ask_the_free_providers                   # noqa: E402
except ImportError:                                # pragma: no cover
    sys.path.insert(0, str(_HERE))
    import ask_the_free_providers                   # noqa: E402,F401

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# The seat (ADR-132). The deputy (agy) and gemini stay the ladder's
# business; this chain escalates from the seat downward.
SEAT_PROVIDER = "claude"

BASE_MODEL_B = "http://127.0.0.1:8081"
BASE_MODEL_A = "http://127.0.0.1:8080"

LOCAL_TIMEOUT_SECONDS = 180.0     # Model B thinks slowly when both share VRAM
LOCAL_CONNECT_TIMEOUT = 3.0       # a down server is a skip, not a wait

ACTOR = "orchestrator"
FREE_PROVIDERS_IN_ORDER = ["groq", "openrouter"]


# =====================================================================
# local rungs
# =====================================================================
def _get_json(url: str, timeout: float):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError,
            json.JSONDecodeError):
        return None


def _first_local_model(base_url: str) -> str | None:
    """The served name, read live - never assumed."""
    data = _get_json(f"{base_url}/v1/models", LOCAL_CONNECT_TIMEOUT)
    rows = (data or {}).get("data") or []
    return rows[0].get("id") if rows else None

def _ask_local_model(base_url: str, prompt: str) -> dict:
    """One non-streaming completion against a local OpenAI-compatible
    endpoint (the llama.cpp servers both models run on).

    Returns has_data/text/model or has_data=False with a plain reason.
    A thinking-model answer may arrive in reasoning_content when
    content is empty (ADR-131) - the content field wins, reasoning is
    the fallback, never the other way round.
    """
    model_name = _first_local_model(base_url)
    if not model_name:
        return {"has_data": False,
                "note": f"no model list at {base_url} - server down or empty"}
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(
                request, timeout=LOCAL_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError,
            json.JSONDecodeError) as problem:
        return {"has_data": False,
                "note": f"{base_url} failed: {problem}"}
    choice = ((data.get("choices") or [{}])[0])
    message = choice.get("message") or {}
    text = (message.get("content") or message.get("reasoning_content")
            or "").strip()
    if not text:
        return {"has_data": False, "note": f"{base_url} returned no text"}
    return {"has_data": True, "text": text, "model": model_name}


# =====================================================================
# the seat rung
# =====================================================================
def _ask_seat(prompt: str, owner_approved: bool) -> dict:
    """One claude CLI attempt through the ladder's own argv builder.

    Every refusal here is inherited from run_headless_cli: gate off,
    provider off, owner_approval missing, daemon/key flag smuggled in -
    each is a plain 'no' with a reason, never an exception.
    """
    gate = load_the_gate()
    if not gate.get("enabled"):
        return {"has_data": False, "note": "gate off by settings"}
    entry = dict(gate.get("providers", {}).get(SEAT_PROVIDER, {}))
    entry[OWNER_APPROVAL_KEY] = bool(owner_approved)
    argv = _command_for(SEAT_PROVIDER, entry, prompt, gate)
    if argv is None:
        if entry.get("requires_owner_approval") and not owner_approved:
            return {"has_data": False,
                    "note": ("seat skipped: the owner has not approved "
                             "this job (ADR-132)")}
        return {"has_data": False, "note": "seat refused by the ladder"}
    try:
        finished = subprocess.run(
            argv, capture_output=True, text=True,
            timeout=float(gate.get("timeout_s", 300)))
    except subprocess.TimeoutExpired:
        return {"has_data": False,
                "note": f"seat timed out past {gate.get('timeout_s', 300)}s"}
    except OSError as problem:
        return {"has_data": False,
                "note": f"could not start the CLI: {problem}"}
    if finished.returncode != 0 or not finished.stdout.strip():
        return {"has_data": False,
                "note": (f"seat exited {finished.returncode}: "
                         f"{(finished.stderr or '')[:160]}")}
    return {"has_data": True, "text": finished.stdout.strip(),
            "model": SEAT_PROVIDER}


# =====================================================================
# the walk
# =====================================================================
def walk_the_chain(prompt: str, correlation_id: str | None = None,
                   owner_approved: bool = False) -> dict:
    """Walk seat -> Model B -> Model A -> free Groq -> free OpenRouter.

    Stops at the first rung that actually answers. Every attempt is
    traced under one correlation_id. When every rung is empty the
    answer says so plainly - empty beats fake.
    """
    correlation_id = correlation_id or new_correlation_id()
    attempts: list[dict] = []

    def _note(rung: str, outcome: str, detail: dict, ms: int) -> None:
        attempts.append({"rung": rung, "outcome": outcome})
        trace(ACTOR, "model", "fallback_chain_rung", target=rung,
              detail={**{k: v for k, v in detail.items() if v is not None},
                      "correlation_id": correlation_id},
              outcome=outcome, duration_ms=ms or None,
              correlation_id=correlation_id)

    # ---- rung 1: the seat ------------------------------------------
    started = time.time()
    seat = _ask_seat(prompt, owner_approved)
    _note("seat_claude", "ok" if seat.get("has_data") else "fail",
          {"reason": None if seat.get("has_data") else seat.get("note")},
          int((time.time() - started) * 1000))
    if seat.get("has_data"):
        return _answered("seat_claude", seat["text"], SEAT_PROVIDER,
                         attempts, correlation_id)

    # ---- rungs 2 and 3: the local models ---------------------------
    for rung_name, base_url in (("model_b", BASE_MODEL_B),
                                ("model_a", BASE_MODEL_A)):
        started = time.time()
        local = _ask_local_model(base_url, prompt)
        _note(rung_name, "ok" if local.get("has_data") else "fail",
              {"reason": None if local.get("has_data") else local.get("note"),
               "model": local.get("model")},
              int((time.time() - started) * 1000))
        if local.get("has_data"):
            return _answered(rung_name, local["text"], local["model"],
                             attempts, correlation_id)

    # ---- rung 4: the free providers --------------------------------
    for provider_id in FREE_PROVIDERS_IN_ORDER:
        started = time.time()
        free = ask_the_free_providers.ask_one(provider_id, prompt=prompt)
        ok = free.get("outcome") == "ok"
        skipped = free.get("outcome") == "skipped_no_key"
        _note(f"free_{provider_id}",
              "ok" if ok else ("skip" if skipped else "fail"),
              {"reason": free.get("error"), "model": free.get("model"),
               "answer_chars": free.get("answer_chars")},
              free.get("latency_ms") or int((time.time() - started) * 1000))
        if ok:
            return _answered(f"free_{provider_id}", "", free.get("model"),
                             attempts, correlation_id)

    trace(ACTOR, "model", "fallback_chain_result", target="every_rung_empty",
          detail={"correlation_id": correlation_id}, outcome="fail",
          correlation_id=correlation_id)
    return {"has_data": False,
            "note": ("every rung came back empty - see attempts for "
                     "which rung said what"),
            "attempts": attempts, "correlation_id": correlation_id}


def _answered(rung: str, text: str, model, attempts, correlation_id) -> dict:
    """The one honest success shape, with its closing ledger row."""
    trace(ACTOR, "model", "fallback_chain_result", target=rung,
          detail={"correlation_id": correlation_id}, outcome="ok",
          correlation_id=correlation_id)
    return {"has_data": True, "rung_used": rung, "text": text,
            "model": model, "attempts": attempts,
            "correlation_id": correlation_id}


# =====================================================================
# RUNNABLE
# =====================================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Walk the Orchestrator's fallback chain once.")
    parser.add_argument("prompt")
    parser.add_argument("--owner-approved", action="store_true",
                        help="claim the owner approved THIS job for the seat")
    args = parser.parse_args()
    result = walk_the_chain(args.prompt, owner_approved=args.owner_approved)
    if result.get("has_data"):
        print(f"[answered by {result['rung_used']}] "
              f"(correlation_id {result['correlation_id']})")
        if result["text"]:
            print(result["text"])
        return 0
    print(f"[no rung answered] {result.get('note', '')}")
    print(f"correlation_id {result.get('correlation_id')}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


