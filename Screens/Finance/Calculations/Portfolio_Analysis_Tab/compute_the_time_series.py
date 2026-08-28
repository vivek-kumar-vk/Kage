"""Time-series maths for the whole portfolio, drawn from series that
already exist on disk.

THE QUESTION THIS FILE ANSWERS
    The rest of this tab reduces history to single numbers (max
    drawdown, 1Y return). This file keeps history AS history: how each
    fund and the whole portfolio moved through time, so the tab can
    draw lines and heatmaps instead of quoting one stale figure.

WHERE EVERY SERIES COMES FROM (C4 - nothing fetched fresh, nothing invented)
    fund NAV histories     the stored per-fund profiles under
                           Saved_Records/fund_profiles/<code>.json -
                           their nav_history.points carry the FULL
                           series from inception since the 2026-08-24
                           change to fetch_fund_facts.nav_history
    benchmark history      fetch_market_facts.index_history - the same
                           cached call analyse_a_fund already makes;
                           twelve hours of cache, never a fresh web
                           call just to open a tab
    transaction lots       Saved_Records/my_investments.csv, one real
                           row per buy or sell
    portfolio value        Saved_Records/fund_nav_ledger.csv, read
                           strictly as-is - it is young, so the chart
                           is thin, and NO row is ever backfilled (C12)
    thresholds             Reference_Data files only. The equity band
                           comes from india_planning_assumptions.json
                           healthy_ratio_targets.equity_allocation_rule;
                           the holding-period split comes from
                           india_income_tax_rules.json capital_gains.

THE HONESTY RULES
    A metric without enough real history returns has_data:false and a
    plain-language note - never zeros wearing a chart costume. Tax
    labels describe holding age only; nothing here recommends buying,
    selling, switching or rebalancing anything (C5).

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Portfolio_Analysis_Tab\\compute_the_time_series.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))         # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fetch_market_facts                        # noqa: E402
import read_what_i_own                           # noqa: E402
import track_the_nav_ledger                      # noqa: E402

REFERENCE_DATA = SCREEN / "Reference_Data"
TAX_RULES_FILE = REFERENCE_DATA / "india_income_tax_rules.json"
PLANNING_ASSUMPTIONS_FILE = REFERENCE_DATA / "india_planning_assumptions.json"

# A display budget, not a data rule: a rolling-CAGR curve spanning years
# can hold thousands of hand-checked points, and no canvas needs all of
# them. First and last point always survive the thinning.
MAX_CHART_POINTS = 400

# Simple (non-compounding) fee arithmetic over real held periods. A leap
# year or two of slop is cheaper here than pretending days are exact.
DAYS_PER_YEAR = 365.25
DAYS_PER_MONTH = 30.4375


# ---------------------------------------------------------------------
# GENERIC PIECES - parse, sort, thin
# ---------------------------------------------------------------------
def _parse_day(raw) -> date | None:
    """mfapi.in publishes dd-mm-yyyy, Yahoo answers ISO. Both accepted."""
    raw = ("" if raw is None else str(raw)).strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass
    try:
        return datetime.strptime(raw, "%d-%m-%Y").date()
    except ValueError:
        return None


def _dated_series(points: list[dict], value_key: str) -> list[tuple[date, float]]:
    """[(day, positive value)] oldest first. Bad rows are skipped, not
    guessed around - a gap the source skipped stays a gap."""
    rows: list[tuple[date, float]] = []
    for row in points or []:
        day = _parse_day(row.get("date"))
        try:
            value = float(row.get(value_key))
        except (TypeError, ValueError):
            continue
        if day is not None and value > 0:
            rows.append((day, value))
    rows.sort(key=lambda r: r[0])
    return rows


def _thin_for_chart(items: list[dict]) -> tuple[list[dict], int | None]:
    """Evenly thin a series to MAX_CHART_POINTS, keeping first and last.
    Returns (thinned, original_count_or_None)."""
    if len(items) <= MAX_CHART_POINTS:
        return items, None
    step = math.ceil(len(items) / MAX_CHART_POINTS)
    picked = items[::step]
    if picked[-1] is not items[-1]:
        picked.append(items[-1])
    return picked, len(items)


def _empty(reason: str, **extra) -> dict:
    return {"has_data": False, "note": reason, **extra}


# ---------------------------------------------------------------------
# ROLLING CAGR - one annualised growth rate per day, windows sliding
# ---------------------------------------------------------------------
def rolling_cagr(points: list[dict], window_points: int,
                 trading_days_per_year: int) -> dict:
    """Annualised return over every window ending at each observation.

    growth**(trading_days / window_points) - 1: a 252-point window on a
    252-day year annualises to itself; a 756-point window un-cubes three
    years of growth into the same annual rate.
    """
    series = _dated_series(points, "nav")
    if len(series) < window_points + 1:
        return _empty(
            f"{len(series)} daily NAV points on file; a rolling "
            f"{window_points}-point window needs at least "
            f"{window_points + 1}",
            points_on_file=len(series))
    exponent = trading_days_per_year / window_points
    every = [{"date": series[i][0].isoformat(),
              "cagr_pct": round(((series[i][1] /
                                  series[i - window_points][1]) **
                                 exponent - 1.0) * 100, 3)}
             for i in range(window_points, len(series))]
    thinned, original = _thin_for_chart(every)
    return {"has_data": True,
            "window_points": window_points,
            "first_day": thinned[0]["date"],
            "last_day": thinned[-1]["date"],
            "points": thinned,
            "downsampled_from": original}


# ---------------------------------------------------------------------
# DRAWDOWN CURVE - running peak, and how far below it each day sat
# ---------------------------------------------------------------------
def drawdown_curve(points: list[dict]) -> dict:
    """The running-peak arithmetic compute_the_ratios.max_drawdown_pct
    reduces to one number, kept whole: one point per observation."""
    series = _dated_series(points, "nav")
    if len(series) < 2:
        return _empty(f"{len(series)} daily NAV points on file; a "
                      "drawdown curve needs at least 2",
                      points_on_file=len(series))
    peak = 0.0
    worst = 0.0
    every = []
    for day, price in series:
        peak = max(peak, price)
        below = (price / peak - 1.0) * 100.0
        worst = min(worst, below)
        every.append({"date": day.isoformat(), "nav": price,
                      "drawdown_pct": round(below, 2)})
    thinned, original = _thin_for_chart(every)
    return {"has_data": True,
            "max_drawdown_pct": round(worst, 2),
            "first_day": thinned[0]["date"],
            "last_day": thinned[-1]["date"],
            "points": thinned,
            "downsampled_from": original}


# ---------------------------------------------------------------------
# PORTFOLIO-WEIGHTED COMBINATION - many fund NAVs, one curve
# ---------------------------------------------------------------------
def portfolio_level_series(series_by_code: dict[str, list[tuple[date, float]]],
                           weights_by_code: dict[str, float]) -> dict:
    """One value-weighted index out of several fund NAV series.

    Every fund is rebased to 1.0 at its own first point; the combined
    level on a day is the current-value-weighted average of the funds'
    growth-since-their-own-start, over the days EVERY included fund
    published. Weights are today's values from the stored snapshot -
    a descriptive blend of where the money sits now, stated as such.
    """
    usable = {c: s for c, s in (series_by_code or {}).items()
              if len(s) >= 2}
    if not usable:
        return _empty("no fund has a stored NAV history with at least "
                      "2 daily points")
    weight_base = sum(weights_by_code.get(c, 0.0) for c in usable)
    if weight_base <= 0:
        return _empty("the holdings snapshot carries no positive current "
                      "values to weight the funds by")
    common: set[date] | None = None
    for series in usable.values():
        days = {d for d, _ in series}
        common = days if common is None else (common & days)
    shared = sorted(common or set())
    if len(shared) < 2:
        return _empty(
            f"only {len(shared)} days are common to every analysed fund's "
            "NAV history - not enough to draw one line for the portfolio",
            funds_combined=sorted(usable))
    price_by_day = {c: dict(s) for c, s in usable.items()}
    first_price = {c: price_by_day[c][shared[0]] for c in usable}
    levels = []
    for day in shared:
        level = sum(weights_by_code.get(c, 0.0) / weight_base
                    * price_by_day[c][day] / first_price[c]
                    for c in usable)
        levels.append((day, level))
    return {"has_data": True,
            "funds_combined": sorted(usable),
            "first_day": shared[0].isoformat(),
            "last_day": shared[-1].isoformat(),
            "levels": levels}


def levels_as_points(levels: list[tuple[date, float]],
                     value_name: str) -> tuple[list[dict], int | None]:
    """[(day, level)] into chart rows, thinned like every other series."""
    every = [{"date": day.isoformat(), value_name: round(level, 4)}
             for day, level in levels]
    return _thin_for_chart(every)


def portfolio_vs_benchmark(levels: list[tuple[date, float]],
                           benchmark_points: list[dict],
                           benchmark_name: str, benchmark_symbol: str,
                           min_shared_days: int) -> dict:
    """Both sides rebased to 100 on the first shared day - growth, not
    level. Same benchmark source analyse_a_fund trusts for beta/alpha."""
    bench = dict(_dated_series(benchmark_points or [], "close"))
    shared = [day for day, _ in levels if day in bench]
    if len(shared) < min_shared_days:
        return _empty(
            f"only {len(shared)} days overlap between the combined "
            f"portfolio curve and {benchmark_name} ({benchmark_symbol}) - "
            f"{min_shared_days} are needed before the comparison means "
            "anything",
            shared_days=len(shared))
    first_day = shared[0]
    portfolio_base = dict(levels)[first_day]
    benchmark_base = bench[first_day]
    every = [{"date": day.isoformat(),
              "portfolio_index": round(level / portfolio_base * 100.0, 2),
              "benchmark_index": round(bench[day] / benchmark_base * 100.0, 2)}
             for day, level in levels if day in bench]
    thinned, original = _thin_for_chart(every)
    return {"has_data": True,
            "benchmark": benchmark_name,
            "benchmark_symbol": benchmark_symbol,
            "shared_days": len(shared),
            "first_day": thinned[0]["date"],
            "last_day": thinned[-1]["date"],
            "points": thinned,
            "downsampled_from": original,
            "note": ("both lines are rebased to 100 on the first shared "
                     "day, so the picture is cumulative growth")}


# ---------------------------------------------------------------------
# CORRELATION - pairwise, on overlapping dates only
# ---------------------------------------------------------------------
def _daily_returns_by_day(series: list[tuple[date, float]]) -> dict[date, float]:
    """One return per day AFTER the first, keyed by that day - so two
    funds only ever share returns they both actually published."""
    return {series[i][0]: series[i][1] / series[i - 1][1] - 1.0
            for i in range(1, len(series)) if series[i - 1][1] > 0}


def pearson(first: list[float], second: list[float]) -> float | None:
    """Pearson r, or None when either side does not vary at all - a flat
    series correlates with nothing, and inventing a 0 would be a lie."""
    n = min(len(first), len(second))
    if n < 2:
        return None
    mean_a = sum(first) / n
    mean_b = sum(second) / n
    cov = sum((first[i] - mean_a) * (second[i] - mean_b) for i in range(n))
    var_a = sum((v - mean_a) ** 2 for v in first[:n])
    var_b = sum((v - mean_b) ** 2 for v in second[:n])
    if var_a == 0 or var_b == 0:
        return None
    return cov / math.sqrt(var_a * var_b)


def correlation_between_funds(series_by_code: dict[str, list[tuple[date, float]]],
                              names_by_code: dict[str, str],
                              min_shared_days: int) -> dict:
    """Every fund pair, correlated on the days BOTH published a NAV."""
    codes = sorted(series_by_code)
    if not codes:
        return _empty("no fund with a stored NAV history was available")
    returns_by_code = {c: _daily_returns_by_day(series_by_code[c])
                       for c in codes}
    pairs = []
    grid: dict[str, dict[str, float | None]] = {c: {} for c in codes}
    any_pair = False
    for i, first_code in enumerate(codes):
        grid[first_code][first_code] = 1.0
        for second_code in codes[i + 1:]:
            shared = sorted(set(returns_by_code[first_code])
                            & set(returns_by_code[second_code]))
            entry = {"first_fund": names_by_code.get(first_code, first_code),
                     "second_fund": names_by_code.get(second_code, second_code),
                     "overlap_days": len(shared)}
            if len(shared) < min_shared_days:
                entry.update({
                    "has_data": False,
                    "correlation": None,
                    "note": (f"only {len(shared)} shared return days - "
                             f"{min_shared_days} are needed before a "
                             "correlation means anything")})
                grid[first_code][second_code] = None
                grid[second_code][first_code] = None
            else:
                r = pearson([returns_by_code[first_code][d] for d in shared],
                            [returns_by_code[second_code][d] for d in shared])
                if r is None:
                    entry.update({
                        "has_data": False,
                        "correlation": None,
                        "note": ("one of the series does not vary on the "
                                 "shared days, so there is nothing to "
                                 "correlate")})
                    grid[first_code][second_code] = None
                    grid[second_code][first_code] = None
                else:
                    rounded = round(r, 4)
                    entry.update({"has_data": True,
                                  "correlation": rounded,
                                  "note": None})
                    grid[first_code][second_code] = rounded
                    grid[second_code][first_code] = rounded
                    any_pair = True
            pairs.append(entry)
    matrix = [[grid[a][b] for b in codes] for a in codes]
    return {"has_data": any_pair,
            "codes": codes,
            "code_names": [names_by_code.get(c, c) for c in codes],
            "matrix": matrix,
            "pairs": pairs,
            "min_shared_days": min_shared_days}


# ---------------------------------------------------------------------
# TAX LOTS - holding age per real purchase, against the rulebook
# ---------------------------------------------------------------------
def tax_lot_breakdown(transactions: list[dict], rules_doc: dict,
                      today: date) -> dict:
    """Long-term / short-term labels for every mutual-fund purchase lot.

    The label comes only from how long ago the money went in, measured
    against india_income_tax_rules.json's holding-period rule. It says
    nothing about what to do with the lot (C5), and it inherits the
    rulebook's [UNVERIFIED] tag until a person checks the Finance Act.
    """
    rule = ((rules_doc or {}).get("capital_gains") or {}
            ).get("listed_equity_and_equity_mutual_funds") or {}
    months_needed = rule.get("long_term_after_months")
    if not months_needed:
        return _empty(
            "india_income_tax_rules.json carries no "
            "capital_gains.listed_equity_and_equity_mutual_funds."
            "long_term_after_months rule to measure holding age against")
    verified = bool(rules_doc.get("verified_by_a_person"))
    tag = "" if verified else "[UNVERIFIED] "

    buys = [t for t in transactions or []
            if t.get("kind") == "mutual_fund"
            and _positive_amount(t)]
    grouped: dict[str, list[dict]] = {}
    for row in buys:
        grouped.setdefault(row["identifier"], []).append(row)

    holdings = []
    total_long = 0.0
    total_short = 0.0
    for identifier, rows in grouped.items():
        lots = []
        long_amount = 0.0
        short_amount = 0.0
        for row in rows:
            held_days = (today - row["_date"]).days
            months_held = int(held_days // DAYS_PER_MONTH)
            treatment = ("long-term" if months_held >= months_needed
                         else "short-term")
            amount = float(row.get("amount") or 0)
            if treatment == "long-term":
                long_amount += amount
                total_long += amount
            else:
                short_amount += amount
                total_short += amount
            units = row.get("units")
            lots.append({"date": row["_date"].isoformat(),
                         "amount": round(amount, 2),
                         "units": round(float(units), 4)
                                  if units not in (None, "") else None,
                         "months_held": months_held,
                         "treatment": treatment})
        holdings.append({"scheme_name": rows[0]["name"],
                         "identifier": identifier,
                         "lots": lots,
                         "long_term_amount": round(long_amount, 2),
                         "short_term_amount": round(short_amount, 2)})
    holdings.sort(key=lambda h: h["scheme_name"])
    if not holdings:
        return {"has_data": False,
                "verified_by_a_person": verified,
                "note": tag + "no mutual-fund purchases are recorded in "
                        "my_investments.csv yet, so there is no holding "
                        "age to describe"}
    return {"has_data": True,
            "as_of": today.isoformat(),
            "holding_period_rule": {
                "long_term_after_months": months_needed,
                "source_file": ("Screens/Finance/Reference_Data/"
                                "india_income_tax_rules.json -> capital_gains."
                                "listed_equity_and_equity_mutual_funds")},
            "verified_by_a_person": verified,
            "holdings": holdings,
            "totals": {"long_term_amount": round(total_long, 2),
                       "short_term_amount": round(total_short, 2)},
            "note": tag + "labels describe each purchase's holding AGE "
                    "against the FY rulebook only - informational, and "
                    "never a suggestion to sell or hold anything (C5)"}


def _positive_amount(row: dict) -> bool:
    """A real buy: an amount that parses positive (a sell parses
    negative and drops out of purchase-only metrics)."""
    try:
        return float(row.get("amount")) > 0
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------
# SIP / LUMP-SUM CASHFLOW VISIBILITY - the real purchase pattern
# ---------------------------------------------------------------------
def cashflow_visibility(transactions: list[dict]) -> dict:
    """What actually went in, when - reads my_investments.csv as-is.

    Sells are excluded: this describes the purchase pattern only. No
    'recurring vs lump-sum' verdict is stamped on a scheme; the counts,
    gaps and monthly totals say enough without INKY editorialising.
    """
    buys = [t for t in transactions or [] if _positive_amount(t)]
    if not buys:
        return _empty("no purchases are recorded in my_investments.csv yet")

    buys.sort(key=lambda r: r["_date"])
    by_month: dict[str, float] = {}
    by_scheme: dict[str, dict] = {}
    total = 0.0
    for row in buys:
        month = row["_date"].strftime("%Y-%m")
        amount = float(row["amount"])
        total += amount
        by_month[month] = by_month.get(month, 0.0) + amount
        bucket = by_scheme.setdefault(row["identifier"], {
            "scheme_name": row["name"], "days": [], "total": 0.0})
        bucket["days"].append(row["_date"])
        bucket["total"] += amount

    schemes = []
    for identifier, bucket in by_scheme.items():
        days = bucket["days"]
        gaps = [(days[i] - days[i - 1]).days for i in range(1, len(days))]
        schemes.append({
            "identifier": identifier,
            "scheme_name": bucket["scheme_name"],
            "purchase_count": len(days),
            "first_purchase": days[0].isoformat(),
            "last_purchase": days[-1].isoformat(),
            "distinct_months": len({d.strftime("%Y-%m") for d in days}),
            "median_gap_days": _median(gaps),
            "total_amount": round(bucket["total"], 2)})
    schemes.sort(key=lambda s: -s["purchase_count"])
    return {"has_data": True,
            "purchases_only": True,
            "first_purchase": buys[0]["_date"].isoformat(),
            "last_purchase": buys[-1]["_date"].isoformat(),
            "total_purchased": round(total, 2),
            "purchase_rows": len(buys),
            "by_month": [{"month": m, "amount": round(a, 2)}
                         for m, a in sorted(by_month.items())],
            "by_scheme": schemes,
            "note": "every figure comes from real my_investments.csv rows; "
                    "sells are excluded"}


def _median(values: list[int]) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) // 2


# ---------------------------------------------------------------------
# EQUITY ALLOCATION VS THE REFERENCE BAND - threshold read, never typed
# ---------------------------------------------------------------------
def equity_vs_band(equity_pct: float | None,
                   assumptions_doc: dict) -> dict:
    """Where the portfolio's equity share sits beside the reference
    formula. The formula itself is READ from
    india_planning_assumptions.json healthy_ratio_targets.equity_allocation_rule -
    never hardcoded here, never turned into advice (C5)."""
    rule = ((assumptions_doc or {}).get("healthy_ratio_targets") or {}
            ).get("equity_allocation_rule") or {}
    source = ("Screens/Finance/Reference_Data/"
              "india_planning_assumptions.json -> healthy_ratio_targets"
              ".equity_allocation_rule")
    band_formula = rule.get("formula")
    if equity_pct is None:
        return {"has_data": False,
                "equity_allocation_pct": None,
                "band_formula": band_formula,
                "band_value_pct": None,
                "band_source_file": source,
                "note": "the analysed funds carry no asset split yet, so "
                        "there is no equity share to place beside the "
                        "reference formula"}
    return {"has_data": True,
            "equity_allocation_pct": round(equity_pct, 2),
            "band_formula": band_formula,
            # The formula needs an age; INKY keeps no age on file, so no
            # number is computed rather than guessed.
            "band_value_pct": None,
            "band_source_file": source,
            "note": "the reference band needs an age, which INKY does not "
                    "have on file, so the formula is quoted instead of "
                    "computed - descriptive framing only (C5)"}


# ---------------------------------------------------------------------
# COST DRAG - what the expense ratios have quietly cost over time
# ---------------------------------------------------------------------
def cost_drag(buys_by_code: dict[str, list[dict]],
              expense_ratio_by_code: dict[str, float],
              values_by_code: dict[str, float], today: date) -> dict:
    """Expense-ratio rupees accrued by each real purchase lot, simple
    (non-compounding), from the lot's date to today:

        fee = amount x expense_ratio% x days_held / 365.25

    Real fees actually leave through the NAV rather than a side pocket,
    so this is a stated approximation - arithmetic on real amounts,
    dates and published expense ratios, nothing more.
    """
    lots = [(code, row["_date"], float(row["amount"]))
            for code, rows in (buys_by_code or {}).items()
            for row in rows
            if expense_ratio_by_code.get(code) is not None
            and _positive_amount(row)]
    valued = [(values_by_code[c], expense_ratio_by_code[c])
              for c in buys_by_code or {}
              if values_by_code.get(c) and expense_ratio_by_code.get(c)
              is not None]
    weight_base = sum(v for v, _ in valued)
    weighted_er = (round(sum(v * e / weight_base for v, e in valued), 3)
                   if weight_base > 0 else None)
    if not lots or weighted_er is None:
        return {"has_data": False,
                "weighted_expense_ratio_pct": weighted_er,
                "note": "no purchase lots with a known expense ratio are "
                        "on file yet, so there is no drag to add up"}
    total = sum(_lot_fee(code, lot_date, amount, expense_ratio_by_code, today)
                for code, lot_date, amount in lots)
    first_year = min(d.year for _, d, _ in lots)
    by_year = []
    for year in range(first_year, today.year + 1):
        boundary = min(date(year, 12, 31), today)
        cumulative = sum(_lot_fee(code, lot_date, amount,
                                  expense_ratio_by_code, boundary)
                         for code, lot_date, amount in lots
                         if lot_date <= boundary)
        by_year.append({"year": year,
                        "cumulative_rupees": round(cumulative, 2)})
    missing = sorted(set(buys_by_code or {}) - set(expense_ratio_by_code))
    return {"has_data": True,
            "as_of": today.isoformat(),
            "weighted_expense_ratio_pct": weighted_er,
            "weighted_over_values": round(weight_base, 2),
            "lots_counted": len(lots),
            "funds_without_expense_ratio": sorted(missing),
            "cumulative_rupees_as_of_today": round(total, 2),
            "by_year": by_year,
            "method_note": ("simple accrual per lot: amount x "
                            "expense_ratio% x days_held / 365.25; real "
                            "fees leave through the NAV, so this is an "
                            "approximation, not a ledger")}


def _lot_fee(code: str, lot_date: date, amount: float,
             expense_ratio_by_code: dict[str, float], upto: date) -> float:
    held_days = max((upto - lot_date).days, 0)
    return (amount * float(expense_ratio_by_code[code]) / 100.0
            * held_days / DAYS_PER_YEAR)


# ---------------------------------------------------------------------
# PORTFOLIO VALUE OVER TIME - from the NAV ledger, as-is, no backfill
# ---------------------------------------------------------------------
def ledger_portfolio_value(ledger_rows: list[dict],
                           transactions: list[dict]) -> dict:
    """Rupee value of the portfolio on every day the NAV ledger holds.

    Value = units held x NAV: the units come cumulatively from real
    my_investments.csv purchases, the NAVs strictly from the ledger's
    own rows. The ledger is young, so this chart is THIN BY DESIGN -
    no past day is ever invented to fatten it (C12). The ledger keeps
    two dates apart on purpose: `date` is when INKY wrote the row,
    `nav_date` is when the fund house published that NAV.
    """
    unit_lots: dict[str, list[tuple[date, float]]] = {}
    names_by_code: dict[str, str] = {}
    for row in transactions or []:
        if row.get("kind") != "mutual_fund" or not _positive_amount(row):
            continue
        code = (row.get("identifier") or "").strip()
        names_by_code.setdefault(code, row.get("name") or code)
        try:
            units = float(row.get("units"))
        except (TypeError, ValueError):
            continue
        if units > 0 and isinstance(row.get("_date"), date):
            unit_lots.setdefault(code, []).append((row["_date"], units))

    nav_history: dict[str, list[tuple[date, float]]] = {}
    for row in ledger_rows or []:
        code = (row.get("amfi_code") or "").strip()
        day = _parse_day(row.get("date"))
        try:
            nav = float(row.get("nav"))
        except (TypeError, ValueError):
            continue
        if code and day is not None and nav > 0:
            nav_history.setdefault(code, []).append((day, nav))
    nav_history = {c: sorted(rows) for c, rows in nav_history.items()}

    tracked_codes = [c for c in sorted(nav_history) if c in unit_lots]
    if not tracked_codes:
        return {"has_data": False,
                "days_covered": 0,
                "funds_without_units_recorded":
                    [names_by_code.get(c, c) for c in sorted(nav_history)
                     if c not in unit_lots],
                "note": ("the NAV ledger carries no rows that pair a real "
                         "purchase with a written NAV yet, so there is no "
                         "portfolio value over time to draw")}
    all_days = sorted({day for c in tracked_codes
                       for day, _ in nav_history[c]})
    points = []
    for day in all_days:
        value = 0.0
        priced = 0
        for code in tracked_codes:
            units = sum(u for d, u in unit_lots[code] if d <= day)
            navs_before = [n for n_day, n in nav_history[code]
                           if n_day <= day]
            if units <= 0 or not navs_before:
                continue
            value += units * navs_before[-1]
            priced += 1
        points.append({"date": day.isoformat(), "value": round(value, 2),
                       "funds_priced": priced})
    first_day = all_days[0].isoformat()
    without_units = [names_by_code.get(c, c) for c in sorted(nav_history)
                     if c not in unit_lots]
    return {"has_data": len(points) >= 1,
            "points": points,
            "days_covered": len(all_days),
            "ledger_first_day": first_day,
            "ledger_last_day": all_days[-1].isoformat(),
            "funds_valued": [names_by_code.get(c, c) for c in tracked_codes],
            "funds_without_units_recorded": without_units,
            "note": (f"the NAV ledger starts {first_day} and holds "
                     f"{len(all_days)} written day(s) so far - the chart "
                     "is thin because the ledger is young; no past value "
                     "is backfilled or invented (C12)"),
            "date_column_note": ("'date' is when INKY wrote the row; "
                                 "'nav_date' is when the fund published "
                                 "the NAV")}


# ---------------------------------------------------------------------
# THE WHOLE TIME-SERIES BLOCK - what lands in the review payload
# ---------------------------------------------------------------------
def _read_reference_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def build_time_series(funds: list[dict], profiles: dict[str, dict],
                      settings: dict, today: date | None = None,
                      benchmark_points: list[dict] | None = None) -> dict:
    """Assemble every time-series metric into one payload block.

    Everything reads from stored series and files that already exist -
    no model call, and no fresh web call except the twelve-hour-cached
    benchmark history when a caller has not supplied it. A metric short
    of real data says so with has_data:false and its reason.
    """
    today = today or date.today()
    settings = settings or {}
    trading_days = int(settings.get("trading_days_per_year") or 252)
    min_points = int(settings.get("min_points_for_ratios") or 60)

    values_by_code: dict[str, float] = {}
    names_by_code: dict[str, str] = {}
    for fund in funds or []:
        code = (fund.get("amfi_code") or "").strip()
        try:
            value = float(fund.get("current") or 0)
        except (TypeError, ValueError):
            value = 0.0
        if code and value > 0:
            values_by_code[code] = value
            names_by_code[code] = fund.get("scheme_name") or code

    series_by_code: dict[str, list[tuple[date, float]]] = {}
    funds_without_history: list[dict] = []
    equity_money = 0.0
    equity_base = 0.0
    expense_ratio_by_code: dict[str, float] = {}
    buys_by_code: dict[str, list[dict]] = {}

    for code, name in names_by_code.items():
        profile = profiles.get(code) or {}
        points = ((profile.get("nav_history") or {}).get("points")) or []
        series = _dated_series(points, "nav")
        if len(series) >= 2:
            series_by_code[code] = series
        else:
            funds_without_history.append({
                "scheme_name": name, "amfi_code": code,
                "reason": "no stored NAV history (or under 2 daily "
                          "points) in fund_profiles - run the daily pull"})
        split = profile.get("asset_split") or {}
        if split.get("equity_pct") is not None:
            equity_money += values_by_code[code] * float(split["equity_pct"]) / 100.0
            equity_base += values_by_code[code]
        if profile.get("expense_ratio") is not None:
            expense_ratio_by_code[code] = float(profile["expense_ratio"])

    transactions: list[dict] = []
    try:
        transactions = read_what_i_own.read_every_transaction()
    except Exception as problem:                              # noqa: BLE001
        transactions = []
    for row in transactions:
        row["_date"] = row.get("date")
        if (row.get("kind") == "mutual_fund"
                and isinstance(row.get("_date"), date)
                and _positive_amount(row)):
            buys_by_code.setdefault((row.get("identifier") or "").strip(),
                                    []).append(row)

    rules_doc = _read_reference_file(TAX_RULES_FILE)
    assumptions_doc = _read_reference_file(PLANNING_ASSUMPTIONS_FILE)
    ledger_rows = track_the_nav_ledger.read_the_ledger()

    benchmark_name = settings.get("benchmark_name") or "NIFTY 50"
    benchmark_symbol = settings.get("benchmark_symbol") or "^NSEI"
    if benchmark_points is None:
        bench_answer = fetch_market_facts.index_history(
            benchmark_symbol, days=int(settings.get("lookback_days") or 400))
        benchmark_points = (bench_answer.get("points") or []
                            if bench_answer.get("has_data") else [])

    combined = portfolio_level_series(series_by_code, values_by_code)
    combined_levels = combined.get("levels") or []

    rolling_block = _rolling_cagr_block(series_by_code, names_by_code,
                                        values_by_code, trading_days)
    portfolio_drawdown = (
        drawdown_curve([{"date": d.isoformat(), "nav": p}
                        for d, p in combined_levels])
        if combined_levels else
        _empty("no combined portfolio curve could be built from the "
               "stored NAV histories"))

    return {
        "built_on": today.isoformat(),
        "describes": ("how each holding and the whole portfolio moved "
                      "through time; arithmetic on already-stored series "
                      "and real transaction rows only"),
        "rolling_cagr": rolling_block,
        "drawdown": {
            "funds": [
                {"scheme_name": names_by_code[code], "amfi_code": code,
                 **drawdown_curve([{"date": d.isoformat(), "nav": p}
                                   for d, p in series])}
                for code, series in sorted(series_by_code.items())],
            "portfolio_weighted": {
                **portfolio_drawdown,
                "note": (portfolio_drawdown.get("note")
                         or "running peak of the value-weighted combined "
                            "curve over every analysed fund's own growth "
                            "since its first stored point")},
        },
        "tax_lots": tax_lot_breakdown(transactions, rules_doc, today),
        "portfolio_vs_benchmark": (
            portfolio_vs_benchmark(combined_levels, benchmark_points,
                                   benchmark_name, benchmark_symbol,
                                   min_points)
            if combined_levels else _empty(
                "no combined portfolio curve could be built from the "
                "stored NAV histories")),
        "cashflow": cashflow_visibility(transactions),
        "equity_allocation_band": equity_vs_band(
            round(equity_money / equity_base * 100, 2) if equity_base
            else None, assumptions_doc),
        "cost_drag": cost_drag(buys_by_code, expense_ratio_by_code,
                               values_by_code, today),
        "fund_correlations": correlation_between_funds(
            series_by_code, names_by_code, min_points),
        "ledger_portfolio_value": ledger_portfolio_value(ledger_rows,
                                                         transactions),
    }


def _rolling_cagr_block(series_by_code, names_by_code, values_by_code,
                        trading_days) -> dict:
    """Per-fund rolling 1Y/3Y CAGR curves plus a value-weighted blend."""
    windows = {"1y": trading_days, "3y": trading_days * 3}
    fund_windows = []
    portfolio_by_window: dict[str, dict] = {}
    any_fund_data = False
    for label, window in windows.items():
        window_results = []
        per_fund_cagr: dict[str, dict[date, float]] = {}
        for code, series in series_by_code.items():
            answer = rolling_cagr(
                [{"date": d.isoformat(), "nav": p} for d, p in series],
                window, trading_days)
            window_results.append({
                "scheme_name": names_by_code[code], "amfi_code": code,
                **answer})
            if answer.get("has_data"):
                any_fund_data = True
                per_fund_cagr[code] = {
                    date.fromisoformat(pt["date"]): pt["cagr_pct"]
                    for pt in answer["points"]}
        common: set[date] | None = None
        for days_map in per_fund_cagr.values():
            keys = set(days_map)
            common = keys if common is None else (common & keys)
        shared_days = sorted(common or set())
        weight_base = sum(values_by_code[c] for c in per_fund_cagr)
        if shared_days and weight_base > 0:
            thinned, original = _thin_for_chart([
                {"date": d.isoformat(),
                 "cagr_pct": round(sum(
                     values_by_code[c] / weight_base * per_fund_cagr[c][d]
                     for c in per_fund_cagr), 3)}
                for d in shared_days])
            portfolio_by_window[label] = {
                "has_data": True,
                "funds_included": [names_by_code[c] for c in per_fund_cagr],
                "points": thinned,
                "downsampled_from": original,
                "note": "each day averages the funds' rolling rates, "
                        "weighted by current value from the snapshot"}
        else:
            portfolio_by_window[label] = _empty(
                f"no fund yet has {window + 1}+ daily NAV points on file "
                f"for a rolling {label} curve")
        fund_windows.append({"window": label,
                             "window_points": window,
                             "funds": window_results})
    return {"has_data": any_fund_data,
            "windows_source": ("Screens/Finance/Reference_Data/"
                               "fund_analysis_settings.json -> "
                               "trading_days_per_year"),
            "funds": fund_windows,
            "portfolio_weighted": portfolio_by_window}


# ---------------------------------------------------------------------
# SELF-CHECK
# ---------------------------------------------------------------------
def main() -> None:
    from datetime import timedelta
    start = date(2024, 1, 1)
    days = [(start + timedelta(days=i)).isoformat() for i in range(90)]
    rising = [100 * (1.001 ** i) for i in range(90)]

    print("SELF-CHECK (hand-checkable)")
    dd = drawdown_curve([{"date": d, "nav": p} for d, p in zip(days, rising)])
    print("  monotonic rise drawdown      :", dd["max_drawdown_pct"],
          "(hand: 0)")
    dipped = [{"date": days[i], "nav": p}
              for i, p in enumerate([100, 110, 90, 95])]
    print("  max drawdown 100/110/90/95   :",
          drawdown_curve(dipped)["max_drawdown_pct"], "(hand: -18.18)")

    corr = correlation_between_funds(
        {"a": [(start + timedelta(days=i), p) for i, p in
               enumerate([100, 110, 105, 118, 112, 130])],
         "b": [(start + timedelta(days=i), p * 2) for i, p in
               enumerate([100, 110, 105, 118, 112, 130])]},
        {"a": "A", "b": "B"}, min_shared_days=3)
    print("  correlation of twin series   :", corr["pairs"][0]["correlation"],
          "(hand: exactly 1 - same moves, twice the level)")


if __name__ == "__main__":
    main()








