"""What one company actually is, by name: its Yahoo symbol, market cap,
P/E and P/B.

WHY THIS EXISTS
    A fund's published holdings say "HDFC Bank" and nothing else. The
    market-cap split and the weighted P/E the analysis tab promises need
    facts about each company, and mfapi.in / mfdata.in do not carry
    them. Yahoo Finance does - through the same yfinance package
    fetch_market_facts.py already uses. This file is Finance's door to
    company-level facts; fetch_market_facts stays index-and-quote only.

THE NAME-MATCHING HONESTY RULE
    Yahoo matches on symbols, not prose. The search step picks the first
    result traded on NSE or BSE (.NS / .BO); if none comes back the
    answer says so and that stock lands in "unknown" buckets upstream -
    it is never guessed into Large Cap to make a pie chart complete.
    Failed lookups are NOT cached, so a flaky night retries tomorrow;
    successful ones are cached 30 days because a company's sector,
    symbol and size barely move month to month.

Standard library plus yfinance. No key, no Secrets_Keys entry.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Shared_Market_Data\\fetch_stock_facts.py "HDFC Bank"
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
FACTS_CACHE_DAYS = 30


def _tidy(stock_name: str) -> str:
    """One cache key per company, however the fund house spelled it."""
    name = (stock_name or "").strip().lower()
    name = "".join(c for c in name if c.isalnum() or c == " ")
    return " ".join(name.split()).replace(" ", "_") or "unknown"


def _cache_path(key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{key}.json"


def _read_cache(key: str, max_age_days: float):
    path = _cache_path(key)
    if not path.exists():
        return None
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > max_age_days * 24:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _write_cache(key: str, payload) -> None:
    _cache_path(key).write_text(json.dumps(payload), encoding="utf-8")


def facts_for(stock_name: str) -> dict:
    """Symbol, market cap (crore), trailing P/E and P/B for one company.

    Every field may be missing independently - Yahoo often has a price
    but no book value. Missing fields come back as None and print as a
    dash on screen, never as a zero (C4).
    """
    key = f"stock_{_tidy(stock_name)}"
    cached = _read_cache(key, FACTS_CACHE_DAYS)
    if cached is not None:
        return {**cached, "cached": True}

    if not AVAILABLE:
        return {"has_data": False, "where_from": "yfinance",
                "note": "yfinance is not installed in this environment"}

    tidy_name = (stock_name or "").strip()
    try:
        quotes = (yfinance.Search(tidy_name, max_results=5).quotes or [])
        symbol = ""
        for quote in quotes:
            candidate = quote.get("symbol") or ""
            if candidate.endswith((".NS", ".BO")):
                symbol = candidate
                break
        if not symbol:
            answer = {"has_data": False, "stock": tidy_name, "symbol": None,
                      "market_cap_cr": None, "pe": None, "pb": None,
                      "where_from": "yfinance",
                      "note": f"no NSE/BSE listing found for '{tidy_name}'"}
            # Not cached: a failed match retries after the next publish,
            # a cached failure would sit there for 30 days.
            return answer

        info = yfinance.Ticker(symbol).info or {}
        market_cap_cr = round(info["marketCap"] / 1e7, 1) if info.get("marketCap") else None
        pe = round(float(info["trailingPE"]), 2) if info.get("trailingPE") else None
        pb = round(float(info["priceToBook"]), 2) if info.get("priceToBook") else None
        answer = {
            "has_data": any(v is not None for v in (market_cap_cr, pe, pb)),
            "stock": tidy_name, "symbol": symbol,
            "market_cap_cr": market_cap_cr, "pe": pe, "pb": pb,
            "where_from": "yfinance",
            "note": None if any(v is not None for v in (market_cap_cr, pe, pb))
                    else f"Yahoo listed {symbol} but published no cap, P/E or P/B for it",
        }
    except Exception as problem:                                      # noqa: BLE001
        return {"has_data": False, "stock": tidy_name, "symbol": None,
                "market_cap_cr": None, "pe": None, "pb": None,
                "where_from": "yfinance",
                "note": f"could not fetch '{tidy_name}': {problem}"}

    if answer["has_data"]:
        _write_cache(key, answer)
    return answer


PRICE_CACHE_HOURS = 12  # a day-close does not change after the fact; an
                        # intraday read is stale within minutes, so both
                        # get one honest half-day cache.


def _looks_like_a_symbol(token: str) -> bool:
    """'RELIANCE.NS' or 'TCS' reads as a ticker; 'HDFC Bank' as prose."""
    return " " not in token and len(token) <= 15


def resolve_symbol(symbol_or_name: str) -> tuple[str | None, str | None]:
    """One Yahoo symbol from either a ticker fragment or a company name.

    Returns (symbol, note). A bare ticker gets .NS tried first - NSE is
    where INKY's money lives - then falls back to search. A name goes
    through the same first-NSE-or-BSE-result search facts_for uses, so
    the two functions can never disagree about what symbol a name means.
    """
    token = (symbol_or_name or "").strip()
    if not token:
        return None, "no symbol or name was given"
    upper = token.upper()
    if upper.endswith((".NS", ".BO")):
        return upper, None
    if _looks_like_a_symbol(token) and token == upper:
        # An all-caps single word is almost certainly a ticker. .NS is
        # tried by the caller's fetch; resolution here just tags it.
        return f"{upper}.NS", None
    facts = facts_for(token)
    # The symbol counts as resolved even when the FACTS have_data is
    # false - an ETF publishes no market cap or P/E, yet its price
    # history is exactly what the caller asked for.
    if facts.get("symbol"):
        return facts["symbol"], None
    return None, facts.get("note") or f"no NSE/BSE listing found for '{token}'"


def price_history(symbol_or_name: str, days: int = 400) -> dict:
    """Daily closes for one stock or ETF, oldest last.

    WHY
        The fund side has nav_history(); this is the same promise for
        anything held directly on an exchange. The ledger writer and any
        chart need closes, not analysis - every field beyond close is
        deliberately not fetched, because a column nothing reads is a
        lie waiting to be trusted.

    HONESTY
        days counts CALENDAR days of history asked for; Yahoo answers in
        trading days, so fewer points can come back than were asked for,
        and that is reported as-is rather than padded. Failures are not
        cached, so tonight retries like every other fetcher here.

    Cached 12 hours under market_facts_cache alongside the company
    facts, keyed per symbol AND window so a short call never serves a
    long one a truncated series.
    """
    key = f"prices_{_tidy(symbol_or_name)}_{int(days)}"
    cached = _read_cache(key, PRICE_CACHE_HOURS / 24)
    if cached is not None:
        return {**cached, "cached": True}

    if not AVAILABLE:
        return {"has_data": False, "asked_for": symbol_or_name, "symbol": None,
                "points": [], "where_from": "yfinance",
                "note": "yfinance is not installed in this environment"}

    symbol, why_not = resolve_symbol(symbol_or_name)
    if symbol is None:
        return {"has_data": False, "asked_for": symbol_or_name, "symbol": None,
                "points": [], "where_from": "yfinance", "note": why_not}

    try:
        frame = yfinance.Ticker(symbol).history(
            period=f"{max(int(days), 1)}d", interval="1d")
    except Exception as problem:                                      # noqa: BLE001
        return {"has_data": False, "asked_for": symbol_or_name, "symbol": symbol,
                "points": [], "where_from": "yfinance",
                "note": f"could not fetch history for {symbol}: {problem}"}

    if frame is None or frame.empty:
        return {"has_data": False, "asked_for": symbol_or_name, "symbol": symbol,
                "points": [], "where_from": "yfinance",
                "note": f"Yahoo knows {symbol} but returned no daily rows "
                        f"for the last {days} days"}

    points = [{"date": stamp.strftime("%Y-%m-%d"),
               "close": round(float(row["Close"]), 4)}
              for stamp, row in frame.iterrows()]
    answer = {
        "has_data": bool(points),
        "asked_for": symbol_or_name, "symbol": symbol,
        "points": points,
        "currency": "INR",   # .NS/.BO quotes are rupees; see resolve_symbol
        "where_from": "yfinance",
        "note": f"{len(points)} trading days returned for a "
                f"{days}-calendar-day ask",
    }
    _write_cache(key, answer)
    return answer


def main() -> None:
    if len(sys.argv) < 2:
        print('usage: fetch_stock_facts.py "HDFC Bank"')
        return
    if "--history" in sys.argv:
        target = sys.argv[1]
        span = int(sys.argv[sys.argv.index("--history") + 1]) \
            if sys.argv.index("--history") + 1 < len(sys.argv) else 30
        result = price_history(target, days=span)
        print("PRICE HISTORY")
        print()
        if not result["has_data"]:
            print(f"  could not fetch it: {result['note']}")
            return
        print(f"  {result['symbol']}  ({result['currency']})  "
              f"- {len(result['points'])} closes")
        for point in result["points"][-5:]:
            print(f"    {point['date']}  {point['close']}")
        return

    facts = facts_for(sys.argv[1])
    print("STOCK FACT")
    print()
    if facts["has_data"]:
        print(f"  {facts['stock']}  ->  {facts['symbol']}")
        print(f"  market cap : {'-' if facts['market_cap_cr'] is None else facts['market_cap_cr']} crore")
        print(f"  P/E        : {facts['pe'] if facts['pe'] is not None else '-'}")
        print(f"  P/B        : {facts['pb'] if facts['pb'] is not None else '-'}")
    else:
        print(f"  could not fetch it: {facts.get('note')}")


if __name__ == "__main__":
    main()
