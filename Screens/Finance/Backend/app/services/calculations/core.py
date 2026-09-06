"""Overview calculations. Every function takes an open sqlite3 connection
(row_factory = Row) and returns plain JSON-safe dicts. All arithmetic is
guarded so an empty DB yields finite zeros / explicit nulls, never NaN or
Infinity. Unknown numbers are returned as None so the UI can show an honest
dash instead of an invented value.
"""
from __future__ import annotations

import datetime as _dt
import json
import math

from services.imports.transactions import compute_xirr
from services.reference import reference

# assumption keys used by the projections (india_planning_assumptions.json)
_RET_EQUITY = "indian_equity"
_RET_CASH = "savings_account"


def _scalar(conn, sql: str, params: tuple = ()) -> float | None:
    """None for no row / NULL / NaN / inf — never a stand-in number."""
    row = conn.execute(sql, params).fetchone()
    if not row or row[0] is None:
        return None
    try:
        v = float(row[0])
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")):  # NaN / inf
        return None
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


def _total_debt(conn) -> float:
    return _scalar(
        conn,
        "SELECT SUM(outstanding) FROM debts WHERE status='active' AND archived_at IS NULL",
    )


def _monthly_emi(conn) -> float | None:
    return _scalar(
        conn,
        "SELECT SUM(emi) FROM debts WHERE status='active' AND archived_at IS NULL",
    )


def _weighted_rate(conn) -> float | None:
    total = _total_debt(conn)
    if not total:
        return None
    numerator = _scalar(
        conn,
        """SELECT SUM(outstanding * COALESCE(interest_rate,0)) FROM debts
           WHERE status='active' AND archived_at IS NULL""",
    )
    if numerator is None:
        return None
    return _safe_div(numerator, total)


def _monthly_net(conn) -> float | None:
    return _scalar(
        conn,
        "SELECT monthly_net FROM salary ORDER BY effective_date DESC, id DESC LIMIT 1",
    )


def _monthly_expenses(conn) -> float | None:
    total = _scalar(conn, "SELECT SUM(-amount) FROM transactions WHERE amount < 0")
    if total is None:
        return None
    return _safe_div(total, _months_span(conn))


def _app_settings(conn) -> dict:
    out: dict = {}
    for r in conn.execute("SELECT key, value FROM app_settings").fetchall():
        try:
            out[r["key"]] = json.loads(r["value"])
        except (TypeError, ValueError):
            out[r["key"]] = r["value"]
    return out


def _sweep_rule(conn) -> dict:
    """Auto-sweep split (percent) from app_settings; house default 45/36/19."""
    raw = _app_settings(conn).get("surplus_split") or {}
    try:
        e, i, g = (float(raw.get("emergency", 45)), float(raw.get("investments", 36)),
                   float(raw.get("goals", 19)))
    except (TypeError, ValueError):
        e, i, g = 45.0, 36.0, 19.0
    if e + i + g <= 0:
        e, i, g = 45.0, 36.0, 19.0
    total = e + i + g
    return {"emergency": e * 100 / total, "investments": i * 100 / total,
            "goals": g * 100 / total}


# --- price series ------------------------------------------------------------

def _price_series(conn) -> dict[str, list[float]]:
    series: dict[str, list[float]] = {}
    for r in conn.execute(
        "SELECT symbol, price FROM price_history ORDER BY symbol, date ASC"
    ).fetchall():
        if r["price"] is not None:
            series.setdefault(r["symbol"], []).append(float(r["price"]))
    return series


def _holdings(conn) -> list:
    return conn.execute(
        "SELECT symbol, name, type, units, avg_cost FROM active_holdings"
    ).fetchall()


_UNPRICEABLE = ("bond", "other")


