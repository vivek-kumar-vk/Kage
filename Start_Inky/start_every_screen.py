"""Starts every screen with one command.

WHAT IT DOES
    Finds the main menu and every screen folder, reads which port each
    one wants, and starts them all at once. Prints a list of addresses.
    Press Ctrl+C once and every one of them stops.

WHY IT DOES NOT LIST THE SCREENS
    Search this file for the name of any part of your life and you will
    not find one. It finds them by looking, exactly like
    Main_Menu\\Backend\\find_every_screen.py does.

    So adding a screen later means creating one folder. This file never
    changes. A test checks that promise and fails if a name ever appears
    here.

WHAT A SCREEN NEEDS TO BE STARTABLE
    Two files, both inside its own Backend folder:

        Backend\\server_for_<name>.py      the program to start
        Backend\\settings_for_<name>.py    which port it wants

    A folder with no Backend folder at all is simply not built yet, and
    is reported that way. A folder with a Backend that is missing one of
    those two files is broken, and is reported differently - because a
    screen that quietly fails to start is much harder to notice than one
    that says why.

RUN IT
    cd <repo root>
    python Start_Inky\\start_every_screen.py

    Or just double-click Start_Inky\\Start_Everything.bat
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

# Print each line as it happens instead of holding it in a buffer.
# Without this, the address list appears only after everything stops -
# which is exactly when it is no longer useful.
sys.stdout.reconfigure(line_buffering=True)

# This file sits at  Start_Inky/start_every_screen.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Reading a port out of a settings file is shared with the main menu,
# which needs the same answer to draw its links. One copy, not two.
from Shared_By_All_Screens.read_screen_settings import read_settings  # noqa: E402
# The restart button on the Main Menu drops a flag here; this file is
# the only thing polling for it, because it is the only process that
# actually owns every screen's child process.
from Shared_By_All_Screens.restart_signal import (           # noqa: E402
    restart_was_requested, clear_restart_request)
from Shared_By_All_Screens.clear_every_data_cache import (   # noqa: E402
    clear_every_data_cache)

# The frame you land on, then everything the frame opens.
SHELL_DIR = PROJECT_ROOT / "Main_Menu"
SCREENS_DIR = PROJECT_ROOT / "Screens"


# =====================================================================
# STEP 1 - FIND THE SCREENS
# =====================================================================
def screen_folders() -> list[Path]:
    """Every folder that could hold a screen. The frame first."""
    folders = [SHELL_DIR] if SHELL_DIR.is_dir() else []
    if SCREENS_DIR.is_dir():
        folders += sorted(p for p in SCREENS_DIR.iterdir()
                          if p.is_dir() and not p.name.startswith((".", "__")))
    return folders


def find_screens() -> list[dict]:
    """Return one entry per screen folder, in the order they will start.

    Each entry always carries a `state`:

        ready       has both files, can be started
        not_built   no Backend folder yet - normal for a planned screen
        broken      has a Backend folder but is missing one of the files
    """
    found: list[dict] = []

    for folder in screen_folders():
        backend_dir = folder / "Backend"

        if not backend_dir.is_dir():
            found.append({"folder": folder.name,
                          "state": "not_built",
                          "problem": None})
            continue

        servers = sorted(backend_dir.glob("server_for_*.py"))
        settings = sorted(backend_dir.glob("settings_for_*.py"))

        if not servers or not settings:
            found.append({
                "folder": folder.name,
                "state": "broken",
                "problem": "Backend needs one server_for_*.py and one settings_for_*.py",
            })
            continue

        found.append({
            "folder": folder.name,
            "state": "ready",
            "server": servers[0],
            "settings": settings[0],
            "problem": None,
        })

    return found


# =====================================================================
# STEP 2 - START THEM
# =====================================================================
def port_pid(port: int) -> int | None:
    """The PID already LISTENING on this port, or None if it is free.

    Uses netstat - the stdlib way to ask Windows who holds a port. A
    screen from a previous run that would not die cleanly is exactly
    the thing this finds, before the new one dies confusingly."""
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True,
                             text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None                  # cannot ask - assume free and let bind decide
    for line in out.splitlines():
        parts = line.split()
        # TCP   127.0.0.1:8001   0.0.0.0:0   LISTENING   12345
        if (len(parts) >= 5 and parts[3].upper() == "LISTENING"
                and parts[1].rsplit(":", 1)[-1] == str(port)):
            try:
                return int(parts[-1])
            except ValueError:
                continue
    return None


def process_name(pid: int) -> str:
    """A process's image name, or '' when it could not be asked."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""
    for line in out.splitlines():
        if line.strip().startswith('"'):
            return line.split('","')[0].strip('"')
    return ""


def find_port_conflicts(ready: list[dict]) -> list[dict]:
    """Ready screens whose port is ALREADY held by another process."""
    conflicts = []
    for s in ready:
        pid = port_pid(s["port"])
        if pid is not None and pid != 0:
            s = dict(s)
            s["pid"] = pid
            s["owner"] = process_name(pid) or "unknown process"
            conflicts.append(s)
    return conflicts


