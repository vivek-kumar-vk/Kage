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

## LESSONS LEDGER — Finance OS V1 (carry-forward; NEVER repeat a line below)
<!-- After each phase, Claude appends the concrete mistakes the 7B just made so
     the next phase can't repeat them or their error-class. Newest phase last. -->

### FROZEN FILES — import them, do NOT regenerate/rewrite them
These already exist and are correct. Import from them. If a task seems to ask you
to "create" one, it means LEAVE IT — emit only the NEW file the task names:
`frontend/tsconfig.json`, `frontend/tailwind.config.ts`, `frontend/next.config.js`,
`frontend/lib/api.ts`, `frontend/lib/types.ts`, `frontend/app/layout.tsx`,
`frontend/app/finance/layout.tsx`, `frontend/components/finance/Card.tsx`,
`frontend/components/finance/Skeleton.tsx`, `frontend/components/finance/FormModal.tsx`,
`backend/services/db.py`, `backend/app_factory.py`, `backend/main.py`,
`backend/routers/{overview,accounts,imports,entities,investments}.py`,
`backend/services/calculations/{core,portfolio,backfill,holdings_upsert,xirr}.py`,
`backend/services/market_data.py`, `frontend/app/finance/page.tsx`,
`frontend/app/finance/investments/page.tsx`,
`frontend/components/finance/charts/InvestmentCharts.tsx`,
`frontend/components/finance/cards/*` (Overview cards),
`backend/routers/debt.py`, `backend/services/calculations/debt.py`,
`backend/services/agents/{investment_specialist,debt_specialist}.py`,
`backend/routers/imports.py` (now multi-entity),
`frontend/app/finance/{investments,debt,tracker}/page.tsx`,
`backend/routers/tracker.py`, `backend/services/agents/tracker_specialist.py`,
`frontend/components/finance/forms/TransactionForm.tsx`,
`backend/services/rag.py`, `backend/routers/learning.py`,
`backend/services/agents/learning_specialist.py`, `backend/scripts/ingest_varsity.py`,
`backend/content/*.md` (public primers), `frontend/app/finance/learning/page.tsx`,
`backend/routers/{settings,health}.py`,
`backend/services/calculations/{scenario,data_health}.py`,
`frontend/app/finance/{settings,scenario}/page.tsx`,
`frontend/components/finance/forms/EntityForms.tsx`,
`finance-os/build.py`, `finance-os/night_worker.py`, `finance-os/CUTOVER.md`,
`backend/main.py`, `backend/scripts/check_view_perf.py`.

### from Phase 2 (frontend) — applies to every later frontend phase (3, 5, 7)
- **Package allow-list.** Import ONLY: `react`, `react-dom`, `next/*`, `three`,
  `@react-three/fiber`, `@react-three/drei`, `lucide-react`,
  `class-variance-authority`, `clsx`, `tailwind-merge`. **BANNED — build dies:**
  `framer-motion`, `shadcn-ui`, `@radix-ui/*`, `use-sync-external-store`, any
  markdown/remark/marked lib, anything not in `frontend/package.json`.
  Animation = Tailwind `animate-pulse` + `motion-reduce:animate-none`. Modal =
  a plain `fixed inset-0` div with an Escape handler (see `FormModal.tsx`).
- **Client hooks need the directive.** ANY file using `useState`/`useEffect`/
  `useSyncExternalStore`/`usePathname`/`useRouter`/`useFinanceData`/`useSubmit`
  MUST have `"use client";` as literal line 1. NEVER put a client hook in
  `app/layout.tsx` (root = server component).
- **Path alias, not traversal.** Import as `@/lib/api`, `@/components/finance/...`
  — never `../../components` or `../services/db`. There is no `frontend/services/`.
- **Page vs layout.** A `page.tsx` renders CONTENT ONLY. Header, `<nav>`, the
  `tabs` array, the FINANCE OS title all live in `app/finance/layout.tsx`
  already — do not re-declare them in a page.
- **Scope + null discipline.** Never read a name outside its block (`tab.href`
  after the `.map()` closes = crash). `useFinanceData` returns `data: T | null`
  — guard `if (!data) return <Empty/>` BEFORE `data.trend.map(...)`.
- **No self-import.** A module must not `import { X }` from itself for names it
  also `export`s (killed `lib/types.ts`).
- **Three explicit states** in every card/page: loading, error, empty — all
  visibly distinct.
- Sparkline: real data min/max + `(max-min)||1`; never force `0` into the range.

