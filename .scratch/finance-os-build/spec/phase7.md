# Phase 7 — Data Health, Scenario Lab, Settings

## LESSONS FROM PHASE 6 — do not repeat (full list in prompt-contract.md "LESSONS LEDGER")
- Box has only fastapi + uvicorn + numpy. NEVER import faiss / torch /
  sentence_transformers / transformers / sklearn / langchain / openai.
- `services/rag.py` = module functions (`retrieve`, `topics`, `topic`), not a class.
- No barrel `from "@/components/finance"`; import `@/components/finance/Card`.
  `useFinanceData` returns `{data,isLoading,error,refetch}` (`error`, not `isError`).


## LESSONS FROM PHASE 5 — do not repeat (full list in prompt-contract.md "LESSONS LEDGER")
- `services/agents/*.py` and `services/calculations/*.py` are framework-free (no
  APIRouter / no fastapi import / no `pass` bodies).
- Backend can't import `finance-os/shared/` — inline small constant tuples with a
  source-of-truth comment. `shared/constants/categories.py` exports TUPLES
  (`TRANSACTION_CATEGORIES` etc), not `Categories`/`CategoryEnum`.
- Only shared FE components: `@/components/finance/{Card,Skeleton,FormModal}` +
  `charts/InvestmentCharts`. Build anything else inline / as a new emitted file.
- `useFinanceData<T>(path)` = one arg; `useSubmit(path, method?)`. Filter in the
  component, not via the hook.


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


Authoritative: master doc §7 (Entity Management + `/overview/data-health`),
§8.8 (Settings page), §12 (Data Health scoring). Settings is NOT a tab — it's a
header-level page.

## META-FIX — see phase0.md.

## Files & responsibilities

- `backend/routers/health.py` — `/overview/data-health` + `/health` read the
  singleton `data_health` row. All writes are `UPDATE ... WHERE id=1` — NEVER
  `INSERT`. `recompute_health()` sets `health_score` high/medium/low per master
  doc §12 (recent imports present? prices fresh? critical data — salary, goals,
  insurance — present?) and surfaces `price_last_refresh` staleness.
- `backend/services/calculations/scenario.py` — pure-math scenario simulator
  (extra payments, salary changes, one-off bonus, SIP step-up) → projected
  net-worth / goal-probability deltas. No LLM.
- `backend/routers/{accounts,goals,insurance,salary}.py` — finish any CRUD not
  done in Phase 1; `salary` POST always inserts a new row (a raise is a new
  record, never an edit of history); "current" = `MAX(effective_date) <= today`.
  - Account `{id}/archive` with active holdings: EITHER cascade a soft-archive to
    child holdings (set their `archived_at`) OR return 409 with a message. Never
    leave holdings live under a hidden account.  **[P]**
  - Goal creation stores `start_date` (baseline for probability `total_months`);
    `current_amount` stays MANUAL — the response/schema notes it can be stale.  **[E]**
- `frontend/app/finance/settings/page.tsx` — master doc §8.8 (Accounts / Goals /
  Insurance / Salary sections, `?tab=` deep-link support), each section = list +
  form + archive. Every form submits through `useSubmit` (Phase 2). Category
  fields use the shared enum.  **[H]**
- `frontend/components/finance/forms/*` — AccountForm, TransactionForm,
  HoldingForm (with a manual-price field for bonds), DebtForm, GoalForm (shows
  the `start_date` baseline; notes `current_amount` is manual/stale), InsuranceForm.
- `frontend/app/finance/scenario/` (or a Settings sub-view) — scenario simulator UI.
- Wire Overview cards' "Manage all →" / "+" triggers to open the relevant
  `<FormModal>` or route to Settings.  **[H]**

## Gate (`gate_phase7.py`)
create + edit + archive an account, a goal, an insurance policy entirely via API;
a goal carries a baseline date; archiving an account that has an active holding
either cascade-archives the holding (no orphan) or returns 409 leaving it intact;
`data_health` stays exactly one row after mutations; scenario/simulate reachable.