def _start_all(ready: list[dict]) -> list[tuple]:
    """Launch one process per ready screen, staggered so their startup
    lines do not interleave. Shared by the first start and by every
    restart the flag triggers afterwards - same code, same behaviour.

    Ctrl+C mid-stagger stops what was already started instead of
    orphaning half a fleet."""
    processes = []
    try:
        for s in ready:
            proc = subprocess.Popen([sys.executable, str(s["server"])],
                                    cwd=str(PROJECT_ROOT))
            processes.append((s, proc))
            time.sleep(0.4)   # stagger, so the startup lines do not interleave
        time.sleep(1.6)
    except KeyboardInterrupt:
        if processes:
            print("\n  interrupted while starting - stopping the ones "
                  "already up")
            _stop_all(processes)
        raise
    return processes


def _print_running(processes: list[tuple]) -> None:
    print()
    print("=" * 66)
    print("  RUNNING - open the first address, it links to all the others")
    print("=" * 66)
    for s, _ in processes:
        page_written = bool(s["page"] and Path(s["page"]).exists())
        state = "page ready" if page_written else "data only, page not written yet"
        print(f"  http://{s['host']}:{s['port']:<6}  {s['label']:<18} {state}")
    print("=" * 66)
    print()


def _wait_ports_free(ready: list[dict], timeout: float = 10.0) -> bool:
    """True when every screen's port is free again (or within timeout).

    A restart that rebinds while Windows still holds the old socket in
    TIME_WAIT dies confusingly; waiting here makes restart boring."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(port_pid(s["port"]) is not None for s in ready):
            return True
        time.sleep(0.25)
    return not any(port_pid(s["port"]) is not None for s in ready)


def _stop_all(processes: list[tuple]) -> None:
    for s, proc in processes:
        proc.terminate()
    for s, proc in processes:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()   # would not close politely
        print(f"  stopped {s['label']}")


def main() -> None:
    screens = find_screens()

    if not screens:
        print(f"No screens found. Expected folders under {SCREENS_DIR}")
        return

    # ---- check for two screens wanting the same port -----------------
    # Two servers on one port means the second dies with a confusing
    # error. Catching it here says exactly which two clashed.
    ready, skipped, ports = [], [], {}
    for s in screens:
        if s["state"] != "ready":
            skipped.append(s)
            continue

        info = read_settings(s["settings"])
        if info["port"] is None:
            s["state"] = "broken"
            s["problem"] = "its settings file has no PORT"
            skipped.append(s)
            continue
        if info["port"] in ports:
            s["state"] = "broken"
            s["problem"] = f"port {info['port']} is already taken by {ports[info['port']]}"
            skipped.append(s)
            continue

        ports[info["port"]] = s["folder"]
        s.update(info)
        ready.append(s)

    for s in skipped:
        if s["state"] == "not_built":
            print(f"  not built yet   {s['folder']}")
        else:
            print(f"  BROKEN          {s['folder']}: {s['problem']}")

    # ---- a port held by some OTHER process is a stale screen ----------
    # Starting anyway would mean the new server dies with a confusing
    # bind error. Failing fast here names the port, the screen that
    # wants it, and the process that holds it.
    conflicts = find_port_conflicts(ready)
    if conflicts:
        print()
        print("Ports already in use - not starting these:")
        for c in conflicts:
            print(f"  IN USE          {c['label']}: port {c['port']} "
                  f"is held by PID {c['pid']} ({c['owner']}) - "
                  "stop that process first")
        ready = [s for s in ready
                 if all(c["port"] != s["port"] for c in conflicts)]

    if not ready:
        print("Nothing could be started.")
        return

    # A flag left behind by a run that ended uncleanly must not cause an
    # unrequested restart the moment this one starts.
    clear_restart_request()

    # ---- start each one as its own program ---------------------------
    # Separate programs, not threads. If one crashes the others keep
    # running, and you can restart just that one.
    print()
    print("Starting")
    print()
    processes = _start_all(ready)
    _print_running(processes)
    print("  Press Ctrl+C once to stop all of them.")
    print()

    # ---- wait, then shut everything down cleanly ---------------------
    # Each screen that dies on its own is announced once. Without the
    # "reported" set, a dead process keeps answering poll() forever and
    # the same line would print every second until Ctrl+C.
    reported: set[int] = set()
    try:
        while True:
            for i, (s, proc) in enumerate(processes):
                if proc.poll() is not None and i not in reported:
                    reported.add(i)
                    print(f"  {s['label']} stopped on its own "
                          f"(exit code {proc.returncode})")

            # ---- a restart was requested (Main Menu's button) --------
            if restart_was_requested():
                clear_restart_request()
                print()
                print("Restart requested - clearing every data cache "
                      "and restarting every screen")
                for c in clear_every_data_cache():
                    print(f"  cleared {c['cache']} "
                          f"({c['files_deleted']} files)")
                _stop_all(processes)
                _wait_ports_free(ready)
                print()
                print("Starting")
                print()
                processes = _start_all(ready)
                _print_running(processes)
                print("  Press Ctrl+C once to stop all of them.")
                print()
                reported = set()

            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print("Stopping")
        _stop_all(processes)
        print()


if __name__ == "__main__":
    main()
