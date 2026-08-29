"""Debt calculations — pure amortization math + payoff ordering. Every DB-reading
function takes an open sqlite3 connection (row_factory = Row). No FastAPI here.

Finance philosophy (master doc §2): high-interest debt outranks goals/investing,
so the default payoff order is avalanche (highest rate first).
"""
from __future__ import annotations

import datetime as _dt
import math

_BIG = math.inf  # sentinel: payment never clears the balance


def list_debts(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM debts WHERE status='active' AND archived_at IS NULL ORDER BY id"
    ).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


def total_outstanding(conn) -> float:
    r = conn.execute(
        "SELECT COALESCE(SUM(outstanding),0) FROM debts "
        "WHERE status='active' AND archived_at IS NULL"
    ).fetchone()
    return round(float(r[0] or 0.0), 2)


def highest_interest(conn) -> float:
    r = conn.execute(
        "SELECT COALESCE(MAX(interest_rate),0) FROM debts "
        "WHERE status='active' AND archived_at IS NULL"
    ).fetchone()
    return round(float(r[0] or 0.0), 2)


def next_emi(conn) -> dict:
    r = conn.execute(
        "SELECT lender, emi, next_due FROM debts "
        "WHERE status='active' AND archived_at IS NULL AND next_due IS NOT NULL "
        "ORDER BY next_due ASC LIMIT 1"
    ).fetchone()
    if not r:
        return {"lender": None, "emi": 0.0, "next_due": None}
    return {"lender": r["lender"], "emi": round(float(r["emi"] or 0.0), 2),
            "next_due": r["next_due"]}


def months_to_payoff(balance: float, annual_rate_pct: float, payment: float) -> float:
    """Months to amortize `balance` at `annual_rate_pct` with a fixed monthly
    `payment`. Returns _BIG when the payment can't cover the monthly interest."""
    balance = max(float(balance), 0.0)
    if balance <= 0:
        return 0.0
    if payment <= 0:
        return _BIG
    r = float(annual_rate_pct) / 100.0 / 12.0
    if r <= 0:
        return float(math.ceil(balance / payment))
    interest = balance * r
    if payment <= interest:
        return _BIG
    n = -math.log(1.0 - (balance * r) / payment) / math.log(1.0 + r)
    return max(0.0, n)


def total_interest(balance: float, annual_rate_pct: float, payment: float) -> float:
    n = months_to_payoff(balance, annual_rate_pct, payment)
    if math.isinf(n):
        return _BIG
    return max(0.0, payment * n - max(float(balance), 0.0))


def avalanche_order(debts: list[dict]) -> list[dict]:
    return sorted(debts, key=lambda d: (-(d.get("interest_rate") or 0.0),
                                        d.get("outstanding") or 0.0))


def snowball_order(debts: list[dict]) -> list[dict]:
    return sorted(debts, key=lambda d: (d.get("outstanding") or 0.0,
                                        -(d.get("interest_rate") or 0.0)))


def payoff_plan(conn, method: str = "avalanche") -> dict:
    debts = list_debts(conn)
    order = snowball_order(debts) if method == "snowball" else avalanche_order(debts)
    steps = []
    for d in order:
        m = months_to_payoff(d.get("outstanding") or 0.0,
                             d.get("interest_rate") or 0.0,
                             d.get("emi") or 0.0)
        steps.append({
            "id": d["id"],
            "lender": d["lender"],
            "outstanding": round(float(d.get("outstanding") or 0.0), 2),
            "interest_rate": float(d.get("interest_rate") or 0.0),
            "emi": round(float(d.get("emi") or 0.0), 2),
            "months_to_clear": None if math.isinf(m) else round(m, 1),
        })
    finite = [s["months_to_clear"] for s in steps if s["months_to_clear"] is not None]
    return {
        "method": method,
        "steps": steps,
        "total_outstanding": total_outstanding(conn),
        "longest_months": max(finite) if finite else None,
    }


def _book(conn):
    """Collapse the active debt book into one blob: (balance, weighted rate, EMI)."""
    debts = list_debts(conn)
    balance = sum(float(d.get("outstanding") or 0.0) for d in debts)
    emi = sum(float(d.get("emi") or 0.0) for d in debts)
    if balance > 0:
        rate = sum(float(d.get("outstanding") or 0.0) * float(d.get("interest_rate") or 0.0)
                   for d in debts) / balance
    else:
        rate = 0.0
    return balance, rate, emi


def simulate(conn, extra_payment: float = 0.0, salary_increase: float = 0.0,
             bonus: float = 0.0) -> dict:
    """Baseline payoff vs. payoff with extra monthly capacity (extra_payment +
    salary_increase) and an optional one-time `bonus` lump against the balance.
    A zero delta returns exactly zero months / interest saved (identity)."""
    balance, rate, emi = _book(conn)
    extra_monthly = max(0.0, float(extra_payment)) + max(0.0, float(salary_increase))
    lump = max(0.0, float(bonus))

    base_n = months_to_payoff(balance, rate, emi)
    base_int = total_interest(balance, rate, emi)

    new_balance = max(balance - lump, 0.0)
    new_n = months_to_payoff(new_balance, rate, emi + extra_monthly)
    new_int = total_interest(new_balance, rate, emi + extra_monthly)

    def _fin(x):
        return 0.0 if (x is None or math.isinf(x)) else x

    months_saved = _fin(base_n) - _fin(new_n)
    if math.isinf(base_n) and not math.isinf(new_n):
        months_saved = 0.0  # can't quantify a save from "never" -> report 0
    months_saved = max(0.0, min(months_saved, _fin(base_n)))

    interest_saved = max(0.0, _fin(base_int) - _fin(new_int))

    today = _dt.date.today()
    payoff_months = 0 if math.isinf(new_n) else int(round(new_n))
    new_payoff_date = (today + _dt.timedelta(days=payoff_months * 30)).isoformat()

    return {
        "baseline_months": None if math.isinf(base_n) else round(base_n, 1),
        "new_months": None if math.isinf(new_n) else round(new_n, 1),
        "months_saved": round(months_saved, 1),
        "interest_saved": round(interest_saved, 2),
        "new_payoff_date": new_payoff_date,
    }


_LEARN = {
    "avalanche": {
        "action": "Pay the highest-rate debt first",
        "reason": "Interest compounds fastest on the highest APR, so every extra "
                  "rupee there saves the most.",
        "learn": "The avalanche method: keep minimums on everything, throw all "
                 "spare cash at the highest interest rate, then roll that payment "
                 "into the next-highest once it's clear.",
    },
    "snowball": {
        "action": "Clear the smallest balance first",
        "reason": "Quick wins build momentum and free up a full EMI slot sooner.",
        "learn": "The snowball method optimises for motivation over maths — it "
                 "costs slightly more interest than avalanche but people stick "
                 "with it.",
    },
    "credit_card": {
        "action": "Never revolve a credit-card balance",
        "reason": "Card APRs of 36-48% dwarf any investment return; carrying a "
                  "balance is a guaranteed loss.",
        "learn": "Pay the statement balance in full every cycle. If you already "
                 "carry one, a personal loan at ~12% to clear the card is almost "
                 "always worth it.",
    },
}


def learning(topic: str) -> dict:
    return _LEARN.get(topic, {
        "action": "Rank debts by interest rate",
        "reason": "High-interest debt outranks investing in the priority order.",
        "learn": "List every debt with its APR and minimum payment. Attack the "
                 "top of the list; keep minimums on the rest.",
    })
