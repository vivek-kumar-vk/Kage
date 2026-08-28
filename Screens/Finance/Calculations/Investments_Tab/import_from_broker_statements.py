"""One-time import: turns the broker/AMC exports dropped at the project
root into real rows in this screen's own ledgers.

RUN ONCE, BY HAND
    This is not part of the running app - nothing calls it automatically,
    and it is not on any server's import path. Run it yourself, check the
    ledgers it wrote, then delete the source folder:

    python Screens\\Finance\\Calculations\\Investments_Tab\\import_from_broker_statements.py

WHERE IT READS FROM
    My_Investement_details/ at the project root - gitignored, because it
    holds account identifiers and folio numbers. This script is the only
    reader of that folder anywhere in the codebase.

    You supply the exports and a plain-text portfolio snapshot yourself;
    nothing personal is committed to this repo. HOLDINGS and SIPS below
    are empty on purpose - fill them from your own snapshot before running,
    or extend this script to parse the snapshot file directly.

WHAT IT WRITES
    Saved_Records/portfolio_holdings.csv     current snapshot: what I
                                             hold right now, invested vs
                                             current value, per fund
    Saved_Records/active_sips.csv            the recurring monthly SIPs
    Saved_Records/realized_capital_gains.csv every matched buy/sell pair
                                             from both capital-gains
                                             reports - real transaction
                                             dates, real prices

WHAT IT DOES NOT DO
    Guess an AMFI code it is not sure of. Where a fund appears as a name
    only and several similarly named funds exist, the code stays blank
    rather than picking one. A blank is honest; a wrong code silently
    poisons every overlap calculation that reads it later.

    Read password-protected statement PDFs - this script does not attempt
    to guess a password.

    Delete My_Investement_details/. That is a decision for a person,
    made once the ledgers below are checked.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

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

SOURCE = PROJECT_ROOT / "My_Investement_details"
RECORDS = SCREEN / "Saved_Records"

AS_OF = ""             # the date on your portfolio snapshot (YYYY-MM-DD)
SOURCE_LABEL = "user-provided portfolio snapshot"

# =====================================================================
# WHAT I HOLD NOW - fill from your own plain-text portfolio snapshot.
# One tuple per holding. Leave amfi_code blank rather than guessing when
# more than one fund matches a name - a wrong code silently poisons every
# overlap calculation that reads it later. units may be None.
#
# Empty here on purpose: no personal holdings are committed to this repo.
# =====================================================================
HOLDINGS: list[tuple] = [
    # scheme_name, amfi_code, category, units, invested, current, xirr_pct
    # ("Example Flexi Cap Fund Direct Growth", "122639", "mutual_fund", None, 0, 0, 0.0),
]

SIPS: list[tuple] = [
    # scheme_name, monthly_amount
    # ("Example Flexi Cap Fund Direct Growth", 1000),
]

PORTFOLIO_HOLDINGS_COLUMNS = [
    "date", "scheme_name", "amfi_code", "category", "units", "invested",
    "current", "pl_abs", "pl_pct", "pledged_units", "source",
]
ACTIVE_SIPS_COLUMNS = ["scheme_name", "monthly_amount", "notes"]
GAINS_COLUMNS = [
    "scheme_name", "amfi_code", "category", "purchase_date",
    "purchase_price", "matched_quantity", "redeem_date", "redeem_price",
    "short_term_gain", "long_term_gain", "financial_year", "source",
]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def write_portfolio_holdings() -> int:
    rows = []
    for name, code, category, units, invested, current, xirr in HOLDINGS:
        pl_abs = round(current - invested, 2)
        pl_pct = round(pl_abs / invested * 100, 2) if invested else None
        rows.append({
            "date": AS_OF, "scheme_name": name, "amfi_code": code,
            "category": category, "units": units if units is not None else "",
            "invested": invested, "current": current, "pl_abs": pl_abs,
            "pl_pct": pl_pct, "pledged_units": "", "source": SOURCE_LABEL,
        })

    # Any stock/ETF holdings from a broker "holdings statement" xlsx
    # dropped in the source folder. Filename varies per broker/account,
    # so match by prefix rather than hard-coding it.
    stock_file = next(SOURCE.glob("Stocks_Holdings_Statement_*.xlsx"), None)
    if stock_file is not None and stock_file.exists():
        df = pd.read_excel(stock_file, header=None)
        data_row = df.iloc[11]
        units = float(data_row[2])
        invested = round(float(data_row[4]), 2)
        current = round(float(data_row[6]), 2)
        rows.append({
            "date": AS_OF, "scheme_name": "Nippon India ETF Gold BeES",
            "amfi_code": "INF204KB17I5", "category": "etf", "units": units,
            "invested": invested, "current": current,
            "pl_abs": round(current - invested, 2),
            "pl_pct": round((current - invested) / invested * 100, 2),
            "pledged_units": "",
            "source": stock_file.name,
        })

    _write_csv(RECORDS / "portfolio_holdings.csv", PORTFOLIO_HOLDINGS_COLUMNS, rows)
    return len(rows)


def write_active_sips() -> int:
    rows = [{"scheme_name": n, "monthly_amount": a, "notes": ""} for n, a in SIPS]
    _write_csv(RECORDS / "active_sips.csv", ACTIVE_SIPS_COLUMNS, rows)
    return len(rows)


def write_realized_capital_gains() -> int:
    """Every matched buy/sell pair, from both capital-gains reports.
    Real dates and prices - this is the one part of the import that
    needed no name-matching or guessing at all."""
    reports = [
        ("Mutual_Funds_Capital_Gains_Report_01-04-2025_31-03-2026.xlsx", "2025-26"),
        ("Mutual_Funds_Capital_Gains_Report_01-04-2026_31-03-2027.xlsx", "2026-27"),
    ]
    rows = []
    for filename, fy in reports:
        path = SOURCE / filename
        if not path.exists():
            continue
        df = pd.read_excel(path, header=None)
        data = df.iloc[21:].copy()
        data.columns = df.iloc[20]
        data = data.dropna(subset=[data.columns[0]])
        for _, r in data.iterrows():
            if str(r.get("Scheme Code", "")).strip().lower() in ("", "nan", "scheme code"):
                continue  # a footnote/disclaimer row, not a transaction
            rows.append({
                # Folio number deliberately left out - C2, this file is
                # tracked in git and a folio number is exactly the kind
                # of identifier .gitignore's "raw source drops" rule
                # exists to keep out. Nothing here needs it: the AMFI
                # code already identifies the scheme.
                "scheme_name": r["Scheme Name"], "amfi_code": int(r["Scheme Code"]),
                "category": r.get("Category", ""),
                "purchase_date": str(r["Purchase Date"])[:10],
                "purchase_price": round(float(r["Purchase Price"]), 4),
                "matched_quantity": round(float(r["Matched Quantity"]), 4),
                "redeem_date": str(r["Redeem Date"])[:10],
                "redeem_price": round(float(r["Redeem Price"]), 4),
                "short_term_gain": round(float(r.get("Short Term-Capital Gain", 0) or 0), 2),
                "long_term_gain": round(float(r.get("Long Term-Capital Gain", 0) or 0), 2),
                "financial_year": fy, "source": filename,
            })

    _write_csv(RECORDS / "realized_capital_gains.csv", GAINS_COLUMNS, rows)
    return len(rows)


def main() -> None:
    if not SOURCE.exists():
        print(f"No {SOURCE.relative_to(PROJECT_ROOT)} folder - nothing to import.")
        return

    print("IMPORTING BROKER STATEMENTS")
    print()
    n1 = write_portfolio_holdings()
    print(f"  wrote {n1} rows to portfolio_holdings.csv")
    n2 = write_active_sips()
    print(f"  wrote {n2} rows to active_sips.csv")
    n3 = write_realized_capital_gains()
    print(f"  wrote {n3} rows to realized_capital_gains.csv")
    print()
    print("  Any holding left with a blank amfi_code needs one filled in by "
         "hand - a wrong code silently poisons later overlap calculations.")
    print()
    print(f"  Check the three files above, then delete "
         f"{SOURCE.relative_to(PROJECT_ROOT)} yourself when you are satisfied.")


if __name__ == "__main__":
    main()
