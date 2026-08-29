# Finance OS V1 — Master Implementation Plan (Final, v3)

> **Prepared for:** Personal OS Integration
> **Execution Model:** Local Qwen 2.5 Coder 7B (recommended, via Ollama)
> **Architecture:** FastAPI backend (SQLite) + Next.js static frontend (Three.js, modular components)
> **Aesthetic:** Formula 1-inspired premium dashboard
> **Document status:** This is the final, self-contained spec. It supersedes all earlier drafts. Everything needed to implement V1 is in this file — no other document should be consulted. A changelog summarizing what was fixed across revisions is at the very end, for human reference only; the implementing agent should treat Sections 1–17 as the current source of truth and ignore the changelog.

---

## 1. Overview & Philosophy

### Primary Objective
Build a Finance Module that helps a salaried Indian investor understand money, investing, debt, spending, portfolio quality, taxes, and financial mistakes — without becoming a trading terminal, stock prediction engine, gambling platform, or influencer dashboard. The system should think like a "Personal Financial Operating System."

### User Profile
- Single-user system, India based, stable salary
- Uses Groww; invests in India and US markets (Mutual Funds & Stocks)
- Wants education and understanding, not to become an expert
- Uses New Tax Regime; wants LTCG/STCG understanding
- Wants Personal OS integration, Web first (Android later)
- React/Next.js ecosystem

### Product Philosophy
The system answers "What should I do?" and "Why should I do it?"
Every recommendation includes **Action**, **Reason**, and **Learn** (a 2-minute explanation). It must teach, not merely advise.

---

## 2. Hard Locks (Non-negotiable)

### Data Ingestion
- **Allowed:** CAMS CAS, KFin CAS, NSDL CAS, CDSL CAS, Groww CSV, Manual Input, SMS Import, UPI CSV Import
- **Not allowed:** Groww login automation, Playwright scraping, password scraping, browser automation

### Architecture
- One Supervisor, multiple Specialists. Specialists never talk to each other; all report to the Supervisor.

### Model Strategy (for LLM use)
- Day: cheap/free cloud models. Night: local Qwen 7B.
- Only one local model (Qwen 2.5 Coder 7B).
- OmniRoute integration is **out of scope** for this plan; handled separately by the user.

### Finance Philosophy
Always follow this priority order. Never reverse it:
1. Cashflow
2. Insurance
3. Emergency Fund
4. High Interest Debt
5. Goals
6. Investing

---

## 3. Module Structure & Tabs

Finance contains five tabs:
1. Overview
2. Investments
3. Debt & Liabilities
4. Tracker
5. Learning

