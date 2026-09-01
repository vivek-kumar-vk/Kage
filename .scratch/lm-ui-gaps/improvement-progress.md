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

### 2026-08-29 — scout auto-wired into the loop (user)
- `run_phase.py` now fires the scout **automatically after every task** via
  `hermes -p ui_gap_scout chat -Q --yolo --in B:/inky_code --query-file …` —
  no orchestrator hand-invocation. Runs on the local model (llama-server :8080),
  behind the resource gate, `--run-budget 1200`, non-fatal on error.
  Manifest toggle `"scout": false` disables it.
- Build cooldown **90 s → 50 s** (user: "45–60 s"); scout adds a 30 s cooldown
  after its own call. run_phase default + all 5 phase manifests updated.
- Purpose (user): overnight test of (a) the local model driving its own
  improvement loop and (b) the Hermes Bot's self-learning across a full run.
- **Next session should check:** did the bot actually write ledger.md /
  prompt-contract.md each task under `--yolo` (fs tools + auto-approve), or did
  it only echo the entry? If echo-only, add explicit fs toolset to config.yaml.
