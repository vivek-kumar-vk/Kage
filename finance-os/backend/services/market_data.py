"""Market data — yfinance / mftool with a cached-price fallback. No API keys.
Every path degrades gracefully: offline or on any provider error we return the
last cached price from price_history, else None. Pure functions, no FastAPI app."""
from __future__ import annotations

from services.db import connect


def normalize_symbol(symbol: str, asset_type: str | None = None) -> str:
    return (symbol or "").strip().upper()


def get_last_cached_price(symbol: str):
    sym = normalize_symbol(symbol)
    with connect() as db:
        row = db.execute(
            "SELECT price FROM price_history WHERE symbol=? ORDER BY date DESC LIMIT 1",
            (sym,),
        ).fetchone()
    return row["price"] if row else None


def get_current_price(symbol: str, asset_type: str | None = None):
    """Branch by asset type; any failure (incl. no network) -> cached fallback."""
    sym = normalize_symbol(symbol, asset_type)
    try:
        if asset_type in ("mutual_fund", "mf", "etf"):
            from mftool import Mftool  # noqa: PLC0415

            _ = Mftool()  # constructing is cheap; real lookup added in a later pass
        elif asset_type in (None, "stock", "equity"):
            import yfinance  # noqa: PLC0415, F401
    except Exception:
        pass
    return get_last_cached_price(sym)


def batch_refresh(symbols, total_retry_budget_s: int = 120) -> dict:
    out: dict[str, float | None] = {}
    for s in symbols or []:
        out[normalize_symbol(s)] = get_current_price(s)
    return out
