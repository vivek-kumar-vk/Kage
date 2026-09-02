"""ROOM — the lesson player backend. Full room payload (steps, beats,
checkpoints, notes, feynman) plus every write: step status, lab proof,
checklist ticks, checkpoint attempts, notes, feynman."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_learning as cfg
from services.common import (
    get_db, ledger, room_mastery, level_for, jload, jdump, short_name, now_str,
)

router = APIRouter()


class StepStatusBody(BaseModel):
    status: str                      # todo | current | done


class ProofBody(BaseModel):
    text: str


class ChecklistBody(BaseModel):
    items: list[str]


class AttemptBody(BaseModel):
    answer: str | None = None        # chosen index (mcq, as str) or text
    self_grade: str | None = None    # matched | off | skipped (freetext)


class NoteBody(BaseModel):
    body: str
    step_id: int | None = None


class FeynmanBody(BaseModel):
    text: str


def _room_row(conn, room_id):
    room = conn.execute(
        """SELECT r.*, m.name module, m.track_id, t.name track, t.color
           FROM rooms r JOIN modules m ON m.id=r.module_id
           JOIN tracks t ON t.id=m.track_id WHERE r.id=?""",
        (room_id,),
    ).fetchone()
    if not room:
        raise HTTPException(404, "no such room")
    return room


@router.get(cfg.API_PREFIX + "/room/{room_id}")
def get_room(room_id: int, conn=Depends(get_db)):
    room = _room_row(conn, room_id)
    steps_out = []
    for s in conn.execute(
        "SELECT * FROM steps WHERE room_id=? ORDER BY position, id", (room_id,)
    ).fetchall():
        ckpts = []
        for ck in conn.execute(
            """SELECT * FROM checkpoints WHERE step_id=? ORDER BY position, id""",
            (s["id"],),
        ).fetchall():
            attempts = conn.execute(
                """SELECT correct, self_grade, ts FROM attempts
                   WHERE checkpoint_id=? ORDER BY id DESC LIMIT 1""",
                (ck["id"],),
            ).fetchone()
            ckpts.append({
                "id": ck["id"], "kind": ck["kind"], "question": ck["question"],
                "options": jload(ck["options"], []),
                "answer_idx": ck["answer_idx"], "model_answer": ck["model_answer"],
                "answered": bool(attempts),
                "last_correct": attempts["correct"] if attempts else None,
                "last_self_grade": attempts["self_grade"] if attempts else None,
            })
        steps_out.append({
            "id": s["id"], "position": s["position"], "title": s["title"],
            "minutes": s["minutes"], "status": s["status"],
            "explain": s["explain"], "realworld": s["realworld"],
            "lab": {
                "objective": s["lab_objective"], "env": s["lab_env"],
                "link": s["lab_link"],
                "checklist": jload(s["lab_checklist"], []),
                "proof": s["lab_proof"],
            },
            "checkpoints": ckpts,
        })

    notes = conn.execute(
        "SELECT * FROM notes WHERE room_id=? ORDER BY id DESC", (room_id,)
    ).fetchall()

    mastery = room_mastery(conn, room_id)
    next_room = conn.execute(
        """SELECT r.id FROM rooms r JOIN modules m ON m.id=r.module_id
           WHERE m.track_id=? AND r.archived=0 AND r.id>?
           ORDER BY m.position, r.position LIMIT 1""",
        (room["track_id"], room_id),
    ).fetchone()

    return {
        "id": room["id"], "name": room["name"], "short": short_name(room["name"]),
        "module": room["module"], "track": room["track"], "track_id": room["track_id"],
        "color": room["color"], "status": room["status"], "feynman": room["feynman"],
        "mastery": mastery, "level": level_for(mastery),
        "steps": steps_out,
        "notes": [{"id": n["id"], "body": n["body"], "step_id": n["step_id"],
                   "created_at": n["created_at"]} for n in notes],
        "next_room_id": next_room["id"] if next_room else None,
    }


@router.post(cfg.API_PREFIX + "/step/{step_id}/status")
def set_step_status(step_id: int, body: StepStatusBody, conn=Depends(get_db)):
    step = conn.execute("SELECT * FROM steps WHERE id=?", (step_id,)).fetchone()
    if not step:
        raise HTTPException(404, "no such step")
    conn.execute("UPDATE steps SET status=? WHERE id=?", (body.status, step_id))
    if body.status == "done":
        # first pending step becomes current
        nxt = conn.execute(
            """SELECT id FROM steps WHERE room_id=? AND status='todo'
               ORDER BY position LIMIT 1""",
            (step["room_id"],),
        ).fetchone()
        conn.execute("UPDATE steps SET status='current' WHERE id=?",
                     (nxt["id"],)) if nxt else None
        conn.execute(
            "UPDATE rooms SET status='learning' WHERE id=? AND status='todo'",
            (step["room_id"],),
        )
        left = conn.execute(
            """SELECT COUNT(*) n FROM steps WHERE room_id=? AND status!='done'""",
            (step["room_id"],),
        ).fetchone()["n"]
        room = conn.execute("SELECT name FROM rooms WHERE id=?",
                            (step["room_id"],)).fetchone()
        if left == 0:
            conn.execute("UPDATE rooms SET status='done' WHERE id=?",
                         (step["room_id"],))
            ledger(conn, "room", f"room completed — {room['name']}",
                   ref=f"room:{step['room_id']}")
        else:
            ledger(conn, "room", f"step done — {short_name(room['name'])} "
                   f"({left} steps left)")
    conn.commit()
    return {"ok": True}


@router.post(cfg.API_PREFIX + "/step/{step_id}/proof")
def set_proof(step_id: int, body: ProofBody, conn=Depends(get_db)):
    step = conn.execute("SELECT * FROM steps WHERE id=?", (step_id,)).fetchone()
    if not step:
        raise HTTPException(404, "no such step")
    conn.execute("UPDATE steps SET lab_proof=? WHERE id=?", (body.text, step_id))
    ledger(conn, "room", "lab proof pasted", ref=f"step:{step_id}")
    conn.commit()
    return {"ok": True}


@router.post(cfg.API_PREFIX + "/step/{step_id}/checklist")
def set_checklist(step_id: int, body: ChecklistBody, conn=Depends(get_db)):
    conn.execute("UPDATE steps SET lab_checklist=? WHERE id=?",
                 (jdump(body.items), step_id))
    conn.commit()
    return {"ok": True}


@router.post(cfg.API_PREFIX + "/checkpoint/{checkpoint_id}/attempt")
def attempt(checkpoint_id: int, body: AttemptBody, conn=Depends(get_db)):
    ck = conn.execute(
        "SELECT * FROM checkpoints WHERE id=?", (checkpoint_id,)
    ).fetchone()
    if not ck:
        raise HTTPException(404, "no such checkpoint")

    correct = None
    if ck["kind"] == "mcq":
        try:
            correct = 1 if int(body.answer or -1) == ck["answer_idx"] else 0
        except ValueError:
            correct = 0
    conn.execute(
        """INSERT INTO attempts (checkpoint_id, answer, correct, self_grade, ts)
           VALUES (?,?,?,?,?)""",
        (checkpoint_id, body.answer, correct, body.self_grade, now_str()),
    )
    room = conn.execute(
        """SELECT r.id, r.name FROM rooms r
           JOIN steps s ON s.room_id=r.id WHERE s.id=?""",
        (ck["step_id"],),
    ).fetchone()
    verdict = ("correct" if correct == 1 else
               "wrong" if correct == 0 else f"self-graded {body.self_grade}")
    ledger(conn, "attempt", f"checkpoint {verdict}", ref=f"room:{room['id']}")
    conn.commit()
    return {"correct": bool(correct) if correct is not None else None,
            "model_answer": ck["model_answer"]}


@router.post(cfg.API_PREFIX + "/room/{room_id}/note")
def add_note(room_id: int, body: NoteBody, conn=Depends(get_db)):
    cur = conn.execute(
        "INSERT INTO notes (room_id, step_id, body) VALUES (?,?,?)",
        (room_id, body.step_id, body.body),
    )
    ledger(conn, "note", "note captured", ref=f"room:{room_id}")
    conn.commit()
    return {"id": cur.lastrowid}


@router.delete(cfg.API_PREFIX + "/note/{note_id}")
def delete_note(note_id: int, conn=Depends(get_db)):
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    return {"ok": True}


@router.post(cfg.API_PREFIX + "/room/{room_id}/feynman")
def set_feynman(room_id: int, body: FeynmanBody, conn=Depends(get_db)):
    _room_row(conn, room_id)
    conn.execute("UPDATE rooms SET feynman=? WHERE id=?", (body.text, room_id))
    ledger(conn, "room", "feynman check written", ref=f"room:{room_id}")
    conn.commit()
    return {"ok": True}
