Type: grilling
Status: open
Blocked by: —

## Question

Fix the Overview tab's block list, order, and the visualization each block uses.
Seed data only (`app/lib/blueprintSeed.ts`).

Candidate blocks (from the current `OverviewPanel` + `TelemetryPanel` children):

| Block | Source | Current form | Proposed viz |
|---|---|---|---|
| Total Balance | `blueprintSeed.totalBalance` | `TotalBalanceReadout` | line/area + sparkline |
| Cash Flow (income vs expense) | `blueprintSeed.cashFlow` | `CashFlowPanel` | bar / segmented meter |
| Investments | `blueprintSeed.investments.series` | `InvestmentsSpark` | line/area |
| Total Debt | `blueprintSeed.totalDebt` | `DebtReadout` gauge | radial arc |
| Goals | `blueprintSeed.goals` | `GoalsGauges` (RPM) | → replaced by the list, ticket 03 |
| 3-Bucket schematic | `blueprintSeed.buckets` | `BucketSchematic` | segmented fill bars / donut |
| Emergency Fund Tiers | `blueprintSeed.emergencyFund` | `FundTiers` | tier ladder / stacked bar |
| Portfolio value | `blueprintSeed.portfolioValue` | `PortfolioReadout` | donut / ring |
| Gates G1–G4 | `/api/finance/command` (live) | gate strip in `OverviewPanel` | keep / drop / restyle? |
| Health score | `/api/finance/health-score` (live) | ring in `OverviewPanel` | keep / drop / restyle? |
| Surplus formula | `/api/finance/money` (live) | table in `OverviewPanel` | keep / drop / restyle? |

Decide for each: keep / drop / restyle, final order, and the viz. Resolve the
`PulseCore` radar hero (keep re-themed, or drop). Note which blocks are the
"overlap set" that ticket 06 then removes from `TelemetryPanel`.
