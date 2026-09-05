import os
import sqlite3
import pathlib
import contextlib

HERE = pathlib.Path(__file__).resolve().parent
DB_PATH = pathlib.Path(os.environ.get("FINANCE_DB") or (HERE.parent / "data" / "finance.db"))
SCHEMA_PATH = HERE.parent / "scripts" / "schema.sql"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI runs a sync generator dependency and the
    # sync endpoint it feeds on *different* threadpool threads, so the default
    # guard 500s once several requests land at once (the Overview fires nine).
    # Safe here — every request opens and closes its own connection.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    # a second connection opened mid-request (e.g. the market feed caching a
    # BSE scrip code while a batch refresh holds its own connection) must wait
    # for the writer, not 'database is locked' straight away.
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    return conn


_MIGRATIONS = (
    # (name, sql). Table migrations use IF NOT EXISTS; column migrations are
    # pragma-guarded in _migrate below. schema.sql stays the fresh-install
    # base; everything added later lives ONLY here so the two can never drift.
    ("app_settings", """CREATE TABLE IF NOT EXISTS app_settings (
           key TEXT PRIMARY KEY,
           value TEXT NOT NULL,
           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       )"""),
    ("fund_facts", """CREATE TABLE IF NOT EXISTS fund_facts (
           amfi_code TEXT PRIMARY KEY,
           slug TEXT,
           source TEXT NOT NULL DEFAULT 'groww',
           data TEXT NOT NULL,
           portfolio_as_of TEXT,
           fetched_at TEXT NOT NULL
       )"""),
    ("fund_portfolios", """CREATE TABLE IF NOT EXISTS fund_portfolios (
           amfi_code TEXT NOT NULL,
           company TEXT NOT NULL,
           sector TEXT,
           weight REAL NOT NULL,
           instrument TEXT,
           isin TEXT,
           as_of TEXT,
           PRIMARY KEY (amfi_code, company, instrument, as_of)
       )"""),
    ("watchlist", """CREATE TABLE IF NOT EXISTS watchlist (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           symbol TEXT NOT NULL UNIQUE,
           name TEXT,
           asset_type TEXT NOT NULL DEFAULT 'stock',
           notes TEXT,
           added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           archived_at TIMESTAMP
       )"""),
    ("trades", """CREATE TABLE IF NOT EXISTS trades (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           symbol TEXT NOT NULL,
           name TEXT,
           asset_type TEXT NOT NULL DEFAULT 'stock',
           exchange TEXT NOT NULL DEFAULT 'NSE',
           qty REAL NOT NULL,
           entry_price REAL NOT NULL,
           entry_date TEXT NOT NULL,
           exit_price REAL,
           exit_date TEXT,
           charges REAL NOT NULL DEFAULT 0,
           thesis TEXT,
           notes TEXT,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       )"""),
    ("ipos", """CREATE TABLE IF NOT EXISTS ipos (
           name TEXT PRIMARY KEY,
           symbol TEXT,
           open_date TEXT,
           close_date TEXT,
           price_min REAL,
           price_max REAL,
           lot_size INTEGER,
           listing_date TEXT,
           status TEXT,
           applied INTEGER NOT NULL DEFAULT 0,
           upi_mandate TEXT,
           notes TEXT,
           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       )"""),
    ("ref_cache", """CREATE TABLE IF NOT EXISTS ref_cache (
           key TEXT PRIMARY KEY,
           payload TEXT NOT NULL,
           fetched_at TEXT NOT NULL
       )"""),
    ("sips", """CREATE TABLE IF NOT EXISTS sips (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           fund_name TEXT NOT NULL,
           amfi_code TEXT,
           amount REAL NOT NULL,
           frequency TEXT NOT NULL DEFAULT 'monthly',
           day_of_month INTEGER NOT NULL DEFAULT 6,
           active INTEGER NOT NULL DEFAULT 1,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
       )"""),
)

# The owner's standing SIP schedule, checked live on Groww 2026-09-05
# (finance-datamigration.md §7): 7 active SIPs, ₹8,000/month, all due the
# 6th. amfi_code matches holdings.symbol so each row links to its holding.
_SIP_SEED = (
    ("ICICI Prudential NASDAQ 100 Index Fund Direct Growth", "149219", 2500),
    ("Bandhan Small Cap Fund Direct Growth", "147946", 1000),
    ("Parag Parikh Flexi Cap Fund Direct Growth", "122639", 1000),
    ("UTI Nifty Next 50 Index Fund Direct Growth", "143341", 1000),
    ("UTI Multi Asset Allocation Fund Direct Growth", "120760", 1000),
    ("HDFC Mid Cap Fund Direct Growth", "118989", 1000),
    ("JioBlackRock Sector Rotation Fund Direct Growth", "154082", 500),
)


def _migrate(conn) -> None:
    for _, sql in _MIGRATIONS:
        conn.execute(sql)
    # column migrations: add when absent, never touch when present
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(holdings)")}
    if "folio" not in cols:
        conn.execute("ALTER TABLE holdings ADD COLUMN folio TEXT")
    # benchmark seed — NIFTY 50 is the reference index for every beta/alpha
    # in the analysis (fund_analysis_settings.json). INSERT OR IGNORE keeps
    # any hand-edited benchmark row untouched.
    conn.execute(
        "INSERT OR IGNORE INTO benchmarks(name, symbol, type) "
        "VALUES ('NIFTY 50', '^NSEI', 'index')"
    )
    # SIP schedule seed — once, into an empty table; hand-edits after that
    # are the owner's and are never overwritten.
    if conn.execute("SELECT COUNT(*) FROM sips").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO sips(fund_name, amfi_code, amount, day_of_month) "
            "VALUES (?, ?, ?, 6)",
            _SIP_SEED,
        )


def init_db():
    with connect() as conn:
        has = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'"
        ).fetchone()
        if not has:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            conn.commit()
        _migrate(conn)
        conn.commit()


@contextlib.contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
