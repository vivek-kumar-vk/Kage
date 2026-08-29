"""Data-health scoring. The `data_health` table is a SINGLETON — id is fixed at
1 by a CHECK constraint. Every write here is `UPDATE ... WHERE id = 1`, never
INSERT.  [singleton]
"""
from __future__ import annotations

import datetime as _dt


def get_data_health(conn) -> dict:
    row = conn.execute("SELECT * FROM data_health WHERE id = 1").fetchone()
    if not row:
        # never INSERT from app code — the schema seeds row 1. Return a shape.
        return {"id": 1, "cas_last_import": None, "price_last_refresh": None,
                "sms_last_import": None, "unmatched_transactions": 0,
                "missing_info": None, "health_score": None, "updated_at": None}
    return {k: row[k] for k in row.keys()}


def recompute_health(conn) -> dict:
    """Score high / medium / low from: recent imports present, prices fresh,
    critical data (salary, goals, insurance) present. UPDATE-only."""
    today = _dt.date.today()

    holdings = conn.execute("SELECT COUNT(*) FROM active_holdings").fetchone()[0]
    priced = conn.execute(
        "SELECT COUNT(DISTINCT symbol) FROM price_history"
    ).fetchone()[0]
    last_price = conn.execute(
        "SELECT MAX(date) FROM price_history"
    ).fetchone()[0]
    has_salary = conn.execute("SELECT COUNT(*) FROM salary").fetchone()[0] > 0
    has_goals = conn.execute("SELECT COUNT(*) FROM goals").fetchone()[0] > 0
    has_insurance = conn.execute("SELECT COUNT(*) FROM insurance").fetchone()[0] > 0
    unmatched = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE category IS NULL OR category = ''"
    ).fetchone()[0]

    prices_fresh = False
    if last_price:
        try:
            prices_fresh = (today - _dt.date.fromisoformat(str(last_price)[:10])).days <= 7
        except ValueError:
            prices_fresh = False

    missing = []
    if not has_salary:
        missing.append("salary")
    if not has_goals:
        missing.append("goals")
    if not has_insurance:
        missing.append("insurance")
    if holdings and priced < holdings:
        missing.append("prices")

    score = "high"
    if missing or (holdings and not prices_fresh):
        score = "medium"
    if len(missing) >= 3 or (holdings and priced == 0):
        score = "low"

    conn.execute(
        "UPDATE data_health SET price_last_refresh = ?, unmatched_transactions = ?, "
        "missing_info = ?, health_score = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
        (str(last_price) if last_price else None, int(unmatched),
         ",".join(missing) or None, score),
    )
    conn.commit()
    return get_data_health(conn)
