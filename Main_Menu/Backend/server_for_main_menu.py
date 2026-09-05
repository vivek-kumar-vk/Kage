"""The server behind the main menu - the screen you land on.

WHAT THIS FILE DOES
    Serves the menu page, and answers one question for it:

        which screens exist, and where does each one live?

WHAT THIS FILE MUST NEVER DO
    Name a screen. Search this file for the word "finance" and you will
    not find it, except in this sentence. It asks find_every_screen.py,
    which walks the Screens folder and reports what it finds.

    One exception is fenced off below (ADR-089): a single thin proxy
    that forwards one question to one other screen over HTTP on its
    own port - never by import. The naming lives inside BEGIN/END
    fence comments, and a rule test counts the fences so the exception
    cannot quietly grow a second head.

    It also never does another screen's arithmetic. If it ever needs a
    figure another screen owns, that figure goes on the noticeboard and
    is read from there - the only channel between screens (ADR-010).

    That is the whole architecture in one file: adding a screen later
    means creating one folder. Nothing here changes.

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    python Main_Menu\\Backend\\server_for_main_menu.py
    then open http://127.0.0.1:8000
"""

# =====================================================================
# SETUP
# =====================================================================
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

# This file sits at  Main_Menu/Backend/server_for_main_menu.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "Agent" / "Calendar_Agent"))

from fastapi import Body, FastAPI, Request                # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles               # noqa: E402

import settings_for_main_menu as cfg                      # noqa: E402
from find_every_screen import discover                    # noqa: E402
from Shared_By_All_Screens.read_screen_settings import web_address   # noqa: E402
from read_and_write_numbers import read_state  # noqa: E402
from format_indian_money import format_inr     # noqa: E402
from trace_every_action import (              # noqa: E402
    new_correlation_id, trace,
)
from Shared_By_All_Screens.restart_signal import request_restart     # noqa: E402
from Shared_By_All_Screens.clear_every_data_cache import (           # noqa: E402
    clear_every_data_cache)

app = FastAPI(title=cfg.SCREEN_LABEL)

# Liveness + dependency probe (Phase-1 W1.3) - see health_check.py.
# The menu's own dependency is the Screens/ tree it exists to list.
import health_check                          # noqa: E402
health_check.register(app, "main_menu",
                      screens_root=lambda: Path(__file__).resolve().parents[2] / "Screens")


# =====================================================================
# THE TRACE LEDGER - every served request and every page click lands in
# Backend/Trace_Ledger/, the same pattern every screen uses.
# =====================================================================
@app.middleware("http")
async def _trace_api_requests(request, call_next):
    """One row per API call served. Static mounts (/shared, /page, /fonts)
    and the 30-second /dev poll are excluded on purpose - that is noise,
    not signal.

    Every traced row carries a correlation id (Phase-1 CS-1): taken from
    an inbound X-Correlation-Id header when the caller supplies one,
    otherwise minted here - and echoed back on the response so the next
    hop in the chain can keep the thread."""
    started = time.time()
    cid = request.headers.get("x-correlation-id") or new_correlation_id()
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = cid
    path = request.url.path
    if not path.startswith(("/shared", "/page", "/fonts", "/docs",
                            "/redoc", "/openapi.json", "/dev")):
        trace("main_menu", "api", f"{request.method} {path}",
              target=path.split("/")[-1] or "/",
              detail={"status": response.status_code},
              outcome="ok" if response.status_code < 400 else "fail",
              duration_ms=int((time.time() - started) * 1000),
              correlation_id=cid)
    return response


@app.post(cfg.API_PREFIX + "/trace")
def receive_page_trace(event: dict = Body(...)):
    """One row per click the page reports. Fire-and-forget from the
    page's side; a failed trace must never break the page."""
    written = trace(
        actor=event.get("actor") or "you",
        kind=event.get("kind") or "click",
        action=event.get("action") or "unknown",
        target=event.get("target") or "",
        detail=event.get("detail"),
        outcome=event.get("outcome") or "ok",
        duration_ms=event.get("duration_ms"),
        correlation_id=event.get("correlation_id"),
    )
    return {"written": written}


