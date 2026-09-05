"""The server behind the Model screen - the place Kage shows the local
model gateway's own dashboard (D10: OmniRoute iframe embed).

WHAT THIS FILE DOES
    Serves the page, and answers one question for it:

        GET /api/model/overview   is the gateway up, and what does it say?

    That endpoint is a thin, honest proxy to the local model gateway's
    REST API (GATEWAY_BASE_URL in settings). The page uses the answer to
    decide whether to show the OmniRoute dashboard iframe or a "gateway
    unreachable" fallback panel.

WHAT THIS FILE MUST NEVER DO
    Import from Shared_By_All_Screens/ or Shared_By_All_Agents/. This
    screen is a complete independent component (CLAUDE.md Rule 5): its
    trace/health/settings helpers, if it ever needs them, are its own,
    not the shared folders'. It also never reaches into another screen's
    code.

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    python Screens/Model/Backend/server_for_model.py
    then open http://127.0.0.1:8005
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_model as cfg  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402

app = FastAPI(title=cfg.SCREEN_LABEL)


# =====================================================================
# THE PAGE
# =====================================================================
@app.get("/")
def page():
    """This screen's own page.

    NOT a server-side redirect to the gateway - that leaves Kage
    entirely, so when the gateway is down the browser lands on a bare
    connection error with no way back to the menu. Instead the page
    asks /api/model/overview: when the gateway is up it forwards to the
    dashboard from the client (Back then returns to the Main Menu); when
    it is down it stays here and says what to start. The dashboard sends
    X-Frame-Options: DENY, so embedding it in an iframe is not an option
    (D21.3.1).
    """
    if not cfg.PAGE.is_file():
        return JSONResponse(
            {"status": "page missing", "expected": str(cfg.PAGE)},
            status_code=503,
        )
    # Never let the browser cache this shell. It is a few hundred bytes
    # whose whole job is to reflect the gateway's *current* state and
    # forward accordingly; a stale copy (e.g. an older iframe version)
    # would strand the user on :8005 instead of forwarding to :8003.
    return FileResponse(cfg.PAGE, headers={"Cache-Control": "no-store"})


# =====================================================================
# THE ONE ENDPOINT - a thin honest proxy to the local model gateway
# =====================================================================
def _get_json(url: str, timeout: float = 3.0, auth: bool = False):
    """GET a URL and parse JSON, or raise urllib's own error. No retries,
    no shared HTTP helper - this screen carries its own tiny fetch.
    `auth` adds the gateway's API key (needed for its list endpoints)."""
    headers = {"accept": "application/json"}
    if auth and cfg.GATEWAY_API_KEY:
        headers["Authorization"] = f"Bearer {cfg.GATEWAY_API_KEY}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        import json

        return response.status, json.loads(response.read() or b"null")


@app.get(cfg.API_PREFIX + "/overview")
def overview():
    """Is the gateway up, and what models does it list?

    Honest states (never a dressed-up guess):
      gateway "ok"           -> reachable, plus its /v1/models payload
      gateway "unreachable"  -> nothing is listening on GATEWAY_BASE_URL
      gateway "error"        -> it answered, but not with something usable

    The gateway may not be configured yet, so "unreachable" is an expected
    answer and the page says so.
    """
    base = cfg.GATEWAY_BASE_URL.rstrip("/")
    # Reachability first (no auth), then the model list (needs the key).
    # OmniRoute's own health route is /api/monitoring/health; the old
    # /health/liveliness path belonged to the LiteLLM proxy this gateway
    # replaced, and 404s here would read as "unreachable".
    try:
        _get_json(f"{base}/api/monitoring/health")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as problem:
        return {
            "gateway": "unreachable",
            "base_url": base,
            "why": f"nothing answered at {base} ({problem}). "
            "Start OmniRoute (or your model gateway), then try again.",
            "models": [],
        }

    try:
        status, body = _get_json(f"{base}/v1/models", auth=True)
    except urllib.error.HTTPError as problem:
        why = f"{base} answered {problem.code} for /v1/models"
        if problem.code == 401:
            why += " - GATEWAY_API_KEY missing or wrong in .env"
        return {"gateway": "error", "base_url": base, "why": why, "models": []}
    except Exception as problem:  # noqa: BLE001 - malformed answer is a real state
        return {"gateway": "error", "base_url": base, "why": str(problem), "models": []}

    models = []
    if isinstance(body, dict):
        for row in body.get("data") or []:
            if isinstance(row, dict) and row.get("id"):
                models.append({"id": row["id"]})
    return {"gateway": "ok", "base_url": base, "http_status": status, "models": models}


# =====================================================================
# START IT
# =====================================================================
if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
