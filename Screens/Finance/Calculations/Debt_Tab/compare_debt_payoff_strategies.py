"""Two orders for paying off the same debts, and what each one costs.

THE TWO ORDERS
    AVALANCHE   highest interest rate first. Costs the least.
    SNOWBALL    smallest balance first. Clears an account soonest.

    Both pay every minimum every month. The only question is where the
    spare money goes on top. That single choice changes the total
    interest and the date the last debt clears, and this file works out
    by how much.

WHY THIS IS NOT A RECOMMENDATION
    C5. INKY computes and displays; it does not tell anybody what to do.
    The two orders are shown with their real costs side by side, and the
    place where they disagree is named. Which one somebody picks is
    theirs to pick.

    That matters more here than usual, because the standard framework
    imported from American personal finance quietly assumes every debt
    is an arm's-length loan with a rate on it. A 0% loan from a relative
    breaks the arithmetic in a specific way: avalanche sorts it LAST,
    because 0% is the cheapest money in the list, and snowball often
    sorts it FIRST, because it is usually the smallest. The gap between
    those two answers is not a number - it is a relationship. This file
    says so and then stops.

WHAT IT READS
    The noticeboard, for the debts INKY already knows about, and
    debt_payments_record.csv for anything logged there. Nothing is
    invented: a debt with no rate is carried as a debt with no rate and
    reported that way, never as 0% because 0 was convenient.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Debt_Tab\\compare_debt_payoff_strategies.py
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, replace
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

LEDGER = SCREEN / "Saved_Records" / "debt_payments_record.csv"

# A run that has not finished after this long has not converged - almost
# always a minimum smaller than the monthly interest, which never clears.
MAX_MONTHS = 600


# =====================================================================
# ONE DEBT
# =====================================================================
@dataclass(frozen=True)
class Debt:
    """One thing owed.

    `rate_pct` may be None, and that is different from 0.0. None means
    nobody has recorded a rate; 0.0 means somebody recorded that there
    is no interest. A family loan is usually the second. Treating the
    first as the second is how a debt gets sorted to the back of an
    avalanche queue because of a missing field.
    """

    name: str
    outstanding: int
    rate_pct: float | None
    minimum: int
    kind: str = "loan"
    note: str = ""

    @property
    def monthly_rate(self) -> float:
        return (self.rate_pct or 0.0) / 100 / 12

    @property
    def rate_is_known(self) -> bool:
        return self.rate_pct is not None

    @property
    def is_interest_free(self) -> bool:
        return self.rate_pct == 0.0

    @property
    def monthly_interest(self) -> int:
        return int(round(self.outstanding * self.monthly_rate))


@dataclass(frozen=True)
class Run:
    """What one order of payoff produced."""

    strategy: str
    months: int
    total_interest: int
    total_paid: int
    order: list[str]
    cleared_in_month: dict[str, int]
    converged: bool = True

    @property
    def first_cleared(self) -> tuple[str, int] | None:
        if not self.cleared_in_month:
            return None
        name = min(self.cleared_in_month, key=lambda k: self.cleared_in_month[k])
        return name, self.cleared_in_month[name]


# =====================================================================
# THE SIMULATION
# =====================================================================
def _simulate(debts: list[Debt], extra_per_month: int, order_key, roll: bool = True) -> Run:
    """Run the months forward, paying minimums plus the spare on one debt.

    Written as a month-by-month loop rather than a closed-form formula
    on purpose. The rolled payment - a cleared debt's minimum joining
    the spare money for the next one - is the whole reason these
    strategies beat paying minimums, and it is much easier to be sure a
    loop does it right than a formula.

    `roll=False` turns that off, which is what makes the do-nothing
    baseline an actual baseline: when a debt clears, its payment leaves
    the plan instead of moving to the next debt. Getting this wrong once
    made the baseline identical to both strategies and the whole
    comparison show a saving of zero.
    """
    live = {d.name: d.outstanding for d in debts}
    by_name = {d.name: d for d in debts}
    interest_paid = 0.0
    paid = 0.0
    cleared: dict[str, int] = {}

    month = 0
    while any(bal > 0 for bal in live.values()) and month < MAX_MONTHS:
        month += 1

        # Interest first, on what is owed at the start of the month.
        for name, bal in live.items():
            if bal > 0:
                charge = bal * by_name[name].monthly_rate
                live[name] = bal + charge
                interest_paid += charge

        # The pot: every minimum, plus the spare. When rolling, a cleared
        # debt's minimum stays in the pot and moves to the next debt -
        # that rolling is what makes either strategy beat doing nothing.
        pot = float(extra_per_month)
        for name, bal in live.items():
            if bal > 0 or roll:
                pot += by_name[name].minimum

        # Minimums go out first, so nothing falls behind.
        for name, bal in live.items():
            if bal <= 0:
                continue
            pay = min(by_name[name].minimum, bal)
            live[name] = bal - pay
            pot -= pay
            paid += pay
            if live[name] <= 0.005:
                live[name] = 0.0
                cleared.setdefault(name, month)

        # Everything left over goes to whichever debt the strategy picks.
        remaining = [n for n, b in live.items() if b > 0]
        while pot > 0.005 and remaining:
            target = sorted(remaining, key=lambda n: order_key(by_name[n]))[0]
            pay = min(pot, live[target])
            live[target] -= pay
            pot -= pay
            paid += pay
            if live[target] <= 0.005:
                live[target] = 0.0
                cleared.setdefault(target, month)
                remaining.remove(target)

    converged = all(bal <= 0.005 for bal in live.values())
    ordered = sorted(cleared, key=lambda n: cleared[n])

    return Run(
        strategy="",
        months=month,
        total_interest=int(round(interest_paid)),
        total_paid=int(round(paid)),
        order=ordered,
        cleared_in_month=cleared,
        converged=converged,
    )


def avalanche(debts: list[Debt], extra: int) -> Run:
    """Highest rate first. A debt with no recorded rate sorts as unknown
    and is placed after every known rate rather than treated as 0%."""
    def key(d: Debt):
        return (0 if d.rate_is_known else 1, -(d.rate_pct or 0.0), d.outstanding)
    return replace(_simulate(debts, extra, key), strategy="avalanche")


def snowball(debts: list[Debt], extra: int) -> Run:
    """Smallest balance first."""
    return replace(_simulate(debts, extra, lambda d: d.outstanding), strategy="snowball")


def minimums_only(debts: list[Debt]) -> Run:
    """The do-nothing baseline, so the other two have something to beat.

    Nothing extra goes in, and a cleared debt's payment does NOT move to
    the next one - it just stops. That is what actually happens to most
    people, and it is the only fair thing for the two strategies to be
    measured against.
    """
    return replace(
        _simulate(debts, 0, lambda d: d.outstanding, roll=False),
        strategy="minimums only",
    )


# =====================================================================
# READING THE DEBTS INKY ALREADY KNOWS ABOUT
# =====================================================================
def debts_from_the_noticeboard(state: dict | None = None) -> list[Debt]:
    """Everything owed, from the noticeboard and the debt ledger.

    A blank figure is skipped, never defaulted. The revolving line is
    only included when a closing balance has actually been recorded -
    the sanctioned limit is not a debt, and using the limit would invent
    28,000 of borrowing that may not exist.
    """
    state = read_state() if state is None else state
    found: list[Debt] = []

    outstanding = state.get("edu_loan_outstanding")
    if outstanding is not None:
        found.append(Debt(
            name="Education loan",
            outstanding=int(outstanding),
            rate_pct=state.get("edu_loan_rate"),
            minimum=int(state.get("edu_loan_emi") or 0),
            kind="education_loan",
            note="Interest qualifies for 80E, but only under the old regime - "
                 "see compare_tax_regimes.py before assuming that is worth anything.",
        ))

    uncle = state.get("uncle_remaining")
    if uncle is not None:
        found.append(Debt(
            name="Family loan",
            outstanding=int(uncle),
            rate_pct=0.0,          # recorded as interest-free, not missing
            minimum=int(state.get("uncle_monthly") or 0),
            kind="family",
            note="Interest-free. The arithmetic sorts it last; the "
                 "relationship is not in the arithmetic.",
        ))

    closing = state.get("slice_closing_balance")
    if closing:
        found.append(Debt(
            name="Revolving credit line",
            outstanding=int(closing),
            rate_pct=state.get("slice_rate"),
            minimum=int(state.get("slice_minimum") or 0),
            kind="revolving",
        ))

    # Anything logged in the ledger that the noticeboard did not name.
    if LEDGER.is_file():
        known = {d.name.lower() for d in found}
        latest: dict[str, dict] = {}
        with LEDGER.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                account = (row.get("account") or "").strip()
                if account:
                    latest[account] = row          # last row per account wins
        for account, row in latest.items():
            if account.lower() in known:
                continue
            try:
                balance = int(float(row["outstanding"]))
            except (TypeError, ValueError, KeyError):
                continue
            if balance <= 0:
                continue
            try:
                rate = float(row["rate_pct"]) if row.get("rate_pct") else None
            except ValueError:
                rate = None
            try:
                payment = int(float(row.get("payment") or 0))
            except ValueError:
                payment = 0
            found.append(Debt(account, balance, rate, payment, kind="logged"))

    return found


# =====================================================================
# THE COMPARISON
# =====================================================================
@dataclass(frozen=True)
class Comparison:
    debts: list[Debt]
    extra_per_month: int
    avalanche: Run
    snowball: Run
    baseline: Run

    @property
    def total_owed(self) -> int:
        return sum(d.outstanding for d in self.debts)

    @property
    def total_minimums(self) -> int:
        return sum(d.minimum for d in self.debts)

    @property
    def weighted_rate_pct(self) -> float | None:
        """Average rate, weighted by size. None if any rate is unknown."""
        if not self.debts or any(not d.rate_is_known for d in self.debts):
            return None
        owed = self.total_owed
        if owed == 0:
            return 0.0
        return round(sum(d.outstanding * (d.rate_pct or 0) for d in self.debts) / owed, 2)

    @property
    def interest_saved_by_avalanche(self) -> int:
        return self.snowball.total_interest - self.avalanche.total_interest

    @property
    def months_sooner_first_clear(self) -> int:
        a, s = self.avalanche.first_cleared, self.snowball.first_cleared
        if not a or not s:
            return 0
        return a[1] - s[1]

    @property
    def they_agree(self) -> bool:
        return self.avalanche.order == self.snowball.order

    def where_they_disagree(self) -> str:
        """The sentence that carries the actual decision."""
        if self.they_agree:
            return (
                "Both orders clear the debts in the same sequence, so there "
                "is nothing to choose between them here. The order is not "
                "the decision - the amount going in on top of the minimums is."
            )

        free = [d for d in self.debts if d.is_interest_free]
        lines = [
            f"The two orders disagree. Avalanche clears "
            f"{' then '.join(self.avalanche.order)}; snowball clears "
            f"{' then '.join(self.snowball.order)}."
        ]
        if self.interest_saved_by_avalanche > 0:
            lines.append(
                f"Avalanche costs {format_inr(self.interest_saved_by_avalanche)} "
                f"less in interest over the whole run."
            )
        elif self.interest_saved_by_avalanche < 0:
            lines.append(
                f"Snowball happens to cost "
                f"{format_inr(-self.interest_saved_by_avalanche)} less here, "
                f"which is unusual and worth checking the inputs for."
            )
        if self.months_sooner_first_clear > 0:
            lines.append(
                f"Snowball clears its first account "
                f"{self.months_sooner_first_clear} months sooner."
            )
        if free:
            names = " and ".join(d.name for d in free)
            lines.append(
                f"{names} carries no interest, which is why the two orders "
                f"split: to the arithmetic it is the cheapest money you have "
                f"and goes last. Whether that is true of a loan from a person "
                f"is not something a calculation can tell you."
            )
        return " ".join(lines)


def compare(
    debts: list[Debt] | None = None,
    extra_per_month: int | None = None,
    state: dict | None = None,
) -> Comparison | None:
    """Both orders on the same debts. None when there is nothing to run."""
    state = read_state() if state is None else state
    debts = debts_from_the_noticeboard(state) if debts is None else debts
    if not debts:
        return None

    if extra_per_month is None:
        # Only genuinely spare money. A negative surplus means there is
        # nothing on top of the minimums, which is a real answer.
        surplus = state.get("surplus")
        extra_per_month = max(0, int(surplus)) if surplus is not None else 0

    return Comparison(
        debts=debts,
        extra_per_month=extra_per_month,
        avalanche=avalanche(debts, extra_per_month),
        snowball=snowball(debts, extra_per_month),
        baseline=minimums_only(debts),
    )


# =====================================================================
# WHAT YOU SEE WHEN YOU RUN IT
# =====================================================================
def _print_run(run: Run) -> None:
    if not run.converged:
        print(f"    {run.strategy:<16} never clears - a minimum is smaller "
              f"than the monthly interest")
        return
    years, months = divmod(run.months, 12)
    when = f"{years}y {months}m" if years else f"{months}m"
    print(f"    {run.strategy:<16} {when:<8} "
          f"interest {format_inr(run.total_interest):>12}   "
          f"{' -> '.join(run.order)}")


def main() -> None:
    result = compare()

    print("TWO WAYS TO PAY THE SAME DEBTS")
    print("=" * 62)

    if result is None:
        print("  Nothing owed is recorded on the noticeboard, so there is")
        print("  nothing to compare. That is an answer, not an error.")
        return

    print(f"  Owed in total       {format_inr(result.total_owed)}")
    print(f"  Minimums a month    {format_inr(result.total_minimums)}")
    rate = result.weighted_rate_pct
    print(f"  Weighted rate       "
          f"{str(rate) + '%' if rate is not None else 'not known - a rate is missing'}")
    print(f"  Spare on top        {format_inr(result.extra_per_month)}")
    if result.extra_per_month == 0:
        print("                      (surplus is not positive, so there is none)")
    print()

    print("  WHAT IS OWED")
    for d in result.debts:
        rate_text = f"{d.rate_pct}%" if d.rate_is_known else "rate not recorded"
        print(f"    {d.name:<24} {format_inr(d.outstanding):>12}  "
              f"{rate_text:<18} min {format_inr(d.minimum)}")
    print()

    print("  HOW IT PLAYS OUT")
    _print_run(result.baseline)
    _print_run(result.avalanche)
    _print_run(result.snowball)
    print()

    print("  WHERE THEY DIFFER")
    for line in _wrap(result.where_they_disagree(), 58):
        print(f"    {line}")


def _wrap(text: str, width: int) -> list[str]:
    words, lines, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return lines


if __name__ == "__main__":
    main()
