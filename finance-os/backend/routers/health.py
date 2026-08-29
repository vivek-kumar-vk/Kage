"""Data-health admin. `/overview/data-health` itself is served by routers/overview.py
(the read path). This router adds the recompute trigger. `data_health` is a
singleton — recompute is UPDATE ... WHERE id=1.  [singleton]
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from services.calculations.data_health import get_data_health, recompute_health
from services.db import connect

router = APIRouter()


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@router.post("/data-health/recompute")
def recompute(conn=Depends(_db)):
    return recompute_health(conn)


@router.get("/data-health/detail")
def detail(conn=Depends(_db)):
    return get_data_health(conn)
