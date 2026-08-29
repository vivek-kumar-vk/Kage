# Phase 0 — Foundations & shared contracts

Greenfield app at `finance-os/`. Backend FastAPI + stdlib `sqlite3` (Python 3.11).
Frontend Next 15 static export + React 19 + Three.js + Shadcn/ui + Tailwind.
This phase writes no business logic — only the skeleton, the schema, the DB
helper, shared constants, and the perms/gitignore/decision records.

> You do NOT have the master plan file in context. Every literal block you must
> reproduce is embedded BELOW. Reproduce those blocks EXACTLY.

## META-FIX (applies to every task, every phase)
For every fix, also implement the thing one step downstream that consumes it.
A UNIQUE constraint needs its upsert. A new table needs its backfill. A patched
edge case needs its sibling edge case in the same function. A new VIEW needs
every caller switched to it. A locked-in decision needs its deployment check.
Do not stop at the reported symptom.

---

## BLOCK A — `backend/scripts/schema.sql` (emit VERBATIM, whole block)

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,
    institution TEXT,
    currency TEXT DEFAULT 'INR',
    archived_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    amount REAL NOT NULL,
    category TEXT,
    type TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT
);

CREATE TABLE holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    type TEXT,
    units REAL NOT NULL DEFAULT 0,
    avg_cost REAL DEFAULT 0,
    currency TEXT DEFAULT 'INR',
    direct_regular TEXT DEFAULT 'regular',
    benchmark TEXT,
    archived_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
    UNIQUE(account_id, symbol)
);

CREATE TABLE lots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holding_id INTEGER NOT NULL,
    purchase_date DATE NOT NULL,
    units REAL NOT NULL,
    cost_per_unit REAL NOT NULL,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(holding_id) REFERENCES holdings(id) ON DELETE CASCADE,
    UNIQUE(holding_id, purchase_date, units, cost_per_unit)
);

CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target_amount REAL,
    current_amount REAL DEFAULT 0,
    target_date DATE,
    start_date DATE,
    priority INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE debts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lender TEXT NOT NULL,
    type TEXT,
    outstanding REAL NOT NULL,
    interest_rate REAL,
    emi REAL,
    next_due DATE,
    remaining_months INTEGER,
    status TEXT DEFAULT 'active',
    archived_at TIMESTAMP DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE insurance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
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

CREATE TABLE data_health (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    cas_last_import DATE,
    price_last_refresh TIMESTAMP,
    sms_last_import DATE,
    unmatched_transactions INTEGER DEFAULT 0,
    missing_info TEXT,
    health_score TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO data_health (id) VALUES (1);

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
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE(name, version)
);

CREATE TABLE research_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    holding_id INTEGER,
    note_type TEXT,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(holding_id) REFERENCES holdings(id) ON DELETE CASCADE
);

CREATE TABLE benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    symbol TEXT UNIQUE,
    type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    price REAL NOT NULL,
    source TEXT,
    currency TEXT DEFAULT 'INR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

CREATE VIEW latest_prices AS
SELECT symbol, price, date, source, currency
FROM price_history p1
WHERE date = (SELECT MAX(date) FROM price_history p2 WHERE p2.symbol = p1.symbol);

CREATE VIEW active_holdings AS
SELECT h.* FROM holdings h
JOIN accounts a ON a.id = h.account_id
WHERE h.archived_at IS NULL AND a.archived_at IS NULL;

CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_holdings_account ON holdings(account_id);
CREATE INDEX idx_lots_holding ON lots(holding_id);
CREATE INDEX idx_price_history_symbol_date ON price_history(symbol, date);
```

(`goals.start_date` is added vs the original doc — the stored baseline for goal
probability, Group E downstream.)

---

## BLOCK B — `frontend/tailwind.config.ts` (emit VERBATIM)

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

---

## BLOCK C — `frontend/app/globals.css` (emit VERBATIM)

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

---

## BLOCK D — `frontend/next.config.js` (emit VERBATIM)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  async rewrites() {
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

---

## BLOCK E — `backend/services/db.py` (emit VERBATIM)  **[D]**

```python
import os
import sqlite3
import pathlib
import contextlib

