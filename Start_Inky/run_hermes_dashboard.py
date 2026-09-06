"""Starts the Hermes web dashboard that the Hermes screen reports on.

WHAT IT DOES
    Starts `hermes dashboard` on 127.0.0.1:9119 - the address the Hermes
    screen expects (Screens/Hermes/Backend/settings_for_hermes.py,
    DASHBOARD_BASE_URL). The Hermes screen embeds that UI, so this is
    what makes clicking HERMES in the menu show something you can use
    rather than a table of commands to copy into a terminal.

    9119 is Hermes's own default, not a Kage port. If something is
    already listening there this prints that and leaves it alone - safe
    to run twice, same as the other gateway runners here.

    The dashboard binds loopback only. Hermes refuses to serve a public
    bind without an auth provider, and Kage has no business poking a
    hole in that: local means local.

WHAT IT NEEDS
    The repo-local Hermes install (Screens/Hermes/Setup/hermes_home - the
    installer's own output when HERMES_HOME points there) or `hermes` on
    PATH. The first start builds the dashboard's web UI, which needs npm
    and can take a few minutes; every start after that reuses the built
    files. Set HERMES_DASHBOARD_SKIP_BUILD=1 to serve the existing build
    and never attempt a rebuild - the right setting on a box without npm.

RUN IT
    cd <repo root>
    python Start_Inky\\run_hermes_dashboard.py

    Or double-click Start_Inky\\Start_Everything.bat, or just run
    Start_Inky\\start_every_screen.py - both start every gateway runner
    in this folder alongside the screens.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Print each line as it happens, same as the other launchers here.
sys.stdout.reconfigure(line_buffering=True)

# This file sits at  Start_Inky/run_hermes_dashboard.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 9119

# The repo-local Hermes home - one self-contained folder for phone/Termux
# hosting (D40's reasoning), the same pattern as run_openclaw.py. Used
# when HERMES_HOME is unset and the folder exists; the installer writes
# its launcher into <HERMES_HOME>\bin.
LOCAL_HERMES_HOME = (PROJECT_ROOT / "Screens" / "Hermes" / "Setup"
                     / "hermes_home")

# The first run has to build the web UI (needs npm). On a box without
# npm that fails, so this flag serves whatever build already exists.
SKIP_BUILD = os.environ.get("HERMES_DASHBOARD_SKIP_BUILD", "") == "1"


def port_in_use(port: int) -> bool:
    """True when something already listens on the dashboard port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((DASHBOARD_HOST, port)) == 0


def hermes_home() -> Path:
    """The Hermes home to use - an explicit HERMES_HOME wins, then the
    repo-local install, then Hermes' own Windows default. The same rule
    the Hermes screen's settings_for_hermes.py follows, so the runner and
    the screen can never disagree about where the install is."""
    env_home = os.environ.get("HERMES_HOME")
    if env_home:
        return Path(env_home)
    if LOCAL_HERMES_HOME.is_dir():
        return LOCAL_HERMES_HOME
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "hermes"
    return Path.home() / ".hermes"


def hermes_command() -> tuple[list[str], dict[str, str]]:
    """The `hermes` command to spawn plus the env it needs - the
    repo-local install first, a PATH install as the fallback. On Windows
    a shim may be installed as .cmd/.bat, which CreateProcess will not
    run directly, and an extensionless sh shim will not run at all."""
    home = hermes_home()
    env = dict(os.environ)
    if env.get("HERMES_HOME") != str(home):
        env["HERMES_HOME"] = str(home)  # the child must agree on the home

    for name in ("hermes.exe", "hermes.cmd", "hermes.bat"):
        local = home / "bin" / name
        if local.is_file():
            if local.suffix.lower() in (".cmd", ".bat"):
                return ["cmd", "/c", str(local)], env
            return [str(local)], env

    found = shutil.which("hermes")
    if not found:
        print("  hermes is not installed. Install it repo-locally:")
        print("    powershell -NoProfile -ExecutionPolicy Bypass -Command \"")
        print(r"      $env:HERMES_HOME='B:\inky_code\Screens\Hermes\Setup\hermes_home';")
        print("      iex (irm https://hermes-agent.nousresearch.com/install.ps1)\"")
        print("  The Hermes screen will keep saying it is not installed -")
        print("  which is the honest state, not a failure of the screen.")
        sys.exit(1)
    if found.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", found], env
    return [found], env


def main() -> None:
    if port_in_use(DASHBOARD_PORT):
        print(f"  dashboard already running at "
              f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT} - leaving it alone")
        return

    command, child_env = hermes_command()
    command += [
        "dashboard",
        "--host", DASHBOARD_HOST,        # local means local
        "--port", str(DASHBOARD_PORT),
        # Kage opens the dashboard inside the Hermes screen, so hermes
        # must not also throw its own browser tab up on every start.
        "--no-open",
    ]
    if SKIP_BUILD:
        command.append("--skip-build")
        print("  serving the existing dashboard build (skip-build set)")

    print(f"  Hermes dashboard -> http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print("  the Hermes screen embeds this; open the menu and click HERMES.")
    print("  the FIRST start builds its web UI and can take a few minutes.")

    proc = subprocess.Popen(command, cwd=str(PROJECT_ROOT), env=child_env)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
