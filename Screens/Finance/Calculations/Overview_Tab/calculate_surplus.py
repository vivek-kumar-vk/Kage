"""Works out how much money is left over each month.

THE WHOLE IDEA IN FOUR LINES

    SURPLUS    = what comes in  -  everything that must go out
    DEPLOYABLE = SURPLUS  -  what you put aside for emergencies

    Surplus is what is left after the bills.
    Deployable is what is left after the bills AND after saving.

ONE TRAP WORTH KNOWING
    `slice_usage_actual` is what you actually spent on the credit line
    last month. NOT the ₹28,000 limit. Using the limit would pretend you
    spent money you did not spend, and quietly understate your surplus.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Overview_Tab\\calculate_surplus.py
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# =====================================================================
# SETUP — find the project root so imports work from anywhere
# =====================================================================
# This file sits at  Screens/<Screen>/Calculations/<this file>.py
HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))   # so this screen's own files import by name

# The rupee sign is not in the old Windows console codepage. Without this
# line, printing a single figure crashes with a UnicodeEncodeError - which
# looks like a bug in the maths and is not.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


from Shared_By_All_Screens.read_and_write_numbers import read_state, write_state, require  # noqa: E402
from Shared_By_All_Screens.format_indian_money import format_inr, format_signed      # noqa: E402

# Where the answers get written.
LEDGER = SCREEN / "Saved_Records" / "monthly_summary_all_months.csv"
MONTHLY_DIR = LEDGER.parent / "One_File_Per_Month"

# =====================================================================
# THE FORMULA, AS DATA
# =====================================================================
# Listed here rather than typed into the calculation below, so the
# formula can be read at a glance and a test can check that the parts
# still add up to the whole.
#
# `base_sips` is deliberately NOT in here. Corrected 2026-08-22: SIPs are
# funded by drawing back out of the Slice line after it is refilled each
# month, not by a second, separate debit from the bank account. Counting
# both `base_sips` and `slice_usage_actual` as independent outflows
# subtracted the same rupees twice. This is the same rule
# active_sips.csv's own column contract already states -
# "Informational - never added into the surplus formula automatically" -
# it just was not being followed here. See ADR-072.
INFLOW = ("income",)
OUTFLOW = ("fixed_bills", "debt_service", "slice_usage_actual")


# =====================================================================
# THE ANSWER
# =====================================================================
@dataclass(frozen=True)
class Surplus:
    """One month's answer.

    `frozen=True` means nothing can change these numbers after they are
    worked out. If a figure needs to change, the calculation is run
    again from the source. Numbers that can be edited after the fact are
    numbers nobody can trust.
    """

    income: int
    fixed_bills: int
    debt_service: int
    base_sips: int          # informational only - see the note on OUTFLOW above
    slice_usage: int
    surplus: int
    emergency_contribution: int
    deployable: int
    before_slice_refill: int   # see the note on this field, just below

    def lines(self) -> list[tuple[str, int, str]]:
        """The breakdown, one row per line of the formula.

        Money coming in is positive, money going out is negative, so the
        rows literally add up to the surplus. This is what the Money tab
        shows — you can check the total by eye. `base_sips` has no row
        here on purpose: it is not part of the arithmetic (see OUTFLOW).
        """
        return [
            ("Income", self.income, "+"),
            ("Fixed bills", -self.fixed_bills, "-"),
            ("Debt service", -self.debt_service, "-"),
            ("Revolving usage (actual)", -self.slice_usage, "-"),
        ]


# =====================================================================
# STEP 1 — DO THE MATHS
# =====================================================================
def compute(state: dict | None = None) -> Surplus:
    """Read the noticeboard, subtract the outgoings, return the answer.

    If any figure it needs is blank, it stops and names the missing one.
    It never treats a blank as zero. "I do not know" and "it is zero"
    lead to different decisions, and guessing between them is how a
    confident wrong number ends up on screen.
    """
    state = read_state() if state is None else state

    # Refuse to guess. Names exactly which value is missing. base_sips is
    # required too even though it is not summed - it is still displayed,
    # and a blank there should say so, not silently print as 0.
    require(state, *INFLOW, *OUTFLOW, "emergency_contribution", "base_sips")

    income = state["income"]
    outflow = {k: state[k] for k in OUTFLOW}

    surplus = income - sum(outflow.values())
    contribution = state["emergency_contribution"]

    # A second, separate figure, added 2026-08-22 at the owner's request:
    # what is left after bills, debt AND the SIPs, but BEFORE the Slice
    # refill. Not "surplus" - a different question, asked for by name so
    # it does not get silently blended into or confused with surplus
    # (which still includes the full Slice refill, see OUTFLOW above).
    # Same inputs, no new state required.
    before_slice_refill = (income - outflow["fixed_bills"]
                           - outflow["debt_service"] - state["base_sips"])

    return Surplus(
        income=income,
        fixed_bills=outflow["fixed_bills"],
        debt_service=outflow["debt_service"],
        base_sips=state["base_sips"],
        slice_usage=outflow["slice_usage_actual"],
        surplus=surplus,
        emergency_contribution=contribution,
        deployable=surplus - contribution,
        before_slice_refill=before_slice_refill,
    )


# =====================================================================
# STEP 2 — WRITE IT DOWN
# =====================================================================
def append_month(s: Surplus, month: str | None = None, notes: str = "") -> str:
    """Save this month's answer to two places.

    Two files hold the same numbers, on purpose:

        monthly_summary_all_months.csv    every month together, for
                                          spotting trends
        One_File_Per_Month/2026-08.csv    one month alone, easy to open
                                          and correct

    Re-running the same month replaces it in both. It never adds a
    second row for a month that already exists.
    """
    month = month or date.today().strftime("%Y-%m")

    # Column order comes from the frozen schema and is never rearranged
    # here. Renaming or reordering a column breaks every reader silently.
    # A missing ledger is created with that schema rather than crashing -
    # the same "start the records if missing" behaviour every other file
    # in Saved_Records follows. The handle is closed with `with`, not
    # left to the garbage collector.
    if LEDGER.exists():
        with LEDGER.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        with LEDGER.open(newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
    else:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        header = ["month", "income", "fixed_bills", "debt_service",
                  "base_sips", "slice_usage", "surplus",
                  "emergency_added", "notes"]
        with LEDGER.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=header).writeheader()
        rows = []

    row = {
        "month": month,
        "income": s.income,
        "fixed_bills": s.fixed_bills,
        "debt_service": s.debt_service,
        "base_sips": s.base_sips,
        "slice_usage": s.slice_usage,
        "surplus": s.surplus,
        "emergency_added": s.emergency_contribution,
        "notes": notes,
    }

    # --- drop any old row for this month, add the new one, sort -------
    rows = [r for r in rows if r["month"] != month] + [row]
    rows.sort(key=lambda r: r["month"])

    # --- write the master file ----------------------------------------
    with LEDGER.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)

    # --- write the single-month file ----------------------------------
    MONTHLY_DIR.mkdir(exist_ok=True)
    with (MONTHLY_DIR / f"{month}.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerow(row)

    return month


# =====================================================================
# STEP 3 — PRINT IT
# =====================================================================
def main() -> None:
    """What you see when you run this file directly."""
    s = compute()

    print("SURPLUS")
    print()

    # The formula, line by line, so the total can be checked by eye.
    for label, amount, _ in s.lines():
        print(f"  {label:<28}{format_signed(amount):>12}")

    print("  " + "-" * 40)
    print(f"  {'SURPLUS':<28}{format_signed(s.surplus):>12}")
    print(f"  {'less emergency contribution':<28}{format_signed(-s.emergency_contribution):>12}")
    print(f"  {'DEPLOYABLE':<28}{format_signed(s.deployable):>12}")
    print()
    print(f"  {'Before Slice refill':<28}{format_signed(s.before_slice_refill):>12}"
          "   (bills, debt & SIPs only - a separate figure, not surplus)")
    print()

    # Save the answer, and put the surplus back on the noticeboard so
    # every other part of the system reads the same figure.
    month = append_month(s)
    write_state({"surplus": s.surplus, "before_slice_refill": s.before_slice_refill})
    print(f"wrote monthly_summary_all_months.csv row {month}, "
          "and the surplus back onto the noticeboard")


if __name__ == "__main__":
    main()
