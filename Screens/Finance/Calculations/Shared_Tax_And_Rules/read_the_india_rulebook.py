"""Loads the two files in Reference_Data and hands back plain dicts.

WHY THIS FILE EXISTS AT ALL
    Every planning number INKY computes leans on a rate, a limit or an
    assumption. Those could have been typed straight into each
    calculation. They are not, for two reasons.

    C4 says every number traces to a source file or is tagged
    [UNVERIFIED]. A tax slab typed into a Python file traces to nothing.
    A tax slab read from a file that carries its own `source` and
    `as_of` traces to something a person can check.

    And an assumption that is buried is an assumption nobody argues
    with. Putting 6% inflation in a file with the reasoning next to it
    means somebody can disagree, change the one number, and re-run
    everything.

THE TWO FILES ARE DIFFERENT KINDS OF THING
    india_income_tax_rules.json        law. Somebody can look it up.
    india_planning_assumptions.json    judgement. Somebody chose it.

    They are kept apart on purpose, because being wrong about the first
    is a bug and disagreeing with the second is a preference.

STALENESS IS NOT AN ERROR, IT IS A FACT TO REPORT
    Tax slabs change every February. This file will not refuse to work
    when the rulebook is a year old - it reports how old it is and lets
    whatever is showing the number say so. A calculation that refuses to
    run is a calculation nobody runs.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Shared_Tax_And_Rules\\read_the_india_rulebook.py
"""

from __future__ import annotations

import json
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


REFERENCE = SCREEN / "Reference_Data"
TAX_FILE = REFERENCE / "india_income_tax_rules.json"
ASSUMPTIONS_FILE = REFERENCE / "india_planning_assumptions.json"

# A rulebook older than this has almost certainly been through a Union
# Budget. Not an error - a fact the report has to carry.
STALE_AFTER_DAYS = 365


# =====================================================================
# WHAT COMES BACK
# =====================================================================
@dataclass(frozen=True)
class Rulebook:
    """Both files, plus how much they can be trusted.

    `frozen=True` for the same reason every other answer in this project
    is frozen: a rate that can be edited after it was read is a rate
    nobody can trace.
    """

    tax: dict
    assumptions: dict
    financial_year: str
    as_of: str
    source: str
    verified_by_a_person: bool
    days_old: int

    @property
    def is_stale(self) -> bool:
        return self.days_old > STALE_AFTER_DAYS

    @property
    def trust(self) -> str:
        """One word for how much weight a number from here carries.

        Three states, and they are not the same thing:

            verified   somebody opened incometax.gov.in and checked
            unchecked  the file says what it says, nobody confirmed it
            stale      old enough that a Budget has happened since
        """
        if self.is_stale:
            return "stale"
        return "verified" if self.verified_by_a_person else "unchecked"

    @property
    def source_tag(self) -> str | None:
        """What to hand mark_unverified_numbers.tag().

        `None` means "no traceable source", which is what makes the
        shared tagger stamp [UNVERIFIED] on the rendered figure. An
        unchecked rulebook is exactly that: a file somebody typed, not a
        source anybody confirmed.
        """
        if self.trust == "verified":
            return f"{TAX_FILE.name} (FY {self.financial_year}, checked)"
        return None

    def note_for_a_reader(self) -> str:
        """The sentence that goes under any figure derived from here."""
        if self.is_stale:
            return (
                f"Tax figures come from a rulebook written for FY "
                f"{self.financial_year}, last touched {self.as_of} - "
                f"{self.days_old} days ago. At least one Union Budget has "
                f"happened since. Treat every tax number below as out of date "
                f"until Reference_Data is updated."
            )
        if not self.verified_by_a_person:
            return (
                f"Tax figures come from FY {self.financial_year} rates in "
                f"{TAX_FILE.name}. Nobody has checked them against "
                f"incometax.gov.in yet, so they are tagged [UNVERIFIED] "
                f"wherever they appear. Set `verified_by_a_person` to true in "
                f"that file once somebody has."
            )
        return (
            f"Tax figures come from FY {self.financial_year} rates in "
            f"{TAX_FILE.name}, checked against the Finance Act."
        )


# =====================================================================
# READING IT
# =====================================================================
def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"{path.name} is missing from {path.parent}. Every planning "
            f"figure reads from it, so nothing downstream can run without "
            f"it. It is not generated - it is written by hand and lives in "
            f"git."
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as broken:
        raise ValueError(
            f"{path.name} is not valid JSON: {broken}. A half-edited "
            f"rulebook is worse than a missing one, because the half that "
            f"still parses looks fine."
        ) from broken


