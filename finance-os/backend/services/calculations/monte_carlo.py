"""Monte-Carlo goal success probabilities. stdlib only (random.gauss), seeded
per goal so the same inputs always yield the same probability. Expected return
and volatility are blended from the reference assumption files — they are
planning assumptions, never promises, and never a buy/sell recommendation.
"""
from __future__ import annotations

import math
import random

# long-run annualised std devs per asset class (planning approximations)
_VOLS_PCT = {"equity": 15.0, "debt": 4.0, "commodity": 14.0, "cash": 0.5}

_RETURNS_KEY = {"equity": "indian_equity", "debt": "debt_and_bonds",
                "commodity": "gold", "cash": "savings_account"}

_CACHE: dict[tuple, float] = {}
_CACHE_MAX = 128


def blended_return_and_vol(assumptions: dict, targets: dict) -> tuple[float, float]:
    """Weight the reference expected returns by the target allocation to get a
    blended (annual, decimal) return and volatility for goal paths."""
    rets = assumptions.get("expected_returns_pct", {})
    weights = {}
    for cls, pct in (targets or {}).items():
        key = _RETURNS_KEY.get(cls)
        if key and float(pct) > 0:
            weights[cls] = float(pct) / 100.0
    total = sum(weights.values())
    if not weights or total <= 0:  # fall back to a plain equity assumption
        return float(rets.get("indian_equity", 11.0)) / 100, _VOLS_PCT["equity"] / 100
    weights = {k: v / total for k, v in weights.items()}
    ret = sum(w * float(rets.get(_RETURNS_KEY[k], 0.0)) for k, w in weights.items()) / 100
    vol = sum(w * _VOLS_PCT[k] for k, w in weights.items()) / 100
    return ret, vol


def success_probability(current: float, monthly_contribution: float, target: float,
                        months_left: int, exp_ret_annual: float, vol_annual: float,
                        runs: int = 10_000, seed: int = 0) -> float:
    """Share of `runs` simulated paths that reach `target` within `months_left`
    monthly steps. Deterministic via per-goal seed. Results are cached on the
    input tuple so repeat overview loads don't re-pay the simulation."""
    if target <= 0:
        return 0.0
    if months_left <= 0:
        return 100.0 if current >= target else 0.0
    months_left = max(int(months_left), 1)

    key = (round(current, 2), round(monthly_contribution, 2), round(target, 2),
           months_left, round(exp_ret_annual, 4), round(vol_annual, 4), runs, seed)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit

    rng = random.Random(seed)
    mu_m = exp_ret_annual / 12.0
    sig_m = vol_annual / math.sqrt(12.0)
    wins = 0
    for _ in range(runs):
        value = current
        for _m in range(months_left):
            value = value * (1.0 + mu_m + sig_m * rng.gauss(0.0, 1.0)) + monthly_contribution
            if value < 0:
                value = 0.0
        if value >= target:
            wins += 1
    result = round(wins * 100.0 / runs, 1)
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = result
    return result
