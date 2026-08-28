"""Watches RAM and VRAM while the local model works, and frees space
only from a list you wrote yourself, in advance.

WHY THIS IS A LIST YOU WRITE, NOT A GUESS THIS FILE MAKES
    Asked for directly: "kill the unnecessary things live while ollama
    is working overnight." The obvious version of that - guess which
    running programs are unimportant and end them - is exactly the
    kind of unattended, irreversible action
    Shared_By_All_Agents/the_reversibility_gate.py exists to stop
    before, by asking. But this runs overnight, with nobody there to
    ask. The only honest way to reconcile those two things is to move
    the asking earlier: you name, in advance, in a live session like
    this one, exactly which process names are ever allowed to be
    ended automatically. Nothing outside that list is touched, ever,
    no matter how much RAM or VRAM it is using. The list starts empty
    on purpose - an empty list is "ask me first," not "guess for me."

WHAT IT NEVER DOES
    End a process not on KILL_LIST.json, by name. End more than one
    process per check - a laptop that loses three programs in one
    sweep because a threshold was crossed once is a worse outcome than
    a slow overnight run. Touch anything if RAM/VRAM are not actually
    over the threshold.

EVERY ACTION IS WRITTEN DOWN
    Saved_Records/resource_guardian_actions.csv, append-only, so a
    morning read of "what happened last night" is a file, not a guess.
"""

from __future__ import annotations

import csv
import ctypes
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KILL_LIST_FILE = HERE / "resource_guardian_kill_list.json"
ACTIONS_LOG = HERE / "Saved_Records" / "resource_guardian_actions.csv"
ACTIONS_COLUMNS = ["timestamp", "reason", "process_name", "outcome"]

DEFAULT_RAM_THRESHOLD_PCT = 90
DEFAULT_VRAM_THRESHOLD_PCT = 95


# =====================================================================
# READING - what is actually true right now
# =====================================================================
def ram_status() -> dict:
    """Total and available RAM in GB, and percent used. Windows API
    directly - no new dependency for something this small."""
    class _MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    m = _MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    try:
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    except (AttributeError, OSError):
        return {"has_data": False, "note": "not on Windows, or the call failed"}
    total_gb = m.ullTotalPhys / 1024**3
    avail_gb = m.ullAvailPhys / 1024**3
    return {"has_data": True, "total_gb": round(total_gb, 1), "available_gb": round(avail_gb, 1),
           "percent_used": round((total_gb - avail_gb) / total_gb * 100, 1)}


def vram_status() -> dict:
    """Same shape as ram_status(), read from nvidia-smi. has_data:
    False (not a made-up 0%) when there is no NVIDIA GPU to ask."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,memory.used",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"has_data": False, "note": "nvidia-smi not found - no NVIDIA GPU, or driver not installed"}
    if out.returncode != 0 or not out.stdout.strip():
        return {"has_data": False, "note": "nvidia-smi did not answer"}

    total_mb, used_mb = (float(x) for x in out.stdout.strip().split(","))
    return {"has_data": True, "total_gb": round(total_mb / 1024, 1),
           "available_gb": round((total_mb - used_mb) / 1024, 1),
           "percent_used": round(used_mb / total_mb * 100, 1)}


def check_resources() -> dict:
    return {"ram": ram_status(), "vram": vram_status(),
           "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# =====================================================================
# THE PRE-APPROVED LIST - the only source of what may ever be ended
# =====================================================================
def read_kill_list() -> list[str]:
    if not KILL_LIST_FILE.exists():
        return []
    try:
        data = json.loads(KILL_LIST_FILE.read_text(encoding="utf-8"))
        return [str(n) for n in data.get("process_names", [])]
    except ValueError:
        return []


def write_kill_list(process_names: list[str]) -> None:
    KILL_LIST_FILE.write_text(
        json.dumps({"process_names": sorted(set(process_names))}, indent=2),
        encoding="utf-8",
    )


def _log_action(reason: str, process_name: str, outcome: str) -> None:
    ACTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    new_file = not ACTIONS_LOG.exists()
    with ACTIONS_LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ACTIONS_COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow({"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "reason": reason, "process_name": process_name, "outcome": outcome})


def _is_running(process_name: str) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
                         capture_output=True, text=True, timeout=10)
    return process_name.lower() in out.stdout.lower()


def _end_process(process_name: str) -> bool:
    out = subprocess.run(["taskkill", "/IM", process_name, "/F"],
                         capture_output=True, text=True, timeout=10)
    return out.returncode == 0


# =====================================================================
# ACTING - one process, one time, only from the pre-approved list
# =====================================================================
def free_up_resources_if_needed(*, ram_threshold_pct: float = DEFAULT_RAM_THRESHOLD_PCT,
                                vram_threshold_pct: float = DEFAULT_VRAM_THRESHOLD_PCT) -> dict:
    """Ends at most one pre-approved process, only if RAM or VRAM is
    genuinely over its threshold right now. Returns what it found and
    what, if anything, it did - never raises, so a long overnight loop
    calling this between steps is never taken down by it."""
    resources = check_resources()
    ram, vram = resources["ram"], resources["vram"]

    over_ram = ram.get("has_data") and ram["percent_used"] >= ram_threshold_pct
    over_vram = vram.get("has_data") and vram["percent_used"] >= vram_threshold_pct

    if not (over_ram or over_vram):
        return {"acted": False, "resources": resources, "reason": "under threshold"}

    kill_list = read_kill_list()
    if not kill_list:
        return {"acted": False, "resources": resources,
               "reason": "over threshold, but the kill list is empty - nothing is pre-approved"}

    reason = "ram_over_threshold" if over_ram else "vram_over_threshold"
    for name in kill_list:
        if not _is_running(name):
            continue
        ended = _end_process(name)
        _log_action(reason, name, "ended" if ended else "attempted, taskkill reported failure")
        return {"acted": ended, "resources": resources, "reason": reason, "process_name": name}

    return {"acted": False, "resources": resources,
           "reason": "over threshold, but none of the pre-approved processes are currently running"}


def main() -> None:
    resources = check_resources()
    print("RESOURCE GUARDIAN")
    print()
    if resources["ram"]["has_data"]:
        r = resources["ram"]
        print(f"  RAM:  {r['available_gb']} GB free of {r['total_gb']} GB ({r['percent_used']}% used)")
    else:
        print(f"  RAM:  {resources['ram']['note']}")
    if resources["vram"]["has_data"]:
        v = resources["vram"]
        print(f"  VRAM: {v['available_gb']} GB free of {v['total_gb']} GB ({v['percent_used']}% used)")
    else:
        print(f"  VRAM: {resources['vram']['note']}")
    print()
    kill_list = read_kill_list()
    print(f"  pre-approved to end if resources run low: {', '.join(kill_list) or '(nothing - list is empty)'}")


if __name__ == "__main__":
    main()
