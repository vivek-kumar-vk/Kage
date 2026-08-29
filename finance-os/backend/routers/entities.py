"""goals / debts / insurance / salary — thin CRUD over sqlite. Minimal for
Phase 1; per-feature validation lands with each feature's own phase.

Literal routes (`/goals`, `/debts`, ...) are registered explicitly so this
router never shadows another router mounted at the same /api/finance prefix."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.db import connect

router = APIRouter()
_TABLES = ("goals", "debts", "insurance", "salary")


def _dict(row):
    return {k: row[k] for k in row.keys()}


def _make(table: str):
    def _list():
        with connect() as db:
            return [_dict(r) for r in db.execute(
                f"SELECT * FROM {table} ORDER BY id").fetchall()]

    def _create(body: dict):
        body = {k: v for k, v in (body or {}).items()}
        if not body:
            raise HTTPException(status_code=422, detail="empty body")
        cols = ", ".join(body)
        marks = ", ".join("?" for _ in body)
        with connect() as db:
            try:
                cur = db.execute(
                    f"INSERT INTO {table}({cols}) VALUES ({marks})", tuple(body.values()))
                db.commit()
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
            row = db.execute(f"SELECT * FROM {table} WHERE id=?", (cur.lastrowid,)).fetchone()
        return _dict(row)

    return _list, _create


for _t in _TABLES:
    _l, _c = _make(_t)
    router.add_api_route(f"/{_t}", _l, methods=["GET"], name=f"list_{_t}")
    router.add_api_route(f"/{_t}", _c, methods=["POST"], status_code=201, name=f"create_{_t}")