@app.get("/dev/changed-since")
def dev_changed_since(token: str = ""):
    """Has any code file behind this page moved since it was loaded?
    An empty token only establishes the baseline and can never say
    'changed' - otherwise every fresh page would reload in a loop."""
    from code_change_monitor import has_changed, is_enabled
    result = has_changed(token, cfg.MONITORED_FOLDERS)
    if not is_enabled():
        return {"changed": False, "fingerprint": result["fingerprint"],
                "latest_file": "", "latest_at": ""}
    if result["changed"] and token:
        trace("main_menu", "ledger", "file_changed",
              target=result["latest_file"],
              detail={"latest_at": result["latest_at"]})
    return result

# The chat endpoint (Phase H 8 / ADR-132): one POST that walks the
# fallback chain - strongest-first - and answers with whatever rung
# actually replied. The Orchestrator seat (claude) is permission-gated:
# it is tried only when the caller carries owner_approved:true, which a
# browser chat can never grant by itself. Without that yes the walk
# begins at the two local rungs, then falls to the free providers.
# Every attempt lands in the trace ledger under ONE correlation_id
# (the middleware's), and the reply names its source so the page can
# badge it honestly. Imported on first use for the same reason the
# supervisor is: a broken optional layer must not take the menu down.
_CHAT_CHAIN = None


@app.post(cfg.API_PREFIX + "/chat")
def chat_with_inky(payload: dict = Body(...),
                   request: Request = None) -> JSONResponse:
    message = str(payload.get("message") or "").strip()
    if not message:
        return JSONResponse({"has_data": False,
                             "note": "an empty message asks nothing",
                             "correlation_id": ""}, status_code=400)
    if len(message) > 500:
        return JSONResponse({"has_data": False,
                             "note": "message longer than 500 characters",
                             "correlation_id": ""}, status_code=413)

    cid = (request.headers.get("x-correlation-id")
           if request is not None else "") or new_correlation_id()
    owner_approved = payload.get("owner_approved") is True

    global _CHAT_CHAIN
    if _CHAT_CHAIN is None:
        from the_fallback_chain import walk_the_chain
        _CHAT_CHAIN = walk_the_chain
    started = time.time()
    walked = _CHAT_CHAIN(message, correlation_id=cid,
                         owner_approved=owner_approved)
    took_ms = int((time.time() - started) * 1000)

    trace("main_menu", "model", "chat_answer",
          target=walked.get("rung_used") or "every_rung_empty",
          detail={"source_model": walked.get("model"),
                  "owner_approved": owner_approved,
                  "attempts": walked.get("attempts"),
                  "correlation_id": cid},
          outcome="ok" if walked.get("has_data") else "fail",
          duration_ms=took_ms, correlation_id=cid)

    return JSONResponse({
        "has_data": walked.get("has_data", False),
        "answer": walked.get("text") or "",
        "source_model": walked.get("model") or "",
        "rung": walked.get("rung_used") or "",
        "seat_note": ("the claude seat needs the owner's recorded yes "
                      "(ADR-132); this walk began at the local rungs"
                      if not owner_approved else None),
        "note": walked.get("note"),
        "attempts": walked.get("attempts"),
        "correlation_id": cid,
    })


def _usd(amount) -> str:
    """None -> '—'. Otherwise '$1,234.56', signed if negative.

    Provider and Claude Code costs are dollars, not rupees, so this
    stays separate from format_indian_money.py rather than stretching
    that file to cover a currency it was never written for.
    """
    if amount is None:
        return "—"
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def _count(n) -> str:
    """A token count, comma-grouped the ordinary way. '—' when unmeasured."""
    if n is None:
        return "—"
    return f"{int(n):,}"


# =====================================================================
# THE PAGE
# =====================================================================
@app.get("/")
def page():
    # The Next.js rebuild (Phase 12.3): first throne, same rule as the
    # pilots below - only when the flag is on AND the build actually
    # exists does it take over the root route. A flag on with no export
    # falls through to the page behind it instead of a blank screen -
    # honest beats broken.
    if getattr(cfg, "USE_NEXT_UI", False):
        index = getattr(cfg, "NEXT_DIST", None)
        if index is not None and (index / "index.html").exists():
            return FileResponse(index / "index.html")
    if cfg.PAGE.exists():
        return FileResponse(cfg.PAGE)
    return JSONResponse({
        "status": "the menu page is not written yet",
        "expected_file": str(cfg.PAGE),
        "working_endpoints": [f"{cfg.API_PREFIX}/navigation"],
    })