HERE = pathlib.Path(__file__).resolve().parent
DB_PATH = pathlib.Path(os.environ.get("FINANCE_DB") or (HERE.parent / "data" / "finance.db"))
SCHEMA_PATH = HERE.parent / "scripts" / "schema.sql"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        has = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
        ).fetchone()
        if not has:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.commit()


@contextlib.contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
```

---

## BLOCK F — `backend/startup.py` (emit VERBATIM)  **[Q]**

```python
import logging
import os
import pathlib
import subprocess

from starlette.middleware.base import BaseHTTPMiddleware


class PassthroughAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)


def check_encrypted_volume(db_dir) -> None:
    try:
        db_dir = pathlib.Path(db_dir)
        if os.name == "nt":
            anchor = db_dir.anchor or "C:\\"
            res = subprocess.run(["manage-bde", "-status", anchor],
                                 capture_output=True, text=True, timeout=10)
            if "Percentage Encrypted: 100" not in (res.stdout or ""):
                logging.warning("DB dir %s may not be on an encrypted volume", db_dir)
        else:
            res = subprocess.run(["cryptsetup", "status", str(db_dir)],
                                 capture_output=True, text=True, timeout=10)
            if "is active" not in (res.stdout or ""):
                logging.warning("DB dir %s may not be on an encrypted volume", db_dir)
    except Exception:
        logging.warning("encrypted-volume check skipped (non-fatal)")
```

---

## BLOCK G — `backend/app_factory.py` (emit VERBATIM)

```python
import importlib
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import startup
from services import db

ROUTERS = ["overview", "investments", "debt", "tracker", "learning", "health",
           "accounts", "goals", "insurance", "salary", "imports", "entities", "settings"]


def create_app() -> FastAPI:
    app = FastAPI(title="Finance OS")
    app.add_middleware(startup.PassthroughAuth)

    @app.on_event("startup")
    def _boot():
        db.init_db()
        startup.check_encrypted_volume(db.DB_PATH.parent)

    for name in ROUTERS:
        try:
            mod = importlib.import_module(f"routers.{name}")
        except ImportError:
            continue
        app.include_router(mod.router, prefix="/api/finance")

    @app.get("/api/finance/health")
    def _health():
        return {"status": "ok"}

    here = pathlib.Path(__file__).parent
    static = here / "static"
    if static.is_dir():
        app.mount("/assets", StaticFiles(directory=static), name="assets")

    @app.get("/{full_path:path}")
    def _spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        for cand in (static / f"{full_path}.html", static / full_path / "index.html",
                     static / "index.html"):
            if cand.is_file():
                return FileResponse(cand)
        raise HTTPException(status_code=404)

    return app
```

---

## BLOCK H — `backend/main.py` (emit VERBATIM)

```python
from app_factory import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
```

---

## Other files (specs are self-contained in the manifest)

- `backend/scripts/set_perms.py` — POSIX `chmod 600` / Windows `icacls`.  **[Q]**
- `shared/constants/categories.py` + `.ts` — identical category / type / account
  / holding enums, same order.  **[A]**
- `backend/requirements.txt`, `frontend/package.json` (no `export` script).  **[O]**
- `finance-os/.gitignore` — keeps `finance.db`, `backups/`, `vector_store/`,
  `.env`, `out/` out of git.  **[Q / Kage repo]**
- `finance-os/DECISIONS.md` — SQLCipher rejected; OS-encryption locked in; stack
  + FastAPI + no-keys decisions.

## Gate (`gate_phase0.py`)
schema applies to a fresh sqlite with ALL tables + both views + the `data_health`
id=1 row; an FK-violating insert is rejected under `PRAGMA foreign_keys=ON`; NO
bare `sqlite3.connect(` under `backend/` except `services/db.py`; `.gitignore`
covers `finance.db`, `backups`, `vector_store`, `.env`; a shared category
constant exists for both backend and frontend; `backend/main.py` exists.
