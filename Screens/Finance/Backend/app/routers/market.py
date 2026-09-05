"""Market data endpoints. Free public feeds only (mfapi.in / AMFI NAVAll.txt /
yfinance) - no API keys. Mounted by app_factory with prefix /api/finance.

POST /market/refresh   latest price for every active holding -> price_history
POST /market/backfill  real per-symbol history (NAV series) -> price_history
GET  /market/benchmark the ridge's overlay series, read from the local
                       ledger only (D28.4); empty ledger = 404, which the UI
                       renders as NO BENCHMARK LOADED — never a fabricated line.
POST /market/benchmark/backfill  pull ^NSEI closes via yfinance into the ledger.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Body, HTTPException, Query

from services import market_data
from services.db import connect

router = APIRouter()

_BENCHMARK_NAMES = {"^NSEI": "Nifty 50"}


@router.post("/market/refresh")
def refresh(payload: dict = Body(default={})):
    budget = int((payload or {}).get("budget_s") or 90)
    return market_data.refresh_holdings(budget_s=budget, with_history=False)


@router.post("/market/backfill")
def backfill(payload: dict = Body(default={})):
    budget = int((payload or {}).get("budget_s") or 120)
    return market_data.refresh_holdings(budget_s=budget, with_history=True)


def _iso_or_none(raw):
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except ValueError:
        raise HTTPException(status_code=422, detail=f"bad date: {raw}")


@router.get("/market/benchmark")
def benchmark(symbol: str = "^NSEI",
              from_: str | None = Query(None, alias="from"),
              to: str | None = Query(None)):
    sym = (symbol or "^NSEI").strip().upper()
    frm, to_d = _iso_or_none(from_), _iso_or_none(to)
    with connect() as conn:
        rows = conn.execute(
            "SELECT date, price FROM price_history WHERE symbol = ? "
            "ORDER BY date ASC", (sym,)
        ).fetchall()
        bench = conn.execute(
            "SELECT name FROM benchmarks WHERE symbol = ?", (sym,)
        ).fetchone()
    if not rows:
        # D28.4: a 404 here is what makes the card say NO BENCHMARK LOADED.
        raise HTTPException(status_code=404, detail={
            "state": "empty", "symbol": sym,
            "note": f"no {sym} closes in price_history — "
                    "POST /market/benchmark/backfill",
        })
    name = bench["name"] if bench else _BENCHMARK_NAMES.get(sym, sym)
    base_price = None
    points = []
    for r in rows:
        d = date.fromisoformat(str(r["date"])[:10])
        if frm and d < frm:
            continue
        if to_d and d > to_d:
            continue
        if base_price is None:
            base_price = r["price"] or None
        points.append({
            "date": d.isoformat(),
            "indexed": round((r["price"] / base_price) * 100, 4)
            if base_price else None,
        })
    return {
        "symbol": sym, "name": name, "state": "ok", "note": None,
        "base_date": points[0]["date"] if points else None,
        "points": points,
    }


@router.post("/market/benchmark/backfill")
def benchmark_backfill(payload: dict = Body(default={})):
    sym = (payload or {}).get("symbol") or "^NSEI"
    return market_data.backfill_benchmark(symbol=sym)
