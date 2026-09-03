"""Overview dashboard endpoints. Read-only aggregates over the finance DB.
Mounted by app_factory with prefix /api/finance -> /api/finance/overview/*.
"""
from fastapi import APIRouter, Depends

from services.db import connect
from services.calculations import core

router = APIRouter()


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/overview/net-worth")
def get_net_worth(conn=Depends(_db)):
    return core.net_worth(conn)


@router.get("/overview/cashflow")
def get_cashflow(conn=Depends(_db)):
    return core.cashflow(conn)


@router.get("/overview/portfolio-pulse")
def get_portfolio_pulse(conn=Depends(_db)):
    return core.portfolio_pulse(conn)


@router.get("/overview/emergency-fund")
def get_emergency_fund(conn=Depends(_db)):
    return core.emergency_fund(conn)


@router.get("/overview/debt-status")
def get_debt_status(conn=Depends(_db)):
    return core.debt_status(conn)


@router.get("/overview/surplus-allocation")
def get_surplus_allocation(conn=Depends(_db)):
    return core.surplus_allocation(conn)


@router.get("/overview/goals")
def get_goals(conn=Depends(_db)):
    return core.goals_overview(conn)


@router.get("/overview/top-actions")
def get_top_actions(conn=Depends(_db)):
    return core.top_actions(conn)


@router.get("/overview/data-health")
def get_data_health(conn=Depends(_db)):
    return core.data_health(conn)
