# ui-gap-scout — improvement progress

Tracks whether the gap-scout **system itself** is getting better: is Model A's
first-try output improving as the prompt-contract sharpens? Is the scout's
tagging getting cleaner? Maintained by the `ui_gap_scout` Hermes Bot each
session (its SOUL.md mandates one improvement per turn).

## Metrics

| date | tasks | first-try-clean % | human-fix % | avg retries | active contract lines | retired this session | note |
|---|---|---|---|---|---|---|---|
| 2026-08-28 | 0 (backfill only) | — | — | — | 7 (seeded) | 0 | v0 contract seeded from the 31-output `finance-telemetry` scan; not yet evidence-tuned |

## Session log

### 2026-08-28 — setup
- Bot profile `ui_gap_scout` created (Hermes Bot Mode), runs on the local model
  (`local-model-a` @ :8080) → zero Claude cost for reviews.
- `ledger.md` seeded with a backfill summary; `prompt-contract.md` v0 has 7
  lines (use-client, token-colours, read-seed, no-chart-lib, reduced-motion,
  patched-Next, one-file-output).
- **Next session should attack:** `reduced-motion-ignored` — the single most
  recurring gap in the backfill (only ~6/31 prior outputs guarded motion).
  Confirm the v0 contract line actually fixes it on the first real task.

### 2026-08-29 — cadence change (user)
- Scout now runs **once per finished task**, not per file, and does a
  **spec-match reconciliation** (delivered vs. ask; deferred vs. drop) plus a
  `carry-forward` line for the next prompt. SOUL.md + README.md updated.
- Orchestrator now **commits once per finished task**.
- Ticket 01 prototype files (P1/P2 done, P3 pending) are prototype scaffold —
  they get one scout pass + one commit when 01 resolves, not three.
