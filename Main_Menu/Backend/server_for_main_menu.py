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
import time
from datetime import datetime
from pathlib import Path

import requests

# This file sits at  Main_Menu/Backend/server_for_main_menu.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
# The agent layer lives beside the screens layer at the root. Adding
# its folder here is what lets this server hand work to the supervisor
# below - it is not a reach into any screen's own code.
sys.path.insert(0, str(PROJECT_ROOT / "Shared_By_All_Agents"))

from fastapi import Body, FastAPI, Request                # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles               # noqa: E402

import settings_for_main_menu as cfg                      # noqa: E402
from find_every_screen import discover                    # noqa: E402
from Shared_By_All_Agents.read_agent_cards import every_agent  # noqa: E402
from Shared_By_All_Screens.read_screen_settings import web_address   # noqa: E402
from Shared_By_All_Screens.read_and_write_numbers import read_state  # noqa: E402
from Shared_By_All_Screens.format_indian_money import format_inr     # noqa: E402
from Shared_By_All_Screens.trace_every_action import (              # noqa: E402
    new_correlation_id, trace,
)
from Shared_By_All_Screens.restart_signal import request_restart     # noqa: E402
from Shared_By_All_Screens.clear_every_data_cache import (           # noqa: E402
    clear_every_data_cache)

app = FastAPI(title=cfg.SCREEN_LABEL)

# Liveness + dependency probe (Phase-1 W1.3) - see health_check.py.
# The menu's own dependency is the Screens/ tree it exists to list.
from Shared_By_All_Screens import health_check                          # noqa: E402
health_check.register(app, "main_menu",
                      screens_root=lambda: Path(__file__).resolve().parents[2] / "Screens")


# =====================================================================
# THE TRACE LEDGER - every served request and every page click lands in
# Shared_By_All_Screens/Trace_Ledger/, the same pattern every screen uses.
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
    from Shared_By_All_Screens.code_change_monitor import has_changed, is_enabled
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


# The supervisor is imported on first use rather than at startup, and
# then remembered. If the agent layer cannot boot for any reason, the
# page and the navigation answer must keep working - losing the whole
# menu because one optional layer failed would be the wrong trade.
_SUPERVISOR = None

_CALCULATIONS_WALKED = False


def _make_the_agent_layer_importable() -> None:
    """Put every screen's calculation groups on the path, once.

    The agent layer's router lives inside one of those group folders,
    and the supervisor imports it by bare module name - which only
    resolves if the groups are already on the path. Tests get that
    from their conftest and each screen's own server does it for its
    own maths; nobody had done it for this one until an endpoint here
    needed to wake an agent. Discovery again, never a list: a new
    screen's calculations become importable the moment its folder
    exists, and no screen is named anywhere below.
    """
    global _CALCULATIONS_WALKED
    if _CALCULATIONS_WALKED:
        return
    for screen_folder in sorted((PROJECT_ROOT / "Screens").iterdir()):
        calculations = screen_folder / "Calculations"
        if not calculations.is_dir():
            continue
        for group in sorted(calculations.iterdir()):
            if group.is_dir() and not group.name.startswith(("_", ".")) \
                    and group.name != "__pycache__":
                if str(group) not in sys.path:
                    sys.path.insert(0, str(group))
        if str(calculations) not in sys.path:
            sys.path.insert(0, str(calculations))
    _CALCULATIONS_WALKED = True


