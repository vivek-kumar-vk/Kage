# P9 overnight run — 2026-08-29 ~01:00

## What's running

`python run_phase.py phase1.json phase2.json phase3.json` in the background,
authored entirely by the local model (Qwen2.5-Coder-7B-Q4_K_M on
llama-server :8080). 15 tasks, one commit each, 90 s cooldown between.

| Phase | tasks | out |
|---|---|---|
| 1 | DeltaBadge, StatDial, SegmentMeter, TimingRow, TelemetryCard, WipeIn | `app/components/f1/` |
| 2 | TotalBalanceBlock, CashFlowBlock, InvestmentsBlock, DebtBlock, EmergencyFundBlock, BucketBlock, GoalsList | `app/components/overview/` |
| 3 | ReplicaSummary, ReplicaTable | `app/components/investments/` |

Sparkline (Phase 1) already done + hand-fixed (commit `c0b4e6d`; a valid-but-
wrong SVG path the tsc/eslint gate couldn't catch — see ledger).

## Gate per task

`tsc --noEmit` (errors in *that* file only) + `eslint <file>`. ≤2 fix-retries,
then commit. On persistent failure the file reverts to its committed stub and
the task is logged `BLOCKED` — the tree keeps building. `next build` runs at
each phase end.

## Progress / logs

- `.scratch/finance-realism-pass/phase{1,2,3}-progress.md` — timestamped line log
- `.scratch/lm-ui-gaps/ledger.md` — one entry per task (verdict / retries / gate)
- `git log --oneline` — one `P9 Phase N: <id>` commit per passed task
- raw model output: `.scratch/finance-telemetry/raw/<id>.json`

## Morning review checklist

1. `git log --oneline` — count `P9 Phase N:` commits (expect ~15) + any `STUB`.
2. Grep progress files for `BLOCKED` / `EXCEPTION` / `next build rc=` (want rc=0).
3. `cd Screens/Finance/Page/next_app && npm run dev` → open `/`:
   - Overview (Ferrari livery): 7 blocks render, sparkline is a real line,
     dial/meters fill, goals timing rows show bars.
   - Investments (Red Bull livery): summary + holdings table, gains green/red,
     NAV chips, 3 placeholder buttons.
   - nav switches tabs, petals drift (and freeze under reduced-motion).
4. Known follow-ups regardless of run outcome:
   - **Deviation:** Overview dropped the live-endpoint blocks (gates G1–G4,
     health score, surplus formula) — no seed equivalent, deferred to P8.
   - Visual/semantic polish pass (gate can't see layout/optics).
   - Phase 4 (TELEMETRY de-dup) + Phase 5 (delete /theme-lab, log D1.1,
     gap-scout end-of-effort reconcile) — not automated, need a Claude turn.
   - Goal icon slots: `public/goals/<slug>.png` (not wired yet).
   - Total Balance graph left as-is per owner (real data to be wired).

## If it stalled

llama-server down → harness auto-restarts it (`llama_cmd` in each manifest).
If the whole run died: re-run `python .scratch/finance-telemetry/run_phase.py`
with whichever `phaseN.json` still have unbuilt tasks (already-committed tasks
will just be rebuilt identically — safe, but edit the manifest to drop them to
save time).