**Trading does not exist in V1.** Goals are not a tab; they live on Overview (top-3 card) plus a full management surface under **Settings** (see Section 8.8 — Settings is not a tab, it's a header-level page for managing accounts, goals, insurance, and salary records).

---

## 4. Key Architecture Decisions (Final)

| Decision Area | Choice | Notes |
|---|---|---|
| Three.js Usage | Primary visual layer, 30–45 FPS cap, lazy loading, 2D fallback toggle. | Dependencies pinned in `package.json` (Section 8.1). |
| Process & Serving | FastAPI serves the static frontend (Next.js export) and API routes in production; separate dev servers with a proxy in development. | API base `/api/finance`. See Section 8.9 for dev/prod config. |
| State Management | No global store. `useState` + `fetch` with a 5-minute module-level cache, invalidated on mutation. | See Section 8.4 for the corrected invalidation logic. |
| UI Library | Shadcn/ui (copy-paste) + Tailwind CSS, custom F1 theme (dark carbon, neon red/yellow accents). | |
| Database | SQLite (`finance.db`), sole database. Protected via **OS-level disk encryption** (BitLocker / FileVault) + `chmod 600` + `.gitignore`. **SQLCipher explicitly rejected for V1** — see Section 13 for rationale. `PRAGMA foreign_keys = ON` set on every connection. | |
| File Upload & Manual Input | Web-based upload for CAS PDF, Groww CSV, UPI CSV, SMS text paste. Manual forms for all entities. | Every import path is idempotent — see Section 10. |
| Price Data | `yfinance` for stocks/ETFs, `mftool` for Indian Mutual Funds — **not a single linear fallback chain**, branched by asset type (Section 10). Alpha Vantage as a secondary fallback for stocks/ETFs only. Cached price as the final fallback for everything. | |
| RAG | Local FAISS vector store, `sentence-transformers/all-MiniLM-L6-v2` embeddings. Public educational content only — never user financial data. | |
| Night System | `night_worker.py`, runs at 23:00 IST via cron/Task Scheduler, calls local LLM via Ollama, refreshes prices, backs up the DB. | See Section 11. |
| Agents | Supervisor + Specialists as Python services. Deterministic calculations; LLM only for narrative. OmniRoute calls left as placeholders. | |
| Modularity | Each UI card is standalone, fetches its own data, designed for future replacement with Prometheus/Grafana. | |
| Deletion Model | Soft-delete (`archived_at`) by default for all user-managed entities. Hard delete is a separate, rarer operation, blocked while dependent rows exist. | See Section 6 and Section 7. |

---

## 5. Folder Structure

```
finance-os/
├── backend/
│   ├── main.py                    # FastAPI app, static file serving, sets PRAGMA foreign_keys=ON
│   ├── requirements.txt           # fastapi, uvicorn, yfinance, mftool, tenacity, sentence-transformers, faiss-cpu, python-multipart
│   ├── .env                       # API keys, paths — gitignored
│   ├── data/
│   │   ├── finance.db             # SQLite database — gitignored, chmod 600
│   │   ├── backups/                # NEW: nightly rotated backups (last 7)
│   │   ├── vector_store/          # FAISS index files — gitignored
│   │   └── exports/                # CSV exports (optional)
│   ├── routers/
│   │   ├── overview.py
│   │   ├── investments.py
│   │   ├── debt.py
│   │   ├── tracker.py
│   │   ├── learning.py
│   │   ├── health.py
│   │   ├── accounts.py            # NEW
│   │   ├── goals.py               # NEW
│   │   ├── insurance.py           # NEW
│   │   ├── salary.py              # NEW
│   │   └── imports.py             # cas, groww-csv, upi-csv, sms, manual
│   ├── services/
│   │   ├── calculations/
│   │   │   ├── net_worth.py
│   │   │   ├── cashflow.py
│   │   │   ├── portfolio.py
│   │   │   ├── debt.py
│   │   │   ├── emergency.py
│   │   │   ├── goals.py           # bounded probability formula
│   │   │   ├── scenario.py
│   │   │   └── holdings_upsert.py # NEW: weighted-avg-cost merge + lot dedup
│   │   ├── agents/
│   │   │   ├── supervisor.py      # includes sanitize_for_cloud_llm()
│   │   │   ├── investment_specialist.py
│   │   │   ├── debt_specialist.py
│   │   │   ├── tracker_specialist.py
│   │   │   └── learning_specialist.py
│   │   ├── market_data.py         # branched fallback by asset type, retry via tenacity
│   │   ├── rag.py
│   │   └── db.py                  # connection helper, sets PRAGMA on every connection
│   ├── static/                    # Build output from frontend (next build --> out/)
│   └── scripts/
│       ├── import_cas.py          # also callable from the web upload endpoint
│       ├── import_groww.py
│       ├── import_upi.py
│       ├── import_sms.py
│       └── backfill_price_history.py   # NEW: one-time historical backfill per symbol
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # redirect to /finance
│   │   └── finance/
│   │       ├── layout.tsx          # nav
│   │       ├── page.tsx            # Overview (default at /finance)
│   │       ├── investments/page.tsx
│   │       ├── debt/page.tsx
│   │       ├── tracker/page.tsx
│   │       ├── learning/page.tsx
│   │       └── settings/page.tsx   # NEW: Accounts / Goals / Insurance / Salary management
│   ├── components/
│   │   ├── ui/                     # Shadcn/ui
│   │   ├── finance/
│   │   │   ├── cards/
│   │   │   ├── three/
│   │   │   ├── charts/
│   │   │   └── forms/              # NEW: wired to Settings page + modals
│   │   │       ├── AccountForm.tsx
│   │   │       ├── TransactionForm.tsx
│   │   │       ├── HoldingForm.tsx
│   │   │       ├── DebtForm.tsx
│   │   │       ├── GoalForm.tsx
│   │   │       └── InsuranceForm.tsx
│   │   └── layout/
│   ├── lib/
│   │   ├── api.ts                  # fetch wrapper, corrected cache invalidation
│   │   ├── cache.ts
│   │   └── types.ts
│   ├── styles/globals.css
│   ├── public/
│   ├── next.config.js              # output: 'export', dev-mode rewrite proxy
│   ├── tailwind.config.ts
│   └── package.json                # full pinned dependency list, Section 8.1
└── night_worker.py                 # nightly prices, backup rotation, data_health update
```

---

## 6. Database Schema (SQLite)

```sql
-- finance.db
-- PRAGMA foreign_keys = ON;  -- set in db.py on every connection, not just once at init

CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,              -- 'bank', 'demat', 'loan', 'credit_card', 'cash', 'other'
    institution TEXT,
    currency TEXT DEFAULT 'INR',
    archived_at TIMESTAMP DEFAULT NULL,   -- soft delete
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    amount REAL NOT NULL,            -- negative = expense, positive = income
    category TEXT,                   -- validated against a fixed enum in code, both backend and frontend import it from one shared constants file
    type TEXT,                       -- 'income', 'expense', 'transfer', 'investment', 'debt_payment'
    source TEXT,                     -- 'manual', 'groww', 'sms', 'cas', 'upi', 'other'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT
    -- RESTRICT, not CASCADE: an account with transactions cannot be hard-deleted,
    -- only archived. This is deliberate — see Section 13's deletion-model rationale.
);

CREATE TABLE holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    type TEXT,                       -- 'stock', 'mutual_fund', 'etf', 'bond', 'other'
    units REAL NOT NULL DEFAULT 0,
    avg_cost REAL DEFAULT 0,         -- maintained via weighted-average merge, see Section 10
    currency TEXT DEFAULT 'INR',
    direct_regular TEXT DEFAULT 'regular',
    benchmark TEXT,
    archived_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
    UNIQUE(account_id, symbol)       -- one row per symbol per account; re-imports UPDATE via upsert, never duplicate
);

CREATE TABLE lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holding_id INTEGER NOT NULL,
    purchase_date DATE NOT NULL,
    units REAL NOT NULL,
    cost_per_unit REAL NOT NULL,
    -- total_cost intentionally NOT stored — compute units * cost_per_unit on read,
    -- to avoid a derived column drifting out of sync with its source fields.
    source TEXT,                     -- 'manual', 'groww', 'sms', 'cas', 'upi'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(holding_id) REFERENCES holdings(id) ON DELETE CASCADE,
    UNIQUE(holding_id, purchase_date, units, cost_per_unit)
    -- This unique constraint is the idempotency guard for re-imported CSVs:
    -- an identical lot from a duplicate upload is silently skipped (see Section 10),
    -- not double-counted and not a hard error.
);

CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_amount REAL,
    current_amount REAL DEFAULT 0,
    target_date DATE,
    priority INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',    -- 'active', 'completed', 'paused'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lender TEXT NOT NULL,
    type TEXT,                       -- 'credit_card', 'personal_loan', 'home_loan', 'car_loan', 'other'
    outstanding REAL NOT NULL,
    interest_rate REAL,
    emi REAL,
    next_due DATE,
    remaining_months INTEGER,
    status TEXT DEFAULT 'active',    -- 'active', 'closed' (paid off)
    archived_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE insurance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,                       -- 'term', 'health', 'vehicle', 'other'
    provider TEXT,
    coverage_amount REAL,
    premium REAL,
    next_due DATE,
    archived_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE salary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monthly_gross REAL,
    monthly_net REAL,
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- "current" salary = row with MAX(effective_date) <= today; computed in calculations/cashflow.py
);

CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE,
    net_worth REAL,
    cash REAL,
    debt REAL,
    investments REAL,
    emergency_months REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Singleton table: exactly one row (id=1), holding current data-health state.
CREATE TABLE data_health (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cas_last_import DATE,
    price_last_refresh TIMESTAMP,
    sms_last_import DATE,
    unmatched_transactions INTEGER DEFAULT 0,
    missing_info TEXT,
    health_score TEXT,               -- 'high', 'medium', 'low'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO data_health (id) VALUES (1);   -- run once at schema init; all future writes are UPDATE ... WHERE id = 1

CREATE TABLE agent_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advice TEXT,
    user_decision TEXT,
    outcome TEXT,
    timestamp TIMESTAMP,
    reason TEXT,
    confidence REAL
);

CREATE TABLE playbooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    content TEXT,
    is_active INTEGER DEFAULT 0,     -- 1 = the currently live version for this name
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(name, version)
);

CREATE TABLE research_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holding_id INTEGER,
    note_type TEXT,                  -- 'what_is', 'benchmark', 'expense', 'risk', 'learn'
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(holding_id) REFERENCES holdings(id) ON DELETE CASCADE
);

CREATE TABLE benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    symbol TEXT UNIQUE,              -- e.g. '^NSEI' for Nifty 50 — shares price_history with holdings
    type TEXT,                       -- 'index', 'category_average'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Time-series price data. This is the ONLY price table — see note below on why
-- price_cache was deliberately dropped instead of kept alongside this one.
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,            -- matches holdings.symbol or benchmarks.symbol
    date DATE NOT NULL,
    price REAL NOT NULL,
    source TEXT,
    currency TEXT DEFAULT 'INR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)             -- also makes nightly refresh idempotent via INSERT OR IGNORE
);

-- "Latest price per symbol" is a VIEW over price_history, not a separate table.
-- Keeping a separate price_cache table alongside price_history would let the two
-- drift out of sync (the same redundant-derived-data risk as the old lots.total_cost
-- column) — so there is deliberately only one source of truth for prices.
CREATE VIEW latest_prices AS
SELECT symbol, price, date, source, currency
FROM price_history p1
WHERE date = (SELECT MAX(date) FROM price_history p2 WHERE p2.symbol = p1.symbol);

-- Indexes
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_holdings_account ON holdings(account_id);
CREATE INDEX idx_lots_holding ON lots(holding_id);
CREATE INDEX idx_price_history_symbol_date ON price_history(symbol, date);
```

---

## 7. API Endpoint Specifications

All endpoints prefixed with `/api/finance`. Responses are JSON. Every list endpoint (`GET` on a collection) excludes archived rows (`WHERE archived_at IS NULL`) unless an explicit `?include_archived=true` query param is passed.

### Overview
| Endpoint | Method | Description |
|---|---|---|
| `/overview/net-worth` | GET | Total assets, liabilities, net worth, 30-day trend from `snapshots`. |
| `/overview/cashflow` | GET | Current month income, expenses, EMIs, SIPs, surplus. |
| `/overview/portfolio-pulse` | GET | Current portfolio value, day change (via `latest_prices`), total gain/loss, allocation. |
| `/overview/emergency-fund` | GET | Current amount, target, months covered, gap. |
| `/overview/debt-status` | GET | Total debt, highest-interest debt, next EMI, list of active debts. |
| `/overview/surplus-allocation` | GET | Current month surplus and suggested split. |
| `/overview/goals` | GET | Top 3 active goals with progress and bounded probability (Section 10). |
| `/overview/top-actions` | GET | Max 3 recommended actions with Action/Reason/Learn. |
| `/overview/data-health` | GET | Reads the singleton `data_health` row. |

### Investments
| Endpoint | Method | Description |
|---|---|---|
| `/investments/holdings` | GET | All active holdings with calculated fields. |
| `/investments/holdings/{id}` | GET / PUT / DELETE | Retrieve / correct a manual field / hard-delete (only if the holding has no lots — otherwise 409, use archive instead). |
| `/investments/holdings/{id}/archive` | POST | Soft-delete (sets `archived_at`). |
| `/investments/quality` | GET | Issues: regular plans, high TER, concentration, overlap. |
| `/investments/visuals/asset-allocation` | GET | Asset class allocation. |
| `/investments/visuals/geography` | GET | Geographic split. |
| `/investments/visuals/target-vs-actual` | GET | Target vs. actual allocation. |
| `/investments/visuals/portfolio-vs-benchmark` | GET | Uses `price_history` for both portfolio value and benchmark series — requires backfill (Section 10) to have run. |
| `/investments/visuals/rolling-returns` | GET | Uses `price_history`. |
| `/investments/visuals/drawdown` | GET | Uses `price_history`. |
| `/investments/visuals/treemap` | GET | Holdings data for treemap. |
| `/investments/visuals/fund-overlap` | GET | Overlap matrix for mutual funds. |
| `/investments/visuals/expense-ratio` | GET | Expense ratios. |
| `/investments/visuals/sip-calendar` | GET | Upcoming SIP dates. |
| `/investments/visuals/concentration` | GET | Concentration score. |
| `/investments/research/{holding_id}` | GET | Educational content for a holding. |

### Debt
| Endpoint | Method | Description |
|---|---|---|
| `/debt/overview` | GET | Summary. |
| `/debt/table` | GET | All active debts. |
| `/debt/table/{id}` | GET / PUT / DELETE | Retrieve / update / hard-delete (only if no payment history recorded elsewhere — otherwise archive). |
| `/debt/table/{id}/archive` | POST | Soft-delete or mark `status='closed'` if paid off. |
| `/debt/payoff-plan` | GET | Suggested payoff order (avalanche/snowball). |
| `/debt/simulate` | POST | Body: `{extra_payment, salary_increase, bonus}`. Returns months saved, interest saved. |
| `/debt/learning/{topic}` | GET | Learning content. |

### Tracker
| Endpoint | Method | Description |
|---|---|---|
| `/tracker/transactions` | GET | Transactions with filters (date range, category, account). |
| `/tracker/transactions/{id}` | GET / PUT / DELETE | Retrieve / correct / delete a single transaction (hard delete is fine here — transactions are individually correctable by design, unlike accounts/holdings). |
| `/tracker/categories` | GET | Spending by category. |
| `/tracker/recurring` | GET | Detected recurring expenses. |
| `/tracker/trends` | GET | Monthly spending trend. |
| `/tracker/insights` | GET | Leak-of-the-week, biggest category, etc. |

### Learning
| Endpoint | Method | Description |
|---|---|---|
| `/learning/topics` | GET | Learning topics. |
| `/learning/topic/{topic_id}` | GET | Content for a topic. |
| `/learning/personalized` | GET | Personalized lessons based on portfolio/debt. |

### Imports & Data Health
| Endpoint | Method | Description |
|---|---|---|
| `/import/manual` | POST | Adds a manual entry (account, transaction, holding, debt, goal, insurance). |
| `/import/groww-csv` | POST | File upload. Parses Groww CSV, upserts holdings via weighted-avg-cost merge, dedupes lots (Section 10). |
| `/import/cas` | POST | File upload (PDF). Parses CAS, same upsert/dedupe path as above. |
| `/import/upi-csv` | POST | File upload. Parses UPI statement, adds transactions (dedupes by date+amount+description). |
| `/import/sms` | POST | Body: `{text}`. Parses SMS, adds a transaction. |
| `/health` | GET | Reads the singleton `data_health` row. |

### Entity Management (Accounts / Goals / Insurance / Salary)
| Endpoint | Method | Description |
|---|---|---|
| `/accounts` | GET / POST | List active accounts / create one. |
| `/accounts/{id}` | GET / PUT / DELETE | Retrieve / update / hard-delete (blocked by `ON DELETE RESTRICT` while transactions or holdings reference it — returns 409 with a message pointing to archive). |
| `/accounts/{id}/archive` | POST | Soft-delete — the default "remove an account" path. |
| `/goals` | GET / POST | List active goals / create one. |
| `/goals/{id}` | GET / PUT / DELETE | Retrieve / update / delete a goal. |
| `/insurance` | GET / POST | List active policies / create one. |
| `/insurance/{id}` | GET / PUT / DELETE | Retrieve / update / delete. |
| `/insurance/{id}/archive` | POST | Soft-delete. |
| `/salary` | GET / POST | Get current salary (`MAX(effective_date) <= today`) / add a new record (never edits history — a raise is a new row). |

---

## 8. Frontend Implementation Details

### 8.1 Dependencies (`package.json`)

```json
{
  "name": "finance-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.x",
    "react": "18.x",
    "react-dom": "18.x",
    "@react-three/fiber": "^8.15.0",
    "@react-three/drei": "^9.88.0",
    "three": "^0.160.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "lucide-react": "^0.4.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/react": "^18.0.0",
    "@types/node": "^20.0.0",
    "@types/three": "^0.160.0"
  }
}
```

**Note:** there is no separate `"export"` script. With `output: 'export'` set in `next.config.js` (Section 8.9), `next build` performs the static export automatically as of Next.js 13.4+ — running a standalone `next export` command alongside that setting throws an error. Use `npm run build` only.

### 8.2 F1 Theme (`tailwind.config.ts`)

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        carbon: { DEFAULT: '#1a1a1a', light: '#2d2d2d', dark: '#0f0f0f' },
        racing: { red: '#e10600', yellow: '#f9a800', blue: '#00d2ff', green: '#00ff87', silver: '#c0c0c0' },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'neon-red': '0 0 10px rgba(225, 6, 0, 0.5)',
        'neon-blue': '0 0 10px rgba(0, 210, 255, 0.5)',
      },
    },
  },
  plugins: [],
}
export default config
```

### 8.3 Global Styles (`app/globals.css`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { --background: #0a0a0a; --foreground: #e5e7eb; }
body { background-color: var(--background); color: var(--foreground); font-family: 'Inter', sans-serif; }

.card {
  background: linear-gradient(145deg, #1a1a1a 0%, #0f0f0f 100%);
  border: 1px solid #2d2d2d;
  border-radius: 8px;
  padding: 1.5rem;
  position: relative;
  overflow: hidden;
}
.card:hover { border-color: #e10600; box-shadow: 0 0 12px rgba(225, 6, 0, 0.3); transition: all 0.3s ease; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.card-title { font-size: 0.875rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #c0c0c0; }
.value-large { font-size: 2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; color: #ffffff; }
.value-positive { color: #00ff87; }
.value-negative { color: #e10600; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background-color: #00ff87; box-shadow: 0 0 6px #00ff87; }
```