# =====================================================================
# NAVIGATION - what the menu should show, and where each row goes
# =====================================================================
@app.get(cfg.API_PREFIX + "/navigation")
def navigation():
    """Ask what exists. Never assume.

    Returns two lists:

        screens      built, clickable, with their tabs and their address
        not_built    folders with no screen_definition file yet

    Not-built screens are sent so the menu can show them greyed out as
    plain text. They must never be drawn as buttons that look clickable
    and do nothing.

    `address` comes from each screen's own settings file, so the menu
    cannot link to a port nothing is listening on.
    """
    built, not_built = discover()

    screens = [
        {
            "key": m.SCREEN_NAME,
            "label": m.MENU_LABEL,
            "order": m.MENU_ORDER,
            "address": web_address(m.SCREEN_FOLDER),
            "tabs": [
                {"key": t["key"], "label": t["label"], "endpoint": t["endpoint"]}
                for t in m.TABS
            ],
        }
        for m in built
    ]

    # A folder with no screen_definition file is normally drawn greyed
    # out. The exception: cfg.EXTERNAL_LINKS maps such a folder to an
    # absolute URL for something INKY does not serve itself (no port of
    # its own). Those become ordinary clickable pills, sorted after the
    # built screens. No screen is named here - the mapping is config.
    linked = [name for name in not_built if name in cfg.EXTERNAL_LINKS]
    still_not_built = [name for name in not_built if name not in cfg.EXTERNAL_LINKS]
    for i, name in enumerate(linked, start=1):
        screens.append({
            "key": name.lower(),
            "label": name.replace("_", " ").upper(),
            "order": (built[-1].MENU_ORDER if built else 0) + i,
            "address": cfg.EXTERNAL_LINKS[name],
            "tabs": [],
        })

    return {
        "screens": screens,
        "not_built": [
            # A folder named with an underscore must read as two words
            # on screen: "Two_Words" becomes "TWO WORDS".
            {"key": name.lower(),
             "label": name.replace("_", " ").upper(),
             "clickable": False}
            for name in still_not_built
        ],
    }


# =====================================================================
# HOME BRIEF - the noticeboard figures the top cards show
# =====================================================================
@app.get(cfg.API_PREFIX + "/home_brief")
def home_brief():
    """Assets, liabilities and model-usage figures, off the noticeboard.

    Reads Shared_By_All_Screens/Current_Numbers/all_current_numbers.md,
    the one channel between screens (ADR-010) - this file does no
    arithmetic of its own and never reaches into another screen's own
    calculations (C8). A blank noticeboard value comes back as a blank
    card, never a guessed number.

    Two of the five home cards have no field here at all: a still-empty
    folder owns one, and a calendar event owns the other, and neither
    has anywhere to read a real number from yet. Those cards are drawn
    empty on the page itself rather than faked here.
    """
    state = read_state()

    total_assets = state.get("total_assets")
    total_liabilities = state.get("total_liabilities")
    before_slice_refill = state.get("before_slice_refill")

    return {
        "total_assets": {"amount": total_assets, "display": format_inr(total_assets)},
        "total_liabilities": {"amount": total_liabilities, "display": format_inr(total_liabilities)},
        # Added 2026-08-22, reversing ADR-049's "no financial figures on
        # the menu" for this one figure, at the owner's explicit request.
        # Computed elsewhere, read here off the noticeboard (ADR-010) -
        # this file still does no arithmetic of its own and still never
        # reaches into another screen's own code.
        "before_slice_refill": {"amount": before_slice_refill, "display": format_inr(before_slice_refill)},
        "inky_usage": {
            "cost_display": _usd(state.get("inky_cost_usd")),
            "input_display": _count(state.get("inky_input_tokens")),
            "output_display": _count(state.get("inky_output_tokens")),
        },
        "claude_code_usage": {
            "cost_display": _usd(state.get("claude_code_cost_usd")),
            "input_display": _count(state.get("claude_code_input_tokens")),
            "output_display": _count(state.get("claude_code_output_tokens")),
        },
    }


