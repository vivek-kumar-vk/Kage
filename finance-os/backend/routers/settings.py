"""Settings / entity management — the CRUD not covered by the Phase 1 routers:
PUT + soft-archive for accounts/goals/insurance, GET-by-id, and the scenario
simulate endpoint. Mounted by app_factory with prefix /api/finance (this router
adds NO prefix of its own).

Archiving an account that still has active holdings CASCADE-archives those
holdings — never leaves a live holding under a hidden account.  [P]
data_health is never INSERTed here.  [singleton]
"""
from __future__ import annotations

import datetime as _dt

from fastapi import APIRouter, Body, Depends, HTTPException

from services.calculations import scenario as scenario_calc
from services.db import connect

router = APIRouter()


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _dict(row):
    return {k: row[k] for k in row.keys()}


def _get(conn, table: str, rid: int):
    return conn.execute(f"SELECT * FROM {table} WHERE id = ?", (rid,)).fetchone()


def _update(conn, table: str, rid: int, payload: dict, allowed: set[str]):
    if not _get(conn, table, rid):
        raise HTTPException(status_code=404, detail=f"{table[:-1]} not found")
    sets = {k: v for k, v in (payload or {}).items() if k in allowed}
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        conn.execute(f"UPDATE {table} SET {cols} WHERE id = ?", (*sets.values(), rid))
        conn.commit()
    return _dict(_get(conn, table, rid))


# --- accounts ---------------------------------------------------------------

@router.put("/accounts/{aid}")
def update_account(aid: int, payload: dict = Body(default={}), conn=Depends(_db)):
    return _update(conn, "accounts", aid, payload,
                   {"name", "type", "institution", "currency"})


@router.post("/accounts/{aid}/archive")
def archive_account(aid: int, conn=Depends(_db)):
    if not _get(conn, "accounts", aid):
        raise HTTPException(status_code=404, detail="account not found")
    live = conn.execute(
        "SELECT COUNT(*) FROM holdings WHERE account_id = ? AND archived_at IS NULL",
        (aid,),
    ).fetchone()[0]
    now = _dt.datetime.utcnow().isoformat(timespec="seconds")
    if live:
        conn.execute(
            "UPDATE holdings SET archived_at = ? WHERE account_id = ? AND archived_at IS NULL",
            (now, aid),
        )
    conn.execute("UPDATE accounts SET archived_at = ? WHERE id = ?", (now, aid))
    conn.commit()
    return {"state": "ok", "archived_account": aid, "cascaded_holdings": live}


# --- goals ----------------------------------------------------------------

@router.get("/goals/{gid}")
def get_goal(gid: int, conn=Depends(_db)):
    r = _get(conn, "goals", gid)
    if not r:
        raise HTTPException(status_code=404, detail="goal not found")
    d = _dict(r)
    # baseline for probability math: start_date, falling back to created_at  [E]
    d["start_date"] = d.get("start_date") or d.get("created_at")
    d["_current_amount_note"] = "current_amount is entered manually and may be stale"
    return d


@router.put("/goals/{gid}")
def update_goal(gid: int, payload: dict = Body(default={}), conn=Depends(_db)):
    return _update(conn, "goals", gid, payload,
                   {"name", "target_amount", "current_amount", "target_date",
                    "start_date", "priority", "status"})


@router.post("/goals/{gid}/archive")
def archive_goal(gid: int, conn=Depends(_db)):
    if not _get(conn, "goals", gid):
        raise HTTPException(status_code=404, detail="goal not found")
    conn.execute("UPDATE goals SET status = 'archived' WHERE id = ?", (gid,))
    conn.commit()
    return {"state": "ok", "archived_goal": gid}


# --- insurance ----------------------------------------------------------------

@router.get("/insurance/{iid}")
def get_insurance(iid: int, conn=Depends(_db)):
    r = _get(conn, "insurance", iid)
    if not r:
        raise HTTPException(status_code=404, detail="insurance not found")
    return _dict(r)


@router.put("/insurance/{iid}")
def update_insurance(iid: int, payload: dict = Body(default={}), conn=Depends(_db)):
    return _update(conn, "insurance", iid, payload,
                   {"type", "provider", "coverage_amount", "premium", "next_due"})


@router.post("/insurance/{iid}/archive")
def archive_insurance(iid: int, conn=Depends(_db)):
    if not _get(conn, "insurance", iid):
        raise HTTPException(status_code=404, detail="insurance not found")
    conn.execute(
        "UPDATE insurance SET archived_at = CURRENT_TIMESTAMP WHERE id = ?", (iid,)
    )
    conn.commit()
    return {"state": "ok", "archived_insurance": iid}


# --- salary (a raise is a NEW row, never an edit of history) -----------------

@router.post("/salary")
def add_salary(payload: dict = Body(default={}), conn=Depends(_db)):
    p = payload or {}
    cur = conn.execute(
        "INSERT INTO salary(monthly_gross, monthly_net, effective_date) VALUES (?,?,?)",
        (p.get("monthly_gross"), p.get("monthly_net"),
         p.get("effective_date") or _dt.date.today().isoformat()),
    )
    conn.commit()
    return _dict(_get(conn, "salary", cur.lastrowid))


# --- scenario simulator -----------------------------------------------------

@router.post("/scenario/simulate")
def scenario_simulate(payload: dict = Body(default={}), conn=Depends(_db)):
    p = payload or {}
    return scenario_calc.simulate(
        conn,
        extra_debt_payment=float(p.get("extra_debt_payment", 0) or 0),
        monthly_salary_delta=float(p.get("monthly_salary_delta", 0) or 0),
        one_off_bonus=float(p.get("one_off_bonus", 0) or 0),
        sip_step_up_pct=float(p.get("sip_step_up_pct", 0) or 0),
    )