### 8.4 API Client — Cache with Corrected Invalidation

```typescript
import { useState, useEffect } from 'react';

const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000;
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export function invalidateCache(prefix: string) {
  for (const key of cache.keys()) {
    if (key.startsWith(prefix)) cache.delete(key);
  }
}

export async function fetchFinanceData<T>(endpoint: string, options?: RequestInit): Promise<T> {
  // Explicitly detect mutations by method name — do NOT infer "is this a GET"
  // from the absence of options.method, since fetch defaults to GET when
  // method is omitted entirely and an unrelated options object (e.g. custom
  // headers on a GET) would otherwise be wrongly treated as a mutation.
  const method = (options?.method ?? 'GET').toUpperCase();
  const isMutation = MUTATING_METHODS.has(method);

  if (!isMutation) {
    const cached = cache.get(endpoint);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) return cached.data as T;
  }

  const response = await fetch(endpoint, options);
  if (!response.ok) throw new Error(`Failed to fetch ${endpoint}`);
  const data = await response.json();

  if (!isMutation) {
    cache.set(endpoint, { data, timestamp: Date.now() });
  } else {
    invalidateCache('/api/finance/overview');
    invalidateCache('/api/finance/investments');
    invalidateCache('/api/finance/debt');
    invalidateCache('/api/finance/tracker');
    invalidateCache('/api/finance/health');
    invalidateCache('/api/finance/accounts');
    invalidateCache('/api/finance/goals');
    invalidateCache('/api/finance/insurance');
  }
  return data;
}

export function useFinanceData<T>(endpoint: string) {
  const [state, setState] = useState<{ data?: T; isLoading: boolean; error?: string }>({ isLoading: true });
  useEffect(() => {
    let cancelled = false;
    fetchFinanceData<T>(endpoint)
      .then((data) => { if (!cancelled) setState({ data, isLoading: false }); })
      .catch((err) => { if (!cancelled) setState({ error: err.message, isLoading: false }); });
    return () => { cancelled = true; };
  }, [endpoint]);
  return state;
}
```

