"""The number that means work becomes optional, at Indian assumptions.

WHY 25x IS THE WRONG MULTIPLE HERE
    The famous "save 25 times your annual spending" comes from the
    Trinity study - US market returns, US inflation, a 30-year
    retirement, and a state pension plus Medicare sitting underneath the
    whole thing.

    None of those hold in India. Inflation has run at roughly double,
    the usable equity record is much shorter, and an early retiree has
    no state pension and no public healthcare to fall back on. Indian
    discussion of this generally lands between 3% and 3.5% withdrawal
    rather than 4%, which is 29x to 33x rather than 25x.

    india_planning_assumptions.json picks 3.25% - about 31x - and this
    file shows 3%, 3.5% and 4% alongside it, so the choice is visible
    instead of buried. A plan built on 25x in India is roughly a fifth
    short, and being a fifth short is only obvious decades later.

THE FOUR SHAPES, IN INDIAN TERMS
    LEAN        the corpus covers a deliberately small annual spend
    REGULAR     the corpus covers what you spend now, inflated
    COAST       enough already invested that, with nothing further
                added, compounding reaches the number by 60
    PART-TIME   the corpus covers part of it; some work covers the rest

    Coast is the one worth knowing about, because it is reachable long
    before the full number and changes what a job is for.

WHAT THIS FILE WILL NEVER DO
    Say what to hold. It computes what a corpus would have to be and
    what a contribution would grow to if a rate held. Which fund, which
    account, which allocation - not INKY's call (C5).

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Overview_Tab\\calculate_financial_independence.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

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


from Shared_By_All_Screens.read_and_write_numbers import read_state    # noqa: E402
from Shared_By_All_Screens.format_indian_money import format_inr, format_lakh  # noqa: E402
from read_the_india_rulebook import load, Rulebook                    # noqa: E402
import read_portfolio_holdings                                        # noqa: E402

TRADITIONAL_RETIREMENT_AGE = 60     # when EPF and NPS become reachable


@dataclass(frozen=True)
class Independence:
    """The numbers, and how far off they are."""

    annual_spend: int
    withdrawal_rate_pct: float
    number: int
    invested_now: int | None
    saving_per_month: int
    real_return_pct: float
    years_away: float | None
    at_other_rates: dict
    coast_number: int | None
    coast_reached: bool | None
    age: int | None

    @property
    def savings_rate_pct(self) -> float | None:
        annual_income = getattr(self, "_annual_income", None)
        return annual_income

    @property
    def progress_pct(self) -> float | None:
        if self.invested_now is None or self.number <= 0:
            return None
        return round(100 * self.invested_now / self.number, 1)


def _years_to_target(target: float, present: float, per_year: float, rate: float) -> float | None:
    """How long a growing balance plus regular saving takes to reach a target.

    Solved by stepping a year at a time rather than by the closed-form
    annuity formula. The closed form breaks when the rate is zero and
    when saving is zero, and both of those are real states somebody can
    be in - a person saving nothing is exactly who most wants to see the
    answer "never at this rate".
    """
    if present >= target:
        return 0.0
    if per_year <= 0 and rate <= 0:
        return None

    balance = present
    for year in range(1, 101):
        balance = balance * (1 + rate) + per_year
        if balance >= target:
            # Straight-line inside the final year, so the answer is not
            # always a whole number of years.
            previous = (balance - per_year) / (1 + rate)
            span = balance - previous
            if span > 0:
                return round(year - 1 + (target - previous) / span, 1)
            return float(year)
    return None


def _what_is_actually_invested(state: dict) -> int | None:
    """Current value of the holdings, or None if nothing is recorded.

    Falls back to the noticeboard key if it is ever filled in, so this
    keeps working the day an Investments screen does get built.
    """
    try:
        summary = read_portfolio_holdings.a_summary_for_the_screen()
    except Exception:
        summary = {"has_data": False}

    if summary.get("has_data") and summary.get("total_current"):
        return int(round(summary["total_current"]))

    written = state.get("portfolio_total")
    return int(written) if written is not None else None


def compute(
    state: dict | None = None,
    book: Rulebook | None = None,
    age: int | None = None,
    annual_spend: int | None = None,
) -> Independence:
    """The FI number and the distance to it, from what INKY knows."""
    state = read_state() if state is None else state
    book = book or load()

    swr = book.assumptions["safe_withdrawal_rate_pct"]
    rate_pct = swr["value"]

    # What retirement would have to cover: the bills that survive it.
    # Debt service is excluded - the education loan ends in 2031 and the
    # family loan in 2027, so neither is a lifelong cost. Including them
    # would inflate the number by something that expires.
    if annual_spend is None:
        fixed = state.get("fixed_bills") or 0
        living = state.get("slice_usage_actual") or 0
        annual_spend = int((fixed + living) * 12)

    number = int(round(annual_spend * 100 / rate_pct))

    # What is actually invested, read from this screen's own holdings
    # file rather than from the noticeboard.
    #
    # `portfolio_total` on the noticeboard is still blank, and it is
    # meant to be: that key was reserved for a separate Investments
    # screen that was never built, because Finance absorbed the idea
    # instead. Reading Finance's own Saved_Records is a screen reading
    # its own records, which is exactly what C8 allows - the noticeboard
    # is only for values that cross between screens.
    invested = _what_is_actually_invested(state)

    # Only genuinely spare money goes in. A negative surplus is not a
    # small contribution, it is none.
    surplus = state.get("surplus")
    sips = state.get("base_sips") or 0
    saving = int(sips) + max(0, int(surplus)) if surplus is not None else int(sips)

    # Real return: growth above inflation. Using the nominal 11% against
    # a target in today's rupees would count the same inflation twice.
    nominal = book.assumptions["expected_returns_pct"]["indian_equity"] / 100
    inflation = book.assumptions["inflation"]["general_pct"] / 100
    real = (1 + nominal) / (1 + inflation) - 1

    years = _years_to_target(number, invested or 0, saving * 12, real)

    others = {}
    for other in swr["also_show"]:
        n = int(round(annual_spend * 100 / other))
        others[other] = {
            "number": n,
            "years": _years_to_target(n, invested or 0, saving * 12, real),
        }

    coast_number = None
    coast_reached = None
    if age is not None and age < TRADITIONAL_RETIREMENT_AGE:
        # What would have to be invested TODAY so that, with nothing
        # further added, compounding alone reaches the number by 60.
        span = TRADITIONAL_RETIREMENT_AGE - age
        coast_number = int(round(number / ((1 + real) ** span)))
        coast_reached = invested is not None and invested >= coast_number

    return Independence(
        annual_spend=annual_spend,
        withdrawal_rate_pct=rate_pct,
        number=number,
        invested_now=invested,
        saving_per_month=saving,
        real_return_pct=round(real * 100, 2),
        years_away=years,
        at_other_rates=others,
        coast_number=coast_number,
        coast_reached=coast_reached,
        age=age,
    )


def main() -> None:
    book = load()
    fi = compute(book=book)

    print("FINANCIAL INDEPENDENCE")
    print("=" * 62)
    print(f"  Annual spend it must cover   {format_inr(fi.annual_spend)}")
    print(f"     fixed bills + living costs, twelve times over")
    print(f"     debt service excluded - both loans end before retirement")
    print()
    print(f"  Withdrawal rate              {fi.withdrawal_rate_pct}%"
          f"   ({round(100 / fi.withdrawal_rate_pct, 1)}x annual spending)")
    print(f"  THE NUMBER                   {format_lakh(fi.number)}")
    print()

    print("  AT OTHER WITHDRAWAL RATES")
    for rate, row in sorted(fi.at_other_rates.items()):
        years = row["years"]
        when = f"{years} years away" if years is not None else "not reachable at this saving"
        print(f"    {rate}%   {format_lakh(row['number']):>14}   {when}")
    print()

    print("  WHERE YOU ARE")
    if fi.invested_now is None:
        print("    Nothing is recorded in portfolio_holdings.csv and")
        print("    `portfolio_total` is blank, so the distance cannot be")
        print("    worked out. Blank is not zero.")
    else:
        print(f"    Invested now               {format_lakh(fi.invested_now)}"
              f"   ({fi.progress_pct}% of the number)")
    print(f"    Going in each month        {format_inr(fi.saving_per_month)}")
    print(f"    Real return assumed        {fi.real_return_pct}%"
          f"   (11% growth less 6% inflation)")
    if fi.years_away is not None:
        print(f"    Years away                 {fi.years_away}")
    else:
        print(f"    Years away                 not reachable at this saving rate")
    print()
    print("  Every figure here rests on assumptions in")
    print("  Reference_Data/india_planning_assumptions.json. Change one and")
    print("  re-run - that is what the file is for.")


if __name__ == "__main__":
    main()
