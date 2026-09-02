"""Fills the price ledger with REAL dated history only.

HISTORY NOTE: an earlier version drew a synthetic straight-line series
off the latest quote when a source had no history. That is exactly the
manufactured-data failure D13.3/FD6 exist to prevent — the fabricated
rows silently flattened every day change, return and drawdown computed
from the ledger. When no source answers, NOTHING is written and the
caller gets 0 rows; the UI's honest "no history" state is the result.
"""
from __future__ import annotations

from services.db import connect
from services.market_data import history_for, normalize_symbol


def _has_history(db, sym: str) -> bool:
    return db.execute(
        "SELECT 1 FROM price_history WHERE symbol = ? LIMIT 1", (sym,)
    ).fetchone() is not None


def backfill_price_history(symbol: str, asset_type: str | None = None,
                           days: int = 90) -> int:
    """Insert real daily rows for `symbol` if it has none yet.
    Returns the number of rows written (0 when the source has no history)."""
    sym = normalize_symbol(symbol, asset_type)
    with connect() as db:
        if _has_history(db, sym):
            return 0
    res = history_for(sym, asset_type, days=days)
    if not res.get("has_data"):
        return 0
    written = 0
    with connect() as db:
        for p in res.get("points") or []:
            day = (p.get("date") or "")[:10]
            price = p.get("price")
            try:
                price = float(price) if price is not None else None
            except (TypeError, ValueError):
                price = None
            if not day or price is None or price <= 0:
                continue
            try:
                cur = db.execute(
                    "INSERT OR IGNORE INTO price_history(symbol,date,price,source,currency) "
                    "VALUES (?,?,?,?,?)",
                    (sym, day, price, res.get("where_from", "unknown"),
                     p.get("currency", "INR")),
                )
                written += cur.rowcount or 0
            except Exception:  # noqa: BLE001
                pass
        db.commit()
    return written
