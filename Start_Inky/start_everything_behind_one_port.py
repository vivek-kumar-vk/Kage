"""Starts every screen with INKY_BEHIND_PROXY set, then the one-port
router in front of them, then prints the ngrok command that reaches all
of it from outside this device.

WHY A SEPARATE FILE
    start_every_screen.py says, in its own docstring, that it never
    changes - a promise a test holds it to (adding a screen must never
    cost editing that file). This wraps it instead of touching it: the
    same discovery, the same screens, one environment variable set
    before they start, and one more small server after.

WHAT INKY_BEHIND_PROXY DOES
    Read by Shared_By_All_Screens\\read_screen_settings.py. With it set,
    Main Menu's navigation links read "/finance/" instead of
    "http://127.0.0.1:8001/" - a relative address that still works once
    only one port (this proxy's) is actually reachable from outside.

RUN IT
    cd <repo root>
    python Start_Inky\\start_everything_behind_one_port.py

    Then, in another terminal (or another Termux session):
    ngrok http 9000 --domain <your ngrok domain> --basic-auth "<user>:<password>"

    The domain and the ngrok authtoken (`ngrok config add-authtoken ...`,
    a one-time setup step) live in
    Secrets_Keys\\my_api_keys_and_passwords.md - never typed into a
    script, never committed.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROXY_PORT = os.environ.get("INKY_PROXY_PORT", "9000")


def main() -> None:
    env = os.environ.copy()
    env["INKY_BEHIND_PROXY"] = "1"

    print("Starting every screen (INKY_BEHIND_PROXY=1)...")
    screens = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "Start_Inky" / "start_every_screen.py")],
        cwd=str(PROJECT_ROOT), env=env,
    )

    # The screens stagger their own startup already; give the last one
    # a moment to finish before the proxy starts routing to it.
    time.sleep(3)

    print()
    print("Starting the one-port router...")
    proxy = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / "Start_Inky" / "serve_everything_on_one_port.py")],
        cwd=str(PROJECT_ROOT), env=os.environ.copy(),
    )

    print()
    print("=" * 70)
    print(f"  Everything is reachable at http://127.0.0.1:{PROXY_PORT}")
    print()
    print("  To reach it from outside this device, in another terminal:")
    print()
    print(f'    ngrok http {PROXY_PORT} --domain <your ngrok domain> '
         '--basic-auth "<user>:<password>"')
    print()
    print("  The token and domain are in")
    print("  Secrets_Keys\\my_api_keys_and_passwords.md - never in a script,")
    print("  never in git.")
    print("=" * 70)
    print("  Press Ctrl+C once to stop everything.")
    print()

    try:
        screens.wait()
    except KeyboardInterrupt:
        print()
        print("Stopping")
    finally:
        for proc in (proxy, screens):
            proc.terminate()
        for proc in (proxy, screens):
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
