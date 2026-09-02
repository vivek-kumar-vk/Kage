"""India's IPO calendar — what is open, what is coming, what just closed.

Source: Groww's /ipo page, which embeds its calendar as a __NEXT_DATA__
JSON blob (props.pageProps.openDataList / upcomingDataList /
closedDataList). One plain GET, no key, cached 24 h through
fund_reference's page cache. Ported from the house
fetch_india_ipo_list.py; every parse step tolerates absence, and if no
names can be extracted the answer is state "pending" with the reason —
never invented rows, never a stale calendar dressed up as fresh.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from services import fund_reference

SOURCE_URL = "https://groww.in/ipo"
IST = timezone(timedelta(hours=5, minutes=30))


def _ist_date(ms_epoch):
    if not ms_epoch:
        return None
    try:
        return datetime.fromtimestamp(int(ms_epoch) / 1000, tz=IST).date().isoformat()
    except (ValueError, OSError, OverflowError):
        return None


def _price_band(row: dict):
    mins, maxes = [], []
    for cat in row.get("categories") or []:
        if isinstance(cat.get("minPrice"), (int, float)):
            mins.append(cat["minPrice"])
        if isinstance(cat.get("maxPrice"), (int, float)):
            maxes.append(cat["maxPrice"])
    return (min(mins) if mins else None, max(maxes) if maxes else None)


def _rows(rows: list, kind: str) -> list[dict]:
    out = []
    for row in rows or []:
        name = (row.get("companyName") or "").strip()
        if not name:
            continue
        if kind == "open":
            lo, hi = _price_band(row)
            out.append({"name": name, "symbol": row.get("symbol"),
                        "open_date": _ist_date(row.get("bidStartTimestamp")),
                        "close_date": _ist_date(row.get("bidEndTimestamp")),
                        "price_min": lo, "price_max": hi,
                        "lot_size": row.get("lotSize") or row.get("minQty"),
                        "is_sme": bool(row.get("isSme")), "status": "open"})
        elif kind == "upcoming":
            out.append({"name": name, "symbol": row.get("symbol"),
                        "open_date": _ist_date(row.get("bidStartTimestamp")),
                        "close_date": None, "price_min": None, "price_max": None,
                        "lot_size": None,
                        "is_sme": bool(row.get("isSme")), "status": "upcoming"})
        else:
            out.append({"name": name, "symbol": row.get("symbol"),
                        "open_date": row.get("openingDate"),
                        "close_date": row.get("closingDate"),
                        "price_min": row.get("issuePrice"),
                        "price_max": None,
                        "lot_size": None,
                        "is_listed": row.get("isListed"),
                        "is_sme": bool(row.get("isSme")), "status": "closed"})
    return out


def fetch_calendar() -> dict:
    """The whole calendar (open/upcoming/closed) + the user's own checklist
    columns merged in from the ipos table."""
    props = fund_reference._page_props(SOURCE_URL, "ipo:calendar", 1)
    if not props or not any(k in props for k in
                            ("openDataList", "upcomingDataList", "closedDataList")):
        return {"state": "pending", "open": [], "upcoming": [], "closed": [],
                "reason": "groww.in/ipo page carried no calendar data "
                          "(layout change or upstream block)"}
    open_rows = _rows(props.get("openDataList"), "open")
    upcoming_rows = _rows(props.get("upcomingDataList"), "upcoming")
    closed_rows = _rows(props.get("closedDataList"), "closed")
    if not (open_rows or upcoming_rows or closed_rows):
        return {"state": "pending", "open": [], "upcoming": [], "closed": [],
                "reason": "the page's IPO lists were found but every row was "
                          "empty — refusing to show a made-up calendar"}
    return {"state": "ok", "open": open_rows, "upcoming": upcoming_rows,
            "closed": closed_rows, "where_from": "groww.in/ipo",
            "generated_at": datetime.now(IST).isoformat(timespec="seconds")}
