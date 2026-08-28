"""Reads my own investment records. Two CSVs I maintain by hand, nothing
else.

These files are the ground truth for every investment figure the
Finance screen shows. If a figure cannot be traced back to a row in one
of them, it does not get printed - it gets a dash. usage.has_data:
false, applied to money.

Saved_Records/my_investments.csv
    date,kind,name,identifier,amount,units,notes

    kind        mutual_fund | share
    identifier  AMFI scheme code for a fund, NSE symbol for a share
    amount      rupees put in on that date (a buy is positive, a sell negative)
    units       units or shares received; blank is allowed, amount is not

    One row per transaction, never per holding. The holding is derived,
    so a correction is a new row rather than an edit, and the history
    survives.

Saved_Records/my_watchlist.csv
    identifier,name,why_i_am_watching,added_on

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\read_what_i_own.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime
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

INVESTMENT_COLUMNS = ["date", "kind", "name", "identifier", "amount", "units", "notes"]
WATCHLIST_COLUMNS = ["identifier", "name", "why_i_am_watching", "added_on"]


class TheRecordsAreWrong(Exception):
    """Raised when a row cannot be trusted. Never guessed around."""


def investments_path() -> Path:
    return SCREEN / "Saved_Records" / "my_investments.csv"


def watchlist_path() -> Path:
    return SCREEN / "Saved_Records" / "my_watchlist.csv"


def start_the_records_if_missing() -> Path:
    where = investments_path()
    where.parent.mkdir(parents=True, exist_ok=True)
    if not where.exists():
        with where.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(INVESTMENT_COLUMNS)
    watchlist = watchlist_path()
    if not watchlist.exists():
        with watchlist.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(WATCHLIST_COLUMNS)
    return where


def read_every_transaction() -> list[dict]:
    """Return the rows, checked. A bad row stops the read and names itself.

    Loud beats quiet here: a silently dropped transaction makes every
    downstream percentage wrong in a way nobody notices for months.
    """
    where = investments_path()
    if not where.exists():
        return []

    rows = []
    with where.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in INVESTMENT_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise TheRecordsAreWrong("my_investments.csv is missing columns: " + ", ".join(missing))
        for line_number, row in enumerate(reader, start=2):
            if not any((row.get(c) or "").strip() for c in INVESTMENT_COLUMNS):
                continue
            rows.append(_check_one_row(row, line_number))
    rows.sort(key=lambda r: r["date"])
    return rows


def _check_one_row(row: dict, line_number: int) -> dict:
    where = f"my_investments.csv line {line_number}"

    try:
        when = datetime.strptime((row.get("date") or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        raise TheRecordsAreWrong(f"{where}: the date '{row.get('date')}' is not YYYY-MM-DD")

    kind = (row.get("kind") or "").strip().lower()
    if kind not in ("mutual_fund", "share"):
        raise TheRecordsAreWrong(f"{where}: kind is '{kind}'. It must be mutual_fund or share.")

    identifier = (row.get("identifier") or "").strip()
    if not identifier:
        raise TheRecordsAreWrong(
            f"{where}: no identifier. A fund needs its AMFI code, a share its "
            "NSE symbol. Names change; codes do not."
        )

    try:
        amount = float((row.get("amount") or "0").replace(",", "").strip())
    except ValueError:
        raise TheRecordsAreWrong(f"{where}: amount '{row.get('amount')}' is not a number")
    if amount == 0:
        raise TheRecordsAreWrong(f"{where}: amount is zero, so nothing happened")

    units_text = (row.get("units") or "").strip()
    units = None
    if units_text:
        try:
            units = float(units_text.replace(",", ""))
        except ValueError:
            raise TheRecordsAreWrong(f"{where}: units '{units_text}' is not a number")

    return {"date": when, "kind": kind, "name": (row.get("name") or "").strip(),
           "identifier": identifier, "amount": amount, "units": units,
           "notes": (row.get("notes") or "").strip()}


def what_i_hold_now() -> list[dict]:
    """Fold the transactions into current holdings.

    Cost is money in minus money out - not a valuation. Nothing here
    knows today's NAV; the screen fetches that separately and says
    where it came from.
    """
    transactions = read_every_transaction()

    holdings = defaultdict(lambda: {
        "kind": "", "name": "", "identifier": "", "money_in": 0.0, "money_out": 0.0,
        "units": 0.0, "units_are_known": True, "first_bought": None,
        "last_touched": None, "transaction_count": 0,
    })

    for row in transactions:
        holding = holdings[row["identifier"]]
        holding["kind"] = row["kind"]
        holding["identifier"] = row["identifier"]
        if row["name"]:
            holding["name"] = row["name"]
        if row["amount"] > 0:
            holding["money_in"] += row["amount"]
        else:
            holding["money_out"] += abs(row["amount"])
        if row["units"] is None:
            holding["units_are_known"] = False
        else:
            holding["units"] += row["units"] if row["amount"] > 0 else -row["units"]
        if holding["first_bought"] is None:
            holding["first_bought"] = row["date"]
        holding["last_touched"] = row["date"]
        holding["transaction_count"] += 1

    result = []
    for holding in holdings.values():
        net = holding["money_in"] - holding["money_out"]
        if holding["units_are_known"]:
            # Units are the honest signal once they exist: a buy price
            # never equals a sell price, so "money in minus money out"
            # almost never nets to exactly zero even after every unit
            # is gone. Checking cash here would keep a fully round-tripped
            # trade looking like a live holding forever.
            # 0.0001 units, not 0 exactly - summing floats from several
            # buys before subtracting a sell leaves residue like 1e-14,
            # which is not a fractional unit anyone actually holds.
            if holding["units"] <= 0.0001:
                continue  # fully exited; not a holding any more
        elif abs(net) < 0.01:
            continue  # units were never logged; cash netting to ~0 is all we have
        result.append({
            "kind": holding["kind"], "name": holding["name"] or holding["identifier"],
            "identifier": holding["identifier"], "amount_invested": round(net, 2),
            "units": round(holding["units"], 4) if holding["units_are_known"] else None,
            "units_are_known": holding["units_are_known"],
            "first_bought": holding["first_bought"].isoformat() if holding["first_bought"] else None,
            "last_touched": holding["last_touched"].isoformat() if holding["last_touched"] else None,
            "transactions": holding["transaction_count"],
        })

    result.sort(key=lambda r: r["amount_invested"], reverse=True)
    return result


def how_much_i_put_in_each_month() -> list[dict]:
    """Money in per calendar month - the habit, separated from the outcome."""
    transactions = read_every_transaction()
    by_month = defaultdict(float)
    for row in transactions:
        if row["amount"] > 0:
            by_month[row["date"].strftime("%Y-%m")] += row["amount"]
    return [{"month": m, "invested": round(by_month[m], 2)} for m in sorted(by_month)]


def a_summary_for_the_screen() -> dict:
    """One small dict the page can draw without doing arithmetic itself."""
    holdings = what_i_hold_now()
    if not holdings:
        return {"has_data": False, "note": (
            "Saved_Records/my_investments.csv has no transactions yet. Add "
            "one row per buy and every number on this screen starts working."
        )}
    total = sum(row["amount_invested"] for row in holdings)
    funds = [row for row in holdings if row["kind"] == "mutual_fund"]
    shares = [row for row in holdings if row["kind"] == "share"]
    return {
        "has_data": True, "total_invested": round(total, 2),
        "how_many_funds": len(funds), "how_many_shares": len(shares),
        "biggest_holding": holdings[0]["name"] if holdings else None,
        "months_investing": len(how_much_i_put_in_each_month()),
    }


def main() -> None:
    start_the_records_if_missing()
    summary = a_summary_for_the_screen()
    print("WHAT I OWN")
    print()
    if not summary["has_data"]:
        print(f"  {summary['note']}")
        return
    print(f"  total invested   Rs {summary['total_invested']:,.2f}")
    print(f"  funds            {summary['how_many_funds']}")
    print(f"  shares           {summary['how_many_shares']}")
    print(f"  biggest holding  {summary['biggest_holding']}")


if __name__ == "__main__":
    main()
