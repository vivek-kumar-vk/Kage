<!-- Prepended to every Model A build-task prompt. Maintained by ui-gap-scout.
     Keep it short. A line earns its place only after its tag recurs >=2x. -->

# Model A prompt contract (v1 — 1 real task in: P1)

- The literal first line of any client component is these 8 characters then a
  semicolon: `"use client";` — WITH the double quotes. `use client;` is a bug.
- Colours come only from the locked theme tokens (see the task's token list).
  Never a raw hex outside an explicitly-labelled data/tokens object. Red is
  reserved for "act now" state, never decoration.
- When asked for N distinct variants, each must differ in background hue AND
  contrast level AND one structural choice. Near-duplicate variants = failed task.
- If colour tokens are given as inline CSS vars (`var(--x)`), style with the
  `style={{}}` prop ONLY — never `className`/Tailwind. Spacing = literal numbers.
  Tailwind classes resolve only for tokens in the project's `@theme`; task-local
  vars are not there. Arbitrary Tailwind values need brackets: `max-w-[920px]`.
- Given a data series for a chart, COMPUTE the SVG path from it (index→x,
  value→y via min/max). Never hand-draw an approximation. A polyline is ONE
  `M` (first point) then `L` for every next point, space-joined — NOT `M..L..`
  per point (that draws disconnected zero-length dots).
- Read figures from the seed module named in the task
  (`app/lib/blueprintSeed.ts` or `app/lib/replicaHoldings.ts`). Never invent a
  number.
- No chart or 3D library. Visualizations are hand-rolled SVG + `framer-motion`
  (already a dependency).
- Every animation gets a `@media (prefers-reduced-motion: reduce)` /
  `useReducedMotion()` guard that freezes it.
- This repo runs a **patched Next.js** — follow the API shapes in the task, not
  your training data.
- Output **one file**, complete, no prose, no markdown fence around it beyond a
  single optional ```tsx wrapper.

## Python / FastAPI (Finance OS V1 build — .scratch/finance-os-build)

- **Meta-fix.** For every fix, also implement the thing one step downstream that
  consumes it. A UNIQUE constraint needs its upsert. A new table needs its
  backfill. A patched edge case needs its sibling edge case in the SAME function.
  A new VIEW needs every caller switched to it. A locked-in decision needs its
  deployment check. Do not stop at the reported symptom.
- Every DB open goes through `backend/services/db.py:connect()` — it sets
  `PRAGMA foreign_keys=ON` first, every connection. Never `import sqlite3` +
  `sqlite3.connect(` anywhere else.
- Read the `active_holdings` view, never the `holdings` table, in any calculation
  (it already excludes archived holdings + archived accounts).
- No module-level `import openai` / `ollama` / `litellm` in a specialist. The LLM
  client is passed into `__init__`. Cloud payloads go through
  `supervisor.sanitize_for_cloud_llm()` first (no PAN, account/holding/lender
  names, descriptions, or ticker symbols — aggregates only).
- Any network loop in a request path (price backfill, batch refresh) runs as a
  FastAPI `BackgroundTasks` / queue job — the request returns immediately.
- One `dedupe_transaction()` shared by UPI-CSV and SMS import — same txn from two
  paths must not double-count.
- `upsert_holding` takes `mode`: `add_lot` (Groww/SMS — units ADD, weighted-avg
  cost) vs `set_snapshot` (CAS — units are the total, SET). `cost_per_unit=None`
  → keep existing `avg_cost`, skip the recompute.
- Unpriceable assets (bond/other → price `None`): exclude from portfolio-value
  math and flag them; never render as ₹0.
- Time-series endpoints return an explicit `{"state": "ok"|"partial"|"pending"}`
  discriminator, not a bare empty array.
- `data_health` writes are `UPDATE ... WHERE id=1`, never `INSERT`.
- Frontend: no `next export` script; `output:'export'` makes `next build` export.
  Sparkline scaling uses real data min/max with `(max-min)||1` — no forced `0`.
- Output ONE complete file, no prose, no fence.

## Retired
<!-- lines whose tag stopped recurring; kept for history -->
