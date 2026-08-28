"""Assembles everything into one report a person can actually read.

WHAT THIS PRODUCES
    Screens/Finance/Saved_Records/Reports/Finance_Report_<month>.md

    Markdown with Obsidian frontmatter and wikilinks (C7), so it opens
    as a note in the vault rather than as a wall of text. One file per
    month, so last month's report survives this month's.

WHY MARKDOWN AND NOT A PDF
    The framework this is adapted from renders a nine-page PDF through
    ReportLab. A PDF is a good deliverable for sending somebody a bill
    and a bad one for a personal system: it cannot be searched with the
    rest of the vault, cannot be linked to, cannot be diffed against
    last month, and needs a library that is not currently installed.

    Everything else in INKY is a flat file you can open and edit. This
    is too.

WHAT IS IN IT AND WHAT IS NOT
    In:  the score and its five parts, the cash-flow arithmetic, both
         debt orders and what each costs, the emergency-fund gap, the
         tax comparison, the FI number, and every assumption underneath.

    Not: any instruction. The report says what is true and what each
         option would cost. It never says which to pick (C5). A section
         of "Top 10 Actions ranked by impact" is exactly what was left
         out of the adaptation, on purpose.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Overview_Tab\\write_the_finance_report.py
"""

from __future__ import annotations

import sys
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


from Shared_By_All_Screens.read_and_write_numbers import read_state          # noqa: E402
from Shared_By_All_Screens.format_indian_money import format_inr, format_lakh, format_signed  # noqa: E402
from Shared_By_All_Screens.mark_unverified_numbers import tag                # noqa: E402
from read_the_india_rulebook import load                                     # noqa: E402
import score_financial_health                                                # noqa: E402
import compare_debt_payoff_strategies                                        # noqa: E402
import compare_tax_regimes                                                   # noqa: E402
import size_the_emergency_fund                                               # noqa: E402
import calculate_financial_independence                                      # noqa: E402
import check_investment_gates                                                # noqa: E402
import read_portfolio_holdings                                               # noqa: E402

REPORTS = SCREEN / "Saved_Records" / "Reports"

# Where each figure came from. A key missing from here renders with
# [UNVERIFIED] next to it, which is the point - the default is "not
# traced", never "probably fine".
SOURCES = {
    "noticeboard": "Shared_By_All_Screens/Current_Numbers/all_current_numbers.md",
    "holdings": "Screens/Finance/Saved_Records/portfolio_holdings.csv",
    "monthly": "Screens/Finance/Saved_Records/monthly_summary_all_months.csv",
}


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _months(n: int) -> str:
    years, rest = divmod(n, 12)
    if years and rest:
        return f"{_plural(years, 'year')} {_plural(rest, 'month')}"
    if years:
        return _plural(years, "year")
    return _plural(rest, "month")


