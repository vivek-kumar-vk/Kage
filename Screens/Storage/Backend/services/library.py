"""The agent library (D40) - the one place every screen's agent writes its
current state, so any other agent can read it without a screen-to-screen
call. A thin naming convention over the existing seam, not a new store:
`library/<screen>/<tab>/<card>/<card>_<timestamp>.md`. Every write is a new
dated file - never an overwrite - so a card's folder is its own history.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

import settings_for_storage as cfg
from services import seam

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))
LIBRARY_PREFIX = "library"


def _card_prefix(screen: str, tab: str, card: str) -> str:
    return f"{LIBRARY_PREFIX}/{screen}/{tab}/{card}"


def write_snapshot(screen: str, tab: str, card: str, content: str) -> dict:
    """Writes a new dated file under the card's folder. Never overwrites -
    the filename carries the IST timestamp, so history is just the folder."""
    now = datetime.now(IST)
    filename = f"{card}_{now.strftime('%Y%m%d_%H%M%S')}.md"
    path = f"{_card_prefix(screen, tab, card)}/{filename}"
    return seam.write_doc(path, content)


def latest_snapshot(screen: str, tab: str, card: str) -> dict | None:
    """The newest file in a card's folder, or None if nothing's been
    written yet - never a fabricated empty snapshot (Rule 8)."""
    docs = seam.list_docs(_card_prefix(screen, tab, card))
    if not docs:
        return None
    newest = max(docs, key=lambda d: d["path"])  # timestamp in the filename sorts lexically
    content = seam.read_doc(newest["path"])
    return {**newest, "content": content}


def history(screen: str, tab: str, card: str) -> list:
    """Every version on file for a card, oldest first."""
    return seam.list_docs(_card_prefix(screen, tab, card))


# =====================================================================
# ROUTES
# =====================================================================
@router.post(cfg.API_PREFIX + "/library/{screen}/{tab}/{card}")
def api_write_snapshot(screen: str, tab: str, card: str, body: dict = Body(...)):
    content = body.get("content")
    if not isinstance(content, str) or not content.strip():
        return JSONResponse(
            status_code=422, content={"state": "error", "problem": "content must be a non-empty string"}
        )
    try:
        result = write_snapshot(screen, tab, card, content)
    except seam.PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})
    return {"state": "ok", **result}


@router.get(cfg.API_PREFIX + "/library/{screen}/{tab}/{card}/latest")
def api_latest_snapshot(screen: str, tab: str, card: str):
    try:
        result = latest_snapshot(screen, tab, card)
    except seam.PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"state": "error", "problem": f"no snapshot written yet for {screen}/{tab}/{card}"},
        )
    return {"state": "ok", **result}


@router.get(cfg.API_PREFIX + "/library/{screen}/{tab}/{card}")
def api_history(screen: str, tab: str, card: str):
    try:
        docs = history(screen, tab, card)
    except seam.PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})
    return {"state": "ok", "versions": docs}
