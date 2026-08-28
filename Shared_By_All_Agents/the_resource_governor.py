"""The Resource Governor: turns a local model ON when work needs it,
and OFF again after it has been idle for a while.

WHY THIS EXISTS
    Model B is a 30B MoE that eats most of this laptop's RAM and VRAM
    just sitting resident. Left running "just in case", it starves
    everything else; started by hand every time, it is friction nobody
    pays consistently. The governor makes residency follow demand:
    somebody notes "a request for model X is waiting", the governor
    starts that model's real entrypoint if it is not up, and stops it
    again once nothing has asked for it for IDLE_TIMEOUT_SECONDS.

WHAT IT WRAPS (and never reimplements)
    - Ollama: Shared_By_All_Agents/manage_the_local_model.py start() /
      stop() - its ownership rule (INKY only stops what INKY started)
      stays in force; the governor adds nothing on top of it.
    - Model A / Model B: Tools\\run_model_a.bat / Tools\\run_model_b.bat,
      launched as-is so the flags those files specify stay the one
      truth. The same ownership rule applies here: the governor writes
      the pid it started into resource_governor_state.json and refuses
      to stop any port it cannot prove it started itself.

EVERY START AND STOP IS TRACED
    actor "governor", kind "model", with a correlation_id - minted here,
    or carried over from the note_request() call that caused a start -
    so one user-visible action reads start -> serve -> stop as one story
    in Shared_By_All_Screens/Trace_Ledger/.

TESTING RULE
    No test ever launches a real model or kills a real pid. _popen(),
    _taskkill(), is_listening()/model_is_up() and the clock are seams;
    see Tests/test_the_resource_governor.py.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent           # Shared_By_All_Agents
PROJECT_ROOT = HERE.parent                       # the inky folder
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJECT_ROOT))

from Shared_By_All_Screens.trace_every_action import (       # noqa: E402
    new_correlation_id, trace,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# =====================================================================
# WHAT THE GOVERNOR GOVERNS
# =====================================================================
OLLAMA = "ollama"
OLLAMA_PORT = 11434                    # call_the_local_model.OLLAMA_HOST

LAUNCHERS = {
    "model_a": PROJECT_ROOT / "Tools" / "run_model_a.bat",
    "model_b": PROJECT_ROOT / "Tools" / "run_model_b.bat",
}
MODEL_PORTS = {"model_a": 8080, "model_b": 8081}

STATE_FILE = HERE / "resource_governor_state.json"
REQUESTS_FILE = HERE / "resource_governor_requests.json"
SERVE_LOG = HERE / "Saved_Records" / "resource_governor_models.log"

IDLE_TIMEOUT_SECONDS = 300.0           # stop a model idle this long
POLL_SECONDS = 5.0                     # one decision pass per interval

CREATE_NO_WINDOW = 0x08000000          # keep llama-server windows invisible

# Imported lazily so importing THIS file never imports the ollama stack;
# tests swap in a fake before the first governed ollama action.
manage_the_local_model = None


def _manager():
    """The real manage_the_local_model module, imported on first use."""
    global manage_the_local_model
    if manage_the_local_model is None:
        import manage_the_local_model as mod
        manage_the_local_model = mod
    return manage_the_local_model


# =====================================================================
# THE SEAMS - everything a test may replace
# =====================================================================
def is_listening(port: int) -> bool:
    """True when something answers a TCP connect on 127.0.0.1:<port>."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def model_is_up(name: str) -> bool:
    port = OLLAMA_PORT if name == OLLAMA else MODEL_PORTS.get(name)
    if port is None:
        return False
    if name == OLLAMA:
        # The honest check for ollama is the API it serves, not the
        # socket alone - same answer manage_the_local_model trusts.
        try:
            return bool(_manager().call_the_local_model.is_ollama_running())
        except Exception:                                          # noqa: BLE001
            return False
    return is_listening(port)


