"""Tracks the current NAV of every fund I hold, in one ledger.

WHAT THIS FILE OWNS
    Saved_Records/fund_nav_ledger.csv - one row per fund per refresh:
    the latest NAV mfapi.in published for it, when it was published, and
    when we wrote it down. The column schema is frozen in
    Shared_By_All_Screens/Column_Contracts/frozen_column_names.json
    (schema `fund_nav_ledger`) - renaming or reordering a column breaks
    every reader silently.

WHY A LEDGER AND NOT JUST THE CACHE
    fetch_fund_facts.py caches raw API answers for twelve hours, which is
    a performance decision. This file is a record: what the NAV was each
    time INKY looked, so "how stale is this number" is a question with a
    file behind it, not a guess. The NAV freshness badge on the
    Investments tab reads exactly this.

THE HONESTY RULES
    A fund whose NAV cannot be fetched right now keeps its last ledger
    row and is reported as stale - never dropped, never back-filled with
    a made-up number. A fund with no AMFI code cannot be tracked at all
    and is reported in `untracked`, by name.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\track_the_nav_ledger.py
"""

from __future__ import annotations

import csv
import sys
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

import fetch_fund_facts                         # noqa: E402
import read_what_i_own                          # noqa: E402
import read_portfolio_holdings                  # noqa: E402

SAVED_RECORDS = SCREEN / "Saved_Records"
LEDGER = SAVED_RECORDS / "fund_nav_ledger.csv"

# Frozen column contract: fund_nav_ledger (Column_Contracts, v12+).
COLUMNS = ["date", "scheme_name", "amfi_code", "nav", "nav_date", "source"]

# A NAV older than this is flagged stale on screen. Fund NAVs publish
# once a trading day, so anything past a week means the source has been
# unreachable for a while - worth seeing, not worth hiding.
STALE_AFTER_DAYS = 7


def ledger_path() -> Path:
    return LEDGER


def read_the_ledger() -> list[dict]:
    """Every recorded NAV, oldest first. Empty when never run."""
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f)
                if (row.get("amfi_code") or "").strip()]
    rows.sort(key=lambda r: (r["amfi_code"], r["date"]))
    return rows


def _latest_per_fund(rows: list[dict]) -> dict[str, dict]:
    """The most recent row per AMFI code. Ties break toward the later
    write, because the file is append-sorted and the last look wins."""
    latest: dict[str, dict] = {}
    for row in rows:
        code = row["amfi_code"]
        existing = latest.get(code)
        if existing is None or row["date"] >= existing["date"]:
            latest[code] = row
    return latest
def _tracked_funds() -> tuple[list[dict], list[str]]:
    """Every fund INKY could track, and the names of the ones it cannot.

    A fund is trackable when it has an AMFI scheme code - that is the
    only key mfapi.in answers. Snapshot holdings are checked first, then
    hand-logged transactions; a transaction identifier that is not a
    plain numeric AMFI code (an ISIN, a ticker) cannot be looked up, so
    its scheme lands in `untracked` instead of being quietly skipped.
    """
    funds: dict[str, str] = {}          # amfi_code -> best known name
    untracked: list[str] = []

    try:
        snapshot = read_portfolio_holdings.read_every_holding()
    except Exception:
        snapshot = []
    for holding in snapshot:
        code = (holding.get("amfi_code") or "").strip()
        if code:
            funds.setdefault(code, holding["scheme_name"])
        else:
            untracked.append(holding["scheme_name"])

    try:
        for row in read_what_i_own.read_every_transaction():
            if row["kind"] != "mutual_fund":
                continue
            code = (row["identifier"] or "").strip()
            name = row["name"] or code
            if code.isdigit():
                funds.setdefault(code, name)
            elif name.lower() not in {u.lower() for u in untracked}:
                untracked.append(name)
    except read_what_i_own.TheRecordsAreWrong:
        pass   # the transaction file's own error surfaces where it is read properly

    ordered = [{"scheme_name": funds[c], "amfi_code": c} for c in sorted(funds)]
    return ordered, untracked


