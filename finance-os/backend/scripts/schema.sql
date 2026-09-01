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
