"""Analysis-tab endpoints. Mounted by app_factory with prefix /api/finance:
  GET  /investments/analyse/{hid}            one holding's deep-dive sheet
  GET  /investments/analyse/stock/{symbol}   a stock's sheet
  GET  /analysis/overview                    hero numbers + XIRR
  GET  /analysis/lookthrough                 the X-ray (companies, HHI, sectors)
  GET  /analysis/overlap                     pair-overlap matrix
  GET  /analysis/behaviour                   risk ratios vs NIFTY 50
  GET  /analysis/allocation                  asset split vs targets + drift
  GET  /analysis/cost-tax                    blended TER + CG buckets
  GET  /analysis/actions                     the observation list
  GET  /investments/sip-calendar             buy rhythm from lots
  POST /analysis/refresh                     prime the reference cache (bg)
  GET  /analysis/refresh/status              the refresh job's result

Every section is honest about coverage: state ok / partial / pending with
a reason — numbers with no source behind them are never shown. [P]
"""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends

from services.calculations import analysis
from services.db import connect

router = APIRouter()

_REFRESH_KEY = "analysis_refresh"


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/investments/analyse/{hid}")
def analyse_holding(hid: int, conn=Depends(_db)):
    row = conn.execute("SELECT symbol, type FROM holdings WHERE id = ?", (hid,)).fetchone()
    if not row:
        return {"state": "pending", "reason": "no such active holding"}
    if (row["type"] or "").lower() == "stock":
        return analysis.stock_sheet(conn, row["symbol"])
    return analysis.fund_sheet(conn, hid)


@router.get("/investments/analyse/stock/{symbol}")
def analyse_stock(symbol: str, conn=Depends(_db)):
    return analysis.stock_sheet(conn, symbol)


@router.get("/analysis/overview")
def a_overview(conn=Depends(_db)):
    return analysis.review(conn, "overview")


@router.get("/analysis/lookthrough")
def a_lookthrough(conn=Depends(_db)):
    return analysis.review(conn, "lookthrough")


@router.get("/analysis/overlap")
def a_overlap(conn=Depends(_db)):
    return analysis.review(conn, "overlap")


@router.get("/analysis/behaviour")
def a_behaviour(conn=Depends(_db)):
    return analysis.review(conn, "behaviour")


@router.get("/analysis/allocation")
def a_allocation(conn=Depends(_db)):
    return analysis.review(conn, "allocation")


@router.get("/analysis/cost-tax")
def a_cost_tax(conn=Depends(_db)):
    return analysis.review(conn, "cost-tax")


@router.get("/analysis/actions")
def a_actions(conn=Depends(_db)):
    return analysis.review(conn, "actions")


@router.get("/investments/sip-calendar")
def sip_calendar(conn=Depends(_db)):
    return analysis.sip_calendar(conn)


def _refresh_job():
    try:
        result = analysis.refresh_reference_data()
    except Exception as e:  # noqa: BLE001
        result = {"state": "error", "note": str(e)}
    with connect() as db:
        db.execute(
            "INSERT INTO app_settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = CURRENT_TIMESTAMP",
            (_REFRESH_KEY, json.dumps(result)))
        db.commit()


@router.post("/analysis/refresh")
def start_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(_refresh_job)
    return {"state": "started",
            "note": "the reference pages are being fetched in the "
                    "background — poll /analysis/refresh/status"}


@router.get("/analysis/refresh/status")
def refresh_status():
    with connect() as db:
        row = db.execute("SELECT value, updated_at FROM app_settings "
                         "WHERE key = ?", (_REFRESH_KEY,)).fetchone()
    if not row:
        return {"state": "idle"}
    try:
        out = json.loads(row["value"])
    except ValueError:
        return {"state": "idle"}
    out["at"] = row["updated_at"]
    return out
