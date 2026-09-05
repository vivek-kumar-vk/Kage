"""The server behind the OpenClaw screen - the place Kage reports on the
local OpenClaw gateway (github.com/openclaw/openclaw).

WHAT THIS FILE DOES
    Serves the page, and answers one question for it:

        GET /api/openclaw/overview   is the gateway up, and what does it say?

    Everything it reports is a real probe of the OpenClaw gateway's own
    /healthz endpoint. If the gateway is not running, it says exactly
    that (CLAUDE.md Rule 8) - it never fabricates a health snapshot.

WHAT THIS FILE MUST NEVER DO
    Run `openclaw`. Starting the gateway is a deliberate act; a screen
    that is merely open in a tab must never trigger one. The page shows
    the command to copy.

    Import from Shared_By_All_Screens/, or reach into another screen's
    code. This screen is a complete independent component (Rule 5).

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    .venv\\Scripts\\python Screens\\OpenClaw\\Backend\\server_for_openclaw.py
    then open http://127.0.0.1:8006
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_openclaw as cfg  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402

app = FastAPI(title=cfg.SCREEN_LABEL)


@app.get("/")
def page():
    """This screen's own page."""
    if not cfg.PAGE.is_file():
        return JSONResponse(
            {"status": "page missing", "expected": str(cfg.PAGE)},
            status_code=503,
        )
    return FileResponse(cfg.PAGE)


def _gateway_health() -> dict:
    """A real GET against the gateway's own /healthz - never a guess.

    OpenClaw documents this exact shape: {"ok": true, "status": "live"}
    when the gateway can answer HTTP at all (a liveness probe, not a
    readiness one - it can say "live" before every channel/plugin has
    finished settling, which is an honest state, not a false positive).
    """
    url = cfg.GATEWAY_BASE_URL.rstrip("/") + "/healthz"
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            body = json.loads(r.read().decode("utf-8") or "{}")
            return {"state": "ok" if body.get("ok") else "down", "detail": body}
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as problem:
        return {"state": "down", "why": str(problem)}


@app.get(cfg.API_PREFIX + "/overview")
def overview():
    """The gateway's own health, reported honestly.

    Honest states (never a dressed-up guess):
      "ok"   -> the gateway answered /healthz with ok: true
      "down" -> unreachable, or answered but not ok
    """
    health = _gateway_health()
    return {
        "openclaw": health["state"],
        "why": health.get("why", ""),
        "detail": health.get("detail"),
        "base_url": cfg.GATEWAY_BASE_URL,
        "start_command": cfg.GATEWAY_START_COMMAND,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT, log_level="info")