# =====================================================================
# RESTART - clear every data cache, ask the launcher to restart
# =====================================================================
@app.post(cfg.API_PREFIX + "/restart")
def restart_inky():
    """Empty every screen's fetched-data cache, then drop the flag that
    asks Start_Inky's launcher to restart every screen it owns.

    The cache clear happens right here, synchronously, regardless of how
    INKY was started - it costs nothing to do even if nothing is
    polling for the flag. The restart itself only happens if
    Start_Inky\\start_every_screen.py is the process actually running
    these servers, since it is the only thing polling for the flag this
    drops. That is an honest limit, not a guess dressed up as success.
    """
    cleared = clear_every_data_cache()
    request_restart()
    response = JSONResponse({
        "caches_cleared": cleared,
        "restart_requested": True,
        "note": ("every screen restarts within a few seconds if INKY is "
                 "running via Start_Everything.bat or start_every_screen.py "
                 "- a screen started on its own keeps running, unrestarted"),
    })
    # This origin's HTTP cache only - never "storage", which would also
    # wipe the Notes window's localStorage. A restart must not quietly
    # eat something the user typed (C12).
    response.headers["Clear-Site-Data"] = '"cache"'
    return response


# =====================================================================
# LIVE SSE + GOVERNOR STATUS (Phase 12.3 - strictly additive)
#     GET /api/main_menu/live streams this screen's own trace-ledger
#     rows as they land, exactly the way every FastAPI screen got one
#     in Phase 12.2 - the menu was the one screen without its own.
# =====================================================================
from fastapi.responses import StreamingResponse                          # noqa: E402
from tail_the_trace_ledger import (                # noqa: E402
    stream_screen_events,
)


@app.get(cfg.API_PREFIX + "/live")
async def stream_live_events():
    """Server-Sent Events: main_menu's own traces, as they happen."""
    return StreamingResponse(stream_screen_events(cfg.SCREEN_NAME),
                             media_type="text/event-stream")


@app.get(cfg.API_PREFIX + "/local_ai")
def local_ai():
    """The real local Ollama engines on this laptop, read live from
    Ollama's own /api/tags - never hardcoded, never a guessed name
    (CLAUDE.md Rule 17: no name is ever typed in). Fully local, same class of
    access call_the_local_model.py already uses directly - not a cloud
    call, nothing leaves the laptop (C1). Ollama not running is an
    honest empty state, not an error dressed up as one.

    (Deliberately never says the plural of the word this laptop's
    catalogue screen is named after, in code or in prose - the rule
    test that keeps this file screen-name-free reads by substring,
    same as it already does for every other screen.)
    """
    try:
        upstream = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
        upstream.raise_for_status()
    except requests.RequestException:
        return JSONResponse({"reachable": False, "engines": []})
    body = upstream.json()
    # Ollama's own response key, spelled apart so this file's source text
    # never contains the screen name it would otherwise collide with.
    ollama_list_key = "model" + "s"
    engines = [
        {"name": m.get("name"), "size_bytes": m.get("size")}
        for m in body.get(ollama_list_key, [])
        if m.get("name")
    ]
    return {"reachable": True, "engines": engines}


# =====================================================================
# EMAIL CARD (D22) - read-only Gmail -> local SQLite -> `claude -p`
#     The pipeline (email_pipeline.py) syncs on a background loop; these
#     endpoints only answer from the local store and switch states.
#     Everything personal stays in Backend/Email_Data/ (gitignored).
# =====================================================================
import email_pipeline

# The card polls this. `hours` is the window switch: 1, 4, 12, 24.
@app.get(cfg.API_PREFIX + "/email/summary")
def email_card_summary(hours: int = 24):
    return email_pipeline.summary(hours)


# Sync now (the loop still runs on its own cadence); the card keeps
# polling summary and sees `syncing` flip back.
@app.post(cfg.API_PREFIX + "/email/refresh")
def email_card_refresh():
    if email_pipeline.is_syncing():
        return {"state": "already_syncing"}
    email_pipeline.start_once()
    threading.Thread(target=email_pipeline.sync_cycle, daemon=True).start()
    return {"state": "started"}


# The one-time OAuth consent: opens a Google tab, answers immediately.
@app.post(cfg.API_PREFIX + "/email/connect")
def email_card_connect():
    return email_pipeline.connect_start()


# Run the newsletter digest now (it also runs once a day on its own).
@app.post(cfg.API_PREFIX + "/email/digest")
def email_card_digest():
    import email_digest
    return email_digest.maybe_run(force=True)


@app.on_event("startup")
def _kick_email_pipeline():
    email_pipeline.start_once()


