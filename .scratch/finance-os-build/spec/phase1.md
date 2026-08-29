# Phase 1 — Ingestion & CRUD (backend)

Authoritative: `finance-os-master-plan-final.md` §7 (endpoints), §10 (calc
snippets), §13 (security). Every DB open goes through `services/db.py:connect()`.
Merge proven logic from `Screens/Finance/Calculations/` (CAS parse with
PAN-as-PDF-password + AMFI scheme-code resolution, event-envelope price-ledger
idempotency, XIRR) — port the logic, drop all CSV file I/O, keep one impl where
the doc's sketch overlaps.

## META-FIX — see phase0.md. Implement each fix's downstream consumer.

## Files & responsibilities

- `services/market_data.py` — `get_current_price(symbol, asset_type)` branched by
  asset type, NOT a linear chain (master doc §10):
  - `stock`/`etf`: `_fetch_yfinance` (tenacity, 3 attempts, exp backoff 2–10s) →
    on failure `get_last_cached_price` (from `latest_prices` view). **No Alpha
    Vantage** (no key).
  - `mutual_fund`: `_fetch_mftool` → `get_last_cached_price`.
  - `bond`/`other`: return `None` and mark the holding "excluded from value" —
    callers must exclude it from portfolio-value math, never render it as ₹0.  **[J/M]**
  - `normalize_symbol(symbol, asset_type, currency)` — Indian equity/ETF gets
    `.NS` (or `.BO` fallback) before the yfinance call; US ticker unchanged.  **[J/M]**
  - `batch_refresh(holdings, total_retry_budget_s=120)` — a shared retry budget
    for a whole batch; once spent, remaining symbols fall straight to cache.  **[J/M]**
- `services/calculations/holdings_upsert.py` — `upsert_holding(..., mode)` where
  `mode` is `"add_lot"` (Groww CSV / SMS — new units ADD to the position, weighted
  -average cost merge per master doc §10) or `"set_snapshot"` (CAS — units are the
  TOTAL held today; SET, do not add). When incoming `cost_per_unit` is `None`
  (CAS often has units, not cost): keep existing `avg_cost`, skip the recompute —
  never drive it toward 0. Lot insert stays idempotent via
  `UNIQUE(holding_id,purchase_date,units,cost_per_unit)` → catch + pass. After a
  first-ever import of a symbol, enqueue `backfill_price_history` as a background
  task (see below) — do NOT call it inline.  **[C][B]**
- `services/calculations/backfill.py` — `backfill_price_history(symbol, asset_type)`
  per master doc §10; `stock/etf` → yfinance `period="2y"`, `mutual_fund` →
  mftool NAV history keyed by the **resolved AMFI scheme code** stored as
  `holdings.symbol` (without it mftool silently returns nothing). Bulk
  `INSERT OR IGNORE` into `price_history`. Exposed as a function a FastAPI
  `BackgroundTasks` / a tiny in-process queue calls — the import request returns
  immediately.  **[B]**
- `services/calculations/xirr.py` — port `Screens/Finance/Calculations/compute_the_xirr.py`.
- `services/imports/cas.py` — port CAS parsing from
  `Screens/Finance/Calculations/pull_from_cas_statement.py` (PAN as PDF password
  from env/`.env`, AMFI code resolution, snapshot semantics). Returns normalized
  rows; the endpoint calls `upsert_holding(mode="set_snapshot")`.
- `services/imports/groww.py` — Groww CSV → `upsert_holding(mode="add_lot")`.
- `services/imports/transactions.py` — `dedupe_transaction(account_id, date,
  amount, description)` — ONE function both `/import/upi-csv` and `/import/sms`
  call, so the same txn from both paths cannot double-count. Key = normalized
  `date+amount+description`.  **[A]**
- `routers/accounts.py routers/goals.py routers/insurance.py routers/salary.py
  routers/holdings.py routers/debts.py routers/imports.py routers/transactions.py`
  — CRUD per master doc §7. List endpoints exclude `archived_at IS NOT NULL`
  unless `?include_archived=true`. Hard-delete on accounts/holdings blocked by
  `ON DELETE RESTRICT` → return 409 with a message pointing at archive. Manual
  entry: `POST /import/manual` with `{entity, ...fields}`.
