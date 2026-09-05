"""Small shared helpers for the OFFICE services. Screen-local only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def get_db():
    from db import connect
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def today_str(offset_days: int = 0) -> str:
    return (datetime.now(IST) + timedelta(days=offset_days)).date().isoformat()


def now_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
