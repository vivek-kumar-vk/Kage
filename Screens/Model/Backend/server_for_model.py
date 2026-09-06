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
    then open http://127.0.0.1:8001
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
    # would strand the user on :8001 instead of forwarding to :8010.
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
# THE ORCHESTRATOR CHAT - forward to the Agent Deck's one ask path
# =====================================================================
# The Model screen never talks to a model gateway itself (D25.2 posture:
# a run costs money and mutates state, so it happens on the Agent Deck,
# through D27's shared ask path, where it lands in the runs table like
# every other ask). This screen only shapes the HTTP forward and the
# /-command routing. The deck's address comes from settings (discovered,
# never hardcoded); no key is needed here - the deck holds its own.
import json as _json
import urllib.parse

from pydantic import BaseModel  # noqa: E402


class ChatBody(BaseModel):
    message: str = ""
    target: str | None = None


def _agents_offline(problem: str) -> dict:
    return {"state": "agents offline", "reply": None, "agent": None, "problem": problem}


def _fetch_roster() -> dict:
    """GET the deck's workspace roster, or return an honest offline state."""
    if not cfg.AGENTS_BASE_URL:
        return _agents_offline(
            "the Agent Deck's address could not be resolved "
            "(no AGENTS_BASE_URL, no Start_Inky/ports_for_inky.json)"
        )
    try:
        status, body = _get_json(
            f"{cfg.AGENTS_BASE_URL}/api/agents/workspace", timeout=5.0
        )
    except (urllib.error.URLError, TimeoutError, ConnectionError) as problem:
        return _agents_offline(f"{type(problem).__name__}: {problem}")
    except Exception as problem:  # noqa: BLE001 - malformed answer is a real state
        return _agents_offline(str(problem))
    if status != 200 or not isinstance(body, dict):
        return _agents_offline(f"the Agent Deck answered HTTP {status}")
    return body


def _resolve_target(token: str, agents: list) -> str | None:
    """Match a /-command token to a roster name: exact, case-insensitive,
    with or without the _Agent suffix. None = unknown agent."""
    want = token.strip().lower().strip("/").replace("_agent", "")
    if not want:
        return None
    for agent in agents:
        name = agent.get("name") or ""
        if name.lower().replace("_agent", "") == want:
            return name
    return None


def _ask_agent(name: str, message: str) -> dict:
    """One forward to the deck's ask path (D27.1: a failed ask is a result,
    so the deck answers HTTP 200 with state=error and we pass it through)."""
    payload = _json.dumps({"message": message}).encode("utf-8")
    request = urllib.request.Request(
        f"{cfg.AGENTS_BASE_URL}/api/agents/agents/{urllib.parse.quote(name)}/ask",
        data=payload,
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=cfg.ASK_TIMEOUT) as response:  # noqa: S310
            body = _json.loads(response.read() or b"null")
    except (urllib.error.URLError, TimeoutError, ConnectionError) as problem:
        return {
            "agent": name,
            "state": "agents offline",
            "reply": None,
            "problem": f"{type(problem).__name__}: {problem}",
        }
    if not isinstance(body, dict):
        return {"agent": name, "state": "error", "reply": None, "problem": "unusable answer"}
    # Pass the deck's own honest shape through, trimmed to what the chat needs.
    return {
        "agent": name,
        "state": body.get("state", "error"),
        "reply": body.get("reply"),
        "problem": body.get("problem") or body.get("detail"),
        "model": body.get("model"),
    }


@app.post(cfg.API_PREFIX + "/chat")
def chat(body: ChatBody):
    """The page's chat line.

    - plain text              -> the orchestrator (Deck_Main_Agent)
    - {"target": name}        -> that agent, directly
    - "/name message"         -> that agent (name resolved against the roster)
    - "/all message"          -> every main-tier agent in sequence, bounded

    A failure comes back as HTTP 200 with an honest state (D27.1) - the
    chat panel shows the sentence inline instead of a generic network error.
    """
    text = (body.message or "").strip()
    if not text:
        return JSONResponse(
            {"state": "error", "problem": "empty message", "reply": None}, status_code=422
        )

    roster = _fetch_roster()
    if roster.get("state") != "ok":
        return roster

    agents = roster.get("agents") or []
    mains = [a["name"] for a in agents if a.get("tier") == "main" and a.get("name")]

    # An explicit target beats a /-command in the text.
    if body.target:
        target = _resolve_target(body.target, agents)
        if not target:
            return JSONResponse(
                {"state": "error", "problem": f"unknown agent: {body.target}", "reply": None},
                status_code=422,
            )
        return _ask_agent(target, text)

    if text.startswith("/"):
        if text.startswith("/all"):
            broadcast = text[4:].strip()
            if not broadcast:
                return JSONResponse(
                    {"state": "error", "problem": "/all needs a message", "reply": None},
                    status_code=422,
                )
            replies = []
            for name in mains:
                result = _ask_agent(name, broadcast)
                if result.get("reply"):
                    result["reply"] = result["reply"][: cfg.BROADCAST_REPLY_CAP]
                replies.append(result)
            return {"state": "ok", "broadcast": True, "replies": replies}

        head, _, rest = text[1:].partition(" ")
        target = _resolve_target(head, agents)
        if not target:
            return JSONResponse(
                {"state": "error", "problem": f"unknown agent: {head}", "reply": None},
                status_code=422,
            )
        message = rest.strip()
        if not message:
            return JSONResponse(
                {"state": "error", "problem": f"/{head} needs a message", "reply": None},
                status_code=422,
            )
        return _ask_agent(target, message)

    return _ask_agent(cfg.ORCHESTRATOR_AGENT, text)


@app.get(cfg.API_PREFIX + "/agents")
def agents():
    """The /-command autocomplete's name list - a passthrough of the deck's
    roster, so the page never makes a cross-origin call to another screen."""
    roster = _fetch_roster()
    if roster.get("state") != "ok":
        return roster
    return {
        "state": "ok",
        "agents": [
            {"name": a.get("name"), "tier": a.get("tier")}
            for a in (roster.get("agents") or [])
            if a.get("name")
        ],
    }


# =====================================================================
# START IT
# =====================================================================
if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
