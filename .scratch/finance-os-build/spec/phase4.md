# Phase 4 — Debt & Liabilities tab

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


Authoritative: master doc §7 (Debt endpoints), §9.3 (Debt Specialist), §10
(scenario simulator is pure math, no LLM). Finance philosophy priority order
(master doc §2): high-interest debt sits above goals/investing — payoff plan
ranks by that.

## META-FIX — see phase0.md.

## Files & responsibilities

- `backend/routers/debt.py` — `/debt/overview`, `/debt/table` (+`{id}` GET/PUT/
  DELETE, `{id}/archive`), `/debt/payoff-plan`, `POST /debt/simulate`,
  `/debt/learning/{topic}`.
  - `{id}/archive`: sets `archived_at`, OR sets `status='closed'` when
    `outstanding <= 0` (paid off). Hard delete blocked if payment history exists.
- `backend/services/calculations/debt.py` — total outstanding, highest-interest,
  next EMI; `AvalancheCalculator` (order by interest rate desc),
  `SnowballCalculator` (order by outstanding asc); `Simulator` — given
  `{extra_payment, salary_increase, bonus}` returns `{months_saved,
  interest_saved, new_payoff_date}`. Pure amortization math; zero extra payment
  → zero months saved (identity check).
- `backend/services/agents/debt_specialist.py` — wraps the calculators; injected
  LLM only for the Action/Reason/Learn narrative.
- `frontend/app/finance/debt/page.tsx` + cards: debt table, payoff-plan view,
  the simulate form (sliders/inputs → calls `/debt/simulate` via `useSubmit`),
  a learning-content panel (Action / Reason / Learn per master doc §1).

## Gate (`gate_phase4.py`)
create a sample debt; `/debt/overview`, `/debt/payoff-plan` return 200;
`/debt/simulate {extra_payment:5000}` returns sane `months_saved` (0..remaining)
and `interest_saved >= 0`; `{extra_payment:0}` returns `months_saved == 0`.
