"""Trader ledger stub (D11.4) - append-only, via the seam.

The future AI-trader lives in its own screen/agent, unbuilt. This ships
only the ledger it will write to: one JSON file per decision, no
update, no delete. Finance's no-buy/sell-recommendation rule is
unaffected - this is a log, not a recommender.
"""

import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

import settings_for_storage as cfg
from services import seam

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))
LEDGER_PREFIX = "trader/ledger"


@router.post(cfg.API_PREFIX + "/trader/decisions")
def post_decision(body: dict = Body(...)):
    if not isinstance(body, dict) or not body:
        return JSONResponse(
            status_code=422, content={"state": "error", "problem": "empty decision body"}
        )

    now = datetime.now(IST)
    date = now.strftime("%Y-%m-%d")
    seq_path = f"{LEDGER_PREFIX}/{date}"
    existing = [d for d in seam.list_docs(seq_path)]
    seq = len(existing) + 1
    filename = f"{now.strftime('%H%M%S')}-{seq:03d}.json"
    path = f"{seq_path}/{filename}"

    record = {**body, "recorded_at": now.isoformat()}
    result = seam.write_doc(path, json.dumps(record, indent=2))
    return {"state": "ok", "path": result["path"]}


@router.get(cfg.API_PREFIX + "/trader/decisions")
def list_decisions(limit: int = 50):
    docs = seam.list_docs(LEDGER_PREFIX)
    docs.sort(key=lambda d: d["path"], reverse=True)  # newest first: date/time is in the path
    out = []
    for doc in docs[:limit]:
        try:
            content = seam.read_doc(doc["path"])
        except FileNotFoundError:
            continue
        try:
            out.append({"path": doc["path"], **json.loads(content)})
        except json.JSONDecodeError:
            out.append({"path": doc["path"], "problem": "unreadable record"})
    return {"state": "ok", "decisions": out}
