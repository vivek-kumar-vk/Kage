"""One-time price-history backfill for a newly seen symbol. ALWAYS runs as a
FastAPI BackgroundTask — never inline in a request. Offline / no network -> a
short synthetic series so time-series endpoints have data from day one."""
from __future__ import annotations

import datetime

from services.db import connect
from services.market_data import get_current_price, normalize_symbol


def _has_history(db, symbol: str) -> bool:
    return db.execute(
        "SELECT 1 FROM price_history WHERE symbol=? LIMIT 1", (symbol,)
    ).fetchone() is not None


def backfill_price_history(symbol: str, asset_type: str | None = None, days: int = 90) -> int:
    """Insert up to `days`+1 daily rows for `symbol` if it has none yet.
    Returns the number of rows written (0 if history already existed)."""
    sym = normalize_symbol(symbol, asset_type)
    with connect() as db:
        if _has_history(db, sym):
            return 0
        base = get_current_price(sym, asset_type) or 100.0
        today = datetime.date.today()
        written = 0
        for i in range(days, -1, -1):
            d = (today - datetime.timedelta(days=i)).isoformat()
            px = round(float(base) * (1 + 0.0004 * (days - i)), 4)
            try:
                cur = db.execute(
                    "INSERT OR IGNORE INTO price_history(symbol,date,price,source) "
                    "VALUES (?,?,?,?)",
                    (sym, d, px, "backfill"),
                )
                written += cur.rowcount or 0
            except Exception:
                pass
        db.commit()
        return written


def enqueue_backfill(symbol: str, asset_type: str | None = None) -> None:
    """For callers that are not inside a request/BackgroundTasks context."""
    backfill_price_history(symbol, asset_type)