def update_the_ledger(today: date | None = None) -> dict:
    """Fetch the current NAV for every tracked fund and write it down.

    Re-running on the same day replaces that day's row rather than
    stacking a second one. A failed fetch leaves the fund's history
    untouched and is counted in `failed`, never guessed around.
    """
    today = today or date.today()
    funds, untracked = _tracked_funds()

    existing = read_the_ledger()
    kept = [r for r in existing
            if not (r["date"] == today.isoformat() and any(
                f["amfi_code"] == r["amfi_code"] for f in funds))]

    written, failed = [], []
    stamp = today.isoformat()
    for fund in funds:
        answer = fetch_fund_facts.latest_nav(fund["amfi_code"])
        if not answer.get("has_data"):
            failed.append({"scheme_name": fund["scheme_name"],
                           "amfi_code": fund["amfi_code"],
                           "note": answer.get("note", "no data")})
            continue
        written.append({
            "date": stamp,
            "scheme_name": fund["scheme_name"],
            "amfi_code": fund["amfi_code"],
            "nav": answer["nav"],
            "nav_date": answer.get("nav_date", ""),
            "source": answer.get("where_from", "mfapi.in"),
        })

    all_rows = sorted(kept + written, key=lambda r: (r["amfi_code"], r["date"]))
    if all_rows:
        SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(all_rows)

    return {"funds_tracked": len(funds), "written": len(written),
            "failed": failed, "untracked": untracked}


def freshness(amfi_code: str, today: date | None = None) -> dict:
    """How old the newest ledger row for one fund is.

    Returns age_days and a plain fresh/stale/unknown word, so the
    Investments tab can badge a row without knowing where the number
    came from.
    """
    today = today or date.today()
    latest = _latest_per_fund(read_the_ledger()).get(amfi_code)
    if latest is None or not (latest.get("nav_date") or "").strip():
        return {"known": False, "age_days": None, "state": "unknown"}
    published = _parse_nav_date(latest["nav_date"])
    if published is None:
        return {"known": False, "age_days": None, "state": "unknown"}
    age = (today - published).days
    return {"known": True, "age_days": age,
            "state": "fresh" if age <= STALE_AFTER_DAYS else "stale",
            "nav": latest["nav"], "source": latest["source"]}


def _parse_nav_date(raw: str) -> date | None:
    """mfapi.in publishes dates as dd-mm-yyyy; everything else in INKY
    is ISO. Both are accepted here rather than assuming either."""
    raw = (raw or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    try:
        return datetime.strptime(raw, "%d-%m-%Y").date()
    except ValueError:
        return None


def a_summary_for_the_screen(today: date | None = None) -> dict:
    """What the Investments tab needs: the newest NAV per fund, with an
    honest staleness badge attached to each."""
    today = today or date.today()
    latest = _latest_per_fund(read_the_ledger())
    rows = []
    for code in sorted(latest):
        row = latest[code]
        fresh = freshness(code, today)
        rows.append({
            "scheme_name": row["scheme_name"], "amfi_code": code,
            "nav": row["nav"], "nav_date": row["nav_date"],
            "recorded_on": row["date"], "source": row["source"],
            "age_days": fresh["age_days"], "state": fresh["state"],
        })
    return {"has_data": bool(rows), "rows": rows,
            "stale_after_days": STALE_AFTER_DAYS}


def main() -> None:
    result = update_the_ledger()
    print("NAV LEDGER")
    print("=" * 50)
    print(f"  funds tracked : {result['funds_tracked']}")
    print(f"  written       : {result['written']}")
    for failure in result["failed"]:
        print(f"  FAILED        : {failure['scheme_name']} ({failure['note']})")
    for name in result["untracked"]:
        print(f"  untracked     : {name} (no AMFI code)")
    for row in a_summary_for_the_screen()["rows"]:
        print(f"  {row['scheme_name'][:44]:<46} "
              f"NAV {row['nav']:>10} as of {row['nav_date']} [{row['state']}]")


if __name__ == "__main__":
    main()

