"""Overview calculations. Every function takes an open sqlite3 connection
(row_factory = Row) and returns plain JSON-safe dicts. All arithmetic is
guarded so an empty DB yields finite zeros, never NaN / Infinity.
"""
from __future__ import annotations

import datetime as _dt


def _scalar(conn, sql: str, params: tuple = (), default: float = 0.0) -> float:
    row = conn.execute(sql, params).fetchone()
    if not row or row[0] is None:
        return default
    try:
        v = float(row[0])
    except (TypeError, ValueError):
        return default
    if v != v or v in (float("inf"), float("-inf")):  # NaN / inf
        return default
    return v


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _months_span(conn) -> int:
    row = conn.execute(
        "SELECT COUNT(DISTINCT strftime('%Y-%m', date)) FROM transactions"
    ).fetchone()
    return int(row[0]) if row and row[0] else 1


def _cash_balance(conn) -> float:
    return _scalar(
        conn,
        """SELECT SUM(t.amount) FROM transactions t
           JOIN accounts a ON a.id = t.account_id
           WHERE a.archived_at IS NULL""",
    )


def _investments_value(conn) -> float:
    # bond / other are unpriceable here -> excluded from value, not read as 0
    return _scalar(
        conn,
        """SELECT SUM(units * avg_cost) FROM active_holdings
           WHERE COALESCE(type,'') NOT IN ('bond','other')""",
    )


def _total_debt(conn) -> float:
    return _scalar(
        conn,
        "SELECT SUM(outstanding) FROM debts WHERE status='active' AND archived_at IS NULL",
    )


def _monthly_expenses(conn) -> float:
    total = _scalar(conn, "SELECT SUM(-amount) FROM transactions WHERE amount < 0")
    return _safe_div(total, _months_span(conn))


def _monthly_net(conn) -> float:
    return _scalar(
        conn,
        "SELECT monthly_net FROM salary ORDER BY effective_date DESC, id DESC LIMIT 1",
    )


def _monthly_emi(conn) -> float:
    return _scalar(
        conn,
        "SELECT SUM(emi) FROM debts WHERE status='active' AND archived_at IS NULL",
    )


def net_worth(conn) -> dict:
    invest = _investments_value(conn)
    cash = max(_cash_balance(conn), 0.0)
    assets = invest + cash
    liabilities = _total_debt(conn)
    trend = [
        {"date": r["date"], "net_worth": round(float(r["net_worth"] or 0.0), 2)}
        for r in conn.execute(
            "SELECT date, net_worth FROM snapshots ORDER BY date ASC"
        ).fetchall()
    ]
    return {
        "net_worth": round(assets - liabilities, 2),
        "assets": round(assets, 2),
        "liabilities": round(liabilities, 2),
        "trend": trend,
    }


def cashflow(conn) -> dict:
    income = _scalar(conn, "SELECT SUM(amount) FROM transactions WHERE amount > 0")
    expenses = _scalar(conn, "SELECT SUM(-amount) FROM transactions WHERE amount < 0")
    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "cash_flow": round(income - expenses, 2),
    }


def portfolio_pulse(conn) -> dict:
    value = _investments_value(conn)
    count = int(_scalar(conn, "SELECT COUNT(*) FROM active_holdings"))
    return {
        "total_value": round(value, 2),
        "holdings_count": count,
        "day_change": 0.0,
    }


def emergency_fund(conn) -> dict:
    monthly = _monthly_expenses(conn)
    target = 6.0 * monthly
    balance = max(_cash_balance(conn), 0.0)
    return {
        "balance": round(balance, 2),
        "target": round(target, 2),
        "monthly_expenses": round(monthly, 2),
        "months_covered": round(_safe_div(balance, monthly), 2),
        "progress": round(min(_safe_div(balance, target), 1.0), 4),
    }


