"""The true annualised return of each holding, from its own transactions.

WHAT XIRR IS, IN THREE LINES
    Money went in on different dates at different amounts. A simple
    gain/loss percent ignores WHEN - a rupee invested in 2023 earned
    more than a rupee invested last month. XIRR is the single annual
    rate that makes every dated cashflow add up to today's value:

        sum(amount_i / (1 + rate) ** years_i)  =  0

    where money IN is negative and today's value is positive. There is
    no closed form; this file solves it by bisection, which cannot
    diverge and always converges when an answer exists.

WHERE EVERY NUMBER COMES FROM
    Cashflows: my_investments.csv, one row per buy or sell (C4's
    traceability rule). Today's value: the snapshot current value in
    portfolio_holdings.csv. When that is unknown the holding is listed
    in `skipped` with the reason - never guessed.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\compute_the_xirr.py
"""

from __future__ import annotations

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

import read_what_i_own                            # noqa: E402

# Bisection bounds. A rate below -99.99% is meaningless; 100x a year is
# beyond anything worth reporting. If NPV has the same sign at both ends
# there is no answer in between, and that is what gets reported.
RATE_LOW = -0.9999
RATE_HIGH = 10.0
ITERATIONS = 200


def _npv(cashflows: list[tuple[date, float]], rate: float,
         valuation_date: date) -> float:
    total = 0.0
    for when, amount in cashflows:
        # Every flow is compounded FORWARD to the valuation date - a
        # rupee invested two years ago has grown at `rate` for two
        # years. XIRR is the rate that makes the compounded total zero.
        years = max((valuation_date - when).days, 0) / 365.25
        total += amount * ((1.0 + rate) ** years)
    return total


def xirr(cashflows: list[tuple[date, float]],
         valuation_date: date | None = None) -> float | None:
    """Annualised return as a fraction (0.14 == 14% a year), or None."""
    if len(cashflows) < 2:
        return None
    valuation_date = valuation_date or max(when for when, _ in cashflows)
    low_npv = _npv(cashflows, RATE_LOW, valuation_date)
    high_npv = _npv(cashflows, RATE_HIGH, valuation_date)
    if (low_npv > 0) == (high_npv > 0):
        return None

    low, high = RATE_LOW, RATE_HIGH
    for _ in range(ITERATIONS):
        middle = (low + high) / 2.0
        middle_npv = _npv(cashflows, middle, valuation_date)
        if abs(middle_npv) < 0.005:
            return middle
        if (middle_npv > 0) == (low_npv > 0):
            low, low_npv = middle, middle_npv
        else:
            high = middle
    return (low + high) / 2.0


def snapshot_current_values() -> dict[str, dict]:
    """identifier (AMFI code, or lowercase scheme name) -> current value."""
    import csv
    values: dict[str, dict] = {}
    try:
        with (SCREEN / "Saved_Records" / "portfolio_holdings.csv") \
                .open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                code = (row.get("amfi_code") or "").strip()
                name = (row.get("scheme_name") or "").strip().lower()
                if not row.get("current"):
                    continue
                entry = {"value": float(row["current"])}
                if code:
                    values[code] = entry
                if name:
                    values.setdefault(name, entry)
    except FileNotFoundError:
        pass
    return values


def per_holding_xirr(today: date | None = None,
                     latest_values: dict[str, dict] | None = None) -> dict:
    """XIRR for every transaction-logged holding that can support one.

    latest_values maps identifier -> {"value": rupees}. A holding absent
    from it is skipped and named, because an XIRR against a value nobody
    knows would be a guess wearing a suit.
    """
    today = today or date.today()
    latest_values = latest_values or {}

    try:
        transactions = read_what_i_own.read_every_transaction()
    except read_what_i_own.TheRecordsAreWrong as problem:
        return {"has_data": False, "note": str(problem),
                "holdings": [], "skipped": []}

    by_identifier: dict[str, list] = {}
    names: dict[str, str] = {}
    for row in transactions:
        key = row["identifier"] or row["name"]
        by_identifier.setdefault(key, []).append(row)
        names[key] = row["name"] or key

    out, skipped = [], []
    for key, rows in by_identifier.items():
        flows = [(row["date"], -row["amount"]) for row in rows if row["amount"]]
        final = latest_values.get(key)
        if not final or not final.get("value"):
            skipped.append({"name": names[key],
                            "reason": "no current value to close the series with"})
            continue
        flows.append((today, float(final["value"])))
        rate = xirr(flows, today)
        if rate is None:
            skipped.append({"name": names[key],
                            "reason": "cashflows do not cross zero - no XIRR exists"})
            continue
        out.append({"name": names[key],
                    "xirr_pct": round(rate * 100, 2),
                    "transactions": len(rows),
                    "first_invested": min(row["date"].isoformat()
                                          for row in rows)})

    out.sort(key=lambda h: h["xirr_pct"], reverse=True)
    return {"has_data": bool(out), "holdings": out, "skipped": skipped}


def main() -> None:
    answer = per_holding_xirr(latest_values=snapshot_current_values())
    print("XIRR PER HOLDING")
    print("=" * 50)
    if not answer["has_data"]:
        print(f"  {answer.get('note') or 'nothing could be computed yet'}")
    for holding in answer["holdings"]:
        print(f"  {holding['name'][:44]:<46}{holding['xirr_pct']:>8.2f}% a year")
    for skip in answer["skipped"]:
        print(f"  skipped {skip['name']}: {skip['reason']}")


if __name__ == "__main__":
    main()

