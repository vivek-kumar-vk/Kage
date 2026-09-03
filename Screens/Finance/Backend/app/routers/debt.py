"""Debt & Liabilities tab. Mounted by app_factory with prefix /api/finance
-> /api/finance/debt/*. Amortization math lives in services/calculations/debt.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from services.calculations import debt as calc
from services.db import connect

router = APIRouter(prefix="/debt")


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _row(conn, did: int):
    return conn.execute("SELECT * FROM debts WHERE id = ?", (did,)).fetchone()


@router.get("/overview")
def overview(conn=Depends(_db)):
    return {
        "total_outstanding": calc.total_outstanding(conn),
        "highest_interest": calc.highest_interest(conn),
        "next_emi": calc.next_emi(conn),
        "count": len(calc.list_debts(conn)),
    }


@router.get("/table")
def table(conn=Depends(_db)):
    return calc.list_debts(conn)


@router.get("/table/{did}")
def table_item(did: int, conn=Depends(_db)):
    r = _row(conn, did)
    if not r:
        raise HTTPException(status_code=404, detail="debt not found")
    return {k: r[k] for k in r.keys()}


@router.put("/table/{did}")
def update_item(did: int, payload: dict = Body(default={}), conn=Depends(_db)):
    if not _row(conn, did):
        raise HTTPException(status_code=404, detail="debt not found")
    allowed = {"lender", "type", "outstanding", "interest_rate", "emi",
               "next_due", "remaining_months", "status"}
    sets = {k: v for k, v in (payload or {}).items() if k in allowed}
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        conn.execute(f"UPDATE debts SET {cols} WHERE id = ?", (*sets.values(), did))
        conn.commit()
    return table_item(did, conn)


@router.post("/table/{did}/archive")
def archive_item(did: int, conn=Depends(_db)):
    r = _row(conn, did)
    if not r:
        raise HTTPException(status_code=404, detail="debt not found")
    if float(r["outstanding"] or 0.0) <= 0:
        conn.execute("UPDATE debts SET status='closed' WHERE id = ?", (did,))
    else:
        conn.execute(
            "UPDATE debts SET archived_at = CURRENT_TIMESTAMP WHERE id = ?", (did,)
        )
    conn.commit()
    return {"state": "ok", "archived": did}


@router.delete("/table/{did}")
def delete_item(did: int, conn=Depends(_db)):
    if not _row(conn, did):
        raise HTTPException(status_code=404, detail="debt not found")
    hist = conn.execute(
        "SELECT COUNT(*) FROM transactions t JOIN accounts a ON a.id = t.account_id "
        "WHERE t.type = 'emi' AND a.name = (SELECT lender FROM debts WHERE id = ?)",
        (did,),
    ).fetchone()[0]
    if hist:
        raise HTTPException(status_code=409,
                            detail="payment history exists — archive instead")
    conn.execute("DELETE FROM debts WHERE id = ?", (did,))
    conn.commit()
    return {"state": "ok", "deleted": did}


@router.get("/payoff-plan")
def payoff_plan(method: str = "avalanche", conn=Depends(_db)):
    return calc.payoff_plan(conn, method=method)


@router.post("/simulate")
def simulate(payload: dict = Body(default={}), conn=Depends(_db)):
    p = payload or {}
    return calc.simulate(
        conn,
        extra_payment=float(p.get("extra_payment", 0) or 0),
        salary_increase=float(p.get("salary_increase", 0) or 0),
        bonus=float(p.get("bonus", 0) or 0),
    )


@router.get("/learning/{topic}")
def learning(topic: str):
    return calc.learning(topic)
