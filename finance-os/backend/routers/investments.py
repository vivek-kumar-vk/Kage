"""Investments tab endpoints. Mounted by app_factory with prefix /api/finance
-> /api/finance/investments/*. Read paths aggregate over active_holdings /
price_history; writes are edit + archive (soft). Hard DELETE is allowed only for
a holding with zero lots, else 409 -> use archive.  [P]
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from services.calculations import portfolio
from services.db import connect

router = APIRouter()


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _holding_row(conn, hid: int):
    return conn.execute("SELECT * FROM holdings WHERE id = ?", (hid,)).fetchone()


@router.get("/investments/holdings")
def list_holdings(conn=Depends(_db)):
    return portfolio.holdings_with_value(conn)


@router.get("/investments/summary")
def summary(conn=Depends(_db)):
    return portfolio.portfolio_summary(conn)


@router.get("/investments/holdings/{hid}")
def get_holding(hid: int, conn=Depends(_db)):
    row = _holding_row(conn, hid)
    if not row:
        raise HTTPException(status_code=404, detail="holding not found")
    d = {k: row[k] for k in row.keys()}
    d["lots_count"] = conn.execute(
        "SELECT COUNT(*) FROM lots WHERE holding_id = ?", (hid,)
    ).fetchone()[0]
    return d


@router.put("/investments/holdings/{hid}")
def update_holding(hid: int, payload: dict = Body(default={}), conn=Depends(_db)):
    if not _holding_row(conn, hid):
        raise HTTPException(status_code=404, detail="holding not found")
    allowed = {"name", "type", "benchmark", "direct_regular", "units", "avg_cost"}
    sets = {k: v for k, v in (payload or {}).items() if k in allowed}
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        conn.execute(f"UPDATE holdings SET {cols} WHERE id = ?", (*sets.values(), hid))
        conn.commit()
    return get_holding(hid, conn)


@router.post("/investments/holdings/{hid}/archive")
def archive_holding(hid: int, conn=Depends(_db)):
    if not _holding_row(conn, hid):
        raise HTTPException(status_code=404, detail="holding not found")
    conn.execute(
        "UPDATE holdings SET archived_at = CURRENT_TIMESTAMP WHERE id = ?", (hid,)
    )
    conn.commit()
    return {"state": "ok", "archived": hid}


@router.delete("/investments/holdings/{hid}")
def delete_holding(hid: int, conn=Depends(_db)):
    if not _holding_row(conn, hid):
        raise HTTPException(status_code=404, detail="holding not found")
    lots = conn.execute(
        "SELECT COUNT(*) FROM lots WHERE holding_id = ?", (hid,)
    ).fetchone()[0]
    if lots:
        raise HTTPException(
            status_code=409,
            detail="holding has lots — archive it instead of hard-deleting",
        )
    conn.execute("DELETE FROM holdings WHERE id = ?", (hid,))
    conn.commit()
    return {"state": "ok", "deleted": hid}


@router.get("/investments/quality")
def quality(conn=Depends(_db)):
    rows = portfolio.holdings_with_value(conn)
    conc = portfolio.concentration(conn)
    flags = []
    for r in rows:
        if (r.get("direct_regular") or "regular") == "regular":
            flags.append({"symbol": r["symbol"], "flag": "regular_plan",
                          "detail": "regular plan — a direct plan has a lower TER"})
        if r["weight"] and r["weight"] > 0.25:
            flags.append({"symbol": r["symbol"], "flag": "concentration",
                          "detail": f"{round(r['weight'] * 100)}% of the portfolio"})
    return {"state": "ok" if rows else "pending",
            "top5_weight": conc["top5_weight"], "flags": flags}


_VISUALS = {
    "asset-allocation": lambda c: portfolio.asset_allocation(c),
    "concentration": lambda c: portfolio.concentration(c),
    "portfolio-vs-benchmark": lambda c: portfolio.portfolio_vs_benchmark(c),
    "rolling-returns": lambda c: portfolio.rolling_returns(c),
    "drawdown": lambda c: portfolio.drawdown(c),
}


@router.get("/investments/visuals/rolling-returns")
def v_rolling_returns(window: int = 30, conn=Depends(_db)):
    return portfolio.rolling_returns(conn, window_days=window)


@router.get("/investments/visuals/drawdown")
def v_drawdown(conn=Depends(_db)):
    return portfolio.drawdown(conn)


@router.get("/investments/visuals/portfolio-vs-benchmark")
def v_pvb(conn=Depends(_db)):
    return portfolio.portfolio_vs_benchmark(conn)


@router.get("/investments/visuals/asset-allocation")
def v_alloc(conn=Depends(_db)):
    return portfolio.asset_allocation(conn)


@router.get("/investments/visuals/concentration")
def v_conc(conn=Depends(_db)):
    return portfolio.concentration(conn)


@router.get("/investments/visuals/{name}")
def v_other(name: str, conn=Depends(_db)):
    """geography, target-vs-actual, treemap, fund-overlap, expense-ratio,
    sip-calendar — no data source yet, so an explicit pending state."""
    fn = _VISUALS.get(name)
    if fn:
        return fn(conn)
    return {"state": "pending", "series": [], "reason": f"{name} not yet populated"}


@router.get("/investments/research/{holding_id}")
def research(holding_id: int, conn=Depends(_db)):
    rows = conn.execute(
        "SELECT * FROM research_notes WHERE holding_id = ? ORDER BY created_at DESC",
        (holding_id,),
    ).fetchall()
    return {"holding_id": holding_id,
            "notes": [{k: r[k] for k in r.keys()} for r in rows]}
