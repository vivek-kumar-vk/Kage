"""India's IPO calendar - what is open, what is coming, what just closed.

WHY THIS EXISTS
    The watchlist holds funds and a couple of ETFs today, but new
    listings are where an ordinary investor meets the market first, and
    every Indian broker's IPO page is free to read. Groww's /ipo page
    ships its data inside the page itself (the __NEXT_DATA__ JSON blob
    Next.js embeds), so one plain HTTP GET - no key, no login - yields
    the whole calendar. This file is the screen's door to it.

HOW THE PARSING WORKS, AND HOW IT CAN FAIL HONESTLY
    Groww is a Next.js app; the page carries a <script id="__NEXT_DATA__">
    blob whose pageProps holds openDataList / upcomingDataList /
    closedDataList. Layouts change without notice. Every parse step
    here tolerates absence, and if no names can be extracted the answer
    is has_data False with the reason - never invented rows, never a
    stale calendar dressed up as fresh (that is the exact failure an
    IPO tracker must not commit).

    One machine quirk handled honestly rather than hidden: groww.in's
    certificate chain fails against Python's default CA store on this
    laptop, so certifi's bundle is used when installed. If neither CA
    store works, that is reported as the failure it is - TLS is never
    switched off to make a fetch succeed.

THE HONESTY RULES
    Rows carry exactly what Groww published - name, symbol, dates,
    price band - and None wherever a field was absent. verified_by_a_person
    stays false because nobody has cross-checked even one row against
    the company's Red Herring Prospectus. A listing date in this file
    is information, not advice to apply (C5).

CACHE RULE
    An IPO calendar changes a few times a day at most. Within 24 hours
    of the last successful fetch the saved file IS the answer.

Standard library plus certifi (already pulled in by yfinance's stack).
No key, no Secrets_Keys entry.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Shared_Market_Data\\fetch_india_ipo_list.py [--force]
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
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

SOURCE_URL = "https://groww.in/ipo"
CALENDAR_FILE = SCREEN / "Saved_Records" / "ipo_calendar.json"
REFRESH_HOURS = 24
HOW_LONG_WE_WAIT = 30
IST = timezone(timedelta(hours=5, minutes=30))   # Indian listings live in IST


def _ssl_context():
    """A verifying context that prefers certifi's newer CA bundle."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _fetch_page() -> tuple[bool, str]:
    """The raw HTML. Returns (worked, html_or_reason)."""
    request = urllib.request.Request(SOURCE_URL, method="GET")
    request.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 INKY/1.0",
    )
    request.add_header("Accept", "text/html,application/xhtml+xml")
    try:
        with urllib.request.urlopen(request, timeout=HOW_LONG_WE_WAIT,
                                    context=_ssl_context()) as response:
            return True, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as problem:
        return False, f"groww.in answered HTTP {problem.code}"
    except Exception as problem:                                      # noqa: BLE001
        return False, f"could not reach groww.in: {problem}"


def _next_data_props(html: str) -> dict | None:
    """pageProps out of the __NEXT_DATA__ blob, or None."""
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
        html, re.S)
    if not match:
        return None
    try:
        blob = json.loads(match.group(1))
    except ValueError:
        return None
    props = ((blob.get("props") or {}).get("pageProps")) or {}
    lists_found = [k for k in ("openDataList", "upcomingDataList",
                               "closedDataList") if k in props]
    return props if lists_found else None


def _ist_date(ms_epoch):
    """A millisecond epoch into an ISO date in IST. None stays None."""
    if not ms_epoch:
        return None
    try:
        moment = datetime.fromtimestamp(int(ms_epoch) / 1000, tz=IST)
        return moment.date().isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def _price_band(row: dict):
    """(min_price, max_price) out of an open IPO's category rows.

    Groww publishes the band per investor category; they agree, so the
    lowest min and highest max across categories is the band. Anything
    missing comes back as None - never guessed to zero (C4).
    """
    mins, maxes = [], []
    for cat in row.get("categories") or []:
        if isinstance(cat.get("minPrice"), (int, float)):
            mins.append(cat["minPrice"])
        if isinstance(cat.get("maxPrice"), (int, float)):
            maxes.append(cat["maxPrice"])
    return (min(mins) if mins else None, max(maxes) if maxes else None)


def _name_and_symbol(row: dict) -> tuple[str, str | None]:
    return ((row.get("companyName") or "").strip(),
            (row.get("symbol") or "").strip() or None)


