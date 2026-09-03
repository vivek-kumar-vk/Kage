"""Starts the DeepSeek Harness web UI (`dsh web`) that the Deepseek screen
reports on.

WHAT IT DOES
    Starts dsh's web profile on 127.0.0.1:3080 - the address the Deepseek
    screen expects (Screens/Deepseek/Backend/settings_for_deepseek.py,
    DSH_BASE_URL). The Deepseek screen embeds that UI in an iframe, so
    this is what makes clicking DEEPSEEK in the menu show a working
    harness instead of "unreachable".

    3080 is dsh's own default, not a Kage port. If something is already
    listening there this prints that and leaves it alone - safe to run
    twice, same as the other gateway runners here.

    dsh guards its /api routes with a browser-trust fence keyed on the
    requesting authority. The screen's iframe is served from a different
    port than dsh itself, so every Kage screen address is passed as a
    --trusted-host; without that the iframe loads and then fails on its
    own API calls. The addresses come from the generated port snapshot,
    so no screen is named in this file (CLAUDE.md Rule 17).

WHAT IT NEEDS
    dsh on PATH (`npm install -g deepseek-harness`, or however you
    installed it). Everything else is the standard library.

RUN IT
    cd <repo root>
    python Start_Inky\\run_dsh_web.py

    Or double-click Start_Inky\\Start_Everything.bat, which starts this
    in its own window alongside the screens and the other gateways.
    Ctrl+C in this window stops the harness.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Print each line as it happens, same as the other launchers here.
sys.stdout.reconfigure(line_buffering=True)

# This file sits at  Start_Inky/run_dsh_web.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PORTS_SNAPSHOT = Path(__file__).resolve().parent / "ports_for_inky.json"

HARNESS_HOST = "127.0.0.1"
HARNESS_PORT = 3080

# dsh's own state folder - $DSH_HOME if set, else ~/.dsh, the same rule
# dsh itself follows and the same one the Deepseek screen's settings use.
DSH_HOME = Path(os.environ.get("DSH_HOME", Path.home() / ".dsh"))

# The config patch that points dsh's DeepSeek models at the OmniRoute
# gateway instead of DeepSeek's cloud API (D24.1), so there is one place
# model access is configured and no second API key to hold. Starting the
# harness WITHOUT this gives a differently-configured harness that looks
# identical in the browser, so it is passed whenever the file exists.
DSH_PATCH = Path(os.environ.get(
    "DSH_PATCH", DSH_HOME / "omniroute-deepseek.yml"))


def port_in_use(port: int) -> bool:
    """True when something already listens on the harness port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((HARNESS_HOST, port)) == 0


def trusted_authorities() -> list[str]:
    """Every screen's host:port, read from the generated snapshot.

    Walking the snapshot rather than writing "the Deepseek screen is on
    8007" keeps this file free of screen names (Rule 17) and means a
    screen that moves port keeps working after the snapshot is
    regenerated.
    """
    try:
        snapshot = json.loads(PORTS_SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError) as problem:
        print(f"  could not read {PORTS_SNAPSHOT.name} ({problem});"
              " continuing with no extra trusted hosts")
        return []
    authorities = []
    for screen in snapshot.get("screens", []):
        host, port = screen.get("host"), screen.get("port")
        if host and port:
            authorities.append(f"{host}:{port}")
    return authorities


def harness_command() -> list[str]:
    """The `dsh` command to spawn. On Windows npm installs a .cmd shim,
    which CreateProcess will not run directly."""
    found = shutil.which("dsh")
    if not found:
        print("  dsh is not on PATH. Install the DeepSeek Harness first,")
        print("  then re-run this. The Deepseek screen will keep saying")
        print("  'unreachable' until it is - which is the honest state,")
        print("  not a failure of the screen.")
        sys.exit(1)
    if found.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", found]
    return [found]


def main() -> None:
    if port_in_use(HARNESS_PORT):
        print(f"  harness already running at http://{HARNESS_HOST}:{HARNESS_PORT}"
              " - leaving it alone")
        return

    command = harness_command() + [
        "--profile", "web",
        "--host", HARNESS_HOST,          # local means local
        "--port", str(HARNESS_PORT),
        # Kage opens the harness inside the Deepseek screen, so dsh must
        # not also throw its own browser tab up on every start.
        "--no-open",
    ]
    if DSH_PATCH.exists():
        command += ["--patch", DSH_PATCH.as_posix()]
        print(f"  using patch {DSH_PATCH.name} (models via the gateway)")
    else:
        print(f"  no patch at {DSH_PATCH} - starting dsh with its own"
              " default model config, NOT through the gateway")
    for authority in trusted_authorities():
        command += ["--trusted-host", authority]

    print(f"  DeepSeek Harness -> http://{HARNESS_HOST}:{HARNESS_PORT}")
    print("  the Deepseek screen embeds this; open the menu and click DEEPSEEK.")

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
