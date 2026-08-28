"""The NSE equity universe - every company in the Nifty 500, Midcap 150,
Smallcap 250 and Next 50 indices, with its industry, symbol and ISIN.

WHY THIS EXISTS
    Fund facts name companies ("HDFC Bank"), but nothing so far knows
    what business a company is in unless a person typed it into
    Reference_Data/sector_for_stocks.json by hand. NSE publishes the
    constituent lists of its indices as plain CSVs - no login, no key -
    and each row carries an Industry column. Downloading those four
    files turns a hand-typed map of ~90 names into an automatic one of
    ~900, which is the difference between a sector pie that is mostly
    "not yet classified" and one that means something.

THE SOURCES (all verified reachable without auth)
    https://archives.nseindia.com/content/indices/ind_nifty500list.csv
    https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv
    https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv
    https://archives.nseindia.com/content/indices/ind_niftynext50list.csv

THE HONESTY RULES
    The industry labels come straight out of NSE's own CSVs and are
    never edited here - a label is copied through or left out. The file
    carries verified_by_a_person: false because nobody has cross-checked
    even one row against an annual report yet, so everything built on
    this file prints [UNVERIFIED] upstream, exactly like the tax
    rulebook. Offline or blocked, the answer says so: has_data False
    with the reason, never a half-built universe passed off as whole.

CACHE RULE
    Constituents change a few times a year. One refetch per week is
    plenty; within 7 days of the last fetch the existing
    Reference_Data/nse_equity_universe.json IS the answer and no
    network call happens.

Standard library only. No key, no Secrets_Keys entry.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Shared_Market_Data\\fetch_nse_universe.py [--force]
"""

from __future__ import annotations

import csv
import io
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date
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

# Each list verified live 2026-08-24: plain CSV, no login, no key.
SOURCES = {
    "nifty_500": "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    "nifty_midcap_150": "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
    "nifty_smallcap_250": "https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv",
    "nifty_next_50": "https://archives.nseindia.com/content/indices/ind_niftynext50list.csv",
}

UNIVERSE_FILE = SCREEN / "Reference_Data" / "nse_equity_universe.json"
SECTOR_FILE = SCREEN / "Reference_Data" / "sector_for_stocks.json"

REFRESH_DAYS = 7          # constituents move a few times a year, not daily
HOW_LONG_WE_WAIT = 30     # archives.nseindia.com can be slow


def _tidy(name: str) -> str:
    """One canonical key per company name, however it was capitalised."""
    name = (name or "").strip().lower()
    name = "".join(c for c in name if c.isalnum() or c == " ")
    return " ".join(name.split()) or "unknown"


def _fetch_one(url: str):
    """GET one index list. Returns (worked, text_or_reason)."""
    request = urllib.request.Request(url, method="GET")
    # NSE's archive refuses requests without a browser-shaped
    # User-Agent; INKY identifies itself with an honest UA string and
    # if they still refuse, the failure is reported, not worked around.
    request.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) INKY/1.0 personal finance",
    )
    request.add_header("Accept", "text/csv, text/plain, */*")
    try:
        with urllib.request.urlopen(request, timeout=HOW_LONG_WE_WAIT) as response:
            return True, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as problem:
        return False, f"{url.split('/')[-1]} answered HTTP {problem.code}"
    except Exception as problem:                                      # noqa: BLE001
        return False, f"{url.split('/')[-1]} could not be reached: {problem}"

def _parse_csv(text: str, index_label: str) -> list[dict]:
    """Rows out of one index CSV, using whatever the real headers are.

    Column names are matched case-insensitively because NSE has changed
    header spelling between lists before ('ISIN Code' vs 'ISIN').
    """
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for raw in reader:
        lowered = {(k or "").strip().lower(): (v or "").strip()
                   for k, v in raw.items()}
        company = lowered.get("company name", "")
        symbol = lowered.get("symbol", "")
        if not company or not symbol:
            continue                                   # blank or junk line
        rows.append({
            "company_name": company,
            "industry": lowered.get("industry", "") or None,
            "symbol": symbol,
            "isin": lowered.get("isin code", "") or None,
            "indices": [index_label],
        })
    return rows


