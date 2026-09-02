"""CREW — the agent roster (names + duties), the activity feed and the
proposal loop. Live LLM wiring is M4; the contract below is final, only the
`source` flips from 'sample' to 'live'."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_learning as cfg
from services.common import get_db, ledger

router = APIRouter()

AGENTS = [
    {"name": "planner", "title": "Planner",
     "duty": "owns the path — weekly plan inside your time budget, "
             "reorders rooms, keeps both tracks moving",
     "tasks": ["builds the weekly plan from your budget",
               "proposes room reorders as approve-cards",
               "flags when one track is neglected"]},
    {"name": "tutor", "title": "Tutor",
     "duty": "re-explains anything, runs the hint ladder, finds real-world "
             "examples in your context",
     "tasks": ["hint ladder: nudge → hint → new angle → worked example",
               "rewords a step that didn't land",
               "never invents facts outside your material"]},
    {"name": "quizmaster", "title": "Quizmaster",
     "duty": "writes checkpoint questions, grades free-text answers, "
             "mints recall cards from finished rooms",
     "tasks": ["checkpoints per step", "cards into Card Studio",
               "leech detection & rewording"]},
    {"name": "quill", "title": "Quill",
     "duty": "the librarian — files your captures onto the right step, "
             "links related notes, merges duplicates",
     "tasks": ["files ⌘K captures (CTRL+K) to the open step",
               "surfaces notes when a step reopens",
               "keeps the note graph clean"]},
    {"name": "warden", "title": "Warden",
     "duty": "guards focus and momentum — daily briefing, the Today "
             "greeting line, streak & grace, drift nudges",
     "tasks": ["writes the Today greeting from live progress",
               "2-min daily briefing",
               "streak safety + grace banking"]},
    {"name": "auditor", "title": "Auditor",
     "duty": "weekly gap report — wrong answers, decayed rooms, confidence "
             "illusions, and the plan surgery to fix them",
     "tasks": ["weekly gap report",
               "confidence-vs-reality illusions",
               "proposes relearn/reword/resume actions"]},
]


class ProposalBody(BaseModel):
    action: str                     # approved | declined


@router.get(cfg.API_PREFIX + "/crew")
def crew(conn=Depends(get_db)):
    runs = conn.execute(
        "SELECT * FROM agent_runs ORDER BY ts DESC, id DESC LIMIT 15"
    ).fetchall()
    recent = {r["agent"] for r in runs[:3]}
    agents = []
    for a in AGENTS:
        agents.append({**a, "status": "working" if a["name"] in recent else "idle",
                       "last": runs[0]["text"] if runs and runs[0]["agent"] == a["name"]
                       else None})
    proposals = conn.execute(
        "SELECT * FROM proposals ORDER BY (status='pending') DESC, id DESC LIMIT 10"
    ).fetchall()
    return {
        "agents": agents,
        "feed": [{"ts": r["ts"], "agent": r["agent"], "text": r["text"],
                  "source": r["source"]} for r in runs],
        "proposals": [{"id": p["id"], "agent": p["agent"], "kind": p["kind"],
                       "summary": p["summary"], "detail": p["detail"],
                       "status": p["status"]} for p in proposals],
    }


@router.post(cfg.API_PREFIX + "/proposals/{proposal_id}/decide")
def decide(proposal_id: int, body: ProposalBody, conn=Depends(get_db)):
    if body.action not in ("approved", "declined"):
        raise HTTPException(422, "action must be approved|declined")
    p = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
    if not p:
        raise HTTPException(404, "no such proposal")
    conn.execute("UPDATE proposals SET status=? WHERE id=?",
                 (body.action, proposal_id))
    ledger(conn, "crew", f"proposal #{proposal_id} {body.action} — {p['agent']}: "
           f"{p['summary']}")
    conn.commit()
    return {"ok": True, "status": body.action}