def _popen(command: list[str]) -> int:
    """Start the launcher detached; returns its pid. Test seam."""
    flags = CREATE_NO_WINDOW if sys.platform == "win32" else 0
    SERVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with SERVE_LOG.open("ab") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=log,  # noqa: S603
                                creationflags=flags)
    return proc.pid


def _taskkill(pid: int) -> bool:
    """End exactly one pid; True when Windows says it worked. Seam."""
    out = subprocess.run(["taskkill", "/PID", str(pid), "/F"],     # noqa: S603
                         capture_output=True, text=True)
    return out.returncode == 0


# =====================================================================
# STATE - small honest json files next to this file
# =====================================================================
def _now_epoch() -> float:
    """The wall clock as a float. A seam so tests can move time."""
    return time.time()


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8")


def read_started() -> dict:
    """Models the governor started and still owns: name -> pid record."""
    return _read_json(STATE_FILE)


def note_request(model_name: str, correlation_id: str | None = None) -> dict:
    """Record 'a request for this model is waiting'.

    This is the demand signal the loop acts on. Callers without their
    own correlation id get one minted, and it rides the trace rows of
    whatever the governor does about the request.
    """
    requests = _read_json(REQUESTS_FILE)
    cid = correlation_id or new_correlation_id()
    requests[model_name] = {
        "requested_at_epoch": _now_epoch(),
        "requested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "correlation_id": cid,
    }
    _write_json(REQUESTS_FILE, requests)
    return {"ok": True, "correlation_id": cid}


def _consume_request(model_name: str) -> None:
    requests = _read_json(REQUESTS_FILE)
    if model_name in requests:
        del requests[model_name]
        _write_json(REQUESTS_FILE, requests)


# =====================================================================
# ACTING - always through an existing entrypoint, always traced
# =====================================================================
def _trace(action: str, target: str, *, outcome: str = "ok",
           detail: dict | None = None, correlation_id: str | None = None,
           duration_ms: int | None = None) -> None:
    trace("governor", "model", action, target=target, detail=detail,
          outcome=outcome, duration_ms=duration_ms,
          correlation_id=correlation_id)


def start_model(name: str, correlation_id: str | None = None) -> dict:
    """Bring one governed model up through ITS OWN entrypoint."""
    started = time.perf_counter()
    cid = correlation_id or new_correlation_id()
    if name == OLLAMA:
        result = dict(_manager().start())
        ok = bool(result.get("ok"))
        if ok:
            # Track residency for the loop's idle check - stopping still
            # goes through manage_the_local_model's own ownership rule.
            state = read_started()
            state[name] = {"managed_by": "manage_the_local_model.py",
                           "started_at_epoch": _now_epoch()}
            _write_json(STATE_FILE, state)
        _trace("start", name,
               outcome="ok" if ok else "fail",
               detail={k: result[k] for k in ("running", "pid", "reason")
                       if k in result},
               correlation_id=cid,
               duration_ms=int((time.perf_counter() - started) * 1000))
        return {**result, "correlation_id": cid}

    launcher = LAUNCHERS.get(name)

    if launcher is None or not launcher.exists():
        note = f"no launcher found for {name}"
        _trace("start", name, outcome="fail", detail={"reason": note},
               correlation_id=cid)
        return {"ok": False, "running": False, "reason": note,
                "correlation_id": cid}

    pid = _popen(["cmd", "/c", str(launcher)])
    state = read_started()
    state[name] = {"pid": pid, "started_at_epoch": _now_epoch()}
    _write_json(STATE_FILE, state)
    _trace("start", name, detail={"entrypoint": launcher.name, "pid": pid},
           correlation_id=cid,
           duration_ms=int((time.perf_counter() - started) * 1000))
    return {"ok": True, "running": True, "pid": pid, "correlation_id": cid}


