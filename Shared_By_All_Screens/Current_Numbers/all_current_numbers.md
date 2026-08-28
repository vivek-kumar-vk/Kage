---
title: 00_STATE
type: state
updated: 2026-08-09
verified: partial
---

# 00_STATE

Single source of truth. Every computation reads from here.
Blank value = not yet supplied. A blank is honest. A guess is not.
A blank parses as `None`, never as `0` — "unknown" and "zero" are different facts.

Anything unverified is marked `# VERIFY` inline and must be tagged
`[UNVERIFIED]` wherever it surfaces in output (C4).

## ABOUT ME
age:
household_situation:
parent_has_pension:

## CASH
income:
fixed_bills:
debt_service:
base_sips:
slice_usage_actual:
surplus:
before_slice_refill:
                       # i.e. before the Slice refill. A separate figure from surplus, by request -
                       # never blend the two. Computed by calculate_surplus.py

## BUFFERS
emergency_fund:
                           # the actual start of a dedicated account, not just a noticeboard
                           # figure. Row added to Saved_Records/assets_and_liabilities.csv
emergency_target:
                             # target. That one is computed fresh by size_the_emergency_fund.py from
                             # household_situation + parent_has_pension and currently comes out higher;
                             # this is a chosen nearer milestone, see the Protection score for both numbers
emergency_contribution:
                             # What you plan to add to the emergency fund each month.
                             # Blank = not set. emergency_fund below is the one G2
                             # checks, and stays manual - it only rises when money is
                             # actually saved and someone updates it.
buffer_tier_1:
buffer_tier_2:
term_cover_amount:
term_cover_annual_premium:
health_cover_amount:
health_cover_annual_premium:
accident_cover_amount:
accident_cover_annual_premium:

## RETIREMENT
nps_balance:
nps_monthly:
epf_balance:
epf_monthly:

## DEBT
edu_loan_outstanding:
edu_loan_rate:
edu_loan_emi:
uncle_remaining:
uncle_monthly:
slice_limit:
slice_closing_balance:

## PLEDGE
lamf_pledge_value:
lamf_sanctioned_limit:
lamf_drawn:
lamf_annual_fee:

## LEDGERS
restoration_owed:

## MARKET
portfolio_total:

## NET WORTH
total_assets:
total_liabilities:

## MODEL USAGE
inky_cost_usd:
inky_input_tokens:
inky_output_tokens:
claude_code_cost_usd:
claude_code_input_tokens:
claude_code_output_tokens:

## MILESTONES
uncle_debt_clear_date:
edu_loan_payoff_date:

---

## Why `portfolio_total` lives here

The Command tab shows a portfolio figure. That figure will be owned by the
Investments screen, and Finance may not import it (C8). Cross-screen values
pass through this file. Investments writes the key when it is built; Finance
only ever reads it.

Until then it is blank, and the Command screen says so plainly.

## Notes

`slice_usage_actual` is actual spend last month, not the ₹28,000 sanctioned
limit. They happen to be equal right now. That is a coincidence, not a rule.

No daily expense logging. Big or recurring items go in
`Screens/Finance/Saved_Records/big_or_recurring_expenses.csv` by hand. Everything else stays
inside the slice figure.

See [[Guide_To_Finance_Screen]].
