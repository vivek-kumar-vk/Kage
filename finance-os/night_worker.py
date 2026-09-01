"""Finance OS nightly maintenance. Not a web app — a plain script.

  python night_worker.py --once      # run the full pass now, regardless of day
  python night_worker.py             # scheduled mode (23:00 IST via Task Scheduler)
  python night_worker.py --weekly    # only the weekly gap-only price refresh

Sequence (master doc §11):
  1. db.connect() (PRAGMAs set by the helper)                         [D]
  2. refresh latest prices for active_holdings + benchmarks, with a
     CAPPED TOTAL RETRY BUDGET so one dead symbol can't stall the pass [J]
  3. WEEKLY only: gap-only price_history refresh — per symbol fetch
     MAX(date)+1 .. today, INSERT OR IGNORE. Never re-pull the full 2y  [B]
  4. local-LLM portfolio review (placeholder)
  5. snapshots: one row/day ; data_health: UPDATE ... WHERE id=1
  6. compress agent_memory (trim rows older than a window)
  7. research_notes (placeholder)
  8. copy finance.db -> backend/data/backups/finance_YYYYMMDD.db, keep last 7
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "backend"))

from services import db  # noqa: E402
from services.calculations.data_health import recompute_health  # noqa: E402

try:
    from services.market_data import batch_refresh
except Exception:  # pragma: no cover - keep the pass resilient
    def batch_refresh(symbols, total_retry_budget_s: int = 120):
        return {}

RETRY_BUDGET_S = 90          # capped total retry budget for the whole nightly pass
AGENT_MEMORY_WINDOW_DAYS = 90
KEEP_BACKUPS = 7


def _log(msg: str) -> None:
    print(f"[night_worker {_dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def refresh_latest_prices(conn) -> None:
    syms = [r["symbol"] for r in conn.execute(
        "SELECT DISTINCT symbol FROM active_holdings").fetchall()]
    syms += [r["symbol"] for r in conn.execute(
        "SELECT symbol FROM benchmarks").fetchall()]
    if not syms:
        _log("no symbols to refresh")
        return
    out = batch_refresh(syms, total_retry_budget_s=RETRY_BUDGET_S)
    _log(f"latest-price refresh: {len([v for v in out.values() if v is not None])}/{len(syms)} priced "
         f"(retry budget {RETRY_BUDGET_S}s)")


def weekly_gap_only_refresh(conn) -> None:
    """Per symbol, extend price_history from MAX(date)+1 to today. INSERT OR
    IGNORE, so it is safe to re-run and never re-pulls the full history."""
    today = _dt.date.today()
    rows = conn.execute(
        "SELECT symbol, MAX(date) AS max_date, "
        "(SELECT price FROM price_history p2 WHERE p2.symbol = p1.symbol "
        " ORDER BY date DESC LIMIT 1) AS last_price "
        "FROM price_history p1 GROUP BY symbol"
    ).fetchall()
    added = 0
    for r in rows:
        try:
            start = _dt.date.fromisoformat(str(r["max_date"])[:10]) + _dt.timedelta(days=1)
        except (TypeError, ValueError):
            continue
        px = float(r["last_price"] or 0.0)
        d = start
        while d <= today:
            cur = conn.execute(
                "INSERT OR IGNORE INTO price_history(symbol,date,price,source) VALUES (?,?,?,?)",
                (r["symbol"], d.isoformat(), px, "night_worker_gap"),
            )
            added += cur.rowcount or 0
            d += _dt.timedelta(days=1)
    conn.commit()
    _log(f"weekly gap-only refresh: +{added} price_history rows")


def local_llm_review(conn) -> None:  # placeholder — real call wired later
    _log("local-LLM portfolio review: skipped (placeholder)")


def write_snapshot(conn) -> None:
    today = _dt.date.today().isoformat()
    nw = conn.execute(
        "SELECT COALESCE(SUM(units*avg_cost),0) FROM active_holdings "
        "WHERE COALESCE(type,'') NOT IN ('bond','other')"
    ).fetchone()[0]
    debt = conn.execute(
        "SELECT COALESCE(SUM(outstanding),0) FROM debts WHERE status='active' AND archived_at IS NULL"
    ).fetchone()[0]
    conn.execute(
        "INSERT OR IGNORE INTO snapshots(date, net_worth, investments, debt) VALUES (?,?,?,?)",
        (today, float(nw) - float(debt), float(nw), float(debt)),
    )
    conn.commit()
    _log("snapshot written")


def compress_agent_memory(conn) -> None:
    cutoff = (_dt.date.today() - _dt.timedelta(days=AGENT_MEMORY_WINDOW_DAYS)).isoformat()
    cur = conn.execute("DELETE FROM agent_memory WHERE timestamp IS NOT NULL AND timestamp < ?",
                       (cutoff,))
    conn.commit()
    _log(f"agent_memory compressed: -{cur.rowcount or 0} rows older than {cutoff}")


def write_research_notes(conn) -> None:  # placeholder
    _log("research_notes: nothing to write (placeholder)")


def rotate_backups() -> None:
    src = db.DB_PATH
    bdir = src.parent / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    if src.exists():
        dst = bdir / f"finance_{_dt.date.today():%Y%m%d}.db"
        shutil.copy2(src, dst)
        _log(f"backup -> {dst.name}")
    backups = sorted(bdir.glob("finance_*.db"))
    for old in backups[:-KEEP_BACKUPS]:
        old.unlink()
        _log(f"pruned old backup {old.name}")
    _log(f"backups retained: {min(len(backups), KEEP_BACKUPS)} (keep last {KEEP_BACKUPS})")


def run_pass(weekly: bool) -> None:
    db.init_db()
    conn = db.connect()
    try:
        refresh_latest_prices(conn)
        if weekly:
            weekly_gap_only_refresh(conn)
        local_llm_review(conn)
        write_snapshot(conn)
        recompute_health(conn)
        compress_agent_memory(conn)
        write_research_notes(conn)
    finally:
        conn.close()
    rotate_backups()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Finance OS nightly maintenance")
    ap.add_argument("--once", action="store_true",
                    help="run the full pass now, regardless of weekday")
    ap.add_argument("--weekly", action="store_true",
                    help="run only the weekly gap-only price refresh")
    args = ap.parse_args(argv)

    is_sunday = _dt.date.today().weekday() == 6
    if args.weekly:
        db.init_db()
        conn = db.connect()
        try:
            weekly_gap_only_refresh(conn)
        finally:
            conn.close()
        return 0

    # scheduled mode also does the weekly step on Sundays; --once forces a full pass
    run_pass(weekly=args.once or is_sunday)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
