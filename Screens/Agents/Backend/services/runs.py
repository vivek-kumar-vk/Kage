"""Runs: one row per agent ask (V2). Append-only; closed by UPDATE, never deleted."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import settings_for_agents as cfg
from db import connect

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))
INTERRUPTED_AFTER_MINUTES = 10


def _now():
    return datetime.now(IST).replace(microsecond=0).isoformat()


def _duration_ms(started_at: str, ended_at: str) -> int:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        return max(0, round((end - start).total_seconds() * 1000))
    except (TypeError, ValueError):
        return 0


def open_run(conn, agent_name, department, room_id, prompt) -> int:
    started = _now()
    cursor = conn.execute(
        """
        INSERT INTO runs (agent_name, department, room_id, prompt, status, started_at)
        VALUES (?, ?, ?, ?, 'running', ?)
        """,
        (agent_name, department, room_id, prompt, started),
    )
    conn.commit()
    return cursor.lastrowid


def close_run(conn, run_id, *, status, reply=None, model=None, problem=None, usage=None):
    row = conn.execute("SELECT started_at FROM runs WHERE id = ?", (run_id,)).fetchone()
    started_at = row["started_at"] if row else None
    ended_at = _now()
    duration_ms = _duration_ms(started_at, ended_at) if started_at else None

    tokens_in = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    tokens_out = usage.get("completion_tokens") if isinstance(usage, dict) else None

    conn.execute(
        """
        UPDATE runs
        SET status = ?, reply = ?, model = ?, problem = ?,
            tokens_in = ?, tokens_out = ?, ended_at = ?, duration_ms = ?
        WHERE id = ?
        """,
        (status, reply, model, problem, tokens_in, tokens_out, ended_at, duration_ms, run_id),
    )
    conn.commit()


def mark_interrupted_runs():
    """A run left 'running' because the server died is not silently 'ok'."""
    conn = connect()
    try:
        cutoff = (datetime.now(IST) - timedelta(minutes=INTERRUPTED_AFTER_MINUTES)).isoformat()
        conn.execute(
            """
            UPDATE runs
            SET status = 'error', problem = 'interrupted — server restarted', ended_at = ?
            WHERE status = 'running' AND started_at < ?
            """,
            (_now(), cutoff),
        )
        conn.commit()
    finally:
        conn.close()


@router.get(cfg.API_PREFIX + "/runs")
async def list_runs(agent: str = None, limit: int = 50):
    limit = max(1, min(limit, 200))
    conn = connect()
    try:
        if agent:
            rows = conn.execute(
                "SELECT * FROM runs WHERE agent_name = ? ORDER BY id DESC LIMIT ?",
                (agent, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        runs = [dict(row) for row in rows]
        result = {"state": "ok", "runs": runs}
        if not runs:
            result["note"] = "no runs yet"
        return result
    finally:
        conn.close()


@router.get(cfg.API_PREFIX + "/runs/{run_id}")
async def get_run(run_id: int):
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return JSONResponse(
                status_code=404,
                content={"state": "error", "problem": "unknown run"},
            )
        return {"state": "ok", "run": dict(row)}
    finally:
        conn.close()