def fetch_universe(force: bool = False) -> dict:
    """The whole universe, keyed by tidy company name and by symbol.

    Within REFRESH_DAYS of the last fetch the saved file is the answer.
    Otherwise every source list is fetched fresh; whichever ones arrive
    get merged by symbol (the four indices overlap heavily). If NOTHING
    arrives, has_data comes back False and the old file - if any - is
    left exactly as it is rather than overwritten with less.
    """
    if not force and UNIVERSE_FILE.exists():
        age_days = (time.time() - UNIVERSE_FILE.stat().st_mtime) / 86400
        if age_days <= REFRESH_DAYS:
            try:
                saved = json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))
                if saved.get("_meta", {}).get("rows") or saved.get("by_name"):
                    return {**saved,
                            "has_data": True, "where_from": "cache",
                            "cached": True,
                            "note": f"cached, {age_days:.1f} days old "
                                    f"(refetches weekly)"}
            except ValueError:
                pass                       # corrupt cache falls through to refetch

    problems = []
    merged: dict[str, dict] = {}           # by upper-cased NSE symbol
    for index_label, url in SOURCES.items():
        worked, payload = _fetch_one(url)
        if not worked:
            problems.append(payload)
            continue
        # NSE rate-limits rapid back-to-back archive requests into HTTP
        # 200 pages that are NOT the CSV - a silent zero-row parse here
        # would quietly ship half a universe as if it were whole. A
        # fetched-but-unparseable list is recorded as the failure it
        # is, and a small pause between lists keeps the next ask honest.
        if "Company Name" not in payload[:500]:
            problems.append(f"{url.split('/')[-1]} answered without CSV "
                            f"data (rate-limited?)")
            time.sleep(2)
            continue
        parsed = _parse_csv(payload, index_label)
        if not parsed:
            problems.append(f"{url.split('/')[-1]} parsed to zero rows")
        for row in parsed:
            key = row["symbol"].upper()
            if key in merged:
                existing = merged[key]
                if index_label not in existing["indices"]:
                    existing["indices"].append(index_label)
                # An industry from a wider list beats a blank one.
                if existing["industry"] is None and row["industry"]:
                    existing["industry"] = row["industry"]
            else:
                merged[key] = row
        time.sleep(2)

    if not merged:
        return {"has_data": False, "where_from": "archives.nseindia.com",
                "note": "no index list could be fetched: " + "; ".join(problems)}

    by_name: dict[str, dict] = {}
    by_symbol: dict[str, str] = {}
    for row in sorted(merged.values(), key=lambda r: r["company_name"].lower()):
        by_name[_tidy(row["company_name"])] = {
            "company_name": row["company_name"], "industry": row["industry"],
            "symbol": row["symbol"], "isin": row["isin"],
            "indices": row["indices"]}
        by_symbol[row["symbol"].lower()] = row["industry"] or ""

    answer = {
        "_meta": {
            "fetched": date.today().isoformat(),
            "source_urls": SOURCES,
            "rows": len(by_name),
            "verified_by_a_person": False,
            "comment": "Industry labels copied verbatim from NSE's published "
                       "index constituent CSVs. No person has checked a single "
                       "row against an annual report - treat every figure built "
                       "on this file as [UNVERIFIED].",
        },
        "by_name": by_name,
        "by_symbol": by_symbol,
    }
    UNIVERSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    UNIVERSE_FILE.write_text(json.dumps(answer, indent=2), encoding="utf-8")
    refresh_sector_file(answer)
    return {**answer, "has_data": True,
            "where_from": "archives.nseindia.com",
            "note": None if not problems else
                    f"fetched, but some lists failed: {'; '.join(problems)}"}


def refresh_sector_file(universe: dict | None = None) -> dict:
    """Copy the NSE industries into sector_for_stocks.json's second layer.

    Only the 'nse_universe' key is ever written. Every hand-curated key
    in 'sectors' stays exactly as a person typed it - this layer loses
    to the curated one in every lookup, so overwriting nothing here is
    a structural promise, not just politeness.
    """
    if universe is None:
        if not UNIVERSE_FILE.exists():
            return {"updated": False, "note": "no universe file to copy from"}
        universe = json.loads(UNIVERSE_FILE.read_text(encoding="utf-8"))

    sector_doc = {}
    if SECTOR_FILE.exists():
        sector_doc = json.loads(SECTOR_FILE.read_text(encoding="utf-8"))
    sector_doc["nse_universe"] = {
        "by_name": {k: (v.get("industry") or "") for k, v in
                    universe.get("by_name", {}).items()},
        "by_symbol": universe.get("by_symbol", {}),
    }
    comment = sector_doc.get("_comment", "")
    if "nse_universe" not in comment:
        sector_doc["_comment"] = comment + (
            " Layered 2026-08-24: 'sectors' below is still the hand-curated "
            "override layer and always wins; 'nse_universe' is machine-filled "
            "from NSE's index constituent CSVs (see fetch_nse_universe.py) "
            "and is consulted only when the curated map misses. Lookup order "
            "in build_the_sector_map.py: curated exact, NSE universe, curated "
            "substring fallback, else 'not yet classified'.")
    SECTOR_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECTOR_FILE.write_text(json.dumps(sector_doc, indent=2), encoding="utf-8")
    return {"updated": True,
            "names": len(sector_doc["nse_universe"]["by_name"]),
            "symbols": len(sector_doc["nse_universe"]["by_symbol"])}


def main() -> None:
    force = "--force" in sys.argv
    result = fetch_universe(force=force)
    print("NSE EQUITY UNIVERSE")
    print("=" * 50)
    if not result["has_data"]:
        print(f"  FAILED: {result['note']}")
        return
    meta = result.get("_meta", {})
    print(f"  companies : {meta.get('rows', len(result.get('by_name', {})))}")
    print(f"  fetched   : {meta.get('fetched')} "
          f"[{'UNVERIFIED' if not meta.get('verified_by_a_person') else 'verified'}]")
    print(f"  source    : {result['where_from']}"
          f"{' (cache)' if result.get('cached') else ''}")
    if result.get("note"):
        print(f"  note      : {result['note']}")
    shown = 0
    for _name, row in result.get("by_name", {}).items():
        if shown >= 5:
            break
        print(f"    {row['company_name'][:34]:<36}{row['symbol']:<12}"
              f"{row['industry'] or '-'}")
        shown += 1


if __name__ == "__main__":
    main()
