"""Reads and edits the portfolio holdings snapshot.

WHAT THIS FILE IS, AND HOW IT DIFFERS FROM read_what_i_own.py
    read_what_i_own.py derives a holding from a transaction log - one
    row per buy or sell, added up. This file reads the OTHER real shape
    of holdings data: a snapshot someone already computed (a broker
    export, an app screenshot copied in) that states invested and
    current value directly, because the per-transaction history was
    never available to derive it from.

    Both are real. A holding can come from either file; nothing in the
    app assumes only one of them is populated.

WHY THIS ONE IS EDITABLE FROM THE UI, AND THE OTHERS ARE NOT
    A snapshot goes stale the moment prices move. Re-running an import
    script every time a price changes is not realistic, so the Finance
    screen lets you correct `current`, `units` and `pl_*` by hand. What
    is NOT editable from the UI: `scheme_name` and `amfi_code` identify
    the row - changing those is a delete-and-recreate, not an edit, so
    the wrong holding is never silently renamed into a different one.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\read_portfolio_holdings.py
"""

from __future__ import annotations

import csv
import sys
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

COLUMNS = [
    "date", "scheme_name", "amfi_code", "category", "units", "invested",
    "current", "pl_abs", "pl_pct", "pledged_units", "source",
]

EDITABLE_FIELDS = {"date", "units", "invested", "current", "pledged_units", "source"}


class TheRecordsAreWrong(Exception):
    """Raised when a row cannot be trusted. Never guessed around."""


def records_path() -> Path:
    return SCREEN / "Saved_Records" / "portfolio_holdings.csv"


def start_the_records_if_missing() -> Path:
    where = records_path()
    where.parent.mkdir(parents=True, exist_ok=True)
    if not where.exists():
        with where.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(COLUMNS)
    return where


def _row_id(row: dict) -> str:
    """scheme_name + amfi_code identifies a row. Two funds can share a
    name only if one is missing its code, which read_every_holding
    already refuses to allow twice."""
    return f"{row['scheme_name']}|{row.get('amfi_code', '')}"


def read_every_holding() -> list[dict]:
    where = records_path()
    if not where.exists():
        return []

    rows = []
    seen_ids = set()
    with where.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise TheRecordsAreWrong("portfolio_holdings.csv is missing columns: " + ", ".join(missing))

        for line_number, row in enumerate(reader, start=2):
            if not (row.get("scheme_name") or "").strip():
                continue
            where_line = f"portfolio_holdings.csv line {line_number}"
            parsed = _parse_row(row, where_line)
            row_id = _row_id(parsed)
            if row_id in seen_ids:
                raise TheRecordsAreWrong(
                    f"{where_line}: '{parsed['scheme_name']}' appears twice with the "
                    "same amfi_code. Edit the existing row instead of adding a new one."
                )
            seen_ids.add(row_id)
            rows.append(parsed)

    rows.sort(key=lambda r: r["current"] or 0, reverse=True)
    return rows


def _num(text, where: str, field: str):
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        raise TheRecordsAreWrong(f"{where}: {field} '{text}' is not a number")


def _parse_row(row: dict, where: str) -> dict:
    name = (row.get("scheme_name") or "").strip()
    invested = _num(row.get("invested"), where, "invested")
    current = _num(row.get("current"), where, "current")
    return {
        "date": (row.get("date") or "").strip(),
        "scheme_name": name,
        "amfi_code": (row.get("amfi_code") or "").strip(),
        "category": (row.get("category") or "").strip(),
        "units": _num(row.get("units"), where, "units"),
        "invested": invested,
        "current": current,
        "pl_abs": _num(row.get("pl_abs"), where, "pl_abs"),
        "pl_pct": _num(row.get("pl_pct"), where, "pl_pct"),
        "pledged_units": _num(row.get("pledged_units"), where, "pledged_units"),
        "source": (row.get("source") or "").strip(),
    }


def _write_all(rows: list[dict]) -> None:
    where = start_the_records_if_missing()
    with where.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in COLUMNS})


def a_summary_for_the_screen() -> dict:
    holdings = read_every_holding()
    if not holdings:
        return {"has_data": False, "note": (
            "Saved_Records/portfolio_holdings.csv has nothing in it yet. Add a "
            "holding from the Investments tab, or run "
            "import_from_broker_statements.py against a real export."
        )}
    total_invested = sum(h["invested"] or 0 for h in holdings)
    total_current = sum(h["current"] or 0 for h in holdings)
    return {
        "has_data": True,
        "total_invested": round(total_invested, 2),
        "total_current": round(total_current, 2),
        "total_pl": round(total_current - total_invested, 2),
        "how_many_holdings": len(holdings),
        "holdings": holdings,
    }


# =====================================================================
# EDIT - the only writers the Finance backend calls
# =====================================================================
def add_holding(scheme_name: str, *, amfi_code: str = "", category: str = "mutual_fund",
                units=None, invested=None, current=None, source: str = "added by hand") -> dict:
    scheme_name = (scheme_name or "").strip()
    if not scheme_name:
        raise ValueError("a holding needs a name")
    if invested is None or current is None:
        raise ValueError("invested and current are both required")

    rows = read_every_holding()
    new_row = {
        "date": date.today().isoformat(), "scheme_name": scheme_name,
        "amfi_code": (amfi_code or "").strip(), "category": category,
        "units": units, "invested": float(invested), "current": float(current),
        "pl_abs": round(float(current) - float(invested), 2),
        "pl_pct": round((float(current) - float(invested)) / float(invested) * 100, 2) if invested else None,
        "pledged_units": None, "source": source,
    }
    if any(_row_id(r) == _row_id(new_row) for r in rows):
        raise ValueError(f"'{scheme_name}' is already a holding - edit it instead of adding it twice")

    rows.append(new_row)
    _write_all(rows)
    return new_row


def update_holding(scheme_name: str, amfi_code: str, changes: dict) -> dict:
    rows = read_every_holding()
    target_id = f"{scheme_name}|{amfi_code or ''}"
    for row in rows:
        if _row_id(row) != target_id:
            continue
        bad = [k for k in changes if k not in EDITABLE_FIELDS]
        if bad:
            raise ValueError(
                f"cannot edit {', '.join(bad)} - only {', '.join(sorted(EDITABLE_FIELDS))} "
                "may be changed from the UI"
            )
        row.update(changes)
        if "invested" in changes or "current" in changes:
            row["pl_abs"] = round((row["current"] or 0) - (row["invested"] or 0), 2)
            row["pl_pct"] = (round(row["pl_abs"] / row["invested"] * 100, 2)
                             if row["invested"] else None)
        _write_all(rows)
        return row
    raise KeyError(f"no holding called '{scheme_name}'")


def delete_holding(scheme_name: str, amfi_code: str) -> bool:
    rows = read_every_holding()
    target_id = f"{scheme_name}|{amfi_code or ''}"
    kept = [r for r in rows if _row_id(r) != target_id]
    if len(kept) == len(rows):
        return False
    _write_all(kept)
    return True


def main() -> None:
    start_the_records_if_missing()
    summary = a_summary_for_the_screen()
    print("PORTFOLIO HOLDINGS")
    print()
    if not summary["has_data"]:
        print(f"  {summary['note']}")
        return
    for h in summary["holdings"]:
        print(f"  {h['scheme_name']:<55}invested {h['invested']:>10,.2f}  "
             f"current {h['current']:>10,.2f}  {h['pl_pct']:>7.2f}%")
    print()
    print(f"  total invested {summary['total_invested']:,.2f}")
    print(f"  total current  {summary['total_current']:,.2f}")


if __name__ == "__main__":
    main()
