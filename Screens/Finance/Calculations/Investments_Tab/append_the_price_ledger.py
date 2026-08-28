"""Tracks the closing price of every equity or ETF I hold directly.

WHAT THIS FILE OWNS
    Saved_Records/equity_price_ledger.csv - one row per held exchange-
    traded symbol per day. These columns are FROZEN in
    Shared_By_All_Screens/Column_Contracts/frozen_column_names.json
    (schema `equity_price_ledger`, contract v15): renaming or reordering
    one breaks every reader silently, so a new contract version is the
    only way to change them.

THE EVENT ENVELOPE (Phase-1 W1.2 - the first ledger to wear it)
    Every row written since v15 carries four envelope fields after the
    six original ones:

        event_id    a UUID - the row's permanent, merge-safe identity
        written_at  the IST instant INKY wrote it (distinct from `date`,
                    which is the day the PRICE belongs to)
        version     envelope convention version, currently 1
        supersedes  the event_id this row CORRECTS, empty for a first
                    observation

    APPEND-ONLY IS ABSOLUTE: a wrong close is never overwritten. The
    correction is a NEW row whose supersedes names the row it replaces,
    so both stay on file and "why did this number change" has an
    answer in the file itself. Rows from before the envelope (six
    columns, no event_id) are valid history and are all still current.
    Readers that want today's truth call current_rows(), which drops
    exactly the rows another row's supersedes points at.

WHY A LEDGER AND NOT JUST THE CACHE
    fetch_stock_facts.price_history() caches Yahoo answers for twelve
    hours - a performance decision that forgets. This file remembers:
    what a gold ETF or a share was worth on each day INKY looked, so a
    chart or a review can ask "what happened last month" without the
    network being up. It is the equity twin of track_the_nav_ledger.py,
    and deliberately sits beside it with the same shape.

WHAT IT TRACKS
    Every read_portfolio_holdings row whose category is NOT mutual_fund -
    today that is the Gold BeES ETF; tomorrow, any shares. Mutual funds
    are excluded because fund_nav_ledger already owns them; tracking a
    fund twice would let two ledgers disagree about one truth.

THE HONESTY RULES
    A holding whose symbol cannot be resolved is named in `unresolved`
    and gets NO row - a guessed ticker would put some other company's
    price under this holding's name. A price that cannot be fetched is
    named in `failed` and keeps yesterday's rows untouched. Re-running
    with UNCHANGED data writes nothing - idempotence means no invented
    activity, not silent replacement.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\append_the_price_ledger.py
"""

from __future__ import annotations

import csv
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
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

import fetch_stock_facts                        # noqa: E402
import read_portfolio_holdings                  # noqa: E402

SAVED_RECORDS = SCREEN / "Saved_Records"
LEDGER = SAVED_RECORDS / "equity_price_ledger.csv"

# Frozen column contract: equity_price_ledger (v15 - six data columns
# first, then the event envelope, per the trace ledger's own convention).
COLUMNS = ["date", "symbol", "name", "close", "currency", "source",
           "event_id", "written_at", "version", "supersedes"]

# India has no daylight saving; fixed offset, same clock as everywhere.
IST = timezone(timedelta(hours=5, minutes=30), "IST")
ENVELOPE_VERSION = 1


def ledger_path() -> Path:
    return LEDGER


def read_the_ledger() -> list[dict]:
    """Every recorded close, oldest first - INCLUDING superseded rows,
    because history is the point of append-only. Empty when never run."""
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f)
                if (row.get("symbol") or "").strip()]


def current_rows() -> list[dict]:
    """The rows that stand today: everything except rows another row's
    supersedes points at. Pre-envelope rows have no event_id, cannot be
    displaced, and all count as current."""
    rows = read_the_ledger()
    displaced = {r["supersedes"] for r in rows if r.get("supersedes")}
    return [r for r in rows if r.get("event_id") not in displaced]


def _now_iso() -> str:
    return datetime.now(IST).isoformat(timespec="seconds")


def _same_observation(row: dict, close: str, currency: str,
                      source: str) -> bool:
    """True when the standing row already records exactly this close."""
    try:
        prices_agree = float(row.get("close")) == float(close)
    except (TypeError, ValueError):
        prices_agree = (row.get("close") or "") == close
    return (prices_agree
            and (row.get("currency") or "") == currency
            and (row.get("source") or "") == source)


def _read_existing() -> list[dict]:
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f)]


def _append(rows_to_add: list[dict]) -> None:
    """Append rows; migrate a pre-envelope header once, additively.

    The migration rewrites only the HEADER line's column names - every
    old cell keeps its value and the four envelope cells read empty.
    After it, the file is append-only for good.
    """
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    needs_header = not LEDGER.exists()
    stale_header = False
    if not needs_header:
        with LEDGER.open(encoding="utf-8-sig") as f:
            first = f.readline().strip().split(",")
        stale_header = first != COLUMNS
    if stale_header:
        legacy = _read_existing()
        with LEDGER.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS, restval="")
            writer.writeheader()
            writer.writerows(legacy)
    with LEDGER.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        if needs_header:
            writer.writeheader()
        writer.writerows(rows_to_add)