def stop_model(name: str, correlation_id: str | None = None) -> dict:
    """Stop one governed model - but only one the governor started."""
    started = time.perf_counter()
    cid = correlation_id or new_correlation_id()

    if name == OLLAMA:
        result = dict(_manager().stop())   # its own ownership rule applies
        state = read_started()
        if name in state:
            del state[name]
            _write_json(STATE_FILE, state)
        ok = bool(result.get("ok"))

        _trace("stop", name,
               outcome="ok" if ok else "fail",
               detail={k: result[k] for k in ("running", "stopped_pid", "reason")
                       if k in result},
               correlation_id=cid,
               duration_ms=int((time.perf_counter() - started) * 1000))
        return {**result, "correlation_id": cid}

    state = read_started()
    record = state.get(name)
    if not isinstance(record, dict) or not isinstance(record.get("pid"), int):
        note = (f"{name} was not started by the governor, "
                "so it will not be stopped.")
        _trace("stop_refused_not_ours", name, outcome="fail",
               detail={"reason": note}, correlation_id=cid)
        return {"ok": False,
                "running": is_listening(MODEL_PORTS.get(name, 0)),
                "reason": note, "correlation_id": cid}

    pid = int(record["pid"])
    killed = _taskkill(pid)
    del state[name]
    _write_json(STATE_FILE, state)
    _trace("stop", name,
           outcome="ok" if killed else "fail",
           detail={"stopped_pid": pid},
           correlation_id=cid,
           duration_ms=int((time.perf_counter() - started) * 1000))
    return {"ok": killed, "running": False, "stopped_pid": pid,
            "correlation_id": cid}


# =====================================================================
# DECIDING - one pass of the loop, pure enough to drive from a test
# =====================================================================
def governor_once(*, now_fn=time.time,
                  idle_timeout_seconds: float = IDLE_TIMEOUT_SECONDS) -> list[dict]:
    """One decision pass over every governed model.

    Start when a noted request is waiting and the model is down (one
    attempt per request - a failed start is consumed, never retried in
    a hot loop). Stop when the model is up, ours, and has had no fresh
    request for longer than the idle window. Returns what happened.
    """
    now = now_fn()
    actions: list[dict] = []
    requests = _read_json(REQUESTS_FILE)
    state = read_started()

    for name in [OLLAMA] + sorted(LAUNCHERS):
        req = requests.get(name)
        listening = model_is_up(name)

        if isinstance(req, dict) and not listening:
            cid = req.get("correlation_id") or new_correlation_id()
            result = start_model(name, correlation_id=cid)
            _consume_request(name)
            actions.append({"action": "start", "model": name,
                            "ok": bool(result.get("ok")),
                            "correlation_id": cid})
            continue

        if isinstance(req, dict) and listening and name not in state:
            # Demand arrived but the model is already up for somebody
            # else - the request is satisfied, not ours to act on.
            _consume_request(name)
            continue

        if listening and name in state:
            last_activity = max(
                float(state[name].get("started_at_epoch", 0.0)),
                float(req.get("requested_at_epoch", 0.0)) if req else 0.0,
            )
            if now - last_activity > idle_timeout_seconds:
                cid = new_correlation_id()
                result = stop_model(name, correlation_id=cid)
                actions.append({"action": "stop", "model": name,
                                "ok": bool(result.get("ok")),
                                "correlation_id": cid})

    return actions


def governor_loop(*, poll_seconds: float = POLL_SECONDS,
                  idle_timeout_seconds: float = IDLE_TIMEOUT_SECONDS) -> None:
    """The long-running form. Nothing in Tests calls this."""
    while True:
        governor_once(idle_timeout_seconds=idle_timeout_seconds)
        time.sleep(poll_seconds)


def status() -> dict:
    """What is true right now, per model - never merged or guessed."""
    requests = _read_json(REQUESTS_FILE)
    state = read_started()
    models = {}
    for name in [OLLAMA] + sorted(LAUNCHERS):
        req = requests.get(name)
        models[name] = {
            "listening": model_is_up(name),
            "started_by_governor": name in state,
            "pending_request": bool(req),
            "launcher": (str(LAUNCHERS[name].name)
                         if name in LAUNCHERS else "manage_the_local_model.py"),
        }
    return {
        "has_data": True,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "idle_timeout_seconds": IDLE_TIMEOUT_SECONDS,
        "models": models,
    }


def main() -> None:
    print(json.dumps(status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


