"""Backend for the Enhancement UI.

WHAT THIS FILE DOES
    Turns what manage_enhancement_ideas.py already knows into JSON the
    Enhancement page can fetch. Same rule as every other screen's
    server: no arithmetic happens here, only fetching, shaping and
    handing over.

WHERE THIS CAME FROM
    Moved out of Screens/Learning/Backend/server_for_learning.py
    2026-08-22 (ADR-067) - same behaviour, just served from this screen's
    own port instead of Learning's. The board grew a Kanban backend on
    top of the same storage module (SQLite, enhancement_board.db), so
    the endpoints are read / add / edit / move / comment / delete now.

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    python Screens\\Enhancement\\Backend\\server_for_enhancement.py
    then open http://127.0.0.1:8004
"""

# =====================================================================
# SETUP
# =====================================================================
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Enhancement folder
PROJECT_ROOT = HERE.parents[2]              # the inky folder

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCREEN / "Calculations"))

from fastapi import Body, FastAPI                                       # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles                             # noqa: E402

import settings_for_enhancement as cfg                                 # noqa: E402

import manage_enhancement_ideas as ideas                               # noqa: E402
import find_similar_ideas as similar                                   # noqa: E402

# A fresh board starts with the project's planned work already on it
# (tracked seed file). A re-run is a no-op once the board has cards.
ideas.seed_ideas_if_empty()

from Shared_By_All_Screens.show_not_built_yet import page_html          # noqa: E402
from Shared_By_All_Screens.trace_every_action import (                  # noqa: E402
    new_correlation_id, trace,
)

app = FastAPI(title=cfg.SCREEN_LABEL)

# Liveness + dependency probe (Phase-1 W1.3) - see health_check.py.
from Shared_By_All_Screens import health_check                          # noqa: E402
health_check.register(app, "enhancement", saved_records=lambda: cfg.SAVED_RECORDS)


# =====================================================================
# THE TRACE LEDGER - every served request and every page click lands in
# Shared_By_All_Screens/Trace_Ledger/, the same way Finance does it.
# =====================================================================
@app.middleware("http")
async def _trace_api_requests(request, call_next):
    """One row per API call served. Static mounts (/shared, /page, /fonts)
    and the 30-second /dev poll are excluded on purpose - that is noise,
    not signal.

    Phase-1 CS-1: one correlation id per request - honoured from an
    inbound X-Correlation-Id header when present, minted when not,
    echoed back so the caller can chain the next hop."""
    started = time.time()
    cid = request.headers.get("x-correlation-id") or new_correlation_id()
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = cid
    path = request.url.path
    if not path.startswith(("/shared", "/page", "/fonts", "/docs",
                            "/redoc", "/openapi.json", "/dev")):
        trace("enhancement", "api", f"{request.method} {path}",
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
    result = has_changed(token, cfg.WATCHED_FOLDERS)
    if not is_enabled():
        return {"changed": False, "fingerprint": result["fingerprint"],
                "latest_file": "", "latest_at": ""}
    if result["changed"] and token:
        trace("enhancement", "ledger", "file_changed",
              target=result["latest_file"],
              detail={"latest_at": result["latest_at"]})
    return result


# =====================================================================
# THE PAGE
# =====================================================================
@app.get("/")
def page():
    # The Next.js rebuild (Phase 12.4): first throne, same rule as the
    # Svelte pilot below - only when the flag is on AND the build
    # actually exists does it take over the root route. A flag on with
    # no export falls through to the page behind it instead of a blank
    # screen - honest beats broken.
    if getattr(cfg, "USE_NEXT_UI", False):
        index = getattr(cfg, "NEXT_DIST", None)
        if index is not None and (index / "index.html").exists():
            return FileResponse(index / "index.html")
    if cfg.PAGE.exists():
        # no-store, not just no-cache: an enhancement board that edits
        # itself must never let the browser answer from yesterday's copy.
        return FileResponse(cfg.PAGE, headers={"Cache-Control": "no-store"})

    return HTMLResponse(page_html(
        cfg.SCREEN_LABEL,
        cfg.PAGE,
        [f"{cfg.API_PREFIX}/ideas"],
    ))


# =====================================================================
# TAB 1 — BOARD
# =====================================================================
# The board is four columns (ideas / todo / in_progress / done) and the
# endpoints below are exactly what dragging a card around needs: read
# the whole board, add, edit, move, comment, delete.

@app.get(cfg.API_PREFIX + "/ideas")
def get_ideas():
    return {"built": True, "ideas": ideas.read_ideas()}


@app.post(cfg.API_PREFIX + "/ideas")
def add_idea(body: dict = Body(...)):
    try:
        # The de-duplication check rides along but never blocks: it runs
        # against the board as it stands BEFORE the save, and whatever it
        # finds goes back to the page as duplicate_warning next to ok:true.
        matches = similar.find_similar_ideas(
            body.get("title") or "", ideas.read_ideas())
        item = ideas.add_idea(body.get("title"), body.get("note", ""),
                              body.get("area", ""), body.get("source", "user"),
                              body.get("priority", "medium"))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    except ideas.DuplicateIdea as d:
        # Phase-1 CS-2 retry-safety: a double-posted idea is answered
        # with the row already stored, flagged, never a second card.
        return {"ok": True, "item": d.existing, "duplicate": True}
    response = {"ok": True, "item": item}
    if matches:
        best = matches[0]
        response["duplicate_warning"] = {
            "of_id": best["of_id"], "of_key": best["of_key"],
            "of_title": best["of_title"], "reason": best["reason"],
        }
    return response


@app.put(cfg.API_PREFIX + "/ideas/{item_id}")
def edit_idea(item_id: str, body: dict = Body(...)):
    try:
        item = ideas.update_idea(item_id, body.get("title"), body.get("note"),
                                 body.get("area"), body.get("priority"))
    except ideas.NoSuchIdea as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "item": item}


