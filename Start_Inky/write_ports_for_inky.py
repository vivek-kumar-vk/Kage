"""Writes Start_Inky/ports_for_inky.json - one generated map of every port.

WHY THIS EXISTS
    The V2 master prompt asks for a single file that answers "what runs
    where". The danger is a hand-typed list: it drifts the moment a
    screen changes its port, and then the file lies.

    So this file does not hold any port itself. It walks the same screen
    folders the launcher walks, reads each screen's own settings through
    the same Shared_By_All_Screens.read_screen_settings the launcher and
    the menu use, and writes what it found. The per-screen settings files
    stay THE one place a port is written down; this JSON is a snapshot of
    them, regenerated on demand and checked by a test.

RUN IT
    .venv\\Scripts\\python.exe Start_Inky\\write_ports_for_inky.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Shared_By_All_Screens.read_screen_settings import (   # noqa: E402
    read_settings, settings_file)

SNAPSHOT_FILE = HERE / "ports_for_inky.json"

SHELL_DIR = PROJECT_ROOT / "Main_Menu"
SCREENS_DIR = PROJECT_ROOT / "Screens"

# Ports reserved by the V2 two-model runtime (ADR-121). These are
# reservations, not facts about running processes - listed separately so
# the snapshot never claims a model is up when it is not.
RESERVED_PORTS = {
    "local_model_a_llama_cpp": 8080,
    "local_model_b_llama_cpp_moe": 8081,
}


def collect_screens() -> list[dict]:
    """One entry per screen folder that has a settings file."""
    folders: list[Path] = []
    if SHELL_DIR.is_dir():
        folders.append(SHELL_DIR)
    if SCREENS_DIR.is_dir():
        folders += sorted(p for p in SCREENS_DIR.iterdir()
                          if p.is_dir() and not p.name.startswith((".", "__")))

    entries: list[dict] = []
    for folder in folders:
        path = settings_file(folder)
        if path is None:
            continue          # not built yet - honestly absent from the map
        info = read_settings(path)
        if info.get("port") is None:
            continue
        entries.append({
            "name": folder.name,
            "label": info["label"],
            "host": info["host"],
            "port": info["port"],
            "settings_file": str(path.relative_to(PROJECT_ROOT)),
        })
    return entries


def build_snapshot() -> dict:
    screens = collect_screens()
    return {
        "generated_by": "Start_Inky/write_ports_for_inky.py",
        "note": ("Generated snapshot - the single source of truth stays "
                 "each screen's Backend/settings_for_<name>.py. Regenerate "
                 "after changing any port."),
        "screens": screens,
        "reserved_not_running": RESERVED_PORTS,
    }


def main() -> None:
    snapshot = build_snapshot()
    SNAPSHOT_FILE.write_text(
        json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SNAPSHOT_FILE}")
    for s in snapshot["screens"]:
        print(f"  {s['port']}  {s['name']}")


if __name__ == "__main__":
    main()