### 8.5 Layout & Navigation (`app/finance/layout.tsx`)

```tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const tabs = [
  { name: 'Overview', href: '/finance' },
  { name: 'Investments', href: '/finance/investments' },
  { name: 'Debt', href: '/finance/debt' },
  { name: 'Tracker', href: '/finance/tracker' },
  { name: 'Learning', href: '/finance/learning' },
];

export default function FinanceLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="min-h-screen bg-carbon-dark">
      <header className="border-b border-carbon-light bg-carbon">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="status-dot"></span>
            <h1 className="text-xl font-bold text-white tracking-tight">FINANCE OS</h1>
          </div>
          <nav className="flex items-center space-x-1">
            {tabs.map((tab) => {
              const isActive = pathname === tab.href;
              return (
                <Link key={tab.name} href={tab.href}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${isActive ? 'bg-racing-red text-white shadow-neon-red' : 'text-gray-400 hover:text-white hover:bg-carbon-light'}`}>
                  {tab.name}
                </Link>
              );
            })}
            <Link href="/finance/settings" className="ml-2 px-3 py-2 rounded-md text-sm text-gray-400 hover:text-white hover:bg-carbon-light">
              Settings
            </Link>
          </nav>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
}
```

*(Note: the old `isActive` check had a dead branch testing for a `/finance/overview` route that never existed in the folder structure — simplified above to a plain equality check.)*

### 8.6 Overview Page (`app/finance/page.tsx`)

```tsx
import NetWorthCard from '@/components/finance/cards/NetWorthCard';
import CashflowCard from '@/components/finance/cards/CashflowCard';
import PortfolioPulseCard from '@/components/finance/cards/PortfolioPulseCard';
import EmergencyFundCard from '@/components/finance/cards/EmergencyFundCard';
import DebtStatusCard from '@/components/finance/cards/DebtStatusCard';
import SurplusAllocationCard from '@/components/finance/cards/SurplusAllocationCard';
import GoalsCard from '@/components/finance/cards/GoalsCard';
import TopActionsCard from '@/components/finance/cards/TopActionsCard';
import DataHealthCard from '@/components/finance/cards/DataHealthCard';