def _days_since(stamp: str) -> int:
    """How old a YYYY-MM-DD stamp is. Unreadable stamps read as ancient."""
    try:
        return (date.today() - date.fromisoformat(stamp)).days
    except (ValueError, TypeError):
        return 10_000


def load(today: date | None = None) -> Rulebook:
    """Both files, checked for the fields everything downstream needs."""
    tax = _read_json(TAX_FILE)
    assumptions = _read_json(ASSUMPTIONS_FILE)

    for field in ("financial_year", "as_of", "source", "regimes", "cess"):
        if field not in tax:
            raise ValueError(f"{TAX_FILE.name} has no `{field}`")

    for regime in ("new", "old"):
        if regime not in tax["regimes"]:
            raise ValueError(f"{TAX_FILE.name} has no `{regime}` regime")
        if not tax["regimes"][regime].get("slabs"):
            raise ValueError(f"{TAX_FILE.name}: the {regime} regime has no slabs")

    for field in ("inflation", "expected_returns_pct", "safe_withdrawal_rate_pct",
                  "emergency_fund_months", "healthy_ratio_targets",
                  "financial_health_score_weights", "score_bands"):
        if field not in assumptions:
            raise ValueError(f"{ASSUMPTIONS_FILE.name} has no `{field}`")

    stamp = tax["as_of"]
    days = (today - date.fromisoformat(stamp)).days if today else _days_since(stamp)

    return Rulebook(
        tax=tax,
        assumptions=assumptions,
        financial_year=tax["financial_year"],
        as_of=stamp,
        source=tax["source"],
        verified_by_a_person=bool(tax.get("verified_by_a_person", False)),
        days_old=days,
    )


# =====================================================================
# THE SMALL LOOKUPS EVERY OTHER CALCULATION WANTS
# =====================================================================
def grade_for(score: float, book: Rulebook) -> tuple[str, str]:
    """Turn a 0-100 score into a grade and a plain-English signal."""
    for band in book.assumptions["score_bands"]:
        if score >= band["at_least"]:
            return band["grade"], band["signal"]
    return "F", "Foundations not in place yet"


def slabs_for(regime: str, book: Rulebook) -> list[dict]:
    return book.tax["regimes"][regime]["slabs"]


def limit_for(section: str, book: Rulebook, key: str = "limit"):
    """A deduction ceiling. `None` means the section has no ceiling."""
    limits = book.tax.get("deduction_limits", {})
    if section not in limits:
        raise KeyError(f"{TAX_FILE.name} has no deduction limit for {section}")
    return limits[section].get(key)


# =====================================================================
# WHAT YOU SEE WHEN YOU RUN IT
# =====================================================================
def main() -> None:
    book = load()

    print("THE INDIA RULEBOOK")
    print("=" * 62)
    print(f"  Financial year        FY {book.financial_year} (AY {book.tax['assessment_year']})")
    print(f"  Written               {book.as_of}  ({book.days_old} days ago)")
    print(f"  Checked by a person   {'yes' if book.verified_by_a_person else 'no'}")
    print(f"  Trust                 {book.trust}")
    print()
    print(f"  {book.source}")
    print()

    print("  NEW REGIME SLABS")
    for slab in slabs_for("new", book):
        upper = slab["upto"]
        edge = f"up to {upper:,}" if upper else "above the last slab"
        print(f"      {edge:<28} {slab['rate_pct']}%")
    print()

    print("  WHAT THE NEW REGIME GIVES UP")
    old_only = [s for s, d in book.tax["deduction_limits"].items()
                if "old only" in str(d.get("regime", ""))]
    print(f"      {', '.join(old_only)}")
    print()

    a = book.assumptions
    print("  PLANNING ASSUMPTIONS")
    print(f"      Inflation, general       {a['inflation']['general_pct']}%")
    print(f"      Inflation, medical       {a['inflation']['medical_pct']}%")
    print(f"      Indian equity            {a['expected_returns_pct']['indian_equity']}%")
    print(f"      Safe withdrawal rate     {a['safe_withdrawal_rate_pct']['value']}%"
          f"   ({a['safe_withdrawal_rate_pct']['corpus_multiple']}x annual spending)")
    print()
    print("  " + book.note_for_a_reader())


if __name__ == "__main__":
    main()
