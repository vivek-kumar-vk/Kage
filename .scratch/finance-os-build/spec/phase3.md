# Phase 3 — Investments tab

## LESSONS FROM PHASE 2 — do not repeat (full list in prompt-contract.md "LESSONS LEDGER")
- These files are FROZEN — import, never regenerate: `lib/api.ts`, `lib/types.ts`,
  `tsconfig.json`, `tailwind.config.ts`, `app/layout.tsx`, `app/finance/layout.tsx`,
  `components/finance/{Card,Skeleton,FormModal}.tsx`, `backend/services/db.py`,
  `backend/app_factory.py`.
- Import ONLY packages in `frontend/package.json`. BANNED (build dies):
  framer-motion, shadcn-ui, @radix-ui/*, use-sync-external-store, any markdown lib.
  Animate with Tailwind `animate-pulse` + `motion-reduce:`. Modal = plain
  `fixed inset-0` div.
- `"use client";` as literal line 1 of ANY file using a hook. Never a client hook
  in a root layout.
- Imports use `@/...` alias, never `../../` traversal. No `frontend/services/` dir.
- `page.tsx` = content only; header/nav/tabs already live in `app/finance/layout.tsx`.
- Guard `if (!data) return <Empty/>` before touching `data.x`. Never read a var
  outside its block scope. No module self-import.
- Every card/page: distinct loading / error / empty states.


Authoritative: master doc §7 (Investments endpoints), §8 (card patterns), §9.2
(Investment Specialist). All portfolio math reads the `active_holdings` view.

## META-FIX — see phase0.md.

## Files & responsibilities

- `backend/routers/investments.py` — every endpoint in master doc §7 Investments:
  holdings (+`{id}` GET/PUT/DELETE, `{id}/archive`), quality, and all `visuals/*`
  (asset-allocation, geography, target-vs-actual, portfolio-vs-benchmark,
  rolling-returns, drawdown, treemap, fund-overlap, expense-ratio, sip-calendar,
  concentration), research.
  - `{id}` DELETE: allowed ONLY if the holding has zero `lots` → else 409 "use
    archive". `{id}/archive` sets `archived_at`.  **[P]**
  - `visuals/portfolio-vs-benchmark`, `rolling-returns`, `drawdown` read
    `price_history`. Each returns an explicit state discriminator:
    `{"state":"ok"|"partial"|"pending", ...}` — `"pending"` when backfill hasn't
    run, `"partial"` when < the requested window exists. Never just an empty
    array with no explanation.  **[B]**
- `backend/services/calculations/portfolio.py` — current value, gain/loss,
  weight, allocation, XIRR (reuse Phase 1 `xirr.py`), concentration, overlap.
  Reads `active_holdings`. Bonds/`other` (price `None`) are excluded from value
  totals and flagged, not counted as 0.  **[J/M]**
- `backend/services/agents/investment_specialist.py` — `HoldingsAnalyzer`,
  `QualityChecker` (regular-plan flag, high TER, concentration, overlap),
  `AllocationDrift`. Deterministic; LLM (injected) only for the narrative string.
- `frontend/app/finance/investments/page.tsx` + `components/finance/cards/` and
  `components/finance/charts/` for the tab:
  - Holdings table: edit + archive inline. The hard-delete affordance is HIDDEN
    unless `lots.count === 0` (every real holding has lots, so the button is
    otherwise dead).  **[P]**
  - Quality panel, research view, the visuals (hand-rolled SVG + Three.js where
    the doc calls for 3D; lazy `ssr:false`).
  - Each visual renders a distinct "backfill pending" / "partial history" state,
    not only "no data".  **[B]**

## Gate (`gate_phase3.py`)
right after a fresh import, `rolling-returns` + `drawdown` return real ~2y data
(Phase 1 backfill), not empty/pending; an archived holding disappears from
`/investments/holdings` AND from `/overview/portfolio-pulse` (every calc reads
`active_holdings`).  **[P][B]**