@app.patch(cfg.API_PREFIX + "/ideas/{item_id}/status")
def move_idea(item_id: str, body: dict = Body(...)):
    try:
        item = ideas.set_status(item_id, body.get("status"),
                                body.get("order_index"))
    except ideas.NoSuchIdea as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "item": item}


@app.post(cfg.API_PREFIX + "/ideas/{item_id}/comments")
def comment_on_idea(item_id: str, body: dict = Body(...)):
    try:
        # The module hands back just the new comment; the endpoint hands
        # back the whole updated idea, same as every other route here -
        # one response shape across the board is easier to trust.
        ideas.add_comment(item_id, body.get("text"),
                          body.get("author", "user"))
        return {"ok": True, "item": ideas.get_idea(item_id)}
    except ideas.NoSuchIdea as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)


@app.delete(cfg.API_PREFIX + "/ideas")
def remove_idea(id: str):
    # The query parameter is ?id= - the same word the page's fetch uses,
    # and one shape across every screen beats avoiding a builtin shadow.
    try:
        ideas.remove_idea(id)
    except ideas.NoSuchIdea as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True}


# =====================================================================
# LIVE SSE (Phase 12.2 - strictly additive)
#     GET /api/enhancement/live streams this screen's own trace-ledger
#     rows as they land, so a page can show live activity without
#     polling. Tails Shared_By_All_Screens/Trace_Ledger/traces_<date>.
#     jsonl via Shared_By_All_Screens/tail_the_trace_ledger.py.
#
#     Registered BEFORE the static mounts below (Phase 12.4 fix): the
#     Next.js export mounts "/" as a catch-all, and Starlette matches
#     routes in registration order - a route added after a "/" mount
#     is shadowed by it and 404s. Every /api route in this file must
#     stay above the mounts for the same reason.
# =====================================================================
from fastapi.responses import StreamingResponse                          # noqa: E402
from Shared_By_All_Screens.tail_the_trace_ledger import (                # noqa: E402
    stream_screen_events,
)


@app.get(cfg.API_PREFIX + "/live")
async def stream_live_events():
    """Server-Sent Events: enhancement's own traces, as they happen."""
    return StreamingResponse(stream_screen_events("enhancement"),
                             media_type="text/event-stream")


# =====================================================================
# STATIC FILES
# =====================================================================
# The look every screen shares.
if cfg.FONTS_DIR.exists():
    app.mount("/fonts", StaticFiles(directory=cfg.FONTS_DIR), name="fonts")

app.mount("/shared", StaticFiles(directory=cfg.LOOK_AND_FEEL), name="shared")

# This screen's own CSS/JS. Mounted, not routed one file at a time -
# Page/ only ever holds this screen's own look, never anything that
# needs a check before serving.
app.mount("/page", StaticFiles(directory=cfg.PAGE.parent), name="page")

# The Next.js rebuild's static export (Phase 12.4). Mounted BEFORE the
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

# The Svelte pilot's built assets (U2). Mounted last and only when the
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