def fetch_ipo_calendar(force: bool = False) -> dict:
    """The whole calendar, grouped open/upcoming/closed. Cached daily."""
    if not force and CALENDAR_FILE.exists():
        age_hours = (time.time() - CALENDAR_FILE.stat().st_mtime) / 3600
        if age_hours <= REFRESH_HOURS:
            try:
                saved = json.loads(CALENDAR_FILE.read_text(encoding="utf-8"))
                if saved.get("has_data"):
                    return {**saved, "cached": True}
            except ValueError:
                pass                       # corrupt cache falls through to refetch

    worked, payload = _fetch_page()
    if not worked:
        return {"has_data": False, "where_from": "groww.in/ipo",
                "fetched_on": date.today().isoformat(), "note": payload}

    props = _next_data_props(payload)
    if props is None:
        return {"has_data": False, "where_from": "groww.in/ipo",
                "fetched_on": date.today().isoformat(),
                "note": "page fetched but its layout changed: no "
                        "__NEXT_DATA__ IPO lists found in the HTML"}

    open_rows, upcoming_rows, closed_rows = [], [], []
    for row in props.get("openDataList") or []:
        name, symbol = _name_and_symbol(row)
        if not name:
            continue
        band_low, band_high = _price_band(row)
        open_rows.append({
            "name": name, "symbol": symbol,
            "open_date": _ist_date(row.get("bidStartTimestamp")),
            "close_date": _ist_date(row.get("bidEndTimestamp")),
            "price_band_min": band_low, "price_band_max": band_high,
            "is_sme": bool(row.get("isSme")),
        })
    for row in props.get("upcomingDataList") or []:
        name, symbol = _name_and_symbol(row)
        if not name:
            continue
        upcoming_rows.append({
            "name": name, "symbol": symbol,
            "expected_open_date": _ist_date(row.get("bidStartTimestamp")),
            "price_band_min": None, "price_band_max": None,
            "is_sme": bool(row.get("isSme")),
        })
    for row in props.get("closedDataList") or []:
        name, symbol = _name_and_symbol(row)
        if not name:
            continue
        closed_rows.append({
            "name": name, "symbol": symbol,
            "open_date": row.get("openingDate") or None,
            "close_date": row.get("closingDate") or None,
            "issue_price": row.get("issuePrice"),
            "listing_price": row.get("listingPrice"),
            "is_listed": row.get("isListed"),
            "is_sme": bool(row.get("isSme")),
        })

    if not (open_rows or upcoming_rows or closed_rows):
        return {"has_data": False, "where_from": "groww.in/ipo",
                "fetched_on": date.today().isoformat(),
                "note": "the page's IPO lists were found but every row was "
                        "empty - refusing to show a made-up calendar"}

    answer = {
        "_meta": {
            "verified_by_a_person": False,
            "comment": "Rows copied from Groww's /ipo page data exactly as "
                       "published. No person has checked any row against a "
                       "Red Herring Prospectus - [UNVERIFIED] until one has.",
        },
        "open": open_rows,
        "upcoming": upcoming_rows,
        "closed": closed_rows,
    }
    CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    CALENDAR_FILE.write_text(json.dumps(answer, indent=2), encoding="utf-8")
    return {**answer, "has_data": True, "where_from": "groww.in/ipo",
            "fetched_on": date.today().isoformat(), "cached": False,
            "note": None}


def main() -> None:
    force = "--force" in sys.argv
    result = fetch_ipo_calendar(force=force)
    print("INDIA IPO CALENDAR")
    print("=" * 50)
    if not result["has_data"]:
        print(f"  FAILED: {result['note']}")
        return
    flag = "" if result["_meta"]["verified_by_a_person"] else "  [UNVERIFIED]"
    print(f"  fetched {result['fetched_on']} from {result['where_from']}"
          f"{' (cache)' if result.get('cached') else ''}{flag}")
    for group, label in (("open", "OPEN NOW"), ("upcoming", "UPCOMING"),
                         ("closed", "RECENTLY CLOSED")):
        rows = result.get(group) or []
        print(f"\n  {label}: {len(rows)}")
        for row in rows[:5]:
            dates = (row.get("close_date") or row.get("expected_open_date")
                     or row.get("open_date") or "-")
            band = ""
            if row.get("price_band_min") and row.get("price_band_max"):
                band = f"  Rs {row['price_band_min']}-{row['price_band_max']}"
            elif row.get("issue_price"):
                band = f"  issued at Rs {row['issue_price']}"
            print(f"    {row['name'][:38]:<40}{dates}{band}")


if __name__ == "__main__":
    main()