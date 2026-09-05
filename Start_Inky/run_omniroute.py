"""Starts the model gateway (OmniRoute) that the Model screen reports on.

WHAT IT DOES
    Starts `omniroute` - the npm-installed AI gateway - on
    127.0.0.1:8010, the port the Model screen expects
    (Screens/Model/Backend/settings_for_model.py). The dashboard and
    the OpenAI-compatible /v1 API share that one port.

    On first run it generates the gateway's secrets into the repo-root
    .env, so nothing secret is ever written into a committed file. If
    something is already listening on the gateway port, this prints
    that and leaves the running gateway alone - safe to run twice.

WHAT IT NEEDS
    `npm install -g omniroute` once (needs Node.js). Everything else
    is the standard library. The key the Model screen sends with its
    requests lives in .env as GATEWAY_API_KEY; create it once in the
    gateway dashboard (Endpoints -> new key).

RUN IT
    cd <repo root>
    python Start_Inky\\run_omniroute.py

    Or just double-click Start_Inky\\Start_Everything.bat, which starts
    this in its own window alongside the screens. Ctrl+C in this
    window stops the gateway.
"""

from __future__ import annotations

import os
import secrets
import shutil
import socket
import subprocess
import sys
from pathlib import Path

# Print each line as it happens, same as the other launchers here.
sys.stdout.reconfigure(line_buffering=True)

# This file sits at  Start_Inky/run_omniroute.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 8010

# .env name this launcher owns -> the env name the gateway expects.
# The process env always wins over the .env files omniroute reads
# itself, so exporting these here makes the repo the single source.
SECRET_VARS = {
    "OMNIROUTE_JWT_SECRET": "JWT_SECRET",
    "OMNIROUTE_API_KEY_SECRET": "API_KEY_SECRET",
    "OMNIROUTE_INITIAL_PASSWORD": "INITIAL_PASSWORD",
}


def read_env_file() -> dict[str, str]:
    """The repo-root .env as a plain dict. Same line format the Model
    screen's settings parser reads - one small copy, not a shared
    module (CLAUDE.md Rule 5)."""
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip("\"'")
    return values


def append_env_lines(lines: list[str]) -> None:
    with ENV_FILE.open("a", encoding="utf-8") as env:
        env.write("\n" + "\n".join(lines) + "\n")


def ensure_secrets(env: dict[str, str]) -> dict[str, str]:
    """Return the gateway secrets, generating any missing one into .env.
    Generated once, then reused on every later start."""
    missing = [name for name in SECRET_VARS if not env.get(name)]
    if missing:
        generated = [
            f"{name}={secrets.token_urlsafe(12 if name.endswith('PASSWORD') else 48)}"
            for name in missing
        ]
        append_env_lines(
            ["# --- OmniRoute gateway secrets (Start_Inky/run_omniroute.py) ---"]
            + generated
        )
        for line in generated:
            name, _, _ = line.partition("=")
            env[name] = line.partition("=")[2]
        print(f"  generated {len(missing)} gateway secret(s) into .env")
    return {dotnet: env[name] for name, dotnet in SECRET_VARS.items()}


def port_in_use(port: int) -> bool:
    """True when something already listens on the gateway port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((GATEWAY_HOST, port)) == 0


def gateway_command() -> list[str]:
    """The npm-global `omniroute` command to spawn. On Windows npm
    installs a .cmd shim, which CreateProcess will not run directly."""
    found = shutil.which("omniroute")
    if not found:
        print("  omniroute is not installed. Run:  npm install -g omniroute")
        sys.exit(1)
    if found.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", found]
    return [found]


def _disable_dashboard_login(env_vars: dict[str, str]) -> None:
    """After OmniRoute boots, log in and disable the requireLogin setting
    so the Model screen's iframe (D10) loads the dashboard directly without
    prompting for a password. Self-contained - no shared module (CLAUDE.md Rule 5).
    """
    import json
    import time
    import urllib.request
    import urllib.error

    base = f"http://{GATEWAY_HOST}:{GATEWAY_PORT}"
    password = env_vars.get("INITIAL_PASSWORD", "")
    if not password:
        print("  [login-bypass] no INITIAL_PASSWORD — skipping")
        return

    # Wait for the gateway to be ready (health endpoint)
    for attempt in range(30):
        try:
            req = urllib.request.Request(
                f"{base}/api/monitoring/health",
                headers={"accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    break
        except Exception:
            pass
        time.sleep(2)
    else:
        print("  [login-bypass] gateway didn't become healthy — skipping")
        return

    # Log in to get a session cookie
    try:
        login_data = json.dumps({"password": password}).encode()
        req = urllib.request.Request(
            f"{base}/api/auth/login",
            data=login_data,
            headers={"Content-Type": "application/json", "accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            cookie = r.getheader("Set-Cookie") or ""
    except Exception as exc:
        print(f"  [login-bypass] login failed: {exc}")
        return

    if not cookie:
        print("  [login-bypass] no session cookie returned — skipping")
        return

    session = cookie.split(";")[0]

    # Disable requireLogin
    try:
        payload = json.dumps({"requireLogin": False}).encode()
        req = urllib.request.Request(
            f"{base}/api/settings/require-login",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "accept": "application/json",
                "Cookie": session,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status == 200:
                print("  [login-bypass] dashboard login disabled (D10)")
            else:
                print(f"  [login-bypass] unexpected status {r.status}")
    except Exception as exc:
        print(f"  [login-bypass] disable failed: {exc}")


def main() -> None:
    if port_in_use(GATEWAY_PORT):
        print(f"  gateway already running at http://{GATEWAY_HOST}:{GATEWAY_PORT}"
              " - leaving it alone")
        return

    file_env = read_env_file()
    gateway_secrets = ensure_secrets(file_env)

    env = dict(os.environ)
    env.update({
        "PORT": str(GATEWAY_PORT),
        "OMNIROUTE_SERVER_HOST": GATEWAY_HOST,   # local means local
        "API_HOST": GATEWAY_HOST,
        "REQUIRE_API_KEY": "true",
        **gateway_secrets,
    })

    print(f"  OmniRoute -> http://{GATEWAY_HOST}:{GATEWAY_PORT}"
          "  (dashboard + /v1 API)")
    print("  first start after an install can take a minute; the Model")
    print("  screen (http://127.0.0.1:8001) reports this gateway's state.")
    proc = subprocess.Popen(gateway_command(), cwd=str(PROJECT_ROOT), env=env)

    # After the gateway boots, disable the dashboard login so the Model
    # screen's iframe (D10) loads without prompting for a password.
    import threading
    threading.Thread(
        target=_disable_dashboard_login,
        args=(gateway_secrets,),
        daemon=True,
    ).start()

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

