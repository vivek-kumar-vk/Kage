# T7 — Model page: data + representation

Type: prototype
Status: open
Blocked by: 02, 06
Blocks: 08

## Question

The deferred design question. Which LiteLLM REST endpoints back which blocks
(`/model/info`, `/v1/models`, `/health`, `/spend/logs`, `/global/spend/report`,
`/user/daily/activity`, `/global/activity`). Block set: models+health table,
usage/cost charts by day/model/provider, request-log viewer, optional test-prompt
box. Master-key-holding backend proxy shape. Mobile layout. Each block reads one
endpoint directly (rule 4). Use `dataviz` for the charts.

## Answer
