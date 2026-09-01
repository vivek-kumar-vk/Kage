Type: grilling
Status: open
Blocked by: 02

## Question

Once the Overview tab carries the summary visualizations (ticket 02 output),
decide what the `TELEMETRY` tab keeps.

- Which `TelemetryPanel` children are now duplicated on Overview and get
  **removed** from `TelemetryPanel` (`PulseCore`, `BucketSchematic`,
  `CashFlowPanel`, `GoalsGauges`, `InvestmentsSpark`, `DebtReadout`,
  `PortfolioReadout`)?
- Does anything stay as a deeper drill-down, or does the tab (and the nav entry)
  get removed entirely? (ties to ticket 04's nav question.)
- Strip the seed/endpoint disclaimer strings from this tab's UI too (same as
  D-e).
- If the tab stays: does it inherit the ticket-01 theme now, or is that the
  follow-up effort?