export default function OverviewPage() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <NetWorthCard />
        <CashflowCard />
        <PortfolioPulseCard />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <EmergencyFundCard />
        <DebtStatusCard />
        <SurplusAllocationCard />
      </div>
      <GoalsCard />
      <TopActionsCard />
      <DataHealthCard />
    </div>
  );
}
```

### 8.7 Example Card — `NetWorthCard.tsx` (corrected sparkline)

```tsx
'use client';
import { useFinanceData } from '@/lib/api';
import type { NetWorthData } from '@/lib/types';
import Card from '../Card';
import Skeleton from '../Skeleton';

export default function NetWorthCard() {
  const { data, isLoading, error } = useFinanceData<NetWorthData>('/api/finance/overview/net-worth');
  if (isLoading) return <Card title="Net Worth"><Skeleton /></Card>;
  if (error) return <Card title="Net Worth">Error</Card>;

  const values = data.trend.map(p => p.net_worth);
  const hasData = values.length > 0;
  const max = hasData ? Math.max(...values, 0) : 1;
  const min = hasData ? Math.min(...values, 0) : 0;
  // Guard against a flat trend (max === min), which would otherwise divide by zero.
  const range = (max - min) || 1;

  return (
    <Card title="Net Worth">
      <div className="value-large">₹ {data.net_worth.toLocaleString()}</div>
      <div className="text-sm text-gray-400 mt-2">
        Assets: ₹{data.assets.toLocaleString()} | Liabilities: ₹{data.liabilities.toLocaleString()}
      </div>
      {hasData && (
        <div className="mt-4">
          <svg width="100%" height="40">
            {data.trend.map((point, i) => {
              const x = data.trend.length > 1 ? (i / (data.trend.length - 1)) * 100 : 50;
              const y = 35 - ((point.net_worth - min) / range) * 30;
              return <circle key={i} cx={`${x}%`} cy={y} r="2" fill="#00d2ff" />;
            })}
          </svg>
        </div>
      )}
    </Card>
  );
}
```

*(Other cards follow the same pattern: fetch via `useFinanceData`, handle loading/error/empty states explicitly.)*

### 8.8 Settings Page (`app/finance/settings/page.tsx`) — closes the "modeled but no workflow" gap

```tsx
'use client';
import { useState } from 'react';
import AccountForm from '@/components/finance/forms/AccountForm';
import GoalForm from '@/components/finance/forms/GoalForm';
import InsuranceForm from '@/components/finance/forms/InsuranceForm';
import { useFinanceData, fetchFinanceData } from '@/lib/api';

const SECTIONS = ['Accounts', 'Goals', 'Insurance', 'Salary'] as const;

export default function SettingsPage() {
  const [active, setActive] = useState<typeof SECTIONS[number]>('Accounts');

  return (
    <div className="space-y-6">
      <div className="flex space-x-2">
        {SECTIONS.map((s) => (
          <button key={s} onClick={() => setActive(s)}
            className={`px-3 py-1.5 rounded-md text-sm ${active === s ? 'bg-racing-red text-white' : 'text-gray-400 hover:text-white'}`}>
            {s}
          </button>
        ))}
      </div>

      {active === 'Accounts' && <AccountsSection />}
      {active === 'Goals' && <GoalsSection />}
      {active === 'Insurance' && <InsuranceSection />}
      {active === 'Salary' && <SalarySection />}
    </div>
  );
}

function AccountsSection() {
  const { data, isLoading } = useFinanceData<any[]>('/api/finance/accounts');
  const archive = async (id: number) => {
    await fetchFinanceData(`/api/finance/accounts/${id}/archive`, { method: 'POST' });
  };
  return (
    <div className="space-y-4">
      <AccountForm onSaved={() => {/* list re-fetches via cache invalidation */}} />
      {!isLoading && data?.map((a) => (
        <div key={a.id} className="card flex justify-between items-center">
          <span>{a.name} — {a.type}</span>
          <button onClick={() => archive(a.id)} className="text-sm text-gray-400 hover:text-racing-red">Archive</button>
        </div>
      ))}
    </div>
  );
}

// GoalsSection, InsuranceSection, SalarySection follow the identical
// list + form + archive pattern shown above.
function GoalsSection() { /* same pattern as AccountsSection, using GoalForm + /api/finance/goals */ return null; }
function InsuranceSection() { /* same pattern, using InsuranceForm + /api/finance/insurance */ return null; }
function SalarySection() { /* list of salary history + "add new record" form; never edits past rows */ return null; }
```

**`GoalsCard.tsx` must link here** — this is the piece that actually connects the Overview summary to the management surface:

```tsx
// inside GoalsCard.tsx, in the card header:
<Link href="/finance/settings?tab=goals" className="text-xs text-gray-400 hover:text-white">
  Manage all goals →