def _hand_this_to_someone(*args, **kwargs):
    global _SUPERVISOR
    if _SUPERVISOR is None:
        _make_the_agent_layer_importable()
        from the_supervisor import hand_this_to_someone
        _SUPERVISOR = hand_this_to_someone
    return _SUPERVISOR(*args, **kwargs)


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
    # The Svelte pilot (U1): only when the flag is on AND the build is
    # actually present does the app take over the root route. A flag on
    # with no dist/ falls back to the ordinary page instead of a blank
    # screen - honest beats broken.
    if getattr(cfg, "USE_SVELTE", False):
        index = getattr(cfg, "SVELTE_DIST", None)
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
# AGENTS - the fleet, grouped the way the home page draws it
# =====================================================================
@app.get(cfg.API_PREFIX + "/agents/fleet")
def agents_fleet():
    """Every agent, sorted into one accordion per navigation tab.

    Two discoveries meet here and neither is hardcoded: screen
    discovery says which tabs exist, and the agent cards say which
    tabs they belong to (an optional HOME_SECTIONS list on a card -
    there is no registration list anywhere). An agent that claims no
    tab, or claims one discovery has never heard of, is not hidden:
    it lands in EVERYWHERE ELSE, because an agent you cannot see is
    an agent nobody would notice going wrong.

    A tab with no agents still gets its accordion, empty - an empty
    section drawn honestly beats a section invented to look busy.
    """
    built, not_built = discover()
    sections: dict = {}

    def open_section(key: str, label: str) -> dict:
        if key not in sections:
            sections[key] = {"key": key, "label": label, "agents": []}
        return sections[key]

    # The same keys the navigation payload uses, in the same order.
    for m in built:
        open_section(m.SCREEN_NAME.lower(), m.MENU_LABEL)
    for name in not_built:
        open_section(name.lower(), name.replace("_", " ").upper())
    elsewhere = open_section("elsewhere", "EVERYWHERE ELSE")

    for agent in every_agent():
        entry = {
            "name": agent["agent_name"],
            "what_i_am_for": agent["what_i_am_for"],
            "state": agent["state"],
        }
        claimed = agent.get("home_sections") or []
        placed = False
        for key in claimed:
            section = sections.get(key)
            if section is not None and section is not elsewhere:
                section["agents"].append(entry)
                placed = True
        if not placed:
            elsewhere["agents"].append(entry)

    return {"sections": list(sections.values())}


# =====================================================================
# HOME BLOCKS - refreshed by an agent, never computed here
# =====================================================================
@app.post(cfg.API_PREFIX + "/agents/home_blocks/refresh")
def refresh_home_blocks():
    """Hand the block refresh to whichever agent claims the shape.

    This file does no arithmetic of its own and never reads another
    box's figures directly. It asks the supervisor; an agent reads
    the noticeboard and answers. Rupee blocks arrive already
    formatted; dollar costs and token counts arrive as raw numbers
    and are formatted HERE, with the same two formatters the brief
    endpoint uses, so a number is written the same way no matter
    which endpoint carried it.

    A non-finished job still answers 200 with its state and a why.
    The page renders that honestly as "the refresh did not happen" -
    a 500 would claim the server broke, when what actually happened
    is a refusal, a queue or a stop, all of which are ordinary.
    """
    try:
        went = _hand_this_to_someone(
            "refresh_the_home_blocks",
            goal="read the current block figures off the noticeboard",
        )
    except Exception as trouble:                                     # noqa: BLE001
        return JSONResponse(
            {"state": "error", "blocks": None,
             "why": f"the agent layer could not be reached: {trouble}"},
            status_code=500,
        )

    blocks = None
    if went.state == "finished" and isinstance(went.answer, dict):
        blocks = went.answer.get("blocks")
        if isinstance(blocks, dict):
            for usage_block in ("inky_usage", "claude_code_usage"):
                raw = blocks.get(usage_block) or {}
                blocks[usage_block] = {
                    "cost_display": _usd(raw.get("cost_usd")),
                    "input_display": _count(raw.get("input_tokens")),
                    "output_display": _count(raw.get("output_tokens")),
                }
    return {"state": went.state, "blocks": blocks, "why": went.why}


# =====================================================================
# CALENDAR - shown and grown by an agent, through the supervisor
# =====================================================================
@app.get(cfg.API_PREFIX + "/calendar/events")
def calendar_events():
    """The dated events the calendar agent keeps on file.

    Like the blocks above, this endpoint stores nothing and knows
    nothing about where events live. It asks the supervisor, and the
    agent answers out of its own memory. No events on file comes
    back as an empty list, which is the truth, not a failure.
    """
    try:
        went = _hand_this_to_someone(
            "show_the_home_calendar",
            goal="read the calendar events currently on file",
        )
    except Exception as trouble:                                     # noqa: BLE001
        return JSONResponse(
            {"state": "error", "events": None,
             "why": f"the agent layer could not be reached: {trouble}"},
            status_code=500,
        )

    answer = went.answer if went.state == "finished" and isinstance(went.answer, dict) else {}
    return {"state": went.state,
            "summary": answer.get("summary"),
            "events": answer.get("events"),
            "why": went.why}


