"""One number out of 100 for the state of the money, and the five it is made of.

WHAT A SCORE IS FOR
    Not a verdict. A way of noticing that four things are fine and one
    is not, without reading five reports. The five parts are always
    shown next to the total, because the total on its own hides which
    part moved.

THE ONE RULE THAT MAKES IT HONEST
    A category with no data scores nothing and says so. It never gets a
    middling default.

    That is the trap in every scoring framework: a missing input quietly
    becomes half marks, the total looks like a measurement, and nobody
    can tell the difference between "this is average" and "nobody has
    checked". INKY reports the score out of the points it could actually
    measure, and states how many that was. Rule 12, applied to a number
    rather than to a table.

WHAT WAS CHANGED FROM THE FRAMEWORK THIS COMES FROM
    The five-category, twenty-points-each shape is kept. Every threshold
    underneath it is Indian and lives in
    Reference_Data/india_planning_assumptions.json:

        DTI            -> FOIR, which is what an Indian lender computes
        3-6 months     -> 6-12 months, no unemployment insurance here
        401k / IRA     -> EPF, NPS, PPF
        4% withdrawal  -> 3.25%
        percentile vs national net worth -> dropped entirely, because
                          the Indian household data to do it honestly
                          does not exist and inventing it breaks C4

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Overview_Tab\\score_financial_health.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
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
from read_the_india_rulebook import load, Rulebook, grade_for         # noqa: E402
import size_the_emergency_fund                                        # noqa: E402
import compare_debt_payoff_strategies                                 # noqa: E402
import read_portfolio_holdings                                        # noqa: E402


@dataclass(frozen=True)
class Category:
    """One of the five, scored out of its own weight."""

    name: str
    weight: int
    scored: float | None          # None = could not be measured
    measured: list[str] = field(default_factory=list)
    could_not_measure: list[str] = field(default_factory=list)

    @property
    def was_measured(self) -> bool:
        return self.scored is not None

    @property
    def out_of(self) -> int:
        return self.weight

    @property
    def pct(self) -> float | None:
        if self.scored is None:
            return None
        return round(100 * self.scored / self.weight, 1)


@dataclass(frozen=True)
class Health:
    """The whole picture."""

    categories: list[Category]
    points_scored: float
    points_possible: int
    score_out_of_100: float | None
    grade: str
    signal: str

    @property
    def measured_categories(self) -> list[Category]:
        return [c for c in self.categories if c.was_measured]

    @property
    def unmeasured_categories(self) -> list[Category]:
        return [c for c in self.categories if not c.was_measured]

    @property
    def coverage_pct(self) -> int:
        total = sum(c.weight for c in self.categories)
        return int(round(100 * self.points_possible / total)) if total else 0

    @property
    def weakest(self) -> Category | None:
        scored = [c for c in self.measured_categories]
        return min(scored, key=lambda c: c.pct) if scored else None


# =====================================================================
# A SMALL HELPER FOR SCORING A RATIO AGAINST BANDS
# =====================================================================
def _band_score(value: float, points: float, healthy: float,
                fair: float, weak: float, higher_is_better: bool = True) -> float:
    """Straight-line score between the weak and healthy thresholds.

    Deliberately not a step function. A FOIR of 40.1% and 39.9% are the
    same situation, and a score that jumps four points between them
    invites arguing with the score instead of reading it.
    """
    if higher_is_better:
        if value >= healthy:
            return points
        if value <= weak:
            return 0.0
        return round(points * (value - weak) / (healthy - weak), 2)
    if value <= healthy:
        return points
    if value >= weak:
        return 0.0
    return round(points * (weak - value) / (weak - healthy), 2)


# =====================================================================
# THE FIVE
# =====================================================================
def _cash_flow(state: dict, book: Rulebook, weight: int) -> Category:
    """Does more come in than goes out, and how much is kept."""
    targets = book.assumptions["healthy_ratio_targets"]["savings_rate_pct"]
    income = state.get("income")
    surplus = state.get("surplus")

    if income is None or surplus is None or income <= 0:
        return Category("Cash flow", weight, None,
                        could_not_measure=["`income` or `surplus` is blank"])

    rate = round(100 * surplus / income, 1)

    # Half the weight on the sign of the surplus, half on its size. A
    # negative surplus is not a small positive one - it is the single
    # fact that decides everything downstream, so it scores zero on both
    # halves rather than being averaged into looking survivable.
    positive = weight / 2 if surplus > 0 else 0.0
    size = _band_score(rate, weight / 2,
                       healthy=targets["healthy_at_or_above"],
                       fair=targets["fair_below"],
                       weak=0)

    return Category(
        "Cash flow", weight, round(positive + size, 2),
        measured=[
            f"Surplus {format_inr(surplus)} a month",
            f"Savings rate {rate}% (healthy is {targets['healthy_at_or_above']}%+)",
        ],
    )


def _debt(state: dict, book: Rulebook, weight: int) -> Category:
    """How much of the income is already spoken for."""
    foir_targets = book.assumptions["healthy_ratio_targets"]["foir_pct"]
    income = state.get("income")
    fixed = state.get("fixed_bills")
    service = state.get("debt_service")

    if income is None or service is None or income <= 0:
        return Category("Debt", weight, None,
                        could_not_measure=["`income` or `debt_service` is blank"])

    # FOIR, not DTI: every fixed monthly obligation over income. This is
    # the ratio an Indian lender actually computes.
    obligations = service + (fixed or 0)
    foir = round(100 * obligations / income, 1)

    score = _band_score(foir, weight,
                        healthy=foir_targets["healthy_at_or_below"],
                        fair=foir_targets["watch_above"],
                        weak=foir_targets["critical_above"],
                        higher_is_better=False)

    measured = [
        f"FOIR {foir}% - fixed obligations {format_inr(obligations)} "
        f"against income {format_inr(income)}",
        f"Healthy is {foir_targets['healthy_at_or_below']}% or under; "
        f"{foir_targets['critical_above']}%+ is where lenders stop",
    ]

    comparison = compare_debt_payoff_strategies.compare(state=state)
    if comparison:
        measured.append(
            f"Owed {format_inr(comparison.total_owed)} across "
            f"{len(comparison.debts)} accounts"
        )

    return Category("Debt", weight, score, measured=measured)


def _protection(state: dict, book: Rulebook, weight: int) -> Category:
    """What happens if the income stops.

    Only the emergency fund is scored. Term life and health cover belong
    here too and INKY holds no record of either, so rather than assume
    they are absent - which would be inventing a fact - the category
    reports them as unmeasured and scores out of what it could see.
    """
    fund = size_the_emergency_fund.compute(state=state, book=book)

    if fund.months_covered is None:
        return Category("Protection", weight, None,
                        could_not_measure=["`emergency_fund` is blank"])

    covered = fund.months_covered
    target = fund.adjusted_months

    score = _band_score(covered, weight, healthy=target, fair=3, weak=0)

    term = state.get("term_cover_amount")
    if term is None:
        term_note = "Term life cover - INKY holds no record of it"
    elif term == 0:
        term_note = "No term life cover (confirmed) - already folded into the target above"
    else:
        term_note = f"Term life cover of {format_inr(int(term))} recorded, not yet scored"

    health = state.get("health_cover_amount")
    if not health:
        health_note = "Health insurance outside an employer - no record either"
    else:
        health_note = f"Health cover of {format_inr(int(health))} recorded, not yet scored"

    return Category(
        "Protection", weight, score,
        measured=[
            f"Emergency fund covers {covered} months of the "
            f"{format_inr(fund.monthly_need)} it would take to stand still",
            f"Target for this situation is {target} months "
            f"({format_inr(fund.target)})",
        ],
        could_not_measure=[term_note, health_note],
    )


def _investing(state: dict, book: Rulebook, weight: int) -> Category:
    """Is money going in, and is anything there."""
    sips = state.get("base_sips")

    try:
        portfolio = read_portfolio_holdings.a_summary_for_the_screen()
    except Exception:
        portfolio = {"has_data": False}

    if sips is None and not portfolio.get("has_data"):
        return Category("Investing", weight, None,
                        could_not_measure=["No SIPs recorded and no holdings recorded"])

    measured = []
    score = 0.0

    # Half for something being invested at all.
    if portfolio.get("has_data") and portfolio.get("total_current"):
        score += weight / 2
        measured.append(
            f"{portfolio['how_many_holdings']} holdings worth "
            f"{format_inr(int(portfolio['total_current']))} "
            f"(put in {format_inr(int(portfolio['total_invested']))})"
        )

    # Half for money still going in, scaled against income.
    income = state.get("income")
    if sips is not None and income:
        sip_rate = round(100 * sips / income, 1)
        score += _band_score(sip_rate, weight / 2, healthy=15, fair=10, weak=0)
        measured.append(f"{format_inr(sips)} a month going in - {sip_rate}% of income")

    return Category("Investing", weight, round(score, 2), measured=measured)


def _future_security(state: dict, book: Rulebook, weight: int) -> Category:
    """How far along the road to work being optional.

    Scored on progress towards the FI number, which is the only
    forward-looking measure INKY can compute without asking for an age,
    an EPF balance or an NPS balance - none of which it holds.
    """
    import calculate_financial_independence as fi_module

    fi = fi_module.compute(state=state, book=book)

    if fi.invested_now is None:
        return Category("Future security", weight, None,
                        could_not_measure=["Nothing invested is recorded"])

    progress = fi.progress_pct or 0.0

    # 25% of the way is full marks here, on purpose. This is a measure of
    # having started and kept going, not of being finished - somebody
    # 25% of the way to a 30x corpus is doing the thing that works.
    score = _band_score(progress, weight, healthy=25, fair=10, weak=0)

    measured = [
        f"{progress}% of the way to {format_inr(fi.number)}",
        f"That number is {round(100 / fi.withdrawal_rate_pct, 1)}x annual spending "
        f"at a {fi.withdrawal_rate_pct}% withdrawal rate",
    ]
    if fi.years_away is not None:
        measured.append(f"{fi.years_away} years away at the current rate of saving")

    return Category(
        "Future security", weight, score, measured=measured,
        could_not_measure=[
            "EPF balance - INKY holds no record of it",
            "NPS balance - no record either",
        ],
    )


# =====================================================================
# PUTTING THE FIVE TOGETHER
# =====================================================================
def compute(state: dict | None = None, book: Rulebook | None = None) -> Health:
    state = read_state() if state is None else state
    book = book or load()
    weights = book.assumptions["financial_health_score_weights"]

    categories = [
        _cash_flow(state, book, weights["cash_flow"]),
        _debt(state, book, weights["debt"]),
        _protection(state, book, weights["protection"]),
        _investing(state, book, weights["investing"]),
        _future_security(state, book, weights["future_security"]),
    ]

    scored = sum(c.scored for c in categories if c.was_measured)
    possible = sum(c.weight for c in categories if c.was_measured)

    # Scaled to 100 over the points that could actually be measured, so a
    # missing category lowers confidence rather than lowering the score.
    out_of_100 = round(100 * scored / possible, 1) if possible else None
    grade, signal = grade_for(out_of_100, book) if out_of_100 is not None else ("-", "Not enough recorded to score")

    return Health(
        categories=categories,
        points_scored=round(scored, 2),
        points_possible=possible,
        score_out_of_100=out_of_100,
        grade=grade,
        signal=signal,
    )


# =====================================================================
# WHAT YOU SEE WHEN YOU RUN IT
# =====================================================================
def _bar(pct: float | None, width: int = 20) -> str:
    if pct is None:
        return "?" * width
    filled = int(round(width * pct / 100))
    return "#" * filled + "." * (width - filled)


def main() -> None:
    book = load()
    health = compute(book=book)

    print("FINANCIAL HEALTH")
    print("=" * 62)
    if health.score_out_of_100 is None:
        print("  Not enough is recorded to score anything yet.")
    else:
        print(f"  SCORE   {health.score_out_of_100} / 100      {health.grade}   {health.signal}")
        print(f"          measured {health.points_possible} of "
              f"{sum(c.weight for c in health.categories)} points "
              f"({health.coverage_pct}% coverage)")
    print()

    for c in health.categories:
        head = f"{c.pct}%" if c.was_measured else "not measured"
        print(f"  {c.name:<18} {_bar(c.pct)}  {head}")
        for line in c.measured:
            print(f"        {line}")
        for line in c.could_not_measure:
            print(f"        (not counted) {line}")
        print()

    weakest = health.weakest
    if weakest:
        print(f"  Lowest of the five: {weakest.name} at {weakest.pct}%.")
    if health.unmeasured_categories:
        names = ", ".join(c.name for c in health.unmeasured_categories)
        print(f"  Scored out of {health.points_possible} points, not 100 - "
              f"{names} had nothing to measure.")
    print()
    print("  A score is a way of noticing which part moved. It is not a verdict,")
    print("  and INKY does not turn it into instructions (C5).")


if __name__ == "__main__":
    main()