### from Phase 3 (Investments) — applies to every later backend+frontend phase (4, 5, 7)
- **Router path segment.** `app_factory` mounts every router with ONLY the
  `/api/finance` prefix. Your routes must carry the tab's own segment:
  `@router.get("/investments/holdings")`, `/debt/...`, `/tracker/...` — NOT bare
  `/holdings`. Check the phase's gate for the exact paths it calls.
- **No per-route auth.** `PassthroughAuth` is middleware, already applied
  app-wide. NEVER `auth: PassthroughAuth = Depends()` on a route. The only
  per-route `Depends` is the DB: `def _db(): conn = connect(); try: yield conn
  finally: conn.close()` then `conn = Depends(_db)`.
- **No placeholder bodies.** Zero `pass` / `# your implementation here` / `...`
  route bodies. Every endpoint returns real data or an explicit
  `{"state": "pending"|"partial"|"ok", ...}` dict. A stub file passes ruff and
  then fails the phase gate — you have wasted the round.
- **Series are computed, not tables.** `rolling-returns`, `drawdown`,
  `portfolio-vs-benchmark` are computed from `price_history` JOIN
  `active_holdings`. There is NO `rolling_returns` / `drawdown` table. The schema
  is frozen — the only tables are the ones in `scripts/schema.sql`.
- **Verify import paths against the real tree.** `xirr` lives in
  `services.calculations.xirr`. There is no `PortfolioCalculator` / `XIRR`
  class — `portfolio.py` exposes plain functions taking `conn`. A router must
  not `from routers import <other>`. If you import a name, it must already exist.
- **`useFinanceData` / `useSubmit` are hooks from `@/lib/api`.** Call
  `useFinanceData(path)` ONCE at the top level of a component. NEVER inside
  `useEffect`, an event handler, or an `async` function. Not `@/components/...`,
  not `@/components/finance/useFinanceData` — the path is `@/lib/api`.
- **Chart slice math.** A donut/pie slice's sweep = `value / total` (cumulative
  offset), never `(value - min) / (max - min)`. A line/area path maps
  `index -> x`, `value -> y` via real min/max.

### from Phase 4 (Debt) — applies to every later phase (5, 7, 8)
- **A file contains what its PATH says.** `services/calculations/*.py` = pure
  functions that take an open `conn` — NO `from fastapi import ...`, NO
  `APIRouter`, NO HTTP. A `routers/*.py` = the `APIRouter` + thin handlers that
  call the calc module. Do not put a router in a calculations file.
- **Router prefix = the tab segment ONLY.** `APIRouter(prefix="/debt")`. NEVER
  `prefix="/api/finance/debt"` — `app_factory` already adds `/api/finance`, so
  that produces `/api/finance/api/finance/debt` and every route 404s.
- **A POST that takes a JSON object uses `payload: dict = Body(default={})`** (or
  a Pydantic model). `async def sim(extra_payment: int, bonus: int)` turns those
  into QUERY params and the JSON body is dropped -> 422 on a normal POST.
- **No invented class APIs.** The calc modules export plain functions
  (`simulate(conn, ...)`, `payoff_plan(conn)`), not `Simulator()` /
  `AvalancheCalculator()` classes. Import the function names that actually exist.
- **Sentinel discipline.** If "never pays off" is a sentinel, make it
  `math.inf` and test with `math.isinf(x)`. A magnitude sentinel like `999`
  silently swallows any real value above it (an interest total, a balance).
- `import/manual` now dispatches `entity` in
  {holding, debt, insurance, goal, salary} -> the matching table. Use it for
  manual single-record creation; do not add a parallel path.

### from Phase 5 (Tracker) — applies to every later phase (6, 7, 8)
- **`services/agents/*.py` is framework-free too.** Same rule as
  `services/calculations/`: plain classes/functions, NO `APIRouter`, NO
  `from fastapi`, no `pass`-only method bodies.
- **The backend CANNOT import `finance-os/shared/`** (not on `sys.path` from
  `cwd=backend`). For a small constant list (categories, types) inline the tuple
  in the router with a `# source of truth: shared/constants/...` comment. Do not
  `from shared.constants.categories import ...`.
- **`shared/constants/categories.py` exports TUPLES**, not classes:
  `TRANSACTION_CATEGORIES`, `TRANSACTION_TYPES`, `ACCOUNT_TYPES`, `HOLDING_TYPES`.
  There is no `Categories` / `CategoryEnum`. `lib/types.ts` exports interfaces
  only — no `TRANSACTION_*` arrays there.
