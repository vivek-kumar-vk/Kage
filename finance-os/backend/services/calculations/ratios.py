"""The arithmetic behind every risk/return ratio shown in the Analysis tab
and the Analyse drawer. No network, no DB — maths on two day-aligned
series somebody else fetched. Ported verbatim in spirit from the house
compute_the_ratios.py (Screens/Finance/Calculations) so the numbers stay
hand-checkable and identical across surfaces.

VOCABULARY, so each word means one thing only:
    daily return     p_today / p_yesterday - 1
    ann. return      mean growth compounded over 252 trading days
    ann. volatility  stdev of daily returns x sqrt(252)
    beta             cov(fund, benchmark) / var(benchmark)
    alpha            ann. return minus what beta says it should have earned
    sharpe           (ann. return - rf) / ann. volatility
    sortino          sharpe with only downside days in the denominator
    max drawdown     worst peak-to-trough fall, always <= 0
"""
from __future__ import annotations

import math
from datetime import date, datetime


def daily_returns(prices: list[float]) -> list[float]:
    clean: list[float] = []
    for price in prices:
        try:
            value = float(price)
        except (TypeError, ValueError):
            value = 0.0
        if value > 0:
            clean.append(value)
    return [clean[i] / clean[i - 1] - 1.0 for i in range(1, len(clean))
            if clean[i - 1] > 0]


def annualised_return_pct(daily: list[float], periods: int = 252) -> float | None:
    if not daily:
        return None
    growth = 1.0
    for r in daily:
        growth *= 1.0 + r
    if growth <= 0:
        return None
    years = len(daily) / periods
    if years <= 0:
        return None
    return round((growth ** (1.0 / years) - 1.0) * 100, 2)


def annualised_volatility_pct(daily: list[float], periods: int = 252) -> float | None:
    if len(daily) < 2:
        return None
    mean = sum(daily) / len(daily)
    variance = sum((r - mean) ** 2 for r in daily) / (len(daily) - 1)
    return round(math.sqrt(variance) * math.sqrt(periods) * 100, 2)


def r_squared(fund_daily: list[float], bench_daily: list[float]) -> float | None:
    """How much of the fund's movement the benchmark explains (squared
    correlation). Near 1.0 for an index fund; small means beta says little."""
    n = min(len(fund_daily), len(bench_daily))
    if n < 3:
        return None
    fund = fund_daily[-n:]
    bench = bench_daily[-n:]
    mean_f = sum(fund) / n
    mean_b = sum(bench) / n
    cov = sum((fund[i] - mean_f) * (bench[i] - mean_b) for i in range(n)) / (n - 1)
    var_f = sum((r - mean_f) ** 2 for r in fund) / (n - 1)
    var_b = sum((r - mean_b) ** 2 for r in bench) / (n - 1)
    if var_f <= 0 or var_b <= 0:
        return None
    corr = cov / math.sqrt(var_f * var_b)
    return round(corr * corr, 3)


def beta_and_alpha(fund_daily: list[float], bench_daily: list[float],
                   risk_free_pct: float = 0.0, periods: int = 252) -> dict:
    n = min(len(fund_daily), len(bench_daily))
    if n < 2:
        return {"beta": None, "alpha_pct": None}
    fund = fund_daily[-n:]
    bench = bench_daily[-n:]
    mean_f = sum(fund) / n
    mean_b = sum(bench) / n
    cov = sum((fund[i] - mean_f) * (bench[i] - mean_b) for i in range(n)) / (n - 1)
    var_b = sum((b - mean_b) ** 2 for b in bench) / (n - 1)
    if var_b == 0:
        return {"beta": None, "alpha_pct": None}
    beta = cov / var_b
    fund_ann = annualised_return_pct(fund, periods)
    bench_ann = annualised_return_pct(bench, periods)
    rf = risk_free_pct / 100.0
    if fund_ann is None or bench_ann is None:
        return {"beta": round(beta, 3), "alpha_pct": None}
    expected = rf + beta * (bench_ann / 100.0 - rf)
    return {"beta": round(beta, 3), "alpha_pct": round(fund_ann - expected * 100, 2)}