def debt_status(conn) -> dict:
    total = _total_debt(conn)
    emi = _monthly_emi(conn)
    weighted_rate = _safe_div(
        _scalar(
            conn,
            """SELECT SUM(outstanding * COALESCE(interest_rate,0)) FROM debts
               WHERE status='active' AND archived_at IS NULL""",
        ),
        total,
    )
    count = int(
        _scalar(
            conn,
            "SELECT COUNT(*) FROM debts WHERE status='active' AND archived_at IS NULL",
        )
    )
    return {
        "total_debt": round(total, 2),
        "total_emi": round(emi, 2),
        "weighted_rate": round(weighted_rate, 3),
        "count": count,
    }


def surplus_allocation(conn) -> dict:
    net = _monthly_net(conn)
    expenses = _monthly_expenses(conn)
    emi = _monthly_emi(conn)
    surplus = net - expenses - emi
    allocation: list[dict] = []
    if surplus > 0:
        allocation = [
            {"category": "Emergency / Buffer", "amount": round(surplus * 0.3, 2)},
            {"category": "Investments", "amount": round(surplus * 0.5, 2)},
            {"category": "Goals", "amount": round(surplus * 0.2, 2)},
        ]
    return {
        "surplus": round(surplus, 2),
        "monthly_net": round(net, 2),
        "monthly_expenses": round(expenses, 2),
        "monthly_emi": round(emi, 2),
        "allocation": allocation,
    }


def _goal_probability(current: float, target: float, months_left: float,
                      total_months: float) -> float:
    if target <= 0:
        return 0.0
    if months_left <= 0:
        return 100.0 if current >= target else 0.0
    time_factor = min(_safe_div(months_left, total_months), 1.0) if total_months > 0 else 1.0
    progress = min(_safe_div(current, target), 1.0)
    return round(min(100.0, max(0.0, (progress * 0.7 + time_factor * 0.3) * 100.0)), 1)


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def goals_overview(conn) -> dict:
    today = _dt.date.today()
    out = []
    for g in conn.execute(
        "SELECT * FROM goals WHERE status='active' ORDER BY priority ASC, id ASC"
    ).fetchall():
        target = float(g["target_amount"] or 0.0)
        current = float(g["current_amount"] or 0.0)
        start = _parse_date(g["start_date"]) or _parse_date(g["created_at"]) or today
        end = _parse_date(g["target_date"])
        months_left = _safe_div((end - today).days, 30.0) if end else 0.0
        total_months = _safe_div((end - start).days, 30.0) if end else 0.0
        out.append(
            {
                "id": g["id"],
                "name": g["name"],
                "target_amount": round(target, 2),
                "current_amount": round(current, 2),
                "progress": round(min(_safe_div(current, target), 1.0), 4),
                "probability": _goal_probability(current, target, months_left, total_months),
            }
        )
    return {"goals": out, "count": len(out)}


def top_actions(conn) -> dict:
    actions: list[dict] = []
    dh = conn.execute("SELECT * FROM data_health WHERE id = 1").fetchone()
    if dh:
        if (dh["unmatched_transactions"] or 0) > 0:
            actions.append(
                {
                    "title": "Review unmatched transactions",
                    "detail": f"{dh['unmatched_transactions']} transactions need a category",
                }
            )
        if not dh["price_last_refresh"]:
            actions.append(
                {"title": "Refresh prices", "detail": "No price refresh on record yet"}
            )
        if not dh["cas_last_import"]:
            actions.append(
                {"title": "Import a CAS statement", "detail": "No holdings snapshot imported"}
            )
    if _total_debt(conn) > 0 and _monthly_emi(conn) <= 0:
        actions.append(
            {"title": "Add EMI details", "detail": "Active debt has no EMI recorded"}
        )
    return {"actions": actions, "count": len(actions)}


def data_health(conn) -> dict:
    row = conn.execute("SELECT * FROM data_health WHERE id = 1").fetchone()
    if not row:
        return {
            "id": 1,
            "cas_last_import": None,
            "price_last_refresh": None,
            "sms_last_import": None,
            "unmatched_transactions": 0,
            "missing_info": None,
            "health_score": None,
            "updated_at": None,
        }
    return {k: row[k] for k in row.keys()}
