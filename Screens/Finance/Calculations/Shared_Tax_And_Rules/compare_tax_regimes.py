"""Old regime or new regime, worked out rather than guessed.

THE DECISION THIS EXISTS FOR
    Since FY 2023-24 the new regime is the default. It has wider slabs
    and a lower rate at almost every income, and it takes away nearly
    every deduction: 80C, 80D, 80E, and home loan interest on a place
    you live in.

    So the question is never "which regime is better". It is: are your
    deductions worth more than the wider slabs? That is arithmetic, and
    arithmetic is Tier 0.

THE PART PEOPLE GET WRONG
    They compare the regimes on tax alone and forget that a deduction is
    only worth anything if the tax it removes is larger than zero. Under
    the new regime the 87A rebate wipes out all tax up to 12,00,000 of
    taxable income. Below that line the old regime cannot win no matter
    how large the deductions are, because there is nothing left to
    deduct against.

    This file shows that as its answer rather than as a footnote.

WHAT IT WILL NEVER DO
    Tell anybody to buy an ELSS fund, an insurance policy or an NPS
    contribution to fill an 80C basket. It computes what each regime
    costs given deductions somebody already has or has already decided
    to make. Turning a tax calculation into a product recommendation is
    exactly the move C5 exists to prevent.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Shared_Tax_And_Rules\\compare_tax_regimes.py
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
from read_the_india_rulebook import load, Rulebook                    # noqa: E402


# =====================================================================
# WHAT GOES IN
# =====================================================================
@dataclass(frozen=True)
class Deductions:
    """What somebody could claim, if they chose the old regime.

    Every figure defaults to zero, and zero here honestly means zero -
    unlike the noticeboard, where a blank means "nobody has said". This
    is a set of inputs to a what-if, not a record of fact.
    """

    section_80c: int = 0            # EPF + PPF + ELSS + insurance + principal
    section_80ccd_1b: int = 0       # NPS, self, on top of 80C
    section_80ccd_2: int = 0        # NPS, employer - survives into the new regime
    section_80d: int = 0            # health insurance
    section_80e: int = 0            # education loan INTEREST, uncapped
    section_24b: int = 0            # home loan interest, self-occupied
    section_80tta: int = 0          # savings interest


@dataclass(frozen=True)
class RegimeResult:
    """What one regime costs."""

    regime: str
    gross_income: int
    standard_deduction: int
    other_deductions: int
    taxable_income: int
    tax_before_rebate: int
    rebate: int
    surcharge: int
    cess: int
    total_tax: int
    deductions_used: dict = field(default_factory=dict)
    deductions_ignored: dict = field(default_factory=dict)

    @property
    def take_home(self) -> int:
        return self.gross_income - self.total_tax

    @property
    def effective_rate_pct(self) -> float:
        if self.gross_income <= 0:
            return 0.0
        return round(100 * self.total_tax / self.gross_income, 2)


# =====================================================================
# THE SLAB ARITHMETIC
# =====================================================================
def tax_from_slabs(taxable: int, slabs: list[dict]) -> int:
    """Walk the slabs, charging each band only on the part inside it.

    The mistake this avoids is charging the whole income at the rate of
    the band it lands in. Indian slabs are marginal: an income of
    9,00,000 does not pay 10% on all of it.
    """
    if taxable <= 0:
        return 0

    tax = 0.0
    floor = 0
    for slab in slabs:
        ceiling = slab["upto"]
        band_top = taxable if ceiling is None else min(taxable, ceiling)
        if band_top > floor:
            tax += (band_top - floor) * slab["rate_pct"] / 100
            floor = band_top
        if ceiling is not None and taxable <= ceiling:
            break
    return int(round(tax))


def _rebate(taxable: int, tax: int, rules: dict) -> int:
    """Section 87A. Small, and it decides the whole answer under 12 lakh."""
    if not rules:
        return 0
    if taxable <= rules["total_income_upto"]:
        return min(tax, rules["max_rebate"])

    # Marginal relief: just above the line, tax may not exceed the amount
    # by which income crossed it. Without this, earning one rupee more
    # than 12,00,000 would cost 60,000 in tax.
    if rules.get("marginal_relief"):
        excess = taxable - rules["total_income_upto"]
        if tax > excess:
            return tax - excess
    return 0


def _surcharge(taxable: int, tax: int, book: Rulebook, regime: str) -> int:
    """Only bites above 50 lakh. Computed on tax, not on income."""
    rate = 0
    for band in book.tax.get("surcharge", []):
        if taxable > band["income_above"]:
            rate = band["rate_pct"]
    if regime == "new":
        rate = min(rate, 25)
    return int(round(tax * rate / 100))


# =====================================================================
# ONE REGIME
# =====================================================================
def compute_one(
    regime: str,
    gross_income: int,
    deductions: Deductions,
    book: Rulebook,
    is_salaried: bool = True,
) -> RegimeResult:
    """What this regime costs on this income with these deductions."""
    rules = book.tax["regimes"][regime]
    allowed = set(rules.get("deductions_allowed", []))
    limits = book.tax["deduction_limits"]

    std = rules["standard_deduction_salaried"] if is_salaried else 0

    # Each deduction is either allowed in this regime or it is not, and
    # the ones that are not are reported rather than silently dropped -
    # "your 80E was worth nothing here" is the useful half of the answer.
    claimed: dict[str, int] = {}
    ignored: dict[str, int] = {}

    def consider(section: str, amount: int, cap_key: str = "limit") -> None:
        if amount <= 0:
            return
        if section not in allowed:
            ignored[section] = amount
            return
        cap = limits.get(section, {}).get(cap_key)
        claimed[section] = amount if cap is None else min(amount, cap)

    consider("80C", deductions.section_80c)
    consider("80CCD(1B)", deductions.section_80ccd_1b)
    consider("80D", deductions.section_80d, "limit_self_family")
    consider("80E", deductions.section_80e)                 # no cap at all
    consider("24(b)", deductions.section_24b, "limit_self_occupied")
    consider("80TTA", deductions.section_80tta)

    # 80CCD(2) is the employer's NPS contribution and survives into the
    # new regime. It is the only one that does.
    if deductions.section_80ccd_2 > 0:
        if "80CCD(2)" in allowed:
            pct_key = ("limit_pct_of_salary_new_regime" if regime == "new"
                       else "limit_pct_of_salary_old_regime")
            cap = int(gross_income * limits["80CCD(2)"][pct_key] / 100)
            claimed["80CCD(2)"] = min(deductions.section_80ccd_2, cap)
        else:
            ignored["80CCD(2)"] = deductions.section_80ccd_2

    other = sum(claimed.values())
    taxable = max(0, gross_income - std - other)

    before = tax_from_slabs(taxable, rules["slabs"])
    rebate = _rebate(taxable, before, rules.get("rebate_87a", {}))
    after = before - rebate
    surcharge = _surcharge(taxable, after, book, regime)
    cess = int(round((after + surcharge) * book.tax["cess"]["rate_pct"] / 100))

    return RegimeResult(
        regime=regime,
        gross_income=gross_income,
        standard_deduction=std,
        other_deductions=other,
        taxable_income=taxable,
        tax_before_rebate=before,
        rebate=rebate,
        surcharge=surcharge,
        cess=cess,
        total_tax=after + surcharge + cess,
        deductions_used=claimed,
        deductions_ignored=ignored,
    )


# =====================================================================
# BOTH REGIMES, SIDE BY SIDE
# =====================================================================
@dataclass(frozen=True)
class Comparison:
    new: RegimeResult
    old: RegimeResult
    book: Rulebook

    @property
    def cheaper(self) -> str:
        if self.new.total_tax == self.old.total_tax:
            return "same"
        return "new" if self.new.total_tax < self.old.total_tax else "old"

    @property
    def difference(self) -> int:
        return abs(self.new.total_tax - self.old.total_tax)

    @property
    def deductions_were_worthless(self) -> bool:
        """True when the old regime's deductions bought nothing.

        This is the case almost everybody at moderate income is actually
        in and almost nobody realises: the new regime's rebate already
        took the tax to zero, so a deduction has nothing to reduce.
        """
        return self.new.total_tax == 0 and bool(self.old.deductions_used)

    def what_happened(self) -> str:
        """One paragraph, in plain words, with no advice in it."""
        if self.new.total_tax == 0 and self.old.total_tax == 0:
            return (
                "Both regimes come to zero tax on this income. Nothing you "
                "claim or do not claim changes that, so the deduction "
                "question does not arise this year."
            )
        if self.deductions_were_worthless:
            claimed = ", ".join(self.old.deductions_used)
            return (
                f"The new regime already brings the tax to zero, because the "
                f"87A rebate covers taxable income up to "
                f"{format_inr(self.book.tax['regimes']['new']['rebate_87a']['total_income_upto'])}. "
                f"The old regime charges {format_inr(self.old.total_tax)} even "
                f"after using {claimed}. Those deductions are worth nothing "
                f"here - not because they are small, but because there is no "
                f"tax left for them to remove."
            )
        if self.cheaper == "same":
            return "Both regimes come to the same tax on these figures."
        winner = "new" if self.cheaper == "new" else "old"
        return (
            f"The {winner} regime costs {format_inr(self.difference)} less on "
            f"these figures - {format_inr(min(self.new.total_tax, self.old.total_tax))} "
            f"against {format_inr(max(self.new.total_tax, self.old.total_tax))}."
        )

    def break_even_deductions(self) -> int | None:
        """How much deduction the old regime would need to draw level.

        `None` when no amount of deduction can catch up, which is the
        answer whenever the new regime is already at zero.
        """
        if self.new.total_tax == 0:
            return None

        old_rules = self.book.tax["regimes"]["old"]
        std = old_rules["standard_deduction_salaried"]
        target = self.new.total_tax

        # Walk upwards in 1,000 steps. Slabs are step functions, so a
        # closed-form answer would have to special-case every band edge;
        # 1,000 is finer than any decision anybody makes on this.
        for extra in range(0, self.new.gross_income, 1000):
            taxable = max(0, self.new.gross_income - std - extra)
            before = tax_from_slabs(taxable, old_rules["slabs"])
            rebate = _rebate(taxable, before, old_rules.get("rebate_87a", {}))
            after = before - rebate
            total = after + int(round(after * self.book.tax["cess"]["rate_pct"] / 100))
            if total <= target:
                return extra
        return None


def compare(
    gross_income: int,
    deductions: Deductions | None = None,
    book: Rulebook | None = None,
    is_salaried: bool = True,
) -> Comparison:
    book = book or load()
    deductions = deductions or Deductions()
    return Comparison(
        new=compute_one("new", gross_income, deductions, book, is_salaried),
        old=compute_one("old", gross_income, deductions, book, is_salaried),
        book=book,
    )


# =====================================================================
# FROM THE NOTICEBOARD
# =====================================================================
def from_the_noticeboard(state: dict | None = None, book: Rulebook | None = None) -> Comparison | None:
    """The same comparison, on the income INKY already knows about.

    Returns None when income is blank. A blank is not zero - see
    read_and_write_numbers - and inventing an income to have something
    to show would breach Rule 12.

    The education loan interest is worked out from the outstanding
    balance and rate on the noticeboard, because that is the 80E figure
    for somebody who has one. It is an estimate of the FIRST year's
    interest, which is the largest it will ever be.
    """
    state = read_state() if state is None else state
    book = book or load()

    monthly = state.get("income")
    if monthly is None:
        return None

    annual = int(monthly) * 12

    outstanding = state.get("edu_loan_outstanding")
    rate = state.get("edu_loan_rate")
    interest = 0
    if outstanding is not None and rate is not None:
        interest = int(round(outstanding * rate / 100))

    return compare(
        annual,
        Deductions(section_80e=interest),
        book,
    )


# =====================================================================
# WHAT YOU SEE WHEN YOU RUN IT
# =====================================================================
def _print_regime(r: RegimeResult) -> None:
    print(f"    Gross income            {format_inr(r.gross_income):>14}")
    print(f"    Standard deduction      {format_inr(-r.standard_deduction):>14}")
    if r.deductions_used:
        for section, amount in r.deductions_used.items():
            print(f"    {section:<23} {format_inr(-amount):>14}")
    print(f"    Taxable income          {format_inr(r.taxable_income):>14}")
    print(f"    Tax on slabs            {format_inr(r.tax_before_rebate):>14}")
    if r.rebate:
        print(f"    Less 87A rebate         {format_inr(-r.rebate):>14}")
    if r.surcharge:
        print(f"    Surcharge               {format_inr(r.surcharge):>14}")
    print(f"    Cess                    {format_inr(r.cess):>14}")
    print(f"    TOTAL TAX               {format_inr(r.total_tax):>14}"
          f"   ({r.effective_rate_pct}% of gross)")
    if r.deductions_ignored:
        lost = ", ".join(f"{s} {format_inr(a)}" for s, a in r.deductions_ignored.items())
        print(f"    Not claimable here:     {lost}")


def main() -> None:
    book = load()
    comparison = from_the_noticeboard(book=book)

    print("OLD REGIME OR NEW REGIME")
    print("=" * 62)

    if comparison is None:
        print("  `income` is blank on the noticeboard, so there is nothing to")
        print("  compare. A blank is not zero and this will not invent one.")
        return

    print(f"  FY {book.financial_year}   ({book.trust})")
    print()
    print("  NEW REGIME")
    _print_regime(comparison.new)
    print()
    print("  OLD REGIME")
    _print_regime(comparison.old)
    print()
    print("  WHAT THAT MEANS")
    for line in _wrap(comparison.what_happened(), 58):
        print(f"    {line}")

    gap = comparison.break_even_deductions()
    if gap is not None:
        print()
        print(f"    The old regime would need {format_inr(gap)} of deductions")
        print(f"    to draw level.")
    print()
    print("  " + book.note_for_a_reader())


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