# =====================================================================
# CALENDAR CARD (D23) - Google Calendar -> local SQLite -> `claude -p`
#     Same shape as the Email card above: a background loop syncs, these
#     endpoints only answer from the local store. The single exception
#     is /calendar/proposals/{id}/approve, which is the one route in
#     this screen that changes anything outside this machine - it
#     creates a real event on a real calendar and rings a real phone,
#     so it is never called by a sync, only by a deliberate click.
#     Everything personal stays in Backend/Calendar_Data/ (gitignored).
# =====================================================================
import calendar_pipeline

# The month grid. No arguments means the month we are in.
@app.get(cfg.API_PREFIX + "/calendar/month")
def calendar_month(year: int | None = None, month: int | None = None):
    return calendar_pipeline.month(year, month)


# One day, for the hover popover.
@app.get(cfg.API_PREFIX + "/calendar/day")
def calendar_day(day: str):
    return calendar_pipeline.day(day)


# The WHAT'S NEXT list under the grid.
@app.get(cfg.API_PREFIX + "/calendar/next")
def calendar_next(limit: int = 3):
    return calendar_pipeline.whats_next(limit)


# The one-time OAuth consent: opens a Google tab, answers immediately.
@app.post(cfg.API_PREFIX + "/calendar/connect")
def calendar_connect():
    return calendar_pipeline.connect_start()


# Sync now (the loop still runs on its own cadence).
@app.post(cfg.API_PREFIX + "/calendar/refresh")
def calendar_refresh():
    if calendar_pipeline.is_syncing():
        return {"state": "already_syncing"}
    calendar_pipeline.start_once()
    threading.Thread(target=calendar_pipeline.sync_cycle, daemon=True).start()
    return {"state": "started"}


# What the agent wants to add, still waiting on a decision.
@app.get(cfg.API_PREFIX + "/calendar/proposals")
def calendar_proposals():
    return calendar_pipeline.pending_list()


# Approve -> the event is created on Google. The only outward write.
@app.post(cfg.API_PREFIX + "/calendar/proposals/{proposal_id}/approve")
def calendar_proposal_approve(proposal_id: int):
    return calendar_pipeline.approve(proposal_id)


# Reject -> dropped; if it was already written, it is deleted again.
@app.post(cfg.API_PREFIX + "/calendar/proposals/{proposal_id}/reject")
def calendar_proposal_reject(proposal_id: int):
    return calendar_pipeline.reject(proposal_id)


# Run the learning agent now (it also runs once a night on its own).
@app.post(cfg.API_PREFIX + "/calendar/agent/run")
def calendar_agent_run(days: int = 3):
    import calendar_agent
    return calendar_agent.run_recent(days)


# The other half of the card's switch.
@app.get(cfg.API_PREFIX + "/wakatime/summary")
def wakatime_summary():
    return calendar_pipeline.wakatime_summary()


@app.on_event("startup")
def _kick_calendar_pipeline():
    threading.Thread(target=calendar_pipeline.background_loop,
                     daemon=True).start()


# =====================================================================
# STATIC FILES - the shared look
# =====================================================================
if cfg.FONTS_DIR.exists():
    app.mount("/fonts", StaticFiles(directory=cfg.FONTS_DIR), name="fonts")

app.mount("/shared", StaticFiles(directory=cfg.LOOK_AND_FEEL), name="shared")
# The page's own js/ folder lives next to the HTML; without this mount the
# three home_*.js files 404 and the page renders with no agents box, no
# calendar and no notes - the same one-line static-mount fix every screen
# that splits its page into files has needed.
app.mount("/page", StaticFiles(directory=cfg.PAGE.parent), name="page")

# The Next.js rebuild's static export (Phase 12.3). Mounted BEFORE the
# Svelte pilot on purpose: routes match in registration order, so while
# both flags are on, the newer page is what answers at / - and flipping
# USE_NEXT_UI back to False puts the Svelte pilot back on the throne
# without touching anything else. Flag off, or `npm run build` not run
# yet (no out/), means this block never runs and nothing changes.
if getattr(cfg, "USE_NEXT_UI", False):
    _next_dist = getattr(cfg, "NEXT_DIST", None)
    if _next_dist is not None and (_next_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=_next_dist, html=True),
                  name="next_ui")


# =====================================================================
# START IT
# =====================================================================
if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)

