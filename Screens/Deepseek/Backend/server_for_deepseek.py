"""The server behind the Deepseek screen - the place Kage shows DeepSeek
Harness (`dsh`) and the traces it produces (D24).

WHAT THIS FILE DOES
    Serves the page, and answers one question for it:

        GET /api/deepseek/overview   is the harness up, and how is it wired?

    The answer is honest in both directions (CLAUDE.md Rule 8). If dsh is
    not running, this says so and gives the command; it never shows a
    stale trace or pretends a run happened.

WHAT THIS FILE MUST NEVER DO
    Start dsh. Kage never spawns another process's server (Rule 20) -
    the harness runs in its own window, and "not running" is a real
    state, not a failure to paper over.

    Import from Shared_By_All_Screens/, or reach into another screen's
    code. This screen is a complete independent component (Rule 5).

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    .venv\Scripts\python Screens\Deepseek\Backend\server_for_deepseek.py
    then open http://127.0.0.1:8007
"""

from __future__ import annotations

import json
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_deepseek as cfg  # noqa: E402

import yaml  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402

app = FastAPI(title=cfg.SCREEN_LABEL)


# =====================================================================
# THE PAGE
# =====================================================================
@app.get("/")
def page():
    """This screen's own page - never a redirect to dsh.

    A redirect leaves Kage entirely, and when the harness is down the
    browser lands on a connection error with no way back to the menu.
    The page embeds the harness when it answers and explains itself
    when it does not.
    """
    if not cfg.PAGE.is_file():
        return JSONResponse(
            {"status": "page missing", "expected": str(cfg.PAGE)},
            status_code=503,
        )
    return FileResponse(cfg.PAGE)


# =====================================================================
# READING dsh's OWN STATE - files, not guesses
# =====================================================================
def _harness_reachable() -> tuple[bool, str]:
    """True when something is listening where dsh's web profile serves.

    A plain TCP connect, not an HTTP GET: dsh's web app is a single-page
    bundle with no documented health route, and inventing one would mean
    reporting 404 as "down" the first time they add a redirect.
    """
    host_port = cfg.HARNESS_BASE_URL.split("://", 1)[-1]
    host, _, port = host_port.partition(":")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex((host, int(port or 80))) == 0:
                return True, ""
            return False, f"nothing listening on {host_port}"
    except (OSError, ValueError) as problem:
        return False, str(problem)


def _installed_providers() -> dict:
    """The OpenAI-compatible providers dsh has been told about.

    dsh's own settings.yaml is the source of truth. This reads it; it
    never writes it - Setup/install_dsh_provider.py owns the writing, so
    a screen that is merely being looked at can never change the harness.
    """
    if not cfg.DSH_SETTINGS.is_file():
        return {"state": "missing", "path": str(cfg.DSH_SETTINGS), "providers": {}}
    try:
        loaded = yaml.safe_load(cfg.DSH_SETTINGS.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as problem:
        return {"state": "unreadable", "path": str(cfg.DSH_SETTINGS),
                "why": str(problem), "providers": {}}
    providers = ((loaded.get("llm-pi-ai") or {}).get("providers") or {})
    trimmed = {
        name: {
            "displayName": body.get("displayName", name),
            "baseURL": body.get("baseURL", ""),
            "models": [m.get("id", "") for m in (body.get("models") or [])],
        }
        for name, body in providers.items()
        if isinstance(body, dict)
    }
    return {"state": "ok", "path": str(cfg.DSH_SETTINGS), "providers": trimmed}


def _profiles() -> list[str]:
    """dsh's bootable profiles - the folders under $DSH_HOME/profiles.

    node_modules lives alongside them and is not a profile.
    """
    if not cfg.DSH_PROFILES.is_dir():
        return []
    return sorted(
        entry.name
        for entry in cfg.DSH_PROFILES.iterdir()
        if entry.is_dir() and entry.name != "node_modules"
    )


def _gateway_models() -> dict:
    """Which DeepSeek models the gateway is actually offering right now.

    The harness is only as configured as the gateway behind it: a
    provider block pointing at a gateway that lists no deepseek model is
    a broken wiring, and this is what makes that visible rather than
    letting the first agent run discover it.
    """
    url = cfg.GATEWAY_BASE_URL.rstrip("/") + "/v1/models"
    headers = {"accept": "application/json"}
    if cfg.GATEWAY_API_KEY:
        headers["Authorization"] = f"Bearer {cfg.GATEWAY_API_KEY}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=3.0) as response:  # noqa: S310
            payload = json.loads(response.read() or b"null") or {}
    except urllib.error.HTTPError as problem:
        # It answered, so it is running - saying "unreachable" here would
        # send you restarting a gateway that is already up (Rule 8). 401
        # means the key is missing or wrong, and that is its own fix.
        state = "unauthorized" if problem.code in (401, 403) else "error"
        why = (f"HTTP {problem.code}" +
               ("" if cfg.GATEWAY_API_KEY else " - no GATEWAY_API_KEY in .env"))
        return {"state": state, "why": why, "deepseek": []}
    except (urllib.error.URLError, OSError) as problem:
        return {"state": "unreachable", "why": str(problem), "deepseek": []}
    except json.JSONDecodeError as problem:
        return {"state": "error", "why": f"not JSON: {problem}", "deepseek": []}
    ids = [row.get("id", "") for row in (payload.get("data") or [])]
    return {"state": "ok", "deepseek": sorted(i for i in ids if "deepseek" in i.lower())}


# =====================================================================
# THE ONE ENDPOINT
# =====================================================================
@app.get(cfg.API_PREFIX + "/overview")
def overview():
    """Is the harness up, how is it wired, and what can it reach?

    Honest states (never a dressed-up guess):
      harness "ok"          -> dsh is listening; the page embeds it
      harness "not running" -> nothing there; the page shows the command
    """
    up, why = _harness_reachable()
    return {
        "harness": "ok" if up else "not running",
        "why": why,
        "base_url": cfg.HARNESS_BASE_URL,
        "start_command": cfg.START_COMMAND,
        "dsh_home": str(cfg.DSH_HOME),
        "profiles": _profiles(),
        "wiring": _installed_providers(),
        "expected_provider": cfg.HARNESS_PROVIDER,
        "gateway": {"base_url": cfg.GATEWAY_BASE_URL, **_gateway_models()},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT, log_level="info")
