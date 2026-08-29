# Phase 7 — Data Health, Scenario Lab, Settings

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
