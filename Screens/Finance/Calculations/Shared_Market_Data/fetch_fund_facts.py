"""Fetches Indian mutual fund facts from free, no-key public APIs.

No key, no signup, no provider entry in Secrets_Keys. That matters:
this is market data, not model access, and mixing the two would put a
keyless service into a file whose whole purpose is guarding keys.

Sources, in the order this file tries them:

    mfapi.in    NAV and NAV history by AMFI scheme code. No auth.
    mfdata.in   scheme details and portfolio holdings by AMFI code. No auth.

Both are volunteer-run and both go down sometimes. Every function here
returns a dict carrying where_from and has_data, so the screen can
print a dash and name the source rather than a number nobody can trace.

Standard library only.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Shared_Market_Data\\fetch_fund_facts.py <amfi_code>
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
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

HOW_LONG_WE_WAIT = 20
CACHE_HOURS = 12  # NAV moves once a day; holdings move once a month.
# mfdata.in is a volunteer service behind Cloudflare and answers HTTP
# 522 (origin down) or just times out for stretches (ADR-075). One try
# per call turned one bad minute into a whole failed fund; three tries
# with a short pause ride out the common blips without hanging forever.
FETCH_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 4


def _cache_dir() -> Path:
    where = SCREEN / "Saved_Records" / "fund_facts_cache"
    where.mkdir(parents=True, exist_ok=True)
    return where


def _read_cache(key: str):
    where = _cache_dir() / f"{key}.json"
    if not where.exists():
        return None
    age_hours = (time.time() - where.stat().st_mtime) / 3600
    if age_hours > CACHE_HOURS:
        return None
    try:
        return json.loads(where.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _write_cache(key: str, payload) -> None:
    (_cache_dir() / f"{key}.json").write_text(json.dumps(payload), encoding="utf-8")


def _get(address: str):
    """One GET with retries. Returns (worked, payload_or_reason)."""
    request = urllib.request.Request(address, method="GET")
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "INKY/1.0 (personal finance screen)")
    reason = "no attempt was made"
    for attempt in range(FETCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=HOW_LONG_WE_WAIT) as response:
                return True, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as problem:
            reason = f"the service answered HTTP {problem.code}"
        except urllib.error.URLError as problem:
            reason = f"could not reach the service: {problem.reason}"
        except ValueError:
            return False, "the service sent something that was not JSON"
        except Exception as problem:                                 # noqa: BLE001
            return False, f"unexpected trouble: {problem}"
        # A 5xx or a timeout may be gone next ask; anything else above
        # already returned. Pause grows each round so a dying service is
        # not hammered.
        if attempt < FETCH_ATTEMPTS - 1:
            time.sleep(RETRY_PAUSE_SECONDS * (attempt + 1))
    return False, reason


def _amfi_cache_path(stamp: str) -> Path:
    where = _cache_dir()
    return where / f"amfi_navall_{stamp}.txt"


def _amfi_navall_text(today: date | None = None) -> tuple[bool, str]:
    """The whole AMFI NAVAll.txt file, cached for one day.

    AMFI is the regulator's own publication - the primary source
    mfapi.in itself mirrors. Fetching it costs one ~3 MB GET; caching
    the WHOLE file daily means one fetch serves every scheme lookup
    that day, instead of one per fund.
    """
    today = today or date.today()
    stamp = today.strftime("%Y%m%d")
    path = _amfi_cache_path(stamp)
    if path.exists():
        try:
            return True, path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    request = urllib.request.Request("https://www.amfiindia.com/spages/NAVAll.txt",
                                     method="GET")
    request.add_header("User-Agent", "INKY/1.0 (personal finance screen)")
    try:
        with urllib.request.urlopen(request, timeout=HOW_LONG_WE_WAIT) as response:
            text = response.read().decode("utf-8", errors="replace")
    except Exception as problem:                                      # noqa: BLE001
        return False, f"could not reach amfiindia.com: {problem}"
    if "Scheme Code" not in text[:2000] and ";" not in text[:2000]:
        return False, "amfiindia.com answered with something that is not NAVAll.txt"
    # Yesterday's copy goes in the bin - only today's may answer.
    for old in _cache_dir().glob("amfi_navall_*.txt"):
        if old.name != path.name:
            try:
                old.unlink()
            except OSError:
                pass
    path.write_text(text, encoding="utf-8")
    return True, text


def _amfi_latest_nav(amfi_code: str, today: date | None = None) -> dict:
    """One scheme's newest NAV straight from AMFI's own file.

    The verified live layout (2026-08-24) is semicolon-separated with
    EIGHT fields:
        Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;
        Scheme Name;Plan;Option;Net Asset Value;Date
    so NAV and date are read from the END of the row - that stays
    correct even if AMFI adds or drops a middle column. Matched
    strictly on exact scheme code: a prefix match would hand back some
    other scheme's NAV with total confidence, which is the worst kind
    of wrong.
    """
    worked, text = _amfi_navall_text(today)
    if not worked:
        return {"has_data": False, "where_from": "amfiindia.com", "note": text}
    code = (amfi_code or "").strip()
    best = None
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6 or parts[0] != code:
            continue                                   # header, blank, no match
        raw_nav, raw_date = parts[-2], parts[-1]
        if not raw_nav or not raw_date:
            continue
        try:
            nav_value = float(raw_nav)
        except ValueError:
            continue
        published = None
        for shape in ("%d-%b-%Y", "%d-%m-%Y", "%d-%B-%Y"):
            try:
                published = datetime.strptime(raw_date, shape).date()
                break
            except ValueError:
                continue
        row = {"scheme_name": parts[3], "nav": nav_value,
               "nav_date": published.isoformat() if published else raw_date}
        # The file can repeat a code across plan rows; the later line
        # wins, matching how the ledger treats same-day writes.
        best = row
    if best is None:
        return {"has_data": False, "where_from": "amfiindia.com",
                "note": f"scheme code {code} is not in today's NAVAll.txt"}
    return {"has_data": True, "amfi_code": amfi_code,
            "scheme_name": best["scheme_name"], "fund_house": "",
            "nav": best["nav"], "nav_date": best["nav_date"],
            "where_from": "amfiindia.com NAVAll.txt"}


def latest_nav(amfi_code: str) -> dict:
    """Today's NAV for one scheme, with its date and where it came from.

    mfapi.in first; when IT fails, AMFI's own NAVAll.txt answers. The
    fallback exists because both mfapi.in and mfdata.in are volunteer
    services (ADR-075), while amfiindia.com is the regulator's primary
    publication they both mirror - so a down morning at mfapi.in no
    longer costs a day of the NAV ledger.
    """
    cached = _read_cache(f"nav_{amfi_code}")
    if cached:
        return cached

    worked, payload = _get(f"https://api.mfapi.in/mf/{amfi_code}/latest")
    if not worked:
        fallback = _amfi_latest_nav(amfi_code)
        if fallback.get("has_data"):
            _write_cache(f"nav_{amfi_code}", fallback)
            return fallback
        return {"has_data": False, "amfi_code": amfi_code,
                "where_from": "mfapi.in + amfiindia.com",
                "note": f"{payload}; AMFI fallback also failed: "
                        f"{fallback.get('note')}"}

    entries = payload.get("data") or []
    if not entries:
        return {"has_data": False, "amfi_code": amfi_code, "where_from": "mfapi.in",
                "note": "the service knows this code but published no NAV"}

    answer = {
        "has_data": True, "amfi_code": amfi_code,
        "scheme_name": (payload.get("meta") or {}).get("scheme_name", ""),
        "fund_house": (payload.get("meta") or {}).get("fund_house", ""),
        "nav": float(entries[0]["nav"]), "nav_date": entries[0]["date"],
        "where_from": "mfapi.in",
    }
    _write_cache(f"nav_{amfi_code}", answer)
    return answer


def nav_history(amfi_code: str, how_many_days: int | None = 400) -> dict:
    """NAV history, newest first. For drawing, not advising.

    The full series the source publishes is what gets cached; the trim
    to `how_many_days` happens after, on the way out, so one fetch can
    serve both a short ratio window and an uncapped chart series.
    `how_many_days=None` keeps every point since inception (mfapi.in
    carries scheme history from its first NAV - confirmed 2026-08-24).
    """
    cached = _read_cache(f"history_{amfi_code}")
    if not cached:
        worked, payload = _get(f"https://api.mfapi.in/mf/{amfi_code}")
        if not worked:
            return {"has_data": False, "amfi_code": amfi_code, "where_from": "mfapi.in", "note": payload}

        entries = (payload.get("data") or [])
        cached = {
            "has_data": bool(entries), "amfi_code": amfi_code,
            "scheme_name": (payload.get("meta") or {}).get("scheme_name", ""),
            "points": [{"date": row["date"], "nav": float(row["nav"])} for row in entries],
            "where_from": "mfapi.in",
        }
        _write_cache(f"history_{amfi_code}", cached)

    points = cached.get("points") or []
    if how_many_days is not None:
        points = points[:how_many_days]
    return {**cached, "points": points}


def holdings(amfi_code: str) -> dict:
    """What a fund actually owns - the input find_the_overlap.py needs.

    Holdings are published monthly and lag by weeks. as_of is always
    returned so nobody mistakes last month's portfolio for this
    morning's.
    """
    cached = _read_cache(f"holdings_{amfi_code}")
    if cached:
        return cached

    worked, payload = _get(f"https://mfdata.in/api/v1/schemes/{amfi_code}")
    if not worked:
        return {"has_data": False, "amfi_code": amfi_code, "where_from": "mfdata.in", "note": payload}

    data = payload.get("data") or {}
    family = data.get("family_id") or data.get("family")
    if not family:
        return {"has_data": False, "amfi_code": amfi_code, "where_from": "mfdata.in",
                "note": "the service has this scheme but no portfolio for it"}

    worked, held = _get(f"https://mfdata.in/api/v1/families/{family}/holdings")
    if not worked:
        return {"has_data": False, "amfi_code": amfi_code, "where_from": "mfdata.in", "note": held}

    body = held.get("data") or {}
    equity = body.get("equity_holdings") or []

    answer = {
        "has_data": bool(equity), "amfi_code": amfi_code,
        "scheme_name": data.get("name", ""), "expense_ratio": data.get("expense_ratio"),
        "as_of": body.get("month") or body.get("as_of") or "unknown",
        "holdings": [{"stock_name": row.get("stock_name"),
                     "weight_pct": float(row.get("weight_pct") or 0)} for row in equity],
        "where_from": "mfdata.in",
    }
    _write_cache(f"holdings_{amfi_code}", answer)
    return answer


def find_a_scheme(name_fragment: str) -> dict:
    """Search by name to get the AMFI code. Not cached; used rarely."""
    worked, payload = _get(f"https://api.mfapi.in/mf/search?q={urllib.parse.quote(name_fragment)}")
    if not worked:
        return {"has_data": False, "where_from": "mfapi.in", "note": payload}
    return {
        "has_data": bool(payload), "where_from": "mfapi.in",
        "matches": [{"amfi_code": row.get("schemeCode"), "name": row.get("schemeName")}
                   for row in (payload or [])[:25]],
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: fetch_fund_facts.py <amfi_code>")
        return
    code = sys.argv[1]
    nav = latest_nav(code)
    print("LATEST NAV")
    print()
    if nav["has_data"]:
        print(f"  {nav['scheme_name']}")
        print(f"  Rs {nav['nav']} as of {nav['nav_date']} (from {nav['where_from']})")
    else:
        print(f"  could not fetch it: {nav.get('note')}")


if __name__ == "__main__":
    main()