- `services/agents/supervisor.py` — `sanitize_for_cloud_llm(payload) -> dict`:
  strips account numbers, PAN, txn descriptions, account/holding names, lender
  names, ticker symbols; only aggregates (allocation %, category sums, debt
  totals by type) pass. Specialists receive an LLM client **injected by the
  supervisor** — no `import openai` / `ollama` at module level in any specialist.
  The cloud prompt builder works from allocation %s only.  **[I]**
- `services/agents/*_specialist.py` — stubs that accept `llm_client` in `__init__`.

## REFERENCE BLOCKS (you do NOT have the master plan file — use these)

### goal-probability sibling (used by goals calc, keep identical everywhere)
```python
def goal_probability(current: float, target: float, months_left: int, total_months: int) -> float:
    if target <= 0:
        return 0.0
    if months_left <= 0:
        return 100.0 if current >= target else 0.0
    time_factor = min(months_left / total_months, 1.0)
    progress = min(current / target, 1.0)
    probability = (progress * 0.7 + time_factor * 0.3) * 100
    return min(100.0, max(0.0, probability))
```

### weighted-average-cost merge (mode="add_lot" branch of upsert_holding)
```python
existing = get_holding(account_id, symbol)
if existing is None:
    holding_id = insert_holding(account_id, symbol, name, type_, new_units, new_cost_per_unit, currency)
else:
    total_units = existing.units + new_units
    if total_units == 0:
        merged_avg_cost = 0
    elif new_cost_per_unit is None:
        merged_avg_cost = existing.avg_cost          # [C] null cost -> keep, do not crater
    else:
        merged_avg_cost = ((existing.units * existing.avg_cost)
                           + (new_units * new_cost_per_unit)) / total_units
    update_holding(existing.id, units=total_units, avg_cost=merged_avg_cost)
    holding_id = existing.id
try:
    insert_lot(holding_id, purchase_date, new_units, new_cost_per_unit, source)
except UniqueConstraintViolation:
    pass                                              # identical lot re-import -> expected
```
mode="set_snapshot" (CAS): `update_holding(existing.id, units=new_units, ...)` —
SET units, do NOT add; if `new_cost_per_unit` is None keep `avg_cost`.

### market data — branched by asset type (NO Alpha Vantage, no key)
```python
@tenacity.retry(stop=tenacity.stop_after_attempt(3),
                wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
def _fetch_yfinance(symbol): ...

@tenacity.retry(stop=tenacity.stop_after_attempt(3),
                wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
def _fetch_mftool(symbol): ...

def get_current_price(symbol, asset_type):
    if asset_type in ("stock", "etf"):
        try:
            return _fetch_yfinance(normalize_symbol(symbol, asset_type, currency))
        except Exception:
            return get_last_cached_price(symbol)      # latest_prices view
    elif asset_type == "mutual_fund":
        try:
            return _fetch_mftool(symbol)              # symbol = resolved AMFI code
        except Exception:
            return get_last_cached_price(symbol)
    else:                                             # bond / other
        return None                                   # caller EXCLUDES from value, not ₹0
```

### backfill (runs as a background task, never inline in the import request)
```python
def backfill_price_history(symbol, asset_type):
    if asset_type in ("stock", "etf"):
        history = fetch_yfinance_history(symbol, period="2y")
    elif asset_type == "mutual_fund":
        history = fetch_mftool_nav_history(symbol, period="2y")   # symbol = AMFI code
    else:
        return
    bulk_insert_price_history(symbol, history)        # INSERT OR IGNORE, re-runnable
```

## Gate (`gate_phase1.py`)
double Groww CSV import → exactly one holding, units NOT doubled, avg_cost stable,
no crash; CAS snapshot import → units SET not added; `price_history` gets rows for
a new symbol within ~30s of import (background task ran); a `bond` holding is
excluded from portfolio value, never a ₹0 row; specialists have no module-level
LLM import; `upsert_holding` exposes `mode`.
