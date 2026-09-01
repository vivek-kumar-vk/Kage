# Phase 5 — Tracker tab

## LESSONS FROM PHASE 4 — do not repeat (full list in prompt-contract.md "LESSONS LEDGER")
- `services/calculations/*.py` = pure functions taking `conn`; no FastAPI / no
  `APIRouter` in them. Router prefix is the tab segment only (`prefix="/tracker"`),
  never `/api/finance/...`.
- A POST taking a JSON object uses `payload: dict = Body(default={})` — not bare
  scalar params (those become query params).
- Import function names that exist; no invented `XCalculator` classes.
- "Never / infinite" sentinels are `math.inf` + `math.isinf`, never a magic number.


## LESSONS FROM PHASE 3 — do not repeat (full list in prompt-contract.md "LESSONS LEDGER")
- Router routes carry the tab segment (`/debt/...`, `/tracker/...`, `/scenario/...`) —
  `app_factory` only adds `/api/finance`. Match the gate's exact paths.
- No `pass` / placeholder route bodies. No `Depends()` for auth (middleware is
  global). DB only via a `_db()` generator dependency.
- Time-series = computed from `price_history` + `active_holdings`; no such table.
  Schema frozen to `scripts/schema.sql`.
- Verify every import resolves in the real tree (`services.calculations.xirr`,
  plain functions not classes). No `from routers import <other>`.
- `useFinanceData` / `useSubmit` = hooks from `@/lib/api`, called once at
  component top level — never in `useEffect` / handlers / async.


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


Authoritative: master doc §7 (Tracker endpoints), §9.4 (Tracker Specialist).
Transactions are individually correctable by design — **hard delete IS allowed
here** (unlike accounts/holdings). Every mutation must flow through the Phase 2
cache-version bump so Overview updates with no manual refresh.

## META-FIX — see phase0.md.

## Files & responsibilities

- `backend/routers/tracker.py` — `/tracker/transactions` (GET with date-range /
  category / account filters), `/tracker/transactions/{id}` (GET/PUT/DELETE —
  hard delete fine), `/tracker/categories` (spend by category), `/tracker/
  recurring`, `/tracker/trends` (monthly), `/tracker/insights`.
  - category field validated against the shared enum
    (`shared/constants/categories`) — a bad category is 422, not silent.  **[A]**
- `backend/services/agents/tracker_specialist.py` — `RecurringDetector` (same
  payee + ~monthly cadence + similar amount), `LeakFinder` (leak-of-the-week),
  `BudgetDrift`. Deterministic; injected LLM for narrative only.
- `frontend/app/finance/tracker/page.tsx` + components: filterable transaction
  table with inline edit + delete (via `useSubmit`), category breakdown, monthly
  trend (hand-rolled SVG), recurring list, insights panel.
  - `TransactionForm.tsx` — category `<select>` populated from the shared enum.  **[A]**

## Gate (`gate_phase5.py`)
create a txn, edit its amount → `/overview/cashflow` reflects the new amount
immediately (no stale cache); delete it → `/tracker/categories` recomputes and
`/overview/cashflow` expenses return to 0; `/tracker/recurring` returns 200.
