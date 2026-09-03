"""Market data endpoints. Free public feeds only (mfapi.in / AMFI NAVAll.txt /
yfinance) - no API keys. Mounted by app_factory with prefix /api/finance.

POST /market/refresh   latest price for every active holding -> price_history
POST /market/backfill  real per-symbol history (NAV series) -> price_history
"""
from fastapi import APIRouter, Body

from services import market_data

router = APIRouter()


@router.post("/market/refresh")
def refresh(payload: dict = Body(default={})):
    budget = int((payload or {}).get("budget_s") or 90)
    return market_data.refresh_holdings(budget_s=budget, with_history=False)


@router.post("/market/backfill")
def backfill(payload: dict = Body(default={})):
    budget = int((payload or {}).get("budget_s") or 120)
    return market_data.refresh_holdings(budget_s=budget, with_history=True)
