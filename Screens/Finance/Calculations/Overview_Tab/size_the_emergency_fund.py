"""How many months of cover you need, and how many you have.

WHY THE INDIAN NUMBER IS BIGGER THAN THE AMERICAN ONE
    The framework this is adapted from starts at 3 months and stretches
    to 6 for the self-employed. That band is built on a country with
    unemployment insurance, COBRA continuation of health cover, and a
    culture of two-week notice.

    India has none of those. Employer health cover usually ends with the
    job, there is no unemployment payment, and a notice period cuts both
    ways. So every band in india_planning_assumptions.json starts where
    an American band ends: 6 months is the floor, not the target, and a
    freelancer sits at 12.

WHAT COUNTS AND WHAT DOES NOT
    Money reachable inside a day, without selling at a loss and without
    a tax event. An undrawn credit limit is not savings - it is new debt
    wearing a savings costume, and the month you need it is exactly the
    month a lender may withdraw it.

    Equity mutual funds do not count either. The month somebody loses
    their job is disproportionately likely to be a month the market is
    down, which is the one correlation that matters here.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Overview_Tab\\size_the_emergency_fund.py
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
from Shared_By_All_Screens.format_indian_money import format_inr      # noqa: E402
from read_the_india_rulebook import load, Rulebook                    # noqa: E402


@dataclass(frozen=True)
class EmergencyFund:
    """What is needed, what is there, and how far apart those are."""

    monthly_need: int
    base_months: int
    adjusted_months: int
    situation: str
    adjustments: dict
    target: int
    held: int | None
    months_covered: float | None
    recorded_target: int | None

    @property
    def shortfall(self) -> int | None:
        if self.held is None:
            return None
        return max(0, self.target - self.held)

    @property
    def state(self) -> str:
        """One word. `unknown` is a real state, not a failure."""
        if self.months_covered is None:
            return "unknown"
        if self.months_covered >= self.adjusted_months:
            return "funded"
        if self.months_covered >= 3:
            return "partial"
        if self.months_covered >= 1:
            return "thin"
        return "bare"

    def months_to_fill(self, per_month: int) -> int | None:
        """At this contribution, how long until it is full."""
        if self.shortfall is None or per_month <= 0:
            return None
        return -(-self.shortfall // per_month)     # ceiling division


def _adjustments_from_state(state: dict, situation: str) -> list[str]:
    """Read the adjustments off what is actually recorded, instead of a
    human re-picking them by hand every time something on the
    noticeboard changes. Each one only fires off a real, present fact -
    a blank stays silent rather than guessing what is probably true.
    """
    out: list[str] = []
    has_dependants = situation in (
        "single_earner_salaried_with_dependants", "sole_earner_supporting_parents",
    )
    if has_dependants and not (state.get("term_cover_amount") or 0):
        out.append("no_term_life_cover_and_has_dependants")
    if not (state.get("health_cover_amount") or 0):
        out.append("no_personal_health_insurance_outside_employer")
    if state.get("slice_closing_balance"):
        out.append("carrying_a_revolving_credit_line_balance")
    if situation == "sole_earner_supporting_parents" and state.get("parent_has_pension") == "no":
        out.append("supporting_parents_with_no_pension")
    sanctioned = state.get("lamf_sanctioned_limit") or 0
    drawn = state.get("lamf_drawn") or 0
    if sanctioned > drawn:
        out.append("has_a_fully_liquid_backup_such_as_an_undrawn_lamf_limit")
    return out


def compute(
    state: dict | None = None,
    book: Rulebook | None = None,
    situation: str | None = None,
    adjustments: list[str] | None = None,
) -> EmergencyFund:
    """Size the fund from what the noticeboard already knows.

    The monthly need is the bills that do not stop when income does:
    fixed bills, debt service, and the part of living costs that is not
    discretionary. Base SIPs are deliberately excluded - a SIP can be
    paused, and treating it as a fixed obligation inflates the target.

    situation and adjustments default to what the noticeboard says
    (household_situation, term_cover_amount, health_cover_amount, the
    revolving line, the LAMF headroom). Pass either explicitly to run a
    what-if without touching the noticeboard.
    """
    state = read_state() if state is None else state
    book = book or load()
    matrix = book.assumptions["emergency_fund_months"]

    if situation is None:
        situation = state.get("household_situation") or "single_earner_salaried_no_dependants"
    if adjustments is None:
        adjustments = _adjustments_from_state(state, situation)

    fixed = state.get("fixed_bills") or 0
    debt = state.get("debt_service") or 0
    living = state.get("slice_usage_actual") or 0

    # In a month with no income, discretionary spend is cut. The
    # assumptions file says how far; 70% is the conservative end.
    monthly_need = int(fixed + debt + living * 0.70)

    base = matrix["by_situation"].get(situation)
    if base is None:
        raise KeyError(
            f"`{situation}` is not one of the situations in "
            f"india_planning_assumptions.json. Choices are: "
            f"{', '.join(matrix['by_situation'])}"
        )

    applied: dict[str, int] = {}
    for name in adjustments or []:
        delta = matrix["adjustments_in_months"].get(name)
        if delta is None:
            raise KeyError(f"`{name}` is not an adjustment in the assumptions file")
        applied[name] = delta

    months = max(1, base + sum(applied.values()))

    held = state.get("emergency_fund")
    covered = round(held / monthly_need, 1) if (held is not None and monthly_need) else None

    return EmergencyFund(
        monthly_need=monthly_need,
        base_months=base,
        adjusted_months=months,
        situation=situation,
        adjustments=applied,
        target=monthly_need * months,
        held=int(held) if held is not None else None,
        months_covered=covered,
        recorded_target=state.get("emergency_target"),
    )


def main() -> None:
    book = load()
    fund = compute(book=book)

    print("EMERGENCY FUND")
    print("=" * 62)
    print(f"  Monthly need            {format_inr(fund.monthly_need)}")
    print(f"     fixed bills + debt service + 70% of living costs")
    print(f"     SIPs excluded - a SIP can be paused, a bill cannot")
    print()
    print(f"  Months for your situation   {fund.base_months}"
          f"   ({fund.situation.replace('_', ' ')})")
    for name, delta in fund.adjustments.items():
        print(f"     {delta:+d}  {name.replace('_', ' ')}")
    print(f"  Months used                 {fund.adjusted_months}")
    print()
    print(f"  TARGET                  {format_inr(fund.target)}")
    if fund.recorded_target is not None and fund.recorded_target != fund.target:
        print(f"  On the noticeboard      {format_inr(fund.recorded_target)}"
              f"   ({fund.recorded_target / fund.monthly_need:.1f} months)")
    print(f"  HELD                    {format_inr(fund.held)}")
    if fund.months_covered is not None:
        print(f"  COVERS                  {fund.months_covered} months   [{fund.state}]")
        print(f"  SHORT BY                {format_inr(fund.shortfall)}")
    print()
    print("  WHERE IT COULD SIT")
    for row in book.assumptions["where_to_keep_the_emergency_fund"][:4]:
        print(f"    {row['vehicle']:<28} ~{row['typical_return_pct']}%   {row['access']}")
    print()
    print("  These are places, not products. INKY names no bank and no fund (C5).")


if __name__ == "__main__":
    main()
