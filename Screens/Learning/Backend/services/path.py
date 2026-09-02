"""PATH — fully dynamic tracks / modules / rooms. Add, rename, move, archive,
delete; positions are explicit ints per parent so the UI can reorder freely.
Nothing user-built is silently destroyed: archive is a state, delete is a
cascade that writes a ledger line first."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import settings_for_learning as cfg
from services.common import (
    get_db, ledger, room_mastery, level_for, short_name,
)

router = APIRouter()


class TrackBody(BaseModel):
    name: str
    color: str | None = None
    position: int | None = None
    archived: bool | None = None


class ModuleBody(BaseModel):
    name: str | None = None
    position: int | None = None
    archived: bool | None = None


class RoomBody(BaseModel):
    name: str | None = None
    position: int | None = None
    module_id: int | None = None
    status: str | None = None
    archived: bool | None = None
    est_minutes: int | None = None


def _serialize_track(conn, t):
    modules = conn.execute(
        "SELECT * FROM modules WHERE track_id=? AND archived=0 ORDER BY position, id",
        (t["id"],),
    ).fetchall()
    out_rooms_total, out_rooms_progress = 0, 0
    mods_out = []
    for m in modules:
        rooms = conn.execute(
            "SELECT * FROM rooms WHERE module_id=? AND archived=0 ORDER BY position, id",
            (m["id"],),
        ).fetchall()
        rooms_out = []
        for r in rooms:
            pct = room_mastery(conn, r["id"])
            steps = conn.execute(
                """SELECT COUNT(*) total, COALESCE(SUM(status='done'),0) done
                   FROM steps WHERE room_id=?""",
                (r["id"],),
            ).fetchone()
            rooms_out.append({
                "id": r["id"], "name": r["name"], "short": short_name(r["name"]),
                "status": r["status"], "position": r["position"],
                "est_minutes": r["est_minutes"], "mastery": pct,
                "level": level_for(pct),
                "steps_done": steps["done"], "steps_total": steps["total"],
            })
            out_rooms_total += 1
            out_rooms_progress += pct / 100
        mods_out.append({
            "id": m["id"], "name": m["name"], "position": m["position"],
            "rooms": rooms_out,
        })
    pct = round(100 * out_rooms_progress / out_rooms_total) if out_rooms_total else 0
    return {
        "id": t["id"], "name": t["name"], "color": t["color"],
        "position": t["position"], "archived": bool(t["archived"]),
        "modules": mods_out,
        "room_count": out_rooms_total, "mastery": pct, "level": level_for(pct),
    }


@router.get(cfg.API_PREFIX + "/path")
def get_path(conn=Depends(get_db)):
    tracks = conn.execute(
        "SELECT * FROM tracks WHERE archived=0 ORDER BY position, id"
    ).fetchall()
    return {"tracks": [_serialize_track(conn, t) for t in tracks]}


# ------------------------------------------------------------------ tracks
@router.post(cfg.API_PREFIX + "/tracks")
def add_track(body: TrackBody, conn=Depends(get_db)):
    pos = body.position
    if pos is None:
        pos = (conn.execute("SELECT COALESCE(MAX(position),-1)+1 p FROM tracks"
                            ).fetchone()["p"])
    cur = conn.execute(
        "INSERT INTO tracks (name, color, position) VALUES (?,?,?)",
        (body.name, body.color or "violet", pos),
    )
    ledger(conn, "path", f"track added — {body.name}")
    conn.commit()
    return {"id": cur.lastrowid}


@router.put(cfg.API_PREFIX + "/tracks/{track_id}")
def update_track(track_id: int, body: TrackBody, conn=Depends(get_db)):
    row = conn.execute("SELECT * FROM tracks WHERE id=?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such track")
    name = body.name if body.name is not None else row["name"]
    color = body.color if body.color is not None else row["color"]
    position = body.position if body.position is not None else row["position"]
    archived = int(body.archived) if body.archived is not None else row["archived"]
    conn.execute(
        "UPDATE tracks SET name=?, color=?, position=?, archived=? WHERE id=?",
        (name, color, position, archived, track_id),
    )
    ledger(conn, "path", f"track updated — {name}")
    conn.commit()
    return {"ok": True}


@router.delete(cfg.API_PREFIX + "/tracks/{track_id}")
def delete_track(track_id: int, conn=Depends(get_db)):
    row = conn.execute("SELECT name FROM tracks WHERE id=?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such track")
    ledger(conn, "path", f"track deleted — {row['name']}")
    conn.execute("DELETE FROM tracks WHERE id=?", (track_id,))
    conn.commit()
    return {"ok": True}


# ------------------------------------------------------------------ modules
@router.post(cfg.API_PREFIX + "/tracks/{track_id}/modules")
def add_module(track_id: int, body: ModuleBody, conn=Depends(get_db)):
    if not body.name:
        raise HTTPException(422, "module needs a name")
    pos = body.position
    if pos is None:
        pos = conn.execute(
            "SELECT COALESCE(MAX(position),-1)+1 p FROM modules WHERE track_id=?",
            (track_id,),
        ).fetchone()["p"]
    cur = conn.execute(
        "INSERT INTO modules (track_id, name, position) VALUES (?,?,?)",
        (track_id, body.name, pos),
    )
    ledger(conn, "path", f"module added — {body.name}")
    conn.commit()
    return {"id": cur.lastrowid}


@router.put(cfg.API_PREFIX + "/modules/{module_id}")
def update_module(module_id: int, body: ModuleBody, conn=Depends(get_db)):
    row = conn.execute("SELECT * FROM modules WHERE id=?", (module_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such module")
    name = body.name if body.name is not None else row["name"]
    position = body.position if body.position is not None else row["position"]
    archived = int(body.archived) if body.archived is not None else row["archived"]
    conn.execute(
        "UPDATE modules SET name=?, position=?, archived=? WHERE id=?",
        (name, position, archived, module_id),
    )
    conn.commit()
    return {"ok": True}


@router.delete(cfg.API_PREFIX + "/modules/{module_id}")
def delete_module(module_id: int, conn=Depends(get_db)):
    row = conn.execute("SELECT name FROM modules WHERE id=?", (module_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such module")
    ledger(conn, "path", f"module deleted — {row['name']}")
    conn.execute("DELETE FROM modules WHERE id=?", (module_id,))
    conn.commit()
    return {"ok": True}


# ------------------------------------------------------------------ rooms
@router.post(cfg.API_PREFIX + "/modules/{module_id}/rooms")
def add_room(module_id: int, body: RoomBody, conn=Depends(get_db)):
    if not body.name:
        raise HTTPException(422, "room needs a name")
    pos = body.position
    if pos is None:
        pos = conn.execute(
            "SELECT COALESCE(MAX(position),-1)+1 p FROM rooms WHERE module_id=?",
            (module_id,),
        ).fetchone()["p"]
    cur = conn.execute(
        """INSERT INTO rooms (module_id, name, position, est_minutes)
           VALUES (?,?,?,?)""",
        (module_id, body.name, pos, body.est_minutes or 20),
    )
    ledger(conn, "path", f"room added — {body.name}")
    conn.commit()
    return {"id": cur.lastrowid}


@router.put(cfg.API_PREFIX + "/rooms/{room_id}")
def update_room(room_id: int, body: RoomBody, conn=Depends(get_db)):
    row = conn.execute("SELECT * FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such room")
    name = body.name if body.name is not None else row["name"]
    position = body.position if body.position is not None else row["position"]
    module_id = body.module_id if body.module_id is not None else row["module_id"]
    status = body.status if body.status is not None else row["status"]
    archived = int(body.archived) if body.archived is not None else row["archived"]
    est = body.est_minutes if body.est_minutes is not None else row["est_minutes"]
    conn.execute(
        """UPDATE rooms SET name=?, position=?, module_id=?, status=?,
           archived=?, est_minutes=? WHERE id=?""",
        (name, position, module_id, status, archived, est, room_id),
    )
    if body.archived:
        ledger(conn, "path", f"room archived — {name}")
    elif body.module_id is not None and body.module_id != row["module_id"]:
        ledger(conn, "path", f"room moved between modules — {name}")
    conn.commit()
    return {"ok": True}


@router.delete(cfg.API_PREFIX + "/rooms/{room_id}")
def delete_room(room_id: int, conn=Depends(get_db)):
    row = conn.execute("SELECT name FROM rooms WHERE id=?", (room_id,)).fetchone()
    if not row:
        raise HTTPException(404, "no such room")
    ledger(conn, "path", f"room deleted — {row['name']} (cascade)")
    conn.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    conn.commit()
    return {"ok": True}
