"""Rebuild monthly net-worth snapshots so the Overview ridge chart has a real
series to draw. Idempotent: month-end rows are INSERT OR REPLACE (snapshots.date
is UNIQUE), so re-running refreshes rather than duplicates.

History honesty: price series don't reach back, so pre-today rows value
holdings at COST BASIS from the lots table; today's row uses market value via
the live calculations. Debts carry no history in the schema, so the current
active outstanding is used for every month — an approximation, applied
uniformly rather than invented per month.

Usage:  cd backend && python -m scripts.backfill_snapshots
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.calculations import core  # noqa: E402
from services.db import connect  # noqa: E402


def _month_ends(first: dt.date, last: dt.date) -> list[dt.date]:
    """Last day of each month from `first`'s month through `last`'s month."""
    out = []
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        nxt = dt.date(y + (m // 12), (m % 12) + 1, 1)
        out.append(nxt - dt.timedelta(days=1))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def backfill() -> dict:
    with connect() as conn:
        span = conn.execute(
            "SELECT MIN(date), MAX(date) FROM transactions"
        ).fetchone()
        if not span or not span[0]:
            return {"written": 0, "note": "no transactions to backfill from"}
        first = dt.date.fromisoformat(str(span[0])[:10])
        today = dt.date.today()

        debts = core._total_debt(conn)
        months = core._monthly_expenses(conn) or 0.0

        written = 0
        for end in _month_ends(first, today):
            if end >= today:
                continue  # today's row is written separately below
            end_iso = end.isoformat()
            cash = core._scalar(
                conn,
                """SELECT SUM(t.amount) FROM transactions t
                   JOIN accounts a ON a.id = t.account_id
                   WHERE a.archived_at IS NULL AND t.date <= ?""",
                (end_iso,),
            )
            invested = core._scalar(
                conn,
                """SELECT SUM(l.units * l.cost_per_unit) FROM lots l
                   JOIN holdings h ON h.id = l.holding_id
                   WHERE l.purchase_date <= ? AND h.archived_at IS NULL""",
                (end_iso,),
            )
            cash = max(cash, 0.0)
            conn.execute(
                "INSERT OR REPLACE INTO snapshots"
                "(date, net_worth, cash, debt, investments, emergency_months) "
                "VALUES (?,?,?,?,?,?)",
                (end_iso, round(cash + invested - debts, 2), round(cash, 2),
                 round(debts, 2), round(invested, 2),
                 round((cash / months) if months > 0 else 0.0, 2)),
            )
            written += 1

        # today's row at market value, same shape the live endpoint computes
        invest_mv, _invested, _names = core._valuation(conn)
        cash_now = max(core._cash_balance(conn), 0.0)
        conn.execute(
            "INSERT OR REPLACE INTO snapshots"
            "(date, net_worth, cash, debt, investments, emergency_months) "
            "VALUES (?,?,?,?,?,?)",
            (today.isoformat(), round(invest_mv + cash_now - debts, 2),
             round(cash_now, 2), round(debts, 2), round(invest_mv, 2),
             round((cash_now / months) if months > 0 else 0.0, 2)),
        )
        written += 1
        conn.commit()
    return {"written": written, "first": first.isoformat(), "through": today.isoformat()}


if __name__ == "__main__":
    print(backfill())