</Link>
```

### 8.9 Dev/Prod Configuration (`next.config.js`)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  async rewrites() {
    // Only takes effect under `next dev` — `next build` with output:'export'
    // produces fully static files with no rewrite engine, so this block is
    // inert (and harmless) in production.
    if (process.env.NODE_ENV === 'development') {
      return [
        { source: '/api/finance/:path*', destination: 'http://127.0.0.1:8000/api/finance/:path*' },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
```

Development: run FastAPI on `:8000` and `next dev` on `:3000` — the rewrite proxies API calls so relative `fetch('/api/finance/...')` calls work identically in dev and prod. Production: `next build` exports static files into `frontend/out/`, copied into `backend/static/`; FastAPI serves both the static site and the API from one process/port.

### 8.10 Three.js Integration Example

```tsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Sphere } from '@react-three/drei';

export default function AllocationPucks({ data }) {
  return (
    <Canvas dpr={[1, 2]} camera={{ position: [0, 0, 5] }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} />
      {data.map((item, i) => (
        <Sphere key={i} args={[item.percentage / 10, 32, 32]} position={[i * 1.5 - 2, 0, 0]}>
          <meshStandardMaterial color={item.color} />
        </Sphere>
      ))}
      <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={0.5} />
    </Canvas>
  );
}
```

All Three.js components are lazy-loaded with `next/dynamic` and `ssr: false`.

---

## 9. Agent Design (Supervisor & Specialists)

### 9.1 Supervisor Agent
- **Role:** Coordinates all specialists, aggregates recommendations, prioritizes top actions.
- **Inputs:** Data from calculation services, user context, playbooks, memory.
- **Outputs:** Ranked list of actions (max 3) with Action, Reason, Learn link.
- **Implementation:** `services/agents/supervisor.py`.
- **LLM usage:** Only for narrative generation; ranking is deterministic.
- **New responsibility:** hosts `sanitize_for_cloud_llm(payload: dict) -> dict`, the single enforcement point for the field allow-list in Section 13. Every specialist that needs to call a day-time cloud model routes its payload through this function first — the rule is enforced in code, not left as a convention each specialist has to remember independently.

### 9.2 Investment Specialist
- **Role:** Analyzes portfolio health — regular plans, high TER, concentration, overlap.
- **Subagents:** `HoldingsAnalyzer` (current value, gain/loss, weight), `QualityChecker` (flags issues), `AllocationDrift` (actual vs. target).
- **Outputs:** List of issues with problem, impact, recommendation, learn link.

### 9.3 Debt Specialist
- **Role:** Recommends payoff order, simulates scenarios.
- **Subagents:** `AvalancheCalculator` (by interest rate), `SnowballCalculator` (by outstanding amount), `Simulator` (months/interest saved).

### 9.4 Tracker Specialist
- **Role:** Spending patterns, leaks, recurring expenses.
- **Subagents:** `RecurringDetector`, `LeakFinder`, `BudgetDrift`.

### 9.5 Learning Specialist
- **Role:** Educational content via RAG.
- **Subagents:** `Retriever` (FAISS query), `Personalizer` (lessons based on portfolio/debt).

### 9.6 Clarification Specialist (future)
- **Role:** Asks the user for missing information when needed. Not implemented in V1.

---

## 10. Calculation Services (Deterministic, no LLM)

Located in `backend/services/calculations/`.

### Net Worth, Cashflow, Portfolio, Debt, Emergency Fund
Standard formulas: assets − liabilities; income − expenses − EMIs − SIPs = surplus; current value / day change / allocation %; total outstanding / highest interest / payoff schedule; target = 6 × monthly expenses, gap.

### Goals — bounded probability (fixes the original unbounded formula)

```python
def goal_probability(current: float, target: float, months_left: int, total_months: int) -> float:
    if target <= 0:
        return 0.0
    if months_left <= 0:
        return 100.0 if current >= target else 0.0
    time_factor = min(months_left / total_months, 1.0)   # 0..1
    progress = min(current / target, 1.0)                 # 0..1
    probability = (progress * 0.7 + time_factor * 0.3) * 100
    return min(100.0, max(0.0, probability))
```

### Holdings Upsert — weighted-average cost merge + idempotent lot import
This is the logic that makes `UNIQUE(account_id, symbol)` on `holdings` (Section 6) actually usable instead of just a constraint that throws errors on re-import:

```python
def upsert_holding(account_id, symbol, name, type_, new_units, new_cost_per_unit, currency, source, purchase_date):
    existing = get_holding(account_id, symbol)

    if existing is None:
        holding_id = insert_holding(account_id, symbol, name, type_, new_units, new_cost_per_unit, currency)
    else:
        total_units = existing.units + new_units
        if total_units == 0:
            merged_avg_cost = 0
        else:
            merged_avg_cost = (
                (existing.units * existing.avg_cost) + (new_units * new_cost_per_unit)
            ) / total_units
        update_holding(existing.id, units=total_units, avg_cost=merged_avg_cost)
        holding_id = existing.id

    # Idempotent lot insert: the UNIQUE(holding_id, purchase_date, units, cost_per_unit)
    # constraint on `lots` means re-uploading the same CSV a second time hits this same
    # exact lot row and is silently skipped — no double-counting, no crash.
    try:
        insert_lot(holding_id, purchase_date, new_units, new_cost_per_unit, source)
    except UniqueConstraintViolation:
        pass  # identical lot already recorded — this is the expected re-import path

    if not price_history_exists(symbol):
        backfill_price_history(symbol, type_)  # see below
```

### Price History Backfill — closes the gap where rolling-returns/drawdown had no historical data

```python
def backfill_price_history(symbol: str, asset_type: str):
    """
    Runs once per symbol, the first time it's ever imported, so the
    rolling-returns, drawdown, and portfolio-vs-benchmark endpoints have
    data from day one instead of slowly accumulating one point per night.
    """
    if asset_type in ("stock", "etf"):
        history = fetch_yfinance_history(symbol, period="2y")
    elif asset_type == "mutual_fund":
        history = fetch_mftool_nav_history(symbol, period="2y")
    else:
        return
    bulk_insert_price_history(symbol, history)  # uses INSERT OR IGNORE, safe to re-run
```