# =====================================================================
# THE REPORT
# =====================================================================
def build(state: dict | None = None, when: str | None = None) -> str:
    state = read_state() if state is None else state
    book = load()
    when = when or date.today().strftime("%Y-%m")

    health = score_financial_health.compute(state=state, book=book)
    debts = compare_debt_payoff_strategies.compare(state=state)
    tax = compare_tax_regimes.from_the_noticeboard(state=state, book=book)
    fund = size_the_emergency_fund.compute(state=state, book=book)
    fi = calculate_financial_independence.compute(state=state, book=book)

    try:
        portfolio = read_portfolio_holdings.a_summary_for_the_screen()
    except Exception:
        portfolio = {"has_data": False}

    nb = SOURCES["noticeboard"]
    out: list[str] = []
    w = out.append

    # ---- frontmatter, so Obsidian treats it as a note (C7) ----------
    w("---")
    w(f"title: Finance Report {when}")
    w("type: report")
    w(f"updated: {date.today().isoformat()}")
    w(f"score: {health.score_out_of_100}")
    w(f"grade: {health.grade}")
    w(f"tax_rules: FY {book.financial_year} ({book.trust})")
    w("verified: partial")
    w("---")
    w("")
    w(f"# Finance Report — {when}")
    w("")
    w("Everything below is computed from files in this repository by plain")
    w("Python. No model was called to produce any of it — Finance is Tier 0")
    w("by design (ADR-040). Where a figure could not be traced to a file it")
    w("carries `[UNVERIFIED]`.")
    w("")
    w("**This report never says what to do.** It says what is true, and what")
    w("each option would cost. Choosing is not INKY's job (C5).")
    w("")

    # =================================================================
    w("## The one number")
    w("")
    if health.score_out_of_100 is None:
        w("Not enough is recorded to score anything yet.")
    else:
        w(f"**{health.score_out_of_100} out of 100 — {health.grade}. "
          f"{health.signal}.**")
        w("")
        w(f"Measured across {health.points_possible} of "
          f"{sum(c.weight for c in health.categories)} possible points "
          f"({health.coverage_pct}% coverage). A category with no data scores")
        w("nothing rather than half marks, so this is a score out of what could")
        w("actually be seen.")
    w("")
    w("| Part | Score | What it is measuring |")
    w("|---|---|---|")
    for c in health.categories:
        cell = f"{c.pct}%" if c.was_measured else "not measured"
        first = c.measured[0] if c.measured else (c.could_not_measure[0] if c.could_not_measure else "")
        w(f"| {c.name} | {cell} | {first} |")
    w("")
    if health.weakest:
        w(f"Lowest of the five is **{health.weakest.name}** at "
          f"{health.weakest.pct}%.")
        w("")

    # =================================================================
    w("## Where the money goes each month")
    w("")
    income = state.get("income")
    surplus = state.get("surplus")
    if income is None:
        w("`income` is blank on the noticeboard, so there is nothing to show.")
    else:
        w("| Line | Amount |")
        w("|---|---|")
        w(f"| Income | {tag(format_inr(income), nb)} |")
        for key, label in (("fixed_bills", "Fixed bills"),
                           ("debt_service", "Debt service"),
                           ("slice_usage_actual", "Living costs (actual)")):
            value = state.get(key)
            if value is not None:
                w(f"| {label} | {tag(format_inr(-value), nb)} |")
        w(f"| **Surplus** | **{tag(format_signed(surplus), nb)}** |")
        w("")
        if surplus is not None and surplus < 0:
            w(f"The surplus is negative by {format_inr(abs(surplus))}. That is not")
            w("a rounding problem — it is the fact everything else in this report")
            w("sits on top of. Nothing downstream can be funded from a surplus that")
            w("does not exist, and INKY does not offer a workaround for it.")
            w("")
        step = state.get("uncle_debt_clear_date")
        if step:
            w(f"That changes in **{step}**, when the family loan clears and the")
            w(f"{format_inr(state.get('uncle_monthly') or 0)} a month it takes stops")
            w("going out.")
            w("")

    # =================================================================
    w("## Debt")
    w("")
    if debts is None:
        w("Nothing owed is recorded.")
    else:
        w(f"**{tag(format_inr(debts.total_owed), nb)} owed across "
          f"{len(debts.debts)} accounts**, costing "
          f"{tag(format_inr(debts.total_minimums), nb)} a month in minimums.")
        w("")
        w("| Owed to | Balance | Rate | Minimum |")
        w("|---|---|---|---|")
        for d in debts.debts:
            rate = f"{d.rate_pct}%" if d.rate_is_known else "not recorded"
            w(f"| {d.name} | {tag(format_inr(d.outstanding), nb)} | {rate} | "
              f"{format_inr(d.minimum)} |")
        w("")
        w("### What the order is worth")
        w("")
        w("Three ways to pay exactly the same debts, with exactly the same")
        w("minimums. The only difference is where any spare money goes and")
        w("whether a cleared debt's payment moves to the next one.")
        w("")
        w("| Way | Clear in | Interest paid |")
        w("|---|---|---|")
        for run in (debts.baseline, debts.avalanche, debts.snowball):
            if not run.converged:
                w(f"| {run.strategy} | never clears | — |")
                continue
            w(f"| {run.strategy} | {_months(run.months)} | "
              f"{format_inr(run.total_interest)} |")
        w("")
        saved = debts.baseline.total_interest - debts.avalanche.total_interest
        faster = debts.baseline.months - debts.avalanche.months
        if saved > 0:
            w(f"Rolling a cleared debt's payment into the next one instead of")
            w(f"letting it stop saves **{format_inr(saved)} of interest and")
            w(f"{faster} months**, with no extra money going in at all. That is")
            w("the whole difference between the first row and the other two.")
            w("")
        w(debts.where_they_disagree())
        w("")

    # =================================================================
    w("## The four gates")
    w("")
    w("These decide whether money may be put into the market this month. They")
    w("run in order and stop at the first `no` — a short list is the point, it")
    w("shows exactly where things halted.")
    w("")
    surplus_now = state.get("surplus")
    if surplus_now is None:
        w("`surplus` is blank, so the gates cannot run.")
    else:
        deployable = surplus_now - (state.get("emergency_contribution") or 0)
        results = check_investment_gates.evaluate(surplus_now, deployable, state)
        w("| Gate | | Reason |")
        w("|---|---|---|")
        for r in results:
            w(f"| {r.gate} | {'PASS' if r.passed else 'FAIL'} | {r.reason} |")
        # evaluate() stops at the first failure, so any gate it never
        # reached is absent from the list rather than present with a
        # made-up answer. Say so instead of leaving a silent gap.
        reached = {r.gate for r in results}
        for name in ("G1", "G2", "G3", "G4"):
            if name not in reached:
                w(f"| {name} | — | not asked, the chain stopped earlier |")
        w("")
        stopped = check_investment_gates.blocked_by(results)
        if stopped:
            w(f"**Blocked at {stopped.gate}: {stopped.reason}** That is correct")
            w("behaviour, not a fault.")
            w("With a negative surplus there is no capital to deploy, so the gates")
            w("below it are not asked — their answers would be noise. INKY offers")
            w("no override and no 'invest anyway' path.")
        else:
            w("All four pass.")
    w("")

    # =================================================================
    w("## Emergency fund")
    w("")
    w(f"| | |")
    w(f"|---|---|")
    w(f"| A month of standing still | {format_inr(fund.monthly_need)} |")
    w(f"| Months this situation calls for | {fund.adjusted_months} |")
    w(f"| Target | **{format_inr(fund.target)}** |")
    w(f"| Held | {tag(format_inr(fund.held), nb)} |")
    if fund.months_covered is not None:
        w(f"| Covers | {fund.months_covered} months |")
        w(f"| Short by | {format_inr(fund.shortfall)} |")
    w("")
    w("The monthly figure is fixed bills plus debt service plus 70% of living")
    w("costs. SIPs are left out — a SIP can be paused, a bill cannot.")
    w("")
    recorded = fund.recorded_target
    if recorded is not None and recorded != fund.target:
        w(f"**These two disagree, and the disagreement is worth reading.** The")
        w(f"noticeboard carries an emergency target of {format_inr(recorded)}, which")
        w(f"is {round(recorded / fund.monthly_need, 1)} months. The framework in")
        w(f"`Reference_Data/india_planning_assumptions.json` says "
          f"{fund.adjusted_months} months for this situation, which is")
        w(f"{format_inr(fund.target)}.")
        w("")
        w("INKY has not overwritten the noticeboard figure and will not. One is a")
        w("number somebody chose deliberately; the other is a framework's default.")
        w("Six months is the Indian floor rather than the American three because")
        w("there is no unemployment insurance here and employer health cover ends")
        w("with the job — but a smaller deliberate target is a decision, not an")
        w("error, and this report is not the place it gets overruled.")
        w("")

    # =================================================================
    w("## Tax — which regime")
    w("")
    if tax is None:
        w("`income` is blank, so there is nothing to compare.")
    else:
        unchecked = None if book.trust != "verified" else book.source_tag
        w("| | New regime | Old regime |")
        w("|---|---|---|")
        w(f"| Gross | {format_inr(tax.new.gross_income)} | "
          f"{format_inr(tax.old.gross_income)} |")
        w(f"| Standard deduction | {format_inr(tax.new.standard_deduction)} | "
          f"{format_inr(tax.old.standard_deduction)} |")
        w(f"| Other deductions | {format_inr(tax.new.other_deductions)} | "
          f"{format_inr(tax.old.other_deductions)} |")
        w(f"| Taxable | {format_inr(tax.new.taxable_income)} | "
          f"{format_inr(tax.old.taxable_income)} |")
        w(f"| **Tax** | **{tag(format_inr(tax.new.total_tax), unchecked)}** | "
          f"**{tag(format_inr(tax.old.total_tax), unchecked)}** |")
        w("")
        w(tax.what_happened())
        w("")
        if tax.old.deductions_used:
            claimed = ", ".join(f"{k} {format_inr(v)}"
                                for k, v in tax.old.deductions_used.items())
            w(f"Deductions applied in the old-regime column: {claimed}.")
            w("")
        w(f"> {book.note_for_a_reader()}")
        w("")

    # =================================================================
    w("## What is invested")
    w("")
    if not portfolio.get("has_data"):
        w("Nothing is recorded in `portfolio_holdings.csv`.")
    else:
        w(f"{portfolio['how_many_holdings']} holdings. Put in "
          f"{tag(format_inr(int(portfolio['total_invested'])), SOURCES['holdings'])}, "
          f"now worth "
          f"{tag(format_inr(int(portfolio['total_current'])), SOURCES['holdings'])} — "
          f"{format_signed(int(portfolio['total_pl']))}.")
        w("")
        w("| Holding | Put in | Worth now | Change |")
        w("|---|---|---|---|")
        for h in portfolio.get("holdings", []):
            w(f"| {h['scheme_name']} | {format_inr(h.get('invested'))} | "
              f"{format_inr(h.get('current'))} | "
              f"{format_signed(h.get('pl_abs'))} |")
        w("")
        w("No view is offered on any of these. INKY displays holdings and")
        w("computes availability; it never rates a fund or suggests a change (C5).")
        w("")

    # =================================================================
    w("## The far end")
    w("")
    w(f"At a {fi.withdrawal_rate_pct}% withdrawal rate — "
      f"{round(100 / fi.withdrawal_rate_pct, 1)}× annual spending, not the")
    w(f"American 25× — covering {format_inr(fi.annual_spend)} a year needs")
    w(f"**{format_lakh(fi.number)}**.")
    w("")
    w("| Withdrawal rate | Corpus needed | Years away |")
    w("|---|---|---|")
    for rate, row in sorted(fi.at_other_rates.items()):
        years = f"{row['years']}" if row["years"] is not None else "not reachable"
        w(f"| {rate}% | {format_lakh(row['number'])} | {years} |")
    w(f"| **{fi.withdrawal_rate_pct}% (used)** | **{format_lakh(fi.number)}** | "
      f"**{fi.years_away if fi.years_away is not None else 'not reachable'}** |")
    w("")
    if fi.invested_now is not None:
        w(f"{format_inr(fi.invested_now)} invested is {fi.progress_pct}% of it.")
        w("")
    w(f"Assumes {book.assumptions['expected_returns_pct']['indian_equity']}% growth")
    w(f"against {book.assumptions['inflation']['general_pct']}% inflation — a real")
    w(f"return of {fi.real_return_pct}%. Every one of those is an assumption in")
    w("`Reference_Data/india_planning_assumptions.json`, not a fact. Change one")
    w("and re-run; that is what the file is for.")
    w("")

    # =================================================================
    w("## What INKY could not see")
    w("")
    w("Listed because a report that only shows what it knows reads as though")
    w("it knows everything.")
    w("")
    missing = []
    for c in health.categories:
        for line in c.could_not_measure:
            missing.append(f"{c.name}: {line}")
    if state.get("slice_closing_balance") in (None, ""):
        missing.append("The revolving credit line's closing balance is blank, so it "
                       "is not in the debt totals at all.")
    if not missing:
        missing.append("Nothing — every category had data.")
    for line in missing:
        w(f"- {line}")
    w("")
    w("Fill these in at `Reference_Data/Human_Checklists/What_To_Fill_In.txt` and re-run.")
    w("")

    # =================================================================
    w("## Where every number came from")
    w("")
    w("| Source | What it gave |")
    w("|---|---|")
    w(f"| `{SOURCES['noticeboard']}` | income, bills, debts, buffers |")
    w(f"| `{SOURCES['holdings']}` | the holdings table |")
    w("| `Screens/Finance/Reference_Data/india_income_tax_rules.json` | slabs, deductions, cess |")
    w("| `Screens/Finance/Reference_Data/india_planning_assumptions.json` | inflation, returns, thresholds |")
    w("")
    w("---")
    w("")
    w("Not advice. INKY computes and displays; every decision here is yours.")
    w("")
    # Guides retired project-wide 2026-08-28 (owner's call) - this note
    # still needs a real wikilink for C7 (Obsidian graph edges), so it
    # points at the rules doc instead of a now-deleted guide.
    w("See [[Rules_And_Decisions_2026-08-26]].")
    w("")

    return "\n".join(out)


def write(state: dict | None = None, when: str | None = None) -> Path:
    when = when or date.today().strftime("%Y-%m")
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"Finance_Report_{when}.md"
    path.write_text(build(state=state, when=when), encoding="utf-8")
    return path


def main() -> None:
    path = write()
    print("FINANCE REPORT")
    print("=" * 62)
    print(f"  Written to  {path.relative_to(PROJECT_ROOT)}")
    print(f"  {len(path.read_text(encoding='utf-8').splitlines())} lines")
    print()
    print("  Opens as an Obsidian note - frontmatter and wikilinks (C7).")


if __name__ == "__main__":
    main()