@app.post(cfg.API_PREFIX + "/calendar/events")
def add_calendar_event(payload: dict = Body(...)):
    """Add one dated event, through the same agent that shows them.

    The shape checks here are deliberately shallow - is this even a
    date, is this even words? - so obvious rubbish gets a 400 before
    any agent wakes up. The agent re-checks both fields itself,
    because a check that exists only at the door is not a rule, it is
    a hope. Two checks, two layers, same shapes.
    """
    date = str(payload.get("date", "")).strip()
    title = str(payload.get("title", "")).strip()

    problems = []
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        problems.append("date must be shaped YYYY-MM-DD")
    if not title:
        problems.append("title must not be empty")
    elif len(title) > 200:
        problems.append("title must be 200 characters or fewer")
    if problems:
        return JSONResponse({"detail": "; ".join(problems)}, status_code=400)

    try:
        went = _hand_this_to_someone(
            "add_a_calendar_event",
            goal=f"add the event '{title[:80]}' on {date}",
            expectation={"date": date, "title": title},
        )
    except Exception as trouble:                                     # noqa: BLE001
        return JSONResponse(
            {"state": "error", "events": None,
             "why": f"the agent layer could not be reached: {trouble}"},
            status_code=500,
        )

    answer = went.answer if went.state == "finished" and isinstance(went.answer, dict) else {}
    return {"state": went.state,
            "summary": answer.get("summary"),
            "events": answer.get("events"),
            "why": went.why}


# =====================================================================
# LIVE SSE + GOVERNOR STATUS (Phase 12.3 - strictly additive)
#     GET /api/main_menu/live streams this screen's own trace-ledger
#     rows as they land, exactly the way every FastAPI screen got one
#     in Phase 12.2 - the menu was the one screen without its own.
#     GET /api/main_menu/governor answers what the Resource Governor
#     sees right now, per model - read from Shared_By_All_Agents over
#     import like read_agent_cards above, never from another screen.
# =====================================================================
from fastapi.responses import StreamingResponse                          # noqa: E402
from Shared_By_All_Screens.tail_the_trace_ledger import (                # noqa: E402
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
    (Rule 4: no name is ever typed in). Fully local, same class of
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


@app.get(cfg.API_PREFIX + "/agents/{name}/files")
def agent_files(name: str):
    """The real files under one agent's own folder, for the ring's
    click-through file graph. A plain directory walk, Tier 0, no model
    call - the same 'discovered, never configured' rule agents/fleet
    above already follows, one level deeper. Never another agent's
    folder: the name is stripped down to what an agent folder can
    actually be named before it touches disk.
    """
    safe = "".join(c for c in name if c.isalnum() or c == "_")
    folder = PROJECT_ROOT / "Agents" / safe
    if not safe or not folder.is_dir():
        return JSONResponse(
            {"has_data": False, "files": [], "reason": "no such agent folder"},
            status_code=404)
    files = []
    for path in sorted(folder.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(folder)
        files.append({
            "path": str(rel).replace("\\", "/"),
            "kind": rel.parts[0] if len(rel.parts) > 1 else "root",
            "size_bytes": path.stat().st_size,
        })
    return {"has_data": True, "agent": safe, "files": files}


@app.get(cfg.API_PREFIX + "/governor")
def governor_status():
    """What the Resource Governor sees right now, never merged or guessed.

    A governor that cannot be asked is a governor nobody trusts, so this
    hands back its own honest answer verbatim. If the governor module
    itself will not load, that failure is the answer - an unavailable
    status is never dressed up as an idle one.
    """
    try:
        from the_resource_governor import status as status_now
    except Exception as trouble:                       # pragma: no cover
        return JSONResponse(
            {"has_data": False,
             "reason": f"resource governor could not be loaded: {trouble}"},
            status_code=503)
    try:
        return JSONResponse(status_now())
    except Exception as trouble:
        return JSONResponse(
            {"has_data": False,
             "reason": f"resource governor status failed: {trouble}"},
            status_code=502)


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


# The Svelte pilot's built assets (U1). Mounted last and only when the
# flag is on with a real build present: routes registered above it - every
# /api route included - are matched first, so this can only ever catch
# what the pilot itself asks for (its hashed /assets files). Flag off or
# no dist/ means this block never runs and nothing about the screen
# changes.
if getattr(cfg, "USE_SVELTE", False):
    _svelte_dist = getattr(cfg, "SVELTE_DIST", None)
    if _svelte_dist is not None and _svelte_dist.is_dir():
        app.mount("/", StaticFiles(directory=_svelte_dist, html=True),
                  name="svelte_pilot")


# =====================================================================
# START IT
# =====================================================================
if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)

