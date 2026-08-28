"""The arithmetic behind a fund's advanced ratios. No network, no cache,
no source - just maths on two series somebody else fetched.

WHY THIS FILE EXISTS ALONE
    Every number here can be checked by hand against the inputs, which
    is the whole point of keeping the maths apart from the fetching
    (the same split find_the_overlap.py draws). If a ratio looks wrong,
    the bug is either here or in the data, and this file makes the
    second one visible.

VOCABULARY, so each word means one thing only:

    daily return    p_today / p_yesterday - 1
    ann. return     mean daily return compounded over 252 trading days
    ann. volatility standard deviation of daily returns, x sqrt(252)
    beta            cov(fund, benchmark) / var(benchmark). Above 1 means
                    the fund swings harder than the index, below 1 gentler
    alpha           ann. fund return minus what beta says it should have
                    earned: rf + beta x (ann. benchmark - rf). Positive
                    alpha is return the manager added beyond the market
    sharpe          (ann. return - rf) / ann. volatility
    sortino         like sharpe but only downside days count in the
                    denominator
    max drawdown    worst peak-to-trough fall, always negative or zero

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Portfolio_Analysis_Tab\\compute_the_ratios.py
"""

from __future__ import annotations

from datetime import date, datetime
import math


# ---------------------------------------------------------------------
# PIECES
# ---------------------------------------------------------------------
def daily_returns(prices: list[float]) -> list[float]:
    """One return per price after the first. A zero or negative price is
    skipped with its neighbour, never divided through."""
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
    """How much of the fund's movement the benchmark explains - the
    squared correlation of the two day-aligned return series. 1.0 means
    the index explains everything (an index fund sits near it); a small
    value means the fund dances to its own tune and beta says little."""
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
                   risk_free_pct: float = 0.0,
                   periods: int = 252) -> dict:
    """Beta from cov/var; alpha is what is left once beta explains the
    benchmark's move. The two lists must already be day-aligned."""
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
    return {"beta": round(beta, 3),
            "alpha_pct": round(fund_ann - expected * 100, 2)}


def downside_deviation_pct(daily: list[float], periods: int = 252,
                           target: float = 0.0) -> float | None:
    """Only the days below target count - the denominator Sortino uses."""
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
    """A downside deviation of zero with a positive return is genuinely
    the best kind of year - reported as None-with-a-note upstream, not
    as an infinite number."""
    if ann_return_pct is None or down_dev_pct is None:
        return None
    if down_dev_pct == 0:
        return None
    return round((ann_return_pct - risk_free_pct) / down_dev_pct, 2)


def max_drawdown_pct(prices: list[float]) -> float | None:
    """Worst fall from a running peak. Always <= 0, or None when there
    is no usable series."""
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


# ---------------------------------------------------------------------
# THE WHOLE PERFORMANCE BLOCK, FROM TWO DATED SERIES
# ---------------------------------------------------------------------
def _parse_day(raw: str) -> date | None:
    """mfapi.in publishes dd-mm-yyyy, Yahoo answers ISO. Both accepted."""
    raw = (raw or "").strip()
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
    """fund_points / benchmark_points: [{"date": str, "nav"|"close": float}]

    Only dates present in BOTH series are used - a fund NAV that lags a
    day behind the index is not evidence of anything, and pairing it
    with yesterday's index would quietly corrupt beta.
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
            "note": (f"only {len(shared)} days overlap between the fund's NAV "
                     f"history and the benchmark - {min_points} are needed "
                     "before a ratio means anything"),
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
        "sortino_note": ("no down day against zero in the window" if down == 0 else None),
        # The same window worked out for the benchmark alone, so the
        # advanced-ratios tab can put the fund beside what it tracks -
        # plus r-squared, which says how much of that comparison means
        # anything at all.
        "r_squared": r_squared(fund_daily, bench_daily),
        "benchmark_return_pct": annualised_return_pct(bench_daily, periods),
        "benchmark_volatility_pct": annualised_volatility_pct(bench_daily, periods),
    }


# ---------------------------------------------------------------------
# SELF-CHECK
# ---------------------------------------------------------------------
def main() -> None:
    # A fund that tracks its benchmark with a small extra drift - every
    # printed number can be recomputed by hand from the two series.
    from datetime import timedelta
    start = date(2026, 4, 1)
    days = [(start + timedelta(days=i)).isoformat() for i in range(90)]
    bench = [100 * (1.001 ** i) for i in range(90)]
    fund = [100 * (1.002 ** i) for i in range(90)]
    answer = performance(
        [{"date": d, "nav": p} for d, p in zip(days, fund)],
        [{"date": d, "close": p} for d, p in zip(days, bench)],
        risk_free_pct=0.0, min_points=60)

    print("SELF-CHECK (hand-checkable)")
    for key, value in answer.items():
        print(f"  {key}: {value}")
    print("  max_drawdown of [100, 110, 90, 95]:",
          max_drawdown_pct([100, 110, 90, 95]), "(hand: -18.18)")


if __name__ == "__main__":
    main()
