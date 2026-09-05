"""Starts the OpenClaw gateway that the OpenClaw screen reports on.

WHAT IT DOES
    Starts `openclaw gateway run` (foreground) on 127.0.0.1:18789 - the address the
    OpenClaw screen expects (Screens/OpenClaw/Backend/settings_for_openclaw.py,
    GATEWAY_BASE_URL). The OpenClaw screen embeds its Control UI and
    probes its /healthz, so this is what makes clicking OPENCLAW in the
    menu show something live rather than "gateway is down".

    18789 is OpenClaw's own default port, not a Kage port. If something
    is already listening there this prints that and leaves it alone -
    safe to run twice, same as the other gateway runners here.

    Bound loopback-only (--bind loopback): local means local, same
    reasoning as the Hermes dashboard runner.

WHAT IT NEEDS
    A local (repo-relative) OpenClaw install, not a global npm one - the
    phone/Termux host wants this folder self-contained (same reasoning as
    KAGE_DATA_DIR moving repo-relative, D40). Install it once:
        cd Screens\\OpenClaw\\Setup\\openclaw_install
        npm install
        npm approve-scripts openclaw
    Falls back to `openclaw` on PATH if the local install is not there,
    for a quick manual check.

RUN IT
    cd <repo root>
    python Start_Inky\\run_openclaw.py

    Or double-click Start_Inky\\Start_Everything.bat, or just run
    Start_Inky\\start_every_screen.py - both start every gateway runner
    in this folder alongside the screens.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Print each line as it happens, same as the other launchers here.
sys.stdout.reconfigure(line_buffering=True)

# This file sits at  Start_Inky/run_openclaw.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_INSTALL = (PROJECT_ROOT / "Screens" / "OpenClaw" / "Setup"
                 / "openclaw_install" / "node_modules" / ".bin")

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 18789


def port_in_use(port: int) -> bool:
    """True when something already listens on the gateway port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((GATEWAY_HOST, port)) == 0


def openclaw_command() -> list[str]:
    """The `openclaw` command to spawn - the repo-local install first (one
    self-contained folder for phone/Termux hosting, D40's reasoning), a
    global PATH install as a fallback for a quick manual check. On
    Windows a shim may be installed as .cmd/.bat, which CreateProcess
    will not run directly."""
    local = LOCAL_INSTALL / "openclaw.cmd"
    if local.is_file():
        return ["cmd", "/c", str(local)]

    found = shutil.which("openclaw")
    if not found:
        print("  openclaw is not installed. Install it locally (repo-relative):")
        print("    cd Screens\\OpenClaw\\Setup\\openclaw_install")
        print("    npm install")
        print("    npm approve-scripts openclaw")
        print("  The OpenClaw screen will keep saying the gateway is down -")
        print("  which is the honest state, not a failure of the screen.")
        sys.exit(1)
    if found.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", found]
    return [found]


def main() -> None:
    if port_in_use(GATEWAY_PORT):
        print(f"  OpenClaw gateway already running at "
              f"http://{GATEWAY_HOST}:{GATEWAY_PORT} - leaving it alone")
        return

    command = openclaw_command() + [
        "gateway", "run",               # foreground, not the OS-service installer
        "--port", str(GATEWAY_PORT),
        "--bind", "loopback",           # local means local
        "--auth", "none",               # loopback-only; same reasoning as
                                         # the bind choice, nothing leaves this box
        "--allow-unconfigured",         # no `openclaw setup` run yet - bring the
                                         # gateway up anyway rather than block on it
    ]

    print(f"  OpenClaw gateway -> http://{GATEWAY_HOST}:{GATEWAY_PORT}")
    print("  the OpenClaw screen embeds this; open the menu and click OPENCLAW.")

    proc = subprocess.Popen(command, cwd=str(PROJECT_ROOT))
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