- **The ONLY shared frontend components** are
  `@/components/finance/{Card,Skeleton,FormModal}` and
  `@/components/finance/charts/InvestmentCharts`. Anything else
  (`Select`, `Input`, `Button`, `Empty`, `TransactionTable`, `MonthlyTrend`, ...)
  DOES NOT EXIST — build it inline in the page or as a new file you also emit.
- **Hook signatures:** `useFinanceData<T>(path)` takes ONE argument;
  `useSubmit(path, method?)` takes the path. Filtering is done in the component
  on the returned data, never passed to the hook.
- A manual transaction/record POST sends the column names the table has
  (`account_id`, not `account`).

### from Phase 6 (Learning / RAG) — applies to phases 7, 8
- **This box has ONLY `fastapi`, `uvicorn`, `numpy` (+ stdlib).** NEVER import
  `faiss`, `torch`, `sentence_transformers`, `transformers`, `sklearn`, `scipy`,
  `langchain`, `chromadb`, `openai`. RAG = a dep-free TF-IDF cosine index over
  Markdown files in `backend/content/` (`services/rag.py` already implements it —
  import `rag.retrieve` / `rag.topics` / `rag.topic`).
- **`services/rag.py` exports module-level functions**, not a `RAG` class:
  `retrieve(query, k)`, `topics()`, `topic(id)`, `topic_by_slug(slug)`,
  `ingest(path)` (allow-listed to `backend/content/`). No `.load()` on an index,
  no `get_chunk`/`get_source` stubs.
- **RAG security:** nothing in the learning path opens the DB except
  `Personalizer.shape()`, which returns COUNTS/booleans only. Content served is
  always a whole public file from `backend/content/`. Never interpolate a
  transaction description, account name, or amount into a lesson.
- **Frontend:** no barrel import `from "@/components/finance"` — there is no index
  file; import the exact path (`@/components/finance/Card`). `useFinanceData`
  returns `{data, isLoading, error, refetch}` — the key is `error`, not
  `isError`. No `dangerouslySetInnerHTML`; render text in a
  `whitespace-pre-wrap` block.

### from Phase 7 (Settings / Scenario / Data Health) — applies to phase 8
- **Repeat offenders, now gate-enforced:** router in a `services/calculations/*`
  file; `APIRouter(prefix="/api/finance/...")` double-prefix; barrel
  `import ... from "@/components/finance"`; imports of invented shared components
  (`Button`, `Input`, `Slider`, `Empty`, `Select`, `@/components/finance/constants`).
  None of those exist. Build small UI bits inline.
- `data_health` is a SINGLETON — `UPDATE ... WHERE id = 1`. Never `INSERT`, never
  `DELETE`. `recompute_health()` lives in `services/calculations/data_health.py`.
- Archiving an account with active holdings CASCADE-archives the child holdings
  (set their `archived_at`) in the SAME transaction — never leave a live holding
  under a hidden account.
- `salary` POST always INSERTs a new row (a raise is new history, never an edit).
- The scenario simulate endpoint is `POST /api/finance/scenario/simulate` and its
  math is `services/calculations/scenario.py` (pure, imports `core` + `debt`).

### from Phase 8 (night worker / build / serve) — FINAL
- **`backend/main.py` is 3 lines**: `from app_factory import create_app` /
  `app = create_app()` / the `__main__` uvicorn guard. NEVER rebuild it as a
  FastAPI app with its own middleware/routers — `app_factory` owns all of that
  (router auto-include, StaticFiles, SPA fallback, startup `init_db`).
- **A "worker" / "script" task is a CLI, not a web app.** `night_worker.py` uses
  `argparse` (`--once`, `--weekly`) and runs a sequence — no `FastAPI()`, no
  `uvicorn.run`, no routes. The gate calls `python night_worker.py --once`.
- **`npm` / `npx` are `.cmd` shims on Windows** — `subprocess.run([...],
  shell=True)` or call `node_modules/.bin/next.cmd` directly, else WinError 2.
- `db.connect()` is SYNC. Never `await connect()`.
- `services/market_data.batch_refresh(symbols, total_retry_budget_s=...)` —
  positional symbols list, keyword retry budget. There is no `latest_prices()` /
  `compress_agent_memory()` / `research_notes()` function to import.

## Retired
<!-- lines whose tag stopped recurring; kept for history -->