### Market Data — fallback branched by asset type (not a single linear chain)

```python
import tenacity

@tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
def _fetch_yfinance(symbol):
    ...

@tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=2, max=10))
def _fetch_mftool(symbol):
    ...

def get_current_price(symbol: str, asset_type: str) -> float | None:
    """
    yfinance and mftool are not interchangeable fallbacks for each other —
    mftool only knows AMFI mutual fund NAVs, yfinance only knows tickers.
    Branch by asset type instead of chaining them linearly.
    """
    if asset_type in ("stock", "etf"):
        try:
            return _fetch_yfinance(symbol)
        except Exception:
            try:
                return fetch_alpha_vantage(symbol)
            except Exception:
                return get_last_cached_price(symbol)  # from the latest_prices view
    elif asset_type == "mutual_fund":
        try:
            return _fetch_mftool(symbol)
        except Exception:
            return get_last_cached_price(symbol)
    else:
        return get_last_cached_price(symbol)
```

### Scenario Simulator
Pure math for extra payments, salary changes — no LLM involvement.

---

## 11. Night System & RAG

### Night Worker (`night_worker.py`) — runs at 23:00 IST via cron / Task Scheduler
1. Connects to SQLite (`PRAGMA foreign_keys = ON`).
2. Refreshes `latest_prices` inputs for all active holdings + benchmarks (branched fallback, Section 10).
3. Weekly (not nightly): re-runs `backfill_price_history`-style historical refresh so `price_history` stays current — inserts use `INSERT OR IGNORE`, so re-running is naturally idempotent thanks to the `UNIQUE(symbol, date)` constraint.
4. Generates a portfolio review using the local LLM (placeholder for OmniRoute/Ollama).
5. Updates `snapshots` (new row per day) and `data_health` (`UPDATE ... WHERE id = 1`, never `INSERT`).
6. Compresses `agent_memory` (trims/summarizes rows older than a configurable window).
7. Writes `research_notes`.
8. **New:** copies `finance.db` into `backend/data/backups/finance_YYYYMMDD.db`, keeping the last 7 dated copies and deleting older ones.

### RAG Implementation
- **Vector store:** FAISS index in `backend/data/vector_store/`.
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (384 dims).
- **Ingestion:** chunk Zerodha Varsity PDFs/Markdown, add to index.
- **Retrieval:** `services/rag.py` queries the index, returns top-k chunks.
- **Security:** only public educational content is ever embedded — no user transaction data, account names, or holdings go into the vector store.

---

## 12. Data Health & Failure Modes

### Data Health Scoring
- **High:** all recent imports present, prices fresh, no missing info.
- **Medium:** some stale data, minor gaps.
- **Low:** missing critical data (salary, goals, insurance).

### Failure Modes
- **Price API down:** use `latest_prices` (last cached value); show "—" if none exists.
- **CAS parse fails:** keep previous holdings, alert the user, don't wipe existing data.
- **LLM down:** fall back to rule-based (non-narrative) recommendations.
- **Night worker didn't run (laptop off):** `data_health.price_last_refresh` staleness is surfaced on the Overview `DataHealthCard`, not silently ignored.

---

## 13. Security

### Field allow-list for cloud LLM calls (Day-time, cheap/free models)
Never sent to any cloud model: account numbers, PAN, individual transaction descriptions, account/holding names, lender names, or ticker symbols. Only aggregated, non-identifying figures may be sent — e.g., portfolio allocation percentages, debt totals by category, category-level spending sums. **This is enforced centrally**: every specialist routes its outbound payload through `supervisor.sanitize_for_cloud_llm()` (Section 9.1) rather than each specialist independently remembering the rule.

### Local LLM (night, Ollama)
May receive more contextual detail than the cloud path, but still never PAN or bank account numbers — those are never passed to any LLM, local or cloud, under any circumstance.

### Database protection — decision locked in for V1
**SQLite + OS-level disk encryption (BitLocker on Windows / FileVault on Mac) + `chmod 600 finance.db` + a `.gitignore` entry for `finance.db`, `data/backups/`, `data/vector_store/`, and `.env`.**

SQLCipher was considered and explicitly rejected for V1: it requires swapping the stdlib `sqlite3` driver for `pysqlcipher3` across the entire backend from Phase 0 onward, plus key-management code — real implementation risk for a 7B local model, for a single-user local app whose primary threat model ("laptop lost or stolen") is already covered by OS-level disk encryption. Revisit SQLCipher only if the app starts syncing to a second device or a remote server, since disk encryption stops protecting the data the moment it leaves the machine.

### Backups
Nightly, rotated copies of `finance.db` (last 7) via `night_worker.py` (Section 11) — not a substitute for off-machine backup, but enough to recover from a bad import or accidental hard-delete.

### Auth
No auth on any endpoint in V1 (localhost-only). Endpoints are written to be stateless so a JWT middleware can be added later without a redesign — a placeholder middleware exists in `main.py` that currently allows all requests, ready to be switched on before any non-localhost (e.g., Android) access is enabled.

### File upload safety
Uploaded CAS PDFs and CSVs are size-limited (e.g., 10MB) and validated by content/structure before parsing, not executed or evaluated as code.

---

## 14. Implementation Order (Chronological Tasks, with Testing Gates)

Every phase ends with a gate. Do not proceed to the next phase until the gate passes.

### Phase 0: Project Initialization & Environment
1. Set up backend project (FastAPI, virtualenv, `requirements.txt`) — confidence 5
2. Set up frontend (Next.js, Tailwind, full `package.json` from Section 8.1) — confidence 5
3. Configure SQLite connection helper with `PRAGMA foreign_keys = ON` on every connection — confidence 5
4. Create schema with all constraints, the singleton `data_health` init row, and the `latest_prices` view — confidence 5
5. Set up OS-level disk encryption + `.gitignore` for `finance.db`, backups, vector store, `.env` — confidence 5

**Gate:** database file created; `PRAGMA foreign_keys` confirmed ON via a test insert that violates a FK and expects a rejection; `.gitignore` verified to exclude sensitive paths.

