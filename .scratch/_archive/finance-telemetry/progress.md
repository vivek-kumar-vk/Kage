> **STATUS: SUPERSEDED (archived 2026-08-30).** The 19-task telemetry skin + the
> unbuilt X1–X9 replica are both orphaned by the finance-os V1 cutover (`657774d`).
> Target tree `Screens/Finance/Page/next_app/` no longer serves Finance. History only.
> The shared build harness (`run_phase.py`, `run_task.py`, `bump.py`, `lm_chores.py`)
> stays live at `.scratch/finance-telemetry/` — see `HARNESS.md` there.

# Finance Telemetry — build progress

**Orchestrator:** Claude (Sonnet) · **Code author:** Model A `qwen2.5-coder-7b-instruct-q5_k_m` @ `http://127.0.0.1:8080`
**Target:** `Screens/Finance/Page/next_app/` (additive — existing app untouched except 2 wiring edits)
**Plan:** `C:\Users\vkjha\.claude\plans\role-persona-act-sprightly-jellyfish.md`

**STATUS: complete — 19/19 clean.** `npx next build` green (static export, tsc clean).
Browser-verified against the real backend at `http://127.0.0.1:8001/`.
Model A authored 13 files (T1, T3, T6–T15); orchestrator did the 6 cross-cutting
edits (T2 data, T4/T5 css/layout, T16/T17 wiring) + all review, the
reduced-motion hardening, and verification.

Legend: ⬜ queued · 🟡 prompt sent · 🔵 file written · 🟢 tsc+lint clean · 🔴 needs rework

| # | File | Owner | Status | Notes |
|---|------|-------|--------|-------|
| X1 | `app/lib/replicaHoldings.ts` | Model A | 🔵 | summary + gate alert + 9 holdings rows (exact values) |
| X2 | `app/components/replica/ReplicaTopBar.tsx` | Model A | ⬜ | Rs badge + FINANCE + clock + Back to Menu |
| X3 | `app/components/replica/ReplicaGateAlert.tsx` | Model A | ⬜ | grey to pink banner, G2 in red |
| X4 | `app/components/replica/ReplicaSideNav.tsx` | Model A | ⬜ | 5 items, Investments active (bordered card) |
| X5 | `app/components/replica/ReplicaStatCards.tsx` | Model A | ⬜ | INVESTED / CURRENT VALUE / GAIN-LOSS (green) |
| X6 | `app/components/replica/ReplicaHoldingsTable.tsx` | Model A | ⬜ | header + rows: scheme+pill, invested, current input, gain/loss, units input, analysis/save/delete |
| X7 | `app/replica/page.tsx` | Model A | ⬜ | assemble; light gradient bg covering aurora; sidebar+main grid |
| X8 | `tsc + build` | Claude | ⬜ | npx tsc --noEmit + next build |
| X9 | `browser verify` | Claude | ⬜ | compare /replica to screenshot; screenshot |

## Log

- _(build not started)_
