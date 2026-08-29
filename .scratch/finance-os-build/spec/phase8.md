# Phase 8 — Night worker, backups, build pipeline, cutover, polish

## LESSONS FROM PHASES 2-7 — do not repeat (full list in prompt-contract.md "LESSONS LEDGER")
- Box has only fastapi + uvicorn + numpy. No faiss/torch/sklearn/etc.
- `services/{calculations,agents}/*` are framework-free (no APIRouter/fastapi).
- Router prefix = tab segment only. POST bodies via `Body`/model.
- No `pass` route bodies. DB via a `_db()` generator dependency.
- FE: import exact paths (`@/components/finance/Card`), never a barrel or an
  invented `Button/Input/Slider`. `useFinanceData(path)` 1-arg; hooks at top level.
- `data_health` singleton = UPDATE WHERE id=1.


Authoritative: master doc §11 (night worker sequence), §8.9 (build/serve), §12
(failure modes). This phase makes Finance OS *the* Finance screen.

## META-FIX — see phase0.md.

## Files & responsibilities

- `finance-os/night_worker.py` — runs 23:00 IST via Task Scheduler; `--once`
  flag for a single manual pass. Sequence (master doc §11):
  1. `db.connect()` (PRAGMA set by the helper).  **[D]**
  2. Refresh latest prices for all `active_holdings` + benchmarks via
     `market_data.batch_refresh` with a **capped total retry budget** — one dead
     symbol must not stall the whole pass.  **[J]**
  3. WEEKLY (not nightly): gap-only `price_history` refresh — per symbol fetch
     only `MAX(date)+1 .. today`, `INSERT OR IGNORE`. Never re-pull the full 2y.  **[B]**
  4. Local-LLM portfolio review (placeholder call).
  5. `snapshots` — new row per day; `data_health` — `UPDATE ... WHERE id=1`.
  6. Compress `agent_memory` (trim/summarize rows older than a window).
  7. Write `research_notes`.
  8. Copy `finance.db` → `backend/data/backups/finance_YYYYMMDD.db`, keep last 7,
     delete older.
- `finance-os/build.py` — `npm --prefix frontend run build` → copy
  `frontend/out/*` → `backend/static/` (clean target first). Exit non-zero on any
  step failure. This replaces the "prose" export step.  **[O]**
- `finance-os/backend/main.py` — confirm `StaticFiles(directory="static",
  html=True)` mount + a catch-all route returning `static/<path>.html` or
  `static/index.html` so deep links like `/finance/investments` resolve against
  the Next static export (Next emits `investments.html`).  **[O]**
- `backend/services/calculations/portfolio.py` etc. — perf check: confirm the
  `latest_prices` correlated-subquery view is acceptable on a multi-year
  `price_history`; if slow, the fix is that `idx_price_history_symbol_date`
  covers it (already in schema) — add an EXPLAIN QUERY PLAN assertion in a
  `scripts/check_view_perf.py`.  **[B]**
- **Cutover** — the ONE manual step, done by a human after the autonomous build
  passes (a blind 7B rewrite of the multi-screen serve file risks breaking other
  screens). This phase only writes `finance-os/CUTOVER.md`: the exact checklist to
  point `Start_Inky/serve_everything_on_one_port.py` + `Start_Everything.bat` at
  the `finance-os` backend/static on the Finance route, stop mounting
  `Screens/Finance/server_for_finance.py`, and update the Finance target in
  `Main_Menu/Page/next_app/app/components/NavPanel.tsx` if the path changed.  **[Q1]**
- Lazy-load pass (dynamic imports for Three.js/heavy charts); end-to-end smoke.

## Gate (`gate_phase8.py`)
`build.py` runs clean and populates `backend/static/index.html`; night worker
`--once` runs; `night_worker.py` source shows gap-only weekly refresh + capped
retry budget + last-7 backup rotation; `/overview/data-health` reports staleness
(doesn't present old data as current); deep-link `/finance/investments` served
from the static export with no 404; `serve_everything_on_one_port.py` references
`finance-os` and no longer mounts the old `Screens/Finance` service.
