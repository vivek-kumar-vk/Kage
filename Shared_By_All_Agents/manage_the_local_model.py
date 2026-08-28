"""Turns the local model's RUNTIME itself on and off.

WHY THIS EXISTS AND WHY IT IS NOT THE OLD TOGGLE
    The Agents tab already had a switch - local_model_settings.py - but
    it only gates whether INKY may CALL the local model. It never said
    anything to Ollama itself, which is why the tab kept honestly
    reporting "Ollama is not running" while offering no way to change
    that. Asked for directly: "configure a switch through which I can
    really turn on and off the local model Ollama". This file is that
    switch: it starts and stops the ollama serve process on this laptop.

THE OWNERSHIP RULE (the important one)
    INKY only ever stops a process it started itself. Every start writes
    Shared_By_All_Agents/local_model_process.json recording the pid;
    every stop refuses unless that file exists. If you started Ollama
    from a terminal or it autostarts with Windows, INKY will report it
    as running-but-not-ours and will not touch it - killing a process
    you did not start is exactly how a helper becomes a hazard.

HONESTY PATHS
    No ollama on PATH -> says so. Already running -> says so and starts
    nothing new. Started but never answered within the wait -> says so,
    leaves the process for its owner to inspect, records what happened.
    Every start and stop lands in the trace ledger (actor "local_model")
    so the nightly reflection sees the runtime coming and going.

NOTE ON SUBPROCESS
    The project bans subprocess in manage_mcp_servers.py because INKY
    must never START an MCP SERVER. This file starts the local model
    runtime the owner explicitly asked to control - a different thing,
    decided in ADR-085.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Shared_By_All_Agents
PROJECT_ROOT = HERE.parent                      # the inky folder
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PROJECT_ROOT))

import call_the_local_model                       # noqa: E402
import local_model_settings                        # noqa: E402
from Shared_By_All_Screens.trace_every_action import trace  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PID_FILE = HERE / "local_model_process.json"
SERVE_LOG = HERE / "Saved_Records" / "ollama_serve.log"

# India has no daylight saving; fixed offset, same clock as everywhere.
_IST = timezone(timedelta(hours=5, minutes=30), "IST")

# How long start() waits for the server to answer before giving up.
START_WAIT_SECONDS = 15.0


def _now_iso() -> str:
    return datetime.now(_IST).isoformat(timespec="seconds")


def _creation_flags() -> int:
    """Keep the served process windowless on Windows; harmless elsewhere."""
    if sys.platform == "win32":
        return 0x08000000          # CREATE_NO_WINDOW
    return 0


def ollama_is_installed() -> bool:
    return shutil.which("ollama") is not None


def started_by_inky() -> bool:
    """True when the pid file says a run belongs to us."""
    try:
        data = json.loads(PID_FILE.read_text(encoding="utf-8"))
        return isinstance(data.get("pid"), int)
    except (OSError, ValueError):
        return False


def _write_pid_file(pid: int) -> None:
    PID_FILE.write_text(json.dumps(
        {"pid": pid, "started_at": _now_iso()}, indent=2), encoding="utf-8")


def _clear_pid_file() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def start() -> dict:
    """Start `ollama serve` if it can be started. Never raises."""
    if not ollama_is_installed():
        note = ("ollama was not found on PATH, so there is nothing to "
                "start. Install it or add it to PATH first.")
        trace("local_model", "agent", "start_refused_no_ollama",
              detail={"reason": note}, outcome="fail")
        return {"ok": False, "running": False, "reason": note}

    if call_the_local_model.is_ollama_running():
        note = "Ollama is already running - starting nothing new."
        return {"ok": True, "already_running": True,
                "running": True, "reason": note}

    SERVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with SERVE_LOG.open("a", encoding="utf-8") as log:
            proc = subprocess.Popen(                                  # noqa: S603
                ["ollama", "serve"],
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=_creation_flags(),
            )
    except OSError as trouble:
        note = f"could not start ollama: {trouble}"
        trace("local_model", "agent", "start_failed",
              detail={"reason": note[:200]}, outcome="fail")
        return {"ok": False, "running": False, "reason": note}

    deadline = time.time() + START_WAIT_SECONDS
    while time.time() < deadline:
        if call_the_local_model.is_ollama_running():
            _write_pid_file(proc.pid)
            trace("local_model", "agent", "started_serve",
                  target=str(proc.pid))
            return {"ok": True, "running": True, "pid": proc.pid}
        if proc.poll() is not None:
            # Died immediately - the log holds why; do not guess.
            note = ("ollama serve exited immediately; see "
                    f"{SERVE_LOG.name} for its output.")
            trace("local_model", "agent", "start_failed",
                  detail={"reason": note[:200]}, outcome="fail")
            return {"ok": False, "running": False, "reason": note}
        time.sleep(0.5)

    note = (f"started ollama (pid {proc.pid}) but it did not answer "
            f"within {int(START_WAIT_SECONDS)}s. Leaving it running - "
            "check the log rather than losing the evidence.")
    _write_pid_file(proc.pid)
    trace("local_model", "agent", "start_slow",
          target=str(proc.pid), outcome="escalated",
          detail={"reason": note[:200]})
    return {"ok": False,
            "running": call_the_local_model.is_ollama_running(),
            "pid": proc.pid, "reason": note}


def stop() -> dict:
    """Stop the process INKY started. Refuses anything it did not."""
    if not PID_FILE.exists():
        note = ("INKY did not start Ollama (no record of it), so it "
                "will not stop it.")
        trace("local_model", "agent", "stop_refused_not_ours",
              detail={"reason": note[:200]}, outcome="fail")
        return {"ok": False,
                "running": call_the_local_model.is_ollama_running(),
                "reason": note}

    try:
        data = json.loads(PID_FILE.read_text(encoding="utf-8"))
        pid = int(data["pid"])
    except (OSError, ValueError, KeyError):
        _clear_pid_file()
        return {"ok": False,
                "running": call_the_local_model.is_ollama_running(),
                "reason": "the pid record was unreadable, so it was cleared."}

    killed = subprocess.run(["taskkill", "/PID", str(pid), "/F"],       # noqa: S603
                            capture_output=True, text=True)
    stopped_responding = not call_the_local_model.is_ollama_running()
    _clear_pid_file()

    if killed.returncode != 0 and not stopped_responding:
        note = (f"could not stop pid {pid}: "
                f"{(killed.stderr or '').strip()[:150]}")
        trace("local_model", "agent", "stop_failed",
              target=str(pid), detail={"reason": note[:200]}, outcome="fail")
        return {"ok": False, "running": True, "reason": note}

    trace("local_model", "agent", "stopped_serve", target=str(pid))
    return {"ok": True, "running": False, "stopped_pid": pid}


def status() -> dict:
    """Three different facts, never merged: is the runtime up, did INKY
    start it, and may INKY call the model at all right now."""
    running = call_the_local_model.is_ollama_running()
    return {
        "has_data": True,
        "checked_at": _now_iso(),
        "ollama_installed": ollama_is_installed(),
        "ollama_running": running,
        "powered_by_inky": started_by_inky(),
        "calls_allowed": local_model_settings.is_enabled(),
        "models_pulled": (call_the_local_model.which_models_are_pulled()
                          if running else []),
    }


def main() -> None:
    print(json.dumps(status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

