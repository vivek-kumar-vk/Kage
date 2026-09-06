"""Spine read endpoints (K-05): GET-only views over the projected spine.

Every handler projects FIRST (pull-through, no cache, migrations included),
then reads its view; if projecting fails the handler returns 503 with a
problem sentence. Rule 22: a source absent from the view is absent from the
response.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import settings_for_storage as cfg  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from services import spine_projector as sp  # noqa: E402

router = APIRouter()

_IST = timezone(timedelta(hours=5, minutes=30))


def _today() -> str:
    return datetime.now(_IST).date().isoformat()


def _envelope(meta: dict, extra: dict) -> dict:
    return {
        "state": "ok",
        "projected_at": meta["projected_at"],
        "projector_lag_bytes": meta["lag_bytes"],
        **extra,
    }


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    conn = sp.connect()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _error(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"state": "error", "problem": f"spine read failed: {exc}"},
    )


@router.get(cfg.API_PREFIX + "/spine/freshness")
def freshness():
    try:
        meta = sp.project()
        sources = _rows("SELECT * FROM v_source_freshness")
        return _envelope(meta, {"sources": sources})
    except Exception as exc:
        return _error(exc)


@router.get(cfg.API_PREFIX + "/spine/spend")
def spend(day: str | None = Query(default=None)):
    try:
        meta = sp.project()
        day = day or _today()
        rows = _rows(
            "SELECT day, calls, tokens_in, tokens_out, cost_usd, calls_t2 "
            "FROM v_llm_spend_day WHERE day=?",
            (day,),
        )
        if rows:
            summary = rows[0]
        else:
            summary = {"day": day, "calls": 0, "tokens_in": None,
                       "tokens_out": None, "cost_usd": None, "calls_t2": 0}
        by_agent = _rows(
            "SELECT subject, cost_usd, calls FROM v_llm_spend_agent_day WHERE day=?",
            (day,),
        )
        return _envelope(meta, {**summary, "by_agent": by_agent})
    except Exception as exc:
        return _error(exc)


@router.get(cfg.API_PREFIX + "/spine/numbers")
def numbers():
    try:
        meta = sp.project()
        rows = _rows(
            "SELECT key, value, unit, data_as_of, ts FROM v_latest_numbers"
        )
        return _envelope(meta, {"numbers": rows})
    except Exception as exc:
        return _error(exc)


@router.get(cfg.API_PREFIX + "/spine/decisions")
def decisions(day: str | None = Query(default=None)):
    try:
        meta = sp.project()
        day = day or _today()
        rows = _rows(
            "SELECT * FROM v_decisions_today WHERE day=? ORDER BY rank", (day,)
        )
        return _envelope(meta, {"decisions": rows})
    except Exception as exc:
        return _error(exc)


@router.get(cfg.API_PREFIX + "/spine/watchdog")
def watchdog():
    try:
        meta = sp.project()
        checks = _rows('SELECT "check", verdict, detail, ts FROM v_watchdog_latest')
        return _envelope(meta, {"checks": checks})
    except Exception as exc:
        return _error(exc)


@router.get(cfg.API_PREFIX + "/spine/unfinished")
def unfinished():
    try:
        meta = sp.project()
        row = _rows("SELECT count FROM v_unfinished_count")
        return _envelope(meta, {"count": row[0]["count"], "budget": 12})
    except Exception as exc:
        return _error(exc)


@router.get(cfg.API_PREFIX + "/spine/events")
def events(
    type: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    since: str | None = Query(default=None),
    limit: int = Query(default=100),
):
    try:
        meta = sp.project()
        clauses: list[str] = []
        params: list = []
        if type:
            clauses.append("type = ?")
            params.append(type)
        if subject:
            clauses.append("subject = ?")
            params.append(subject)
        if since:
            clauses.append("ts >= ?")
            params.append(since)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        limit = min(max(limit, 1), 500)
        rows = _rows(
            f"SELECT * FROM events{where} ORDER BY seq DESC LIMIT ?",
            (*params, limit),
        )
        for row in rows:
            row["payload"] = json.loads(row["payload"])
        return _envelope(meta, {"events": rows})
    except Exception as exc:
        return _error(exc)
