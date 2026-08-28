"""Works out when each debt ends.

TWO KINDS OF DEBT, TWO KINDS OF MATHS

  Personal debt (no interest)
      ₹80,000 owed, ₹10,000 a month. Just divide: 8 months.

  Education loan (10.8% interest)
      Cannot be divided. Every payment splits in two — part pays the
      interest that built up this month, the rest reduces what you owe.
      Early on most of it is interest. Later most of it is principal.
      So you step through it month by month. That stepping is called
      AMORTISATION, and it is the only complicated thing in this file.

THE MOST IMPORTANT NUMBER IN THE SYSTEM
      April 2027 — when the personal debt clears.

      That month ₹10,000 stops leaving your account, and nothing takes
      its place. Surplus jumps from -₹1,700 to +₹8,300 overnight. It is
      the leftmost gauge on every screen for that reason.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Debt_Tab\\calculate_debt_dates.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date
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


from Shared_By_All_Screens.read_and_write_numbers import read_state, require   # noqa: E402
from Shared_By_All_Screens.format_indian_money import format_inr, format_signed  # noqa: E402

# A safety net so a bad input cannot loop forever. 100 years.
# Not a rule about loans — just a stop button.
MAX_MONTHS = 1200


def add_months(start: date, n: int) -> date:
    """Month arithmetic on the 1st. Day-of-month is meaningless for a payoff month."""
    total = (start.year * 12 + start.month - 1) + n
    return date(total // 12, total % 12 + 1, 1)


def month_label(d: date) -> str:
    return d.strftime("%b %Y")


# =====================================================================
# LOANS THAT CHARGE INTEREST
# =====================================================================

@dataclass(frozen=True)
class Schedule:
    months: int
    payoff: date
    total_paid: int
    total_interest: int
    rows: list[dict]
    converges: bool = True

    @property
    def payoff_label(self) -> str:
        return month_label(self.payoff) if self.converges else "never"


def amortise(outstanding: float, annual_rate_pct: float, emi: float,
             start: date | None = None, extra: float = 0.0) -> Schedule:
    """Step through the loan one month at a time until it is paid off.

    Each month:
        1. Interest is added on whatever is still owed
        2. Your payment covers that interest first
        3. Whatever is left over reduces the balance

    That is why paying extra helps so much. The extra skips straight to
    step 3 and shrinks the balance, which shrinks every future interest
    charge as well.

    THE TRAP: if the payment is smaller than the first month's interest,
    the balance GROWS every month and the loan never ends. That is
    reported honestly as `converges=False` rather than quietly running
    into the loop limit and printing a date 100 years away.
    """
    start = start or date.today().replace(day=1)
    rate = annual_rate_pct / 12 / 100
    payment = emi + extra
    balance = float(outstanding)

    if payment <= balance * rate:
        return Schedule(0, start, 0, 0, [], converges=False)

    rows, total_interest, total_paid, n = [], 0.0, 0.0, 0

    while balance > 0 and n < MAX_MONTHS:
        n += 1
        interest = balance * rate
        due = min(payment, balance + interest)
        principal = due - interest
        balance -= principal
        if balance < 0.005:
            balance = 0.0
        total_interest += interest
        total_paid += due
        rows.append({
            "n": n,
            "date": add_months(start, n - 1),
            "payment": round(due),
            "interest_component": round(interest),
            "principal_component": round(principal),
            "outstanding": round(balance),
        })

    return Schedule(
        months=n,
        payoff=add_months(start, n - 1),
        total_paid=round(total_paid),
        total_interest=round(total_interest),
        rows=rows,
    )


def extra_payment_effect(outstanding: float, annual_rate_pct: float, emi: float,
                         extra: float, start: date | None = None) -> dict:
    """What paying `extra` every month changes. Answers "what if I pay 2000 more"."""
    base = amortise(outstanding, annual_rate_pct, emi, start)
    faster = amortise(outstanding, annual_rate_pct, emi, start, extra=extra)
    return {
        "base": base,
        "with_extra": faster,
        "months_saved": base.months - faster.months,
        "interest_saved": base.total_interest - faster.total_interest,
    }


# =====================================================================
# DEBTS WITH NO INTEREST
# =====================================================================

@dataclass(frozen=True)
class Countdown:
    remaining: int
    monthly: int
    months_left: int
    clear_date: date

    @property
    def clear_label(self) -> str:
        return month_label(self.clear_date)


def flat_countdown(remaining: int, monthly: int, start: date | None = None) -> Countdown:
    """No interest, so this is just division.

    ₹80,000 at ₹10,000 a month = 8 payments.
    Starting from August 2026, those land Sep, Oct, Nov, Dec, Jan, Feb,
    Mar, Apr — so it clears in April 2027.

    The rounding always goes UP. ₹85,000 at ₹10,000 needs 9 payments,
    not 8.5 — you cannot make half a payment.
    """
    start = start or date.today().replace(day=1)
    # -(-a // b) rounds UP. Plain // rounds down, which would say the
    # debt clears a month before the last payment is actually made.
    months = -(-remaining // monthly)
    return Countdown(remaining, monthly, months, add_months(start, months))


# =====================================================================
# THE JUMP — what happens to surplus when a debt ends
# =====================================================================

@dataclass(frozen=True)
class StepChange:
    date: date
    before: int
    after: int

    @property
    def delta(self) -> int:
        return self.after - self.before

    @property
    def label(self) -> str:
        return month_label(self.date)


def surplus_step_change(current_surplus: int, countdown: Countdown) -> StepChange:
    """How much better things get the month a debt finishes.

    The monthly payment stops leaving your account and nothing replaces
    it, so the entire amount lands in surplus.

        -₹1,700  +  ₹10,000  =  +₹8,300
    """
    return StepChange(countdown.clear_date, current_surplus,
                      current_surplus + countdown.monthly)


# =====================================================================
# WHAT YOU SEE WHEN YOU RUN THIS FILE
# =====================================================================

def main() -> None:
    state = read_state()
    require(state, "edu_loan_outstanding", "edu_loan_rate", "edu_loan_emi",
            "uncle_remaining", "uncle_monthly", "surplus")

    print("PERSONAL DEBT")
    cd = flat_countdown(state["uncle_remaining"], state["uncle_monthly"])
    print(f"  remaining        {format_inr(cd.remaining)}")
    print(f"  monthly          {format_inr(cd.monthly)}")
    print(f"  months left      {cd.months_left}")
    print(f"  clears           {cd.clear_label}")

    step = surplus_step_change(state["surplus"], cd)
    print()
    print(f"  SURPLUS STEP CHANGE on {step.label}")
    print(f"    {format_signed(step.before)}  ->  {format_signed(step.after)}"
          f"   ({format_signed(step.delta)})")

    print()
    print("EDUCATION LOAN")
    sch = amortise(state["edu_loan_outstanding"], state["edu_loan_rate"],
                   state["edu_loan_emi"])
    print(f"  outstanding      {format_inr(state['edu_loan_outstanding'])}")
    print(f"  rate             {state['edu_loan_rate']}% p.a.")
    print(f"  EMI              {format_inr(state['edu_loan_emi'])}")
    print(f"  months left      {sch.months}")
    print(f"  payoff           {sch.payoff_label}")
    print(f"  total interest   {format_inr(sch.total_interest)}")

    print()
    print("  first payment splits as:")
    r = sch.rows[0]
    print(f"    interest       {format_inr(r['interest_component'])}")
    print(f"    principal      {format_inr(r['principal_component'])}")

    print()
    for extra in (2000, 5000):
        e = extra_payment_effect(state["edu_loan_outstanding"], state["edu_loan_rate"],
                                 state["edu_loan_emi"], extra)
        print(f"  pay {format_inr(extra)} more -> {e['with_extra'].payoff_label}"
              f"   ({e['months_saved']} months earlier,"
              f" {format_inr(e['interest_saved'])} interest saved)")


if __name__ == "__main__":
    main()
