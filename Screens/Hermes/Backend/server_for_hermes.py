"""The server behind the Hermes screen - the place Kage shows the Hermes
Agent profile fleet and what each Bot is wired to (D25).

WHAT THIS FILE DOES
    Serves the page, and answers one question for it:

        GET /api/hermes/overview   what profiles exist, and how are they wired?

    Everything it reports is read from the Hermes install on disk. If
    Hermes is not installed, it says exactly that (CLAUDE.md Rule 8) -
    it never invents a profile list.

WHAT THIS FILE MUST NEVER DO
    Run `hermes`. Starting an agent is a deliberate act with a cost and
    a side effect on that profile's memory; a screen that is merely open
    in a tab must never trigger one. The page shows the command to copy.

    Leak a key. Profile configs carry api_key values for custom
    providers - _redacted() below drops them before anything leaves this
    process, so an open tab can never show one.

    Import from Shared_By_All_Screens/, or reach into another screen's
    code. This screen is a complete independent component (Rule 5).

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    .venv\Scripts\python Screens\Hermes\Backend\server_for_hermes.py
    then open http://127.0.0.1:8007
"""

from __future__ import annotations

import socket

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_hermes as cfg  # noqa: E402

import yaml  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402

app = FastAPI(title=cfg.SCREEN_LABEL)

# Any config key whose name looks like this never leaves the process.
SECRET_HINTS = ("api_key", "apikey", "token", "secret", "password")


# =====================================================================
# THE PAGE
# =====================================================================
@app.get("/")
def page():
    """This screen's own page."""
    if not cfg.PAGE.is_file():
        return JSONResponse(
            {"status": "page missing", "expected": str(cfg.PAGE)},
            status_code=503,
        )
    return FileResponse(cfg.PAGE)


# =====================================================================
# READING THE HERMES INSTALL - files, not guesses
# =====================================================================
def _redacted(value):
    """The same structure with every secret-looking leaf replaced.

    Recursive because custom_providers nests one level down, and a key
    two levels deep is exactly as exposed as one at the top.
    """
    if isinstance(value, dict):
        return {
            key: ("<redacted>" if any(h in key.lower() for h in SECRET_HINTS)
                  else _redacted(body))
            for key, body in value.items()
        }
    if isinstance(value, list):
        return [_redacted(item) for item in value]
    return value


def _read_yaml(path: Path) -> tuple[dict, str]:
    """A parsed YAML file, plus a reason when it could not be read."""
    if not path.is_file():
        return {}, "missing"
    try:
        return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}), ""
    except (yaml.YAMLError, OSError) as problem:
        return {}, str(problem)


def _root_config() -> dict:
    """The install-wide defaults every profile inherits."""
    loaded, why = _read_yaml(cfg.HERMES_CONFIG)
    if why:
        return {"state": "unreadable" if why != "missing" else "missing", "why": why}
    model = loaded.get("model") or {}
    return {
        "state": "ok",
        "default_model": model.get("default", ""),
        "default_provider": model.get("provider", ""),
        "base_url": model.get("base_url", ""),
        "custom_providers": [
            p.get("name", "") for p in (loaded.get("custom_providers") or [])
            if isinstance(p, dict)
        ],
        "free_only": bool((loaded.get("auxiliary") or {}).get("free_only", False)),
    }


def _profiles() -> list[dict]:
    """One entry per profile folder: what it runs on and what it is.

    A profile with no config.yaml inherits the root defaults - that is a
    normal, working state, so it is reported as inherited rather than as
    an error.
    """
    if not cfg.HERMES_PROFILES.is_dir():
        return []
    found = []
    for entry in sorted(cfg.HERMES_PROFILES.iterdir()):
        if not entry.is_dir():
            continue
        loaded, why = _read_yaml(entry / cfg.PROFILE_CONFIG_NAME)
        model = (loaded.get("model") or {}) if not why else {}
        soul = entry / cfg.PROFILE_SOUL_NAME
        found.append({
            "name": entry.name,
            "model": model.get("default", "") or "(inherited)",
            "provider": model.get("provider", "") or "(inherited)",
            "custom_providers": _redacted(loaded.get("custom_providers") or []),
            "has_soul": soul.is_file(),
            "soul_bytes": soul.stat().st_size if soul.is_file() else 0,
            "config_state": "inherited" if why == "missing" else ("ok" if not why else "unreadable"),
            "run_command": f"hermes -p {entry.name} chat",
        })
    return found


def _gateway_state() -> dict:
    """Hermes' own gateway process, as it last recorded itself.

    This is Hermes' file, written by Hermes - if it is stale because the
    process died without cleaning up, that is what the file says and
    what this reports. Kage does not second-guess it.
    """
    if not cfg.HERMES_GATEWAY_STATE.is_file():
        return {"state": "unknown", "why": "no gateway_state.json"}
    try:
        return {"state": "ok",
                "detail": _redacted(json.loads(
                    cfg.HERMES_GATEWAY_STATE.read_text(encoding="utf-8") or "null") or {})}
    except (json.JSONDecodeError, OSError) as problem:
        return {"state": "unreadable", "why": str(problem)}


# =====================================================================
# THE ONE ENDPOINT
# =====================================================================
def _dashboard_reachable() -> tuple[bool, str]:
    """True when something is listening where `hermes dashboard` serves.

    A plain TCP connect, not an HTTP GET: the dashboard is a single-page
    bundle with no documented health route, and inventing one would mean
    reporting a 404 as "down" the first time they add a redirect. Same
    reasoning, same shape, as the Deepseek screen's harness check - a
    small deliberate copy, not a shared module (CLAUDE.md Rule 5).
    """
    host_port = cfg.DASHBOARD_BASE_URL.split("://", 1)[-1]
    host, _, port = host_port.partition(":")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex((host, int(port or 80))) == 0:
                return True, ""
            return False, f"nothing listening on {host_port}"
    except (OSError, ValueError) as problem:
        return False, str(problem)


@app.get(cfg.API_PREFIX + "/overview")
def overview():
    """The fleet, and what it is wired to.

    Honest states (never a dressed-up guess):
      hermes "ok"            -> the install is there and readable
      hermes "not installed" -> HERMES_HOME does not exist
    """
    if not cfg.HERMES_HOME.is_dir():
        return {
            "hermes": "not installed",
            "why": f"no Hermes install at {cfg.HERMES_HOME}",
            "home": str(cfg.HERMES_HOME),
            "profiles": [],
            "dashboard": {"state": "unknown",
                          "why": "Hermes is not installed",
                          "base_url": cfg.DASHBOARD_BASE_URL,
                          "start_command": cfg.DASHBOARD_START_COMMAND},
        }
    profiles = _profiles()
    dashboard_up, dashboard_why = _dashboard_reachable()   # one probe, not two
    return {
        "hermes": "ok",
        "home": str(cfg.HERMES_HOME),
        "config": _root_config(),
        "gateway_process": _gateway_state(),
        "profile_count": len(profiles),
        "profiles": profiles,
        "model_gateway": {
            "base_url": cfg.GATEWAY_BASE_URL,
            "provider_name": cfg.GATEWAY_PROVIDER_NAME,
        },
        # The screen embeds this when it answers; "down" is a real state
        # with a real command beside it, never a blank frame (Rule 8).
        "dashboard": {
            "state": "ok" if dashboard_up else "down",
            "why": dashboard_why,
            "base_url": cfg.DASHBOARD_BASE_URL,
            "start_command": cfg.DASHBOARD_START_COMMAND,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT, log_level="info")
