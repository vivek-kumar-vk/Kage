"""The server behind the Model screen - the place Kage shows the local
LiteLLM gateway's own data.

WHAT THIS FILE DOES (T2 scaffold)
    Serves the page, and answers one question for it:

        GET /api/model/overview   is the gateway up, and what does it say?

    That endpoint is a thin, honest proxy to the local LiteLLM proxy's
    REST API (LITELLM_BASE_URL in settings). Right now the gateway is
    not configured yet (wayfinder tickets T3-T6), so a call that cannot
    reach it returns {"gateway": "unreachable", ...} - a real state the
    page renders plainly, never a fake "all good".

WHAT THIS FILE MUST NEVER DO
    Import from Shared_By_All_Screens/ or Shared_By_All_Agents/. This
    screen is a complete independent component (AGENTS.md rule 4 / the
    wayfinder effort's D-W6): its trace/health/settings helpers, if it
    ever needs them, are its own, not the shared folders'. It also never
    reaches into another screen's code.

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
from fastapi.staticfiles import StaticFiles  # noqa: E402

app = FastAPI(title=cfg.SCREEN_LABEL)


# =====================================================================
# THE PAGE
# =====================================================================
@app.get("/")
def page():
    # Parity with the other screens: a Next export takes over only when
    # the flag is on AND the build is actually present. Otherwise the
    # hand-written placeholder page is served; a flag on with no export
    # falls through rather than showing a blank screen.
    if getattr(cfg, "USE_NEXT_UI", False):
        dist = getattr(cfg, "NEXT_DIST", None)
        if dist is not None and (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
    if cfg.PAGE.exists():
        return FileResponse(cfg.PAGE)
    return JSONResponse(
        {
            "status": "the Model page is not written yet",
            "expected_file": str(cfg.PAGE),
            "working_endpoints": [cfg.API_PREFIX + "/overview"],
        }
    )


# =====================================================================
# THE ONE ENDPOINT - a thin honest proxy to the local LiteLLM gateway
# =====================================================================
def _get_json(url: str, timeout: float = 3.0, auth: bool = False):
    """GET a URL and parse JSON, or raise urllib's own error. No retries,
    no shared HTTP helper - this screen carries its own tiny fetch.
    `auth` adds the gateway's admin key (needed for its list endpoints)."""
    headers = {"accept": "application/json"}
    if auth and cfg.LITELLM_MASTER_KEY:
        headers["Authorization"] = f"Bearer {cfg.LITELLM_MASTER_KEY}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        import json

        return response.status, json.loads(response.read() or b"null")


@app.get(cfg.API_PREFIX + "/overview")
def overview():
    """Is the gateway up, and what models does it list?

    Honest states (never a dressed-up guess):
      gateway "ok"           -> reachable, plus its /v1/models payload
      gateway "unreachable"  -> nothing is listening on LITELLM_BASE_URL
      gateway "error"        -> it answered, but not with something usable

    The gateway itself is not configured until tickets T3-T6, so
    "unreachable" is the expected answer today and the page says so.
    """
    base = cfg.LITELLM_BASE_URL.rstrip("/")
    # Reachability first (no auth), then the model list (needs the key).
    try:
        _get_json(f"{base}/health/liveliness")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as problem:
        return {
            "gateway": "unreachable",
            "base_url": base,
            "why": f"nothing answered at {base} ({problem}). "
            "Start it with Tools/run_litellm.bat (or Start_Everything.bat).",
            "models": [],
        }

    try:
        status, body = _get_json(f"{base}/v1/models", auth=True)
    except urllib.error.HTTPError as problem:
        why = f"{base} answered {problem.code} for /v1/models"
        if problem.code == 401:
            why += " - LITELLM_MASTER_KEY missing or wrong in .env"
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
# STATIC FILES - this screen's own page assets (its own theme CSS)
# =====================================================================
app.mount("/page", StaticFiles(directory=cfg.PAGE.parent), name="page")


# =====================================================================
# START IT
# =====================================================================
if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