### Phase 1: Data Ingestion & CRUD (Backend)
1. Implement market data service with branched fallback + retry (Section 10) — confidence 4
2. Implement CRUD endpoints for accounts, transactions, holdings, debts, goals, insurance, salary (Section 7) — confidence 5
3. Implement `upsert_holding` (weighted-avg-cost merge + idempotent lot insert) — confidence 4
4. Implement `backfill_price_history`, wired to run on first import of any symbol — confidence 3
5. Implement import endpoints: Groww CSV, CAS PDF, UPI CSV, SMS — confidence 4

**Gate:** upload the same sample CSV twice — units/avg_cost update correctly once, no duplicate lots, no crash. Confirm `price_history` has 2 years of backfilled data for a newly imported symbol.

### Phase 2: Overview Tab
1. Backend endpoints for Overview cards — confidence 4
2. Frontend layout and navigation (Section 8.5) — confidence 4
3. Build individual Overview cards, with explicit empty/error states — confidence 5
4. Integrate Three.js hero visualizations (lazy-loaded, `ssr: false`) — confidence 3

**Gate:** load Overview with zero data (fresh DB) and confirm no crashes, no `-Infinity`/`NaN` renders.

### Phase 3: Investments Tab
1. Backend endpoints for Investments — confidence 4
2. Holdings table UI with edit/archive (not hard delete by default) — confidence 5
3. Quality panel — confidence 4
4. Visuals with Three.js — confidence 3
5. Research view — confidence 4

**Gate:** confirm `rolling-returns` and `drawdown` render real data immediately after import, using the Phase 1 backfill — not just after several nightly runs.

### Phase 4: Debt Tab
1. Debt backend, including archive/close-when-paid-off — confidence 5
2. Debt UI — confidence 4
3. Debt learning content — confidence 4

**Gate:** run `/debt/simulate` against sample data, confirm months/interest saved are sane.

### Phase 5: Tracker Tab
1. Transaction backend with full CRUD (hard delete allowed here, unlike accounts/holdings) — confidence 5
2. Recurring detection — confidence 3
3. Insights generation — confidence 4
4. Tracker UI — confidence 5

**Gate:** edit and delete a transaction from the UI, confirm cache invalidates and Overview reflects the change without a manual refresh.

### Phase 6: Learning Tab & RAG
1. RAG ingestion — confidence 3
2. Learning backend — confidence 4
3. Learning UI — confidence 4

**Gate:** query a topic, confirm retrieved content is relevant and no user financial data appears in retrieved chunks.

### Phase 7: Data Health, Scenario Lab, Settings
1. Data health backend (singleton `UPDATE`, never `INSERT`) — confidence 4
2. Scenario simulator UI — confidence 5
3. **Settings page** (Accounts / Goals / Insurance / Salary tabs, Section 8.8), wired to CRUD + archive endpoints — confidence 4
4. Wire "Manage all goals →" (and equivalent) links from Overview cards to Settings — confidence 4

**Gate:** create, edit, and archive an account, a goal, and an insurance policy entirely through the UI — no direct DB access required for any of it.

### Phase 8: Night Worker & Polish
1. Night worker script: prices, singleton `data_health` update, weekly `price_history` refresh — confidence 4
2. **Nightly backup rotation** (last 7 copies) — confidence 4
3. Performance optimization (lazy loading) — confidence 3
4. Full end-to-end testing and bug fixes — confidence 3

**Gate:** simulate a laptop-off night (skip the scheduled run) and confirm `DataHealthCard` surfaces the staleness instead of silently showing old data as current.

---

## 15. Local Model Recommendation & Coding Aids

### Recommended Model
- Qwen 2.5 Coder 7B (Q4_K_M) via Ollama.
- Temperature = 0.1 for deterministic code generation.
- At least a 4K context window.

### Coding Aids
- Continue.dev (VS Code extension) to give file context to the local model.
- Aider for direct file editing with git diff control.
- Provide exact file paths, code snippets, and error messages when prompting — feed one phase task at a time, not the whole plan at once.
- After each phase, run the gate checks in Section 14 before moving on — do not let the model self-report "done" without an explicit check.

---

## 16. Confidence Summary

| Component | Confidence (1–5) |
|---|---|
| Database & constraints | 5 |
| FastAPI endpoints | 5 |
| Next.js static export + Shadcn | 4 |
| Holdings upsert / lot dedup | 4 |
| Price history backfill | 3 |
| Three.js integration | 3 |
| RAG (FAISS) | 3 |
| Night worker & LLM integration | 4 |
| F1 aesthetic & animations | 4 |
| Settings/entity management UI | 4 |
| Overall feasibility with local Qwen | 3 |

---

## 17. Next Steps
1. Set up the project skeleton (folders, virtualenv, Next.js init) per Phase 0.
2. Feed Phase 0 to Qwen 2.5 Coder as a single, scoped task — not the whole document at once.
3. Run the Phase 0 gate before starting Phase 1.
4. Proceed phase by phase, gate by gate, through Phase 8.
5. Use Continue.dev to keep the local model's file context accurate as the codebase grows.

---

## Appendix: Changelog (human reference only — not part of the implementation spec)

- **v1 → v2:** Added missing CAS/UPI import endpoints; added `price_history` table; added `UNIQUE` constraints on `holdings` and `data_health`; added `PRAGMA foreign_keys = ON`; fixed the goals-probability formula; added dev/prod rewrite proxy; added cache invalidation; added CRUD for previously read-only entities; operationalized the LLM field allow-list; added phase-by-phase testing gates.
- **v2 → v3 (this document):** Closed the gaps v2 left half-open — added the actual weighted-avg-cost upsert + idempotent lot dedup logic (not just a constraint that threw errors); added the one-time `price_history` backfill so time-series endpoints have data from day one, not just going forward; branched the `yfinance`/`mftool` fallback by asset type instead of chaining them linearly; fixed a second divide-by-zero in the sparkline (flat trend, not just empty trend); fixed a logic bug in cache-invalidation's method detection; removed a conflicting `next export` script alongside `output: 'export'`; replaced blanket `ON DELETE CASCADE` with soft-delete (`archived_at`) as the default deletion model, reserving hard delete/cascade for a separate, restricted path; locked in the SQLCipher-vs-OS-encryption decision instead of deferring it; added the Settings page and wired it to the Overview cards it was supposed to support; added nightly backup rotation.
