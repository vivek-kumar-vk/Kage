# Finance OS V1 — autonomous build handoff

**What this is.** A local-model build of the app specified in
`B:/inky_code/finance-os-master-plan-final.md` (v3), into a new tree at
`finance-os/`, with the Group A–Q "one-step-downstream" fixes baked in as inline
gates. Plan of record: `C:/Users/vkjha/.claude/plans/crispy-spinning-lecun.md`.

**Who does what.**
- Claude: planning + this wiring + memory only. No app code. No proactive tests.
- Local model (Qwen2.5-Coder-7B @ llama-server :8080): authors every file.
- `run_build.py`: the loop — per-file gate, ≤2 fix retries, self-grill, scout,
  executable phase gate. Halts the whole run if a phase gate exits non-zero.
- `ui_gap_scout` Hermes bot: reviews each finished task on the local model
  (zero Claude cost), maintains `.scratch/lm-ui-gaps/ledger.md`.

**One notification.** The run reports to Claude exactly once — at completion or
halt — via `progress/RUN_REPORT.md` + the final stdout line
(`BUILD RUN COMPLETE` / `BUILD RUN HALTED AT <phase>`). No per-phase, no
per-task pings.

## Run it

```
# 1. start the local model (leave it running; it is currently OFF)
C:\inky_models\bin\llama-server.exe --model C:/inky_models/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf ^
  --alias qwen2.5-coder-7b-instruct-q5_k_m --host 127.0.0.1 --port 8080 --threads 6 ^
  --ctx-size 8192 --n-gpu-layers 24 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0

# 2. kick off the whole build (background; ~many hours)
cd B:\inky_code
python .scratch\finance-os-build\run_build.py ^
  .scratch\finance-os-build\manifests\phase0.json ^
  .scratch\finance-os-build\manifests\phase1.json ^
  .scratch\finance-os-build\manifests\phase2.json ^
  .scratch\finance-os-build\manifests\phase3.json ^
  .scratch\finance-os-build\manifests\phase4.json ^
  .scratch\finance-os-build\manifests\phase5.json ^
  .scratch\finance-os-build\manifests\phase6.json ^
  .scratch\finance-os-build\manifests\phase7.json ^
  .scratch\finance-os-build\manifests\phase8.json
```

Resume after a halt: fix the blocker, re-invoke `run_build.py` with the
remaining `phaseN.json` (already-authored files are regenerated identically —
safe; trim the task list to save time).

## Layout

```
.scratch/finance-os-build/
  run_build.py        backend+frontend build loop (fork of ../finance-telemetry/run_phase.py)
  BUILD_BRIEF.md      this file
  spec/phaseN.md      phase brief — folded into every task prompt that phase
  manifests/phaseN.json  run_build manifest (tasks, gate_cmd, setup_cmds)
  gates/gate_phaseN.py   executable phase gate (exit 0 = pass; non-zero halts)
  gates/_util.py         shared gate helpers (fresh sqlite, uvicorn spin-up, http)
  progress/phaseN-progress.md  timestamped log
  progress/RUN_REPORT.md       the single end-of-run report
```

## Phase gates (the objective bar)

| Phase | gate proves |
|---|---|
| 0 | schema applies; FK reject; `active_holdings`+`latest_prices` views; no bare `sqlite3.connect(`; `.gitignore` covers secrets; shared category enum both sides |
| 1 | double CSV import → units not doubled; CAS snapshot SET not added; price_history backfilled via background task; bond excluded from value; no module-level LLM import in specialists |
| 2 | api.ts cache-version + refetch; sparkline no forced 0; FormModal+useSubmit; `next build` → out/; `/overview/*` no NaN on empty DB |
| 3 | rolling-returns+drawdown real 2y right after import; archived holding leaves every calc |
| 4 | `/debt/simulate` sane; zero extra payment → zero months saved |
| 5 | edit/delete a txn → Overview reflects it with no stale cache |
| 6 | RAG retrieval relevant; zero user financial data in any chunk |
| 7 | account/goal/insurance CRUD via API; account-archive with holdings cascades or 409s (no orphan); data_health stays singleton |
| 8 | build.py → static bundle; night worker gap-only weekly refresh + capped retry + 7-backup rotation; deep-link served from static export; `CUTOVER.md` written |

## The one manual step

Cutover (make `finance-os` the live Finance screen) is **not** in the autonomous
run — see `finance-os/CUTOVER.md` after the build passes. Everything else is
hands-off.