def _valuation(conn) -> tuple[float, float, dict[str, float], list[str]]:
    """(market_value, invested, name_map, unpriced_symbols). A holding with
    no price row is excluded from both totals and listed in ledger order —
    never valued at cost (Rule 22: absent is absent)."""
    prices = {s: v[-1] for s, v in _price_series(conn).items()}
    names: dict[str, float] = {}
    market = invested = 0.0
    unpriced: list[str] = []
    for h in _holdings(conn):
        units = float(h["units"] or 0)
        names[h["symbol"]] = h["name"] or h["symbol"]
        price = prices.get(h["symbol"])
        if price is None:
            unpriced.append(h["symbol"])
            continue
        invested += units * float(h["avg_cost"] or 0)
        market += units * price
    return market, invested, names, unpriced


def _add_months(d: _dt.date, months: int) -> _dt.date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    day = min(d.day, [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return _dt.date(y, m, day)


def _pct(cur: float, base: float) -> float | None:
    if base <= 0:
        return None
    return round((cur / base - 1.0) * 100.0, 2)


# --- 1. net worth ------------------------------------------------------------

def net_worth(conn) -> dict:
    invest_mv, _invested, _names, unpriced = _valuation(conn)
    cash = _cash_balance(conn)
    assets = invest_mv + (cash if cash is not None else 0.0)
    liabilities = _total_debt(conn)

    trend = [
        {"date": r["date"], "net_worth": round(float(r["net_worth"] or 0.0), 2)}
        for r in conn.execute(
            "SELECT date, net_worth FROM snapshots ORDER BY date ASC"
        ).fetchall()
    ]
    all_time = month_change = month_abs = None
    if len(trend) >= 2:
        all_time = _pct(trend[-1]["net_worth"], trend[0]["net_worth"])
        month_change = _pct(trend[-1]["net_worth"], trend[-2]["net_worth"])
        month_abs = round(trend[-1]["net_worth"] - trend[-2]["net_worth"], 2)

    return {
        "net_worth": round(assets - (liabilities or 0.0), 2),
        "assets": round(assets, 2),
        "liabilities": round(liabilities, 2) if liabilities is not None else None,
        "unpriced": unpriced,
        "all_time_pct": all_time,
        "month_change_pct": month_change,
        "month_change_abs": month_abs,
        "trend": trend,
        "projection": _projection(conn, invest_mv, cash or 0.0, liabilities or 0.0),
    }


def _projection(conn, invest: float, cash: float, debt: float) -> list[dict]:
    """12-month projection: surplus swept by the app_settings rule, invested
    pool compounds at the reference equity rate, cash at the savings rate,
    debt amortises at its weighted rate. Assumptions, not promises."""
    if invest == 0 and cash == 0 and debt == 0:
        return []
    net = _monthly_net(conn)
    monthly = _monthly_expenses(conn)
    if net is None or monthly is None:
        # No salary (or no spend history): a projection would invent a surplus.
        return []
    assumptions = reference.load("india_planning_assumptions")
    rets = assumptions.get("expected_returns_pct", {})
    r_m = float(rets.get(_RET_EQUITY, 11.0)) / 100 / 12
    c_m = float(rets.get(_RET_CASH, 3.0)) / 100 / 12
    wr_m = (_weighted_rate(conn) or 0.0) / 100 / 12
    emi = _monthly_emi(conn) or 0.0
    surplus = net - monthly - emi
    rule = _sweep_rule(conn)
    to_cash = max(surplus, 0.0) * rule["emergency"] / 100
    to_invest = max(surplus, 0.0) * (rule["investments"] + rule["goals"]) / 100

    today = _dt.date.today()
    out = []
    for m in range(1, 13):
        invest = max(invest * (1 + r_m) + to_invest, 0.0)
        cash = max(cash * (1 + c_m) + to_cash, 0.0)
        if debt > 0 and emi > 0:
            debt = max(debt - max(emi - debt * wr_m, 0.0), 0.0)
        out.append({"month": _add_months(today, m).isoformat()[:7],
                    "net_worth": round(invest + cash - debt, 2)})
    return out


# --- 2. cashflow -------------------------------------------------------------

def cashflow(conn) -> dict:
    income = _scalar(conn, "SELECT SUM(amount) FROM transactions WHERE amount > 0")
    expenses = _scalar(conn, "SELECT SUM(-amount) FROM transactions WHERE amount < 0")
    months = []
    for r in conn.execute(
        """SELECT strftime('%Y-%m', date) AS m,
                  SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS inc,
                  SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS exp
           FROM transactions GROUP BY m ORDER BY m DESC LIMIT 6"""
    ).fetchall():
        months.append({
            "month": r["m"],
            "label": _dt.date(int(r["m"][:4]), int(r["m"][5:7]), 1).strftime("%b").upper(),
            "income": round(float(r["inc"] or 0), 2),
            "expenses": round(float(r["exp"] or 0), 2),
        })
    months.reverse()
    for m in months:
        m["surplus"] = round(m["income"] - m["expenses"], 2)
    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "cash_flow": round(income - expenses, 2),
        "months": months,
    }


# --- 3. portfolio pulse ------------------------------------------------------

def portfolio_pulse(conn) -> dict:
    value, invested, names, unpriced = _valuation(conn)
    holdings = _holdings(conn)
    series = _price_series(conn)

    # real day change: units x (latest - previous) over symbols with >=2 prices
    day_change: float | None = None
    best: dict | None = None
    yesterday_value = 0.0
    for h in holdings:
        prices = series.get(h["symbol"])
        if not prices or len(prices) < 2:
            continue
        units = float(h["units"] or 0)
        delta = units * (prices[-1] - prices[-2])
        yesterday_value += units * prices[-2]
        day_change = (day_change or 0.0) + delta
        pct = (prices[-1] / prices[-2] - 1) * 100 if prices[-2] else 0.0
        if best is None or pct > best["change_pct"]:
            best = {"symbol": h["symbol"], "name": names.get(h["symbol"], h["symbol"]),
                    "change_pct": round(pct, 2)}

    xirr_pct = None
    if value > 0:
        try:
            lots = conn.execute(
                """SELECT l.purchase_date AS d, l.units * l.cost_per_unit AS amt
                   FROM lots l JOIN active_holdings h ON h.id = l.holding_id"""
            ).fetchall()
            flows = [{"date": r["d"], "amount": float(r["amt"] or 0)}
                     for r in lots if r["d"] and float(r["amt"] or 0) > 0]
            if flows:
                x = compute_xirr(flows, value)
                if x is not None and math.isfinite(float(x)):
                    xirr_pct = round(float(x) * 100, 2)
        except Exception:
            xirr_pct = None

    classes = {((h["type"] or "").lower() or "uncategorised") for h in holdings}
    history = [
        {"date": r["date"], "value": round(float(r["investments"] or 0.0), 2)}
        for r in conn.execute(
            "SELECT date, investments FROM snapshots ORDER BY date ASC"
        ).fetchall()
        if r["investments"] is not None
    ]
    return {
        "total_value": round(value, 2),
        "invested": round(invested, 2),
        "history": history,
        "day_change": round(day_change, 2) if day_change is not None else None,
        "day_change_pct": round(_safe_div(day_change, yesterday_value) * 100, 2)
        if day_change is not None and yesterday_value > 0 else None,
        "xirr_pct": xirr_pct,
        "holdings_count": len(holdings),
        "asset_classes": len(classes),
        "unpriced": unpriced,
        "best_today": best,
    }


# --- 4. emergency fund -------------------------------------------------------

def emergency_fund(conn) -> dict:
    monthly = _monthly_expenses(conn)
    balance = max(_cash_balance(conn) or 0.0, 0.0)
    net = _monthly_net(conn)
    emi = _monthly_emi(conn)
    surplus = (net - monthly - (emi or 0.0)) if (net is not None and monthly is not None) else None
    target = 6.0 * monthly if monthly is not None else None
    earmark = max(surplus, 0.0) * _sweep_rule(conn)["emergency"] / 100 if surplus is not None else None
    eta = None
    if (surplus is not None and target is not None
            and target > 0 and balance < target and earmark > 0):
        months_needed = math.ceil((target - balance) / earmark)
        eta = _add_months(_dt.date.today(), months_needed).isoformat()[:10]
    return {
        "balance": round(balance, 2),
        "target": round(target, 2) if target is not None else None,
        "monthly_expenses": round(monthly, 2) if monthly is not None else None,
        "monthly_earmark": round(earmark, 2) if earmark is not None else None,
        "months_covered": round(_safe_div(balance, monthly), 2) if monthly else None,
        "progress": round(min(_safe_div(balance, target), 1.0), 4) if target else None,
        "eta_date": eta,
    }


# --- 5. debt status ----------------------------------------------------------

def debt_status(conn) -> dict:
    rows = conn.execute(
        """SELECT id, lender, type, outstanding, interest_rate, emi
           FROM debts WHERE status='active' AND archived_at IS NULL
           ORDER BY outstanding DESC"""
    ).fetchall()
    total = sum(float(r["outstanding"] or 0) for r in rows)
    emi = _monthly_emi(conn)
    weighted = _weighted_rate(conn)
    loans = []
    for r in rows:
        outstanding = float(r["outstanding"] or 0)
        loans.append({
            "id": r["id"],
            "name": (r["lender"] or r["type"] or "Loan").strip(),
            "outstanding": round(outstanding, 2),
            "rate": float(r["interest_rate"]) if r["interest_rate"] is not None else None,
            "emi": float(r["emi"]) if r["emi"] is not None else None,
            "share": round(_safe_div(outstanding, total), 4),
        })
    return {
        "total_debt": round(total, 2),
        "total_emi": round(emi, 2) if emi is not None else None,
        "weighted_rate": round(weighted, 3) if weighted is not None else None,
        "count": len(loans),
        "loans": loans,
    }


# --- 6. surplus allocation ---------------------------------------------------

def surplus_allocation(conn) -> dict:
    net = _monthly_net(conn)
    expenses = _monthly_expenses(conn)
    emi = _monthly_emi(conn)
    if net is None or expenses is None:
        surplus = None
        note = "no salary recorded" if net is None else None
    else:
        surplus = net - expenses - (emi or 0.0)
        note = None
    rule = _sweep_rule(conn)
    allocation: list[dict] = []
    if surplus is not None and surplus > 0:
        allocation = [
            {"category": "Emergency / Buffer", "amount": round(surplus * rule["emergency"] / 100, 2)},
            {"category": "Investments", "amount": round(surplus * rule["investments"] / 100, 2)},
            {"category": "Goals", "amount": round(surplus * rule["goals"] / 100, 2)},
        ]
    return {
        "surplus": round(surplus, 2) if surplus is not None else None,
        "monthly_net": round(net, 2) if net is not None else None,
        "monthly_expenses": round(expenses, 2) if expenses is not None else None,
        "monthly_emi": round(emi, 2) if emi is not None else None,
        "rule": {k: round(v) for k, v in rule.items()},
        "allocation": allocation,
        "note": note,
    }


# --- 7. goals ----------------------------------------------------------------

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
    from services.calculations.monte_carlo import blended_return_and_vol, success_probability

    today = _dt.date.today()
    rows = conn.execute(
        "SELECT * FROM goals WHERE status='active' ORDER BY priority ASC, id ASC"
    ).fetchall()

    assumptions = reference.load("india_planning_assumptions")
    targets = (reference.load("fund_analysis_settings").get("target_allocation", {})
               .get("targets", {}))
    exp_ret, vol = blended_return_and_vol(assumptions, targets)

    net = _monthly_net(conn)
    expenses = _monthly_expenses(conn)
    surplus = (net - expenses - (_monthly_emi(conn) or 0.0)) \
        if (net is not None and expenses is not None) else 0.0
    per_goal = max(surplus, 0.0) * _sweep_rule(conn)["goals"] / 100 / len(rows) if rows else 0.0

    out = []
    for g in rows:
        target = float(g["target_amount"] or 0.0)
        current = float(g["current_amount"] or 0.0)
        start = _parse_date(g["start_date"]) or _parse_date(g["created_at"]) or today
        end = _parse_date(g["target_date"])
        months_left = _safe_div((end - today).days, 30.0) if end else 0.0
        total_months = _safe_div((end - start).days, 30.0) if end else 0.0
        if end and months_left > 0:
            probability = success_probability(
                current, per_goal, target, int(months_left), exp_ret, vol,
                runs=10_000, seed=int(g["id"]))
            source = "monte-carlo"
        else:
            probability = _goal_probability(current, target, months_left, total_months)
            source = "heuristic"
        out.append(
            {
                "id": g["id"],
                "name": g["name"],
                "target_amount": round(target, 2),
                "current_amount": round(current, 2),
                "target_date": end.isoformat()[:10] if end else None,
                "progress": round(min(_safe_div(current, target), 1.0), 4),
                "probability": probability,
                "probability_source": source,
            }
        )
    return {"goals": out, "count": len(out), "monthly_goal_sip": round(per_goal, 2),
            "assumed_return_pct": round(exp_ret * 100, 1), "assumed_vol_pct": round(vol * 100, 1)}


# --- 8. top actions ----------------------------------------------------------

def top_actions(conn) -> dict:
    """Observations only: a fact plus its named threshold, never an
    instruction and never an amount to pay. The buyer decides."""
    observations: list[dict] = []

    # 1. highest-APR debt — the costliest Rupee in the book
    worst = conn.execute(
        """SELECT lender, type, outstanding, interest_rate FROM debts
           WHERE status='active' AND archived_at IS NULL AND outstanding > 0
           ORDER BY COALESCE(interest_rate,0) DESC LIMIT 1"""
    ).fetchone()
    if worst:
        rate = float(worst["interest_rate"] or 0)
        name = (worst["lender"] or worst["type"] or "loan").strip()
        observations.append({
            "flag": "debt_apr",
            "severity": "flag" if rate > 20 else "watch",
            "detail": f"{name} at {rate:g}% APR (threshold 20%)",
        })

    # 2. emergency fund gap vs the 6-month target
    ef = emergency_fund(conn)
    target = ef.get("target")
    balance = ef.get("balance") or 0.0
    if target is not None and target > balance:
        observations.append({
            "flag": "emergency_gap",
            "severity": "watch",
            "detail": f"₹{target - balance:,.0f} short of the 6-month target",
        })

    # 3. allocation drift vs the reference targets (threshold 5pp)
    drift = _allocation_drift(conn)
    if drift and drift["delta"] > 5:
        observations.append({
            "flag": "allocation_drift",
            "severity": "watch",
            "detail": f"{drift['asset_class']} sits {drift['delta']:.0f}pp "
                      f"over its target (threshold 5pp)",
        })

    # data-quality observations keep their place at the end
    dh = conn.execute("SELECT * FROM data_health WHERE id = 1").fetchone()
    if dh:
        if (dh["unmatched_transactions"] or 0) > 0:
            observations.append({
                "flag": "unmatched_transactions", "severity": "info",
                "detail": f"{dh['unmatched_transactions']} transactions need a category",
            })
        if not dh["price_last_refresh"]:
            observations.append({
                "flag": "no_price_refresh", "severity": "info",
                "detail": "No price refresh on record yet",
            })
        if not dh["cas_last_import"]:
            observations.append({
                "flag": "no_cas_import", "severity": "info",
                "detail": "No holdings snapshot imported",
            })
    if _total_debt(conn) is not None and (_monthly_emi(conn) or 0.0) <= 0:
        observations.append({
            "flag": "no_emi", "severity": "info",
            "detail": "Active debt has no EMI recorded",
        })
    return {"observations": observations, "count": len(observations)}


def _allocation_drift(conn) -> dict | None:
    """Biggest positive drift vs fund_analysis_settings target_allocation.
    Class mapping is best-effort (type + name keywords); skipped entirely when
    less than 60% of the portfolio value can be classified — no invented drift."""
    targets = (reference.load("fund_analysis_settings").get("target_allocation", {})
               .get("targets", {}))
    if not targets:
        return None
    prices = {s: v[-1] for s, v in _price_series(conn).items()}
    buckets: dict[str, float] = {}
    unclassified = 0.0
    for h in _holdings(conn):
        units = float(h["units"] or 0)
        price = prices.get(h["symbol"])
        value = units * price if price is not None else 0.0
        if value <= 0:
            continue
        t = (h["type"] or "").lower()
        n = (h["name"] or "").lower()
        if "gold" in n or "gold" in t:
            cls = "commodity"
        elif t in ("bond", "debt") or any(k in n for k in ("debt", "gilt", "liquid", "bond", "fd")):
            cls = "debt"
        elif t in ("equity", "etf", "mutual_fund", "stock"):
            cls = "equity"
        else:
            unclassified += value
            continue
        buckets[cls] = buckets.get(cls, 0.0) + value
    total = sum(buckets.values())
    if total <= 0 or unclassified / (total + unclassified) > 0.4:
        return None
    best = None
    for cls, target_pct in targets.items():
        actual = _safe_div(buckets.get(cls, 0.0), total) * 100
        delta = actual - float(target_pct)
        if delta > 0 and (best is None or delta > best["delta"]):
            best = {"asset_class": cls, "delta": round(delta)}
    return best


# --- 9. data health ----------------------------------------------------------

def _ago_days(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return (_dt.date.today() - _dt.date.fromisoformat(str(s)[:10])).days
    except ValueError:
        return None


def _freshness_label(days: int | None) -> str | None:
    if days is None:
        return None
    if days <= 0:
        return "live"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    return f"{days // 30}mo ago"


def data_health(conn) -> dict:
    row = conn.execute("SELECT * FROM data_health WHERE id = 1").fetchone()
    if not row:
        return {
            "id": 1, "cas_last_import": None, "price_last_refresh": None,
            "sms_last_import": None, "unmatched_transactions": 0,
            "missing_info": None, "health_score": None, "updated_at": None,
            "freshness": {}, "score": None,
        }
    cas_days = _ago_days(row["cas_last_import"])
    price_days = _ago_days(row["price_last_refresh"])
    sms_days = _ago_days(row["sms_last_import"])

    # numeric score from real data presence (0-100), mirroring recompute_health
    has_salary = conn.execute("SELECT COUNT(*) FROM salary").fetchone()[0] > 0
    has_goals = conn.execute("SELECT COUNT(*) FROM goals WHERE status='active'").fetchone()[0] > 0
    has_insurance = conn.execute(
        "SELECT COUNT(*) FROM insurance WHERE archived_at IS NULL").fetchone()[0] > 0
    unmatched = int(row["unmatched_transactions"] or 0)
    score = 40 + (15 if has_salary else 0) + (15 if has_goals else 0) \
        + (10 if has_insurance else 0) + (20 if price_days is not None and price_days <= 7 else 0) \
        - min(20, unmatched)
    score = max(0, min(100, score))

    return {
        "id": 1,
        "cas_last_import": row["cas_last_import"],
        "price_last_refresh": row["price_last_refresh"],
        "sms_last_import": row["sms_last_import"],
        "unmatched_transactions": unmatched,
        "missing_info": row["missing_info"],
        "health_score": row["health_score"],
        "updated_at": row["updated_at"],
        "freshness": {
            "cas": _freshness_label(cas_days),
            "prices": _freshness_label(price_days),
            "sms": _freshness_label(sms_days),
        },
        "score": score,
    }