def update_the_ledger(today: date | None = None) -> dict:
    """Append today's close per non-mutual-fund holding.

    Safe to re-run in the strictest sense: unchanged data writes
    NOTHING (no invented activity), changed data appends a superseding
    row and keeps the old one on file.
    """
    try:
        holdings = read_portfolio_holdings.read_every_holding()
    except Exception as problem:                                  # noqa: BLE001
        return {"funds_tracked": 0, "written": 0, "failed": [],
                "unresolved": [], "note": f"holdings snapshot unreadable: {problem}"}

    try:
        existing = _read_existing()
    except (UnicodeDecodeError, OSError) as problem:
        # An undecodable ledger is never clobbered by an append - the
        # honest answer is a named refusal a person can act on.
        return {"funds_tracked": 0, "written": 0, "failed": [],
                "unresolved": [],
                "note": (f"ledger unreadable ({problem.__class__.__name__})"
                         " - nothing appended, file left untouched")}

    tracked = [h for h in holdings if h.get("category") != "mutual_fund"]
    existing = _read_existing()

    written, failed, unresolved = [], [], []
    additions: list[dict] = []
    seen_today: set[tuple[str, str]] = set()

    for holding in tracked:
        name = holding["scheme_name"]
        # resolve_symbol, not facts_for.has_data: an ETF publishes no
        # market cap or P/E, so its FACTS answer says has_data false
        # while its symbol is perfectly known for pricing.
        symbol, why_not = fetch_stock_facts.resolve_symbol(name)
        if not symbol:
            unresolved.append({"scheme_name": name,
                               "note": why_not or "no NSE/BSE listing found"})
            continue
        history = fetch_stock_facts.price_history(symbol, days=7)
        points = history.get("points") or []
        newest = points[-1] if points else None
        # The most recent trading day may be earlier than today (a
        # Sunday run writes Friday's close), so `date` comes from the
        # close itself, never from the clock - the row records the day
        # the PRICE belongs to, and the ledger stays honest about it.
        if newest is None:
            failed.append({"scheme_name": name, "symbol": symbol,
                           "note": history.get("note", "no closes returned")})
            continue
        row_date = newest["date"]
        key = (row_date, symbol)
        if key in seen_today:
            continue
        seen_today.add(key)

        # What stands for this date+symbol: the last row of its chain
        # that nothing on file supersedes. Only NON-empty supersedes
        # values displace - an empty string must never kick out rows
        # that simply have no event_id yet.
        same_key = [r for r in existing
                    if r.get("date") == row_date and r.get("symbol") == symbol]
        displaced = {r.get("supersedes") for r in same_key
                     if r.get("supersedes")}
        standing = [r for r in same_key
                    if r.get("event_id") not in displaced]
        current = standing[-1] if standing else None

        currency = history.get("currency") or "INR"
        source = history.get("where_from") or "yfinance"
        if current is not None and _same_observation(
                current, str(newest["close"]), currency, source):
            continue               # already on file, unchanged; write nothing

        new_row = {
            "date": row_date, "symbol": symbol, "name": name,
            "close": newest["close"], "currency": currency, "source": source,
            "event_id": uuid.uuid4().hex,
            "written_at": _now_iso(),
            "version": ENVELOPE_VERSION,
            "supersedes": (current.get("event_id") or "") if current else "",
        }
        existing.append(new_row)   # visible to later holdings of THIS run too
        additions.append(new_row)
        written.append({"symbol": symbol, "date": row_date})

    try:
        _append(additions)
    except (UnicodeDecodeError, OSError) as problem:
        return {"funds_tracked": len(tracked), "written": 0,
                "failed": [], "unresolved": [],
                "note": (f"ledger append refused ({problem.__class__.__name__})"
                         " - nothing was written")}

    return {"funds_tracked": len(tracked), "written": len(written),
            "failed": failed, "unresolved": unresolved, "note": None}


def main() -> None:
    result = update_the_ledger()
    print("EQUITY PRICE LEDGER")
    print("=" * 50)
    print(f"  holdings tracked : {result['funds_tracked']}")
    print(f"  rows written     : {result['written']}")
    for miss in result["unresolved"]:
        print(f"  UNRESOLVED       : {miss['scheme_name']} ({miss['note']})")
    for failure in result["failed"]:
        print(f"  FAILED           : {failure['scheme_name']} "
              f"({failure['note']})")
    if result["note"]:
        print(f"  note             : {result['note']}")
    print()
    for row in read_the_ledger():
        print(f"  {row['date']}  {row['symbol']:<14}{row['name'][:34]:<36}"
              f"{row['close']} {row['currency']} ({row['source']})")


if __name__ == "__main__":
    main()