def downside_deviation_pct(daily: list[float], periods: int = 252,
                           target: float = 0.0) -> float | None:
    misses = [r for r in daily if r < target]
    if not misses:
        return 0.0
    variance = sum((r - target) ** 2 for r in misses) / len(daily)
    return round(math.sqrt(variance) * math.sqrt(periods) * 100, 2)


def sharpe_ratio(ann_return_pct: float | None, ann_vol_pct: float | None,
                 risk_free_pct: float = 0.0) -> float | None:
    if ann_return_pct is None or not ann_vol_pct:
        return None
    return round((ann_return_pct - risk_free_pct) / ann_vol_pct, 2)


def sortino_ratio(ann_return_pct: float | None, down_dev_pct: float | None,
                  risk_free_pct: float = 0.0) -> float | None:
    if ann_return_pct is None or down_dev_pct is None:
        return None
    if down_dev_pct == 0:
        return None
    return round((ann_return_pct - risk_free_pct) / down_dev_pct, 2)


def max_drawdown_pct(prices: list[float]) -> float | None:
    peak = None
    worst = None
    for price in prices:
        try:
            value = float(price)
        except (TypeError, ValueError):
            continue
        if value <= 0:
            continue
        peak = value if peak is None else max(peak, value)
        drawdown = value / peak - 1.0
        worst = drawdown if worst is None else min(worst, drawdown)
    return round(worst * 100, 2) if worst is not None else None


def _parse_day(raw) -> date | None:
    """mfapi writes dd-mm-yyyy; the ledger and Yahoo write ISO. Both parse,
    or the point is skipped."""
    raw = str(raw or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    try:
        return datetime.strptime(raw, "%d-%m-%Y").date()
    except ValueError:
        return None


def performance(fund_points: list[dict], benchmark_points: list[dict],
                risk_free_pct: float = 0.0, periods: int = 252,
                min_points: int = 60) -> dict:
    """fund_points: [{"date", "nav"}]; benchmark_points: [{"date", "close"}].

    Only dates present in BOTH series are used — a fund NAV that lags a
    day behind the index is not evidence of anything, and pairing it with
    yesterday's index would quietly corrupt beta.
    """
    fund_by_day: dict[date, float] = {}
    for row in fund_points or []:
        day = _parse_day(row.get("date"))
        if day is not None and row.get("nav") is not None:
            fund_by_day[day] = float(row["nav"])
    bench_by_day: dict[date, float] = {}
    for row in benchmark_points or []:
        day = _parse_day(row.get("date"))
        if day is not None and row.get("close") is not None:
            bench_by_day[day] = float(row["close"])

    shared = sorted(set(fund_by_day) & set(bench_by_day))
    if len(shared) < min_points:
        return {
            "has_data": False,
            "note": (f"only {len(shared)} days overlap between the two series — "
                     f"{min_points} are needed before a ratio means anything"),
            "shared_days": len(shared),
        }

    fund_prices = [fund_by_day[d] for d in shared]
    fund_daily = daily_returns(fund_prices)
    bench_daily = daily_returns([bench_by_day[d] for d in shared])

    beta_alpha = beta_and_alpha(fund_daily, bench_daily, risk_free_pct, periods)
    ann_return = annualised_return_pct(fund_daily, periods)
    vol = annualised_volatility_pct(fund_daily, periods)
    down = downside_deviation_pct(fund_daily, periods)

    return {
        "has_data": True,
        "shared_days": len(shared),
        "first_day": str(shared[0]),
        "last_day": str(shared[-1]),
        "return_1y_pct": ann_return,
        "volatility_pct": vol,
        "max_drawdown_pct": max_drawdown_pct(fund_prices),
        "beta": beta_alpha["beta"],
        "alpha_pct": beta_alpha["alpha_pct"],
        "sharpe": sharpe_ratio(ann_return, vol, risk_free_pct),
        "sortino": sortino_ratio(ann_return, down, risk_free_pct),
        "r_squared": r_squared(fund_daily, bench_daily),
        "benchmark_return_pct": annualised_return_pct(bench_daily, periods),
        "benchmark_volatility_pct": annualised_volatility_pct(bench_daily, periods),
    }
