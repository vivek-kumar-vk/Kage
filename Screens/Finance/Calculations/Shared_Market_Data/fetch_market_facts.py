"""Market facts off Yahoo Finance, for the things mfapi.in cannot say.

WHAT THIS FILE IS FOR
    mfapi.in knows mutual fund NAVs. It does not know what sector HDFC
    Bank is in, or what the NIFTY 50 closed at. Yahoo Finance does, via
    the yfinance package - so this file is Finance's one door to it.

    Configured 2026-08-22 at the owner's request alongside the NAV
    ledger work. Like fetch_fund_facts.py: no key, free service, every
    answer carries where_from and has_data so a missing fact is printed
    as a dash with its reason, never as a zero (C4).

WHY EVERY ANSWER IS CACHED ON DISK
    yfinance is rate-limited and occasionally flaky. A small JSON cache
    under Saved_Records/market_facts_cache/ means a sector looked up
    once stays looked up, and a screen refresh never re-pays for it.
    Sectors of listed companies barely ever change; prices are cached
    only briefly.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Shared_Market_Data\\fetch_market_facts.py ^NSEI
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import yfinance
    AVAILABLE = True
except ImportError:
    yfinance = None
    AVAILABLE = False

CACHE_DIR = SCREEN / "Saved_Records" / "market_facts_cache"
PRICE_CACHE_HOURS = 1     # a price older than this is fetched again
SECTOR_CACHE_DAYS = 30    # a company's sector does not drift week to week
HISTORY_CACHE_HOURS = 12  # an index's past closes do not change; NAV moves daily


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "^.-_" else "_" for c in key)
    return CACHE_DIR / f"{safe}.json"


def _read_cache(key: str, max_age_hours: float):
    path = _cache_path(key)
    if not path.exists():
        return None
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > max_age_hours:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _write_cache(key: str, payload) -> None:
    _cache_path(key).write_text(json.dumps(payload), encoding="utf-8")


def index_quote(symbol: str) -> dict:
    """The last close of an index or stock (^NSEI, ^BSESN, RELIANCE.NS).

    Cached for an hour. Offline or throttled, the answer says so instead
    of pretending the market stands still.
    """
    cached = _read_cache(f"price_{symbol}", PRICE_CACHE_HOURS)
    if cached is not None:
        return {**cached, "cached": True}

    if not AVAILABLE:
        return {"has_data": False, "where_from": "yfinance",
                "note": "yfinance is not installed in this environment"}

    try:
        history = yfinance.Ticker(symbol).history(period="5d")
        if history.empty:
            return {"has_data": False, "where_from": "yfinance",
                    "note": f"Yahoo answered but has nothing for {symbol}"}
        last = history.iloc[-1]
        answer = {
            "has_data": True, "symbol": symbol,
            "close": round(float(last["Close"]), 2),
            "as_of": str(history.index[-1].date()),
            "where_from": "yfinance",
        }
    except Exception as problem:                                      # noqa: BLE001
        return {"has_data": False, "where_from": "yfinance",
                "note": f"could not fetch {symbol}: {problem}"}

    _write_cache(f"price_{symbol}", answer)
    return {**answer, "cached": False}


def sector_of(stock_name: str) -> dict:
    """The business sector of one company, by name.

    Yahoo matches on tickers, not prose, so the caller may hand over an
    already-known NSE symbol; when only a name is known we say so rather
    than guessing a symbol from it.
    """
    key = f"sector_{stock_name}"
    cached = _read_cache(key, SECTOR_CACHE_DAYS * 24)
    if cached is not None:
        return {**cached, "cached": True}

    if not AVAILABLE:
        return {"has_data": False, "where_from": "yfinance",
                "note": "yfinance is not installed in this environment"}

    # `stock_name` here is whatever the fund facts called the company -
    # usually a plain name ("HDFC Bank"), which Yahoo will not match.
    # The honest answer is "unknown" unless a real symbol resolves.
    return {"has_data": False, "where_from": "yfinance",
            "note": "sector lookup needs an exchange symbol, not a fund's "
                    "spelling of the name"}


def index_history(symbol: str, days: int = 400) -> dict:
    """Daily closes of an index, oldest last, for ratio arithmetic.

    compute_the_ratios.performance() pairs these against a fund's NAV
    history to get beta, alpha, Sharpe and Sortino. Cached twelve hours
    - an index does not rewrite history, so the second fund analysed
    today re-pays nothing.
    """
    cached = _read_cache(f"history_{symbol}_{days}", HISTORY_CACHE_HOURS)
    if cached is not None:
        return {**cached, "cached": True}

    if not AVAILABLE:
        return {"has_data": False, "where_from": "yfinance",
                "note": "yfinance is not installed in this environment"}

    try:
        history = yfinance.Ticker(symbol).history(period="2y")
        if history.empty:
            return {"has_data": False, "where_from": "yfinance",
                    "note": f"Yahoo answered but has no history for {symbol}"}
        points = [{"date": str(idx.date()), "close": round(float(row["Close"]), 2)}
                  for idx, row in history.iterrows()]
        answer = {"has_data": bool(points), "symbol": symbol,
                  "points": points[-days:], "where_from": "yfinance"}
    except Exception as problem:                                      # noqa: BLE001
        return {"has_data": False, "where_from": "yfinance",
                "note": f"could not fetch {symbol}: {problem}"}

    _write_cache(f"history_{symbol}_{days}", answer)
    return {**answer, "cached": False}


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: fetch_market_facts.py <symbol>   e.g. ^NSEI")
        return
    quote = index_quote(sys.argv[1])
    print("MARKET FACT")
    print()
    if quote["has_data"]:
        print(f"  {quote['symbol']}  close {quote['close']} as of {quote['as_of']}")
    else:
        print(f"  could not fetch it: {quote.get('note')}")


if __name__ == "__main__":
    main()
