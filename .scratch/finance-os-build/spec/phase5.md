# Phase 5 — Tracker tab

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
