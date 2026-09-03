"""Scenario simulator — pure math over the current DB snapshot. No FastAPI, no
LLM. Given a set of levers (extra debt payment, monthly salary change, one-off
bonus, SIP step-up %), project the change in net worth and in goal probability.
"""
from __future__ import annotations

import datetime as _dt

from services.calculations import core, debt as debt_calc


def _goal_prob_total(conn) -> float:
    g = core.goals_overview(conn)
    if not g["goals"]:
        return 0.0
    return round(sum(x["probability"] for x in g["goals"]) / len(g["goals"]), 2)


def simulate(conn, extra_debt_payment: float = 0.0, monthly_salary_delta: float = 0.0,
             one_off_bonus: float = 0.0, sip_step_up_pct: float = 0.0,
             horizon_months: int = 36) -> dict:
    extra_debt_payment = max(0.0, float(extra_debt_payment))
    monthly_salary_delta = float(monthly_salary_delta)
    one_off_bonus = max(0.0, float(one_off_bonus))
    sip_step_up_pct = max(0.0, float(sip_step_up_pct))

    nw = core.net_worth(conn)
    base_net_worth = nw["net_worth"]

    # --- debt leg: extra payment + bonus lump shorten payoff and cut interest ---
    debt_sim = debt_calc.simulate(
        conn, extra_payment=extra_debt_payment, bonus=one_off_bonus
    )
    interest_saved = debt_sim.get("interest_saved", 0.0)

    # --- investing leg: freed cash + salary delta + SIP step-up, compounded ---
    monthly_invest_capacity = monthly_salary_delta + sip_step_up_pct  # rupees/mo
    r = 0.10 / 12.0  # 10% p.a. nominal, monthly
    fv_contributions = 0.0
    if monthly_invest_capacity > 0:
        fv_contributions = monthly_invest_capacity * (((1 + r) ** horizon_months - 1) / r)
    fv_bonus_if_invested = 0.0  # bonus went to debt above; alternative not modelled

    projected_net_worth = round(
        base_net_worth + interest_saved + fv_contributions + fv_bonus_if_invested, 2
    )

    base_goal_prob = _goal_prob_total(conn)
    # extra capacity nudges goal funding; bounded, simple linear model
    lift = min(25.0, (monthly_invest_capacity / 5000.0) * 5.0 + (one_off_bonus / 100000.0) * 5.0)
    projected_goal_prob = round(min(100.0, base_goal_prob + lift), 2)

    today = _dt.date.today()
    return {
        "horizon_months": horizon_months,
        "levers": {
            "extra_debt_payment": extra_debt_payment,
            "monthly_salary_delta": monthly_salary_delta,
            "one_off_bonus": one_off_bonus,
            "sip_step_up_pct": sip_step_up_pct,
        },
        "net_worth": {
            "current": base_net_worth,
            "projected": projected_net_worth,
            "delta": round(projected_net_worth - base_net_worth, 2),
        },
        "debt": debt_sim,
        "goal_probability": {
            "current": base_goal_prob,
            "projected": projected_goal_prob,
            "delta": round(projected_goal_prob - base_goal_prob, 2),
        },
        "as_of": today.isoformat(),
    }
