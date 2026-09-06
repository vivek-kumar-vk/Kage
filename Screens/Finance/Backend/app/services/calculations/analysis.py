"""The whole-portfolio review and the per-holding deep dives.

WHAT ONE CALL PRODUCES
    fund_sheet(hid)      everything one fund's ANALYSE button shows:
                         facts, the published portfolio with weights,
                         return buckets, risk ratios vs NIFTY 50, SIP
                         returns, peers, pros/cons
    stock_sheet(symbol)  price history, fundamentals, 52-week range for
                         a directly-held or watchlisted stock
    review(conn, part)   the whole-portfolio read: look-through X-ray
                         (which companies you really own, HHI), the
                         pair-overlap matrix, behaviour vs the index,
                         blended cost, asset split vs targets, capital-
                         gains buckets from lots, XIRR, and the
                         observation list a reviewer would flag first

WHERE EACH NUMBER COMES FROM
    portfolio values     the ledger (holdings x latest_prices)
    NAV series           price_history (mfapi.in, already backfilled)
    benchmark series     price_history (^NSEI via yfinance, refreshed
                         here when older than 7 days)
    fund facts/portfolio Groww public pages via services.fund_reference
    risk-ratio maths     services.calculations.ratios (pure, ported from
                         the house compute_the_ratios.py)
    thresholds           reference/fund_analysis_settings.json
    tax rates            reference/india_income_tax_rules.json

THE HOUSE RULES THIS FILE OBEYS
    Advisory-neutral: an observation is a FACT with a threshold ("pair
    overlap 64% — significant"), never "buy/sell fund X". Anything
    derived from an unverified assumption carries the settings file's
    verified_by_a_person=false tag to the UI. A section with no data
    says state "pending" with the reason — never a made-up number.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime

from services import fund_reference, market_data
from services.calculations import portfolio, ratios
from services.calculations.backfill import backfill_price_history
from services.db import connect
from services.reference import load as _load

SETTINGS = _load("fund_analysis_settings") or {}
TAX = _load("india_income_tax_rules") or {}
_UNVERIFIED = not SETTINGS.get("verified_by_a_person", False)

BENCHMARK_SYMBOL = SETTINGS.get("benchmark_symbol", "^NSEI")
BENCHMARK_NAME = SETTINGS.get("benchmark_name", "NIFTY 50")
RF_PCT = float(SETTINGS.get("risk_free_rate_pct", 5.5))
LOOKBACK_DAYS = int(SETTINGS.get("lookback_days", 365))
MIN_POINTS = int(SETTINGS.get("min_points_for_ratios", 60))
PERIODS = int(SETTINGS.get("trading_days_per_year", 252))

# review thresholds (the house build_the_portfolio_review.py values)
SINGLE_FUND_FLAG_PCT = 25.0      # one fund this large is one bet
TOP_TEN_WATCH_PCT = 25.0
TOP_TEN_FLAG_PCT = 40.0
PAIR_OVERLAP_WATCH_PCT = 40.0
SECTOR_FLAG_PCT = 30.0
EXPENSE_WATCH_PCT = 1.0
DRIFT_FLAG_PP = 5.0

_EQUITY_CATEGORY_MARKERS = ("equity", "flexi", "elss", "index", "sector",
                            "small", "mid", "nifty", "nasdaq", "children",
                            "focused", "value", "growth")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _round(x, nd=2):
    return None if x is None else round(x, nd)


# ---------------------------------------------------------------- series
def _nav_points(conn, symbol: str, days: int | None = None) -> list[dict]:
    sql = "SELECT date, price FROM price_history WHERE symbol = ? ORDER BY date ASC"
    rows = conn.execute(sql, (symbol,)).fetchall()
    points = [{"date": r["date"], "nav": float(r["price"])} for r in rows]
    return points[-days:] if days else points


def _benchmark_points(conn, days: int | None = None) -> list[dict]:
    """Benchmark closes from the local ledger only — reads never fetch.
    A stale series is used as is; the review's behaviour.benchmark carries
    data_as_of so staleness is visible instead of papered over."""
    rows = conn.execute(
        "SELECT date, price FROM price_history WHERE symbol = ? ORDER BY date ASC",
        (BENCHMARK_SYMBOL,)).fetchall()
    points = [{"date": r["date"], "close": float(r["price"])} for r in rows]
    return points[-days:] if days else points


def _point_to_point_returns(points: list[dict], key: str) -> dict:
    """Return buckets from one dated series: the latest value against the
    value nearest (at-or-before) N days back. A series too short for a
    window is simply missing that window."""
    if len(points) < 2:
        return {}
    latest = points[-1]
    try:
        last_day = datetime.strptime(latest["date"], "%Y-%m-%d").date()
    except ValueError:
        return {}
    out: dict[str, float] = {}
    for label, back in (("1m", 30), ("3m", 91), ("6m", 182), ("1y", 365),
                        ("3y", 365 * 3), ("5y", 365 * 5)):
        target = last_day.toordinal() - back
        base = None
        for p in points:
            try:
                d = datetime.strptime(p["date"], "%Y-%m-%d").date()
            except ValueError:
                continue
            if d.toordinal() <= target:
                base = p
            else:
                break
        if base is not None and float(base[key]) > 0:
            out[label] = _round((float(latest[key]) / float(base[key]) - 1.0) * 100)
    return out


# ---------------------------------------------------------------- XIRR
# One XIRR (K-16): the shared bisection implementation replaced the local one.
from services.calculations.xirr import xirr as _xirr  # noqa: E402


# ---------------------------------------------------------------- facts
def _fund_facts_out(data: dict) -> dict:
    """The mfServerSideData dict trimmed to what the drawer shows. Shapes
    verified against the live pages 2026-09-02: return_stats is a LIST of
    per-scheme stat rows, analysis is a LIST of typed PROS/CONS rows, and
    expense_ratio arrives as a string."""
    ret_rows = data.get("return_stats")
    if isinstance(ret_rows, dict):
        ret_rows = [ret_rows]
    ret = (ret_rows[0] if isinstance(ret_rows, list) and ret_rows else {}) or {}
    _KNOWN_RET_BUCKETS = {"1d", "1w", "1m", "3m", "6m", "9m", "1y", "2y",
                          "3y", "4y", "5y", "7y", "10y"}
    published_returns = {k[len("return"):]: v for k, v in ret.items()
                         if k.startswith("return") and k != "return_default"
                         and k[len("return"):] in _KNOWN_RET_BUCKETS
                         and isinstance(v, (int, float))}
    cat_returns = {k[len("cat_return"):]: v for k, v in ret.items()
                   if k.startswith("cat_return") and isinstance(v, (int, float))}
    ratios_out = {k: ret.get(k) for k in ("alpha", "beta", "sharpe_ratio",
                                          "sortino_ratio", "standard_deviation",
                                          "information_ratio", "mean_return")
                  if isinstance(ret.get(k), (int, float))}
    analysis_rows = data.get("analysis") or []
    pros = [a.get("analysis_desc") for a in analysis_rows
            if isinstance(a, dict) and a.get("analysis_type") == "PROS"]
    cons = [a.get("analysis_desc") for a in analysis_rows
            if isinstance(a, dict) and a.get("analysis_type") == "CONS"]
    peers = []
    for p in (data.get("peerComparison") or [])[:6]:
        if not isinstance(p, dict):
            continue
        peers.append({k: p[k] for k in ("search_id", "scheme_name", "aum",
                                        "return1y", "return3y", "groww_rating",
                                        "risk_rating", "sub_category")
                      if k in p})
    managers = data.get("fund_manager_details") or []
    names = [m.get("person_name") for m in managers
             if isinstance(m, dict) and m.get("person_name")]
    if not names:
        fm = data.get("fund_manager")
        if isinstance(fm, str) and fm.strip():
            names = [s.strip() for s in fm.split(",") if s.strip()]
    ter = data.get("expense_ratio")
    try:
        ter = float(ter) if ter is not None else None
    except (TypeError, ValueError):
        ter = None
    hold_rows = data.get("holdings") or []
    portfolio_date = next((h.get("portfolio_date") for h in hold_rows
                           if isinstance(h, dict) and h.get("portfolio_date")), None)
    lock = data.get("lock_in") or {}
    lock_text = None
    if isinstance(lock, dict) and any(lock.get(k) for k in ("years", "months", "days")):
        lock_text = f"{lock.get('years') or 0}y {lock.get('months') or 0}m {lock.get('days') or 0}d"
    sip = data.get("sip_return") or {}
    sip_returns = {k[len("return"):]: v for k, v in sip.items()
                   if k.startswith("return")
                   and k[len("return"):] in _KNOWN_RET_BUCKETS
                   and isinstance(v, (int, float))}
    return {
        "scheme_name": data.get("scheme_name") or data.get("fund_name"),
        "search_id": data.get("search_id"),
        "isin": data.get("isin"),
        "amc": ((data.get("amc_info") or {}).get("name")
                if isinstance(data.get("amc_info"), dict) else None),
        "category": data.get("category"),
        "sub_category": data.get("sub_category"),
        "plan_type": data.get("plan_type"),
        "scheme_type": data.get("scheme_type"),
        "aum_cr": data.get("aum"),
        "expense_ratio_pct": ter,
        "portfolio_turnover_pct": data.get("portfolio_turnover"),
        "launch_date": data.get("launch_date"),
        "fund_managers": names,
        "exit_load": data.get("exit_load"),
        "min_sip_investment": data.get("min_sip_investment"),
        "min_lumpsum_investment": data.get("min_investment_amount"),
        "benchmark_name": data.get("benchmark_name") or data.get("benchmark"),
        "risk": data.get("nfo_risk") or data.get("risk"),
        "risk_rating": data.get("risk_rating"),
        "groww_rating": data.get("groww_rating"),
        "lock_in": lock_text,
        "description": data.get("description"),
        "tax_impact": ((data.get("category_info") or {}).get("tax_impact")
                       if isinstance(data.get("category_info"), dict) else None),
        "portfolio_date": (portfolio_date or "")[:10] or None,
        "published_returns": published_returns or None,
        "category_returns": cat_returns or None,
        "published_ratios": ratios_out or None,
        "sip_return": sip_returns or None,
        "peers": peers,
        "pros": [p for p in pros if p],
        "cons": [c for c in cons if c],
    }


# ---------------------------------------------------------------- sheets
def fund_sheet(conn, hid: int, allow_fetch: bool = False) -> dict:
    hrows = portfolio.holdings_with_value(conn)
    holding = next((r for r in hrows if r["id"] == hid), None)
    if holding is None:
        return {"state": "pending", "reason": "no such active holding"}
    symbol = holding["symbol"]
    asset_type = (holding["type"] or "").lower()
    hrow = conn.execute("SELECT direct_regular, folio FROM holdings WHERE id = ?",
                        (hid,)).fetchone()

    base = {
        "holding": holding,
        "plan": hrow["direct_regular"] if hrow else None,
        "folio": hrow["folio"] if hrow else None,
        "benchmark": {"symbol": BENCHMARK_SYMBOL, "name": BENCHMARK_NAME,
                      "risk_free_rate_pct": RF_PCT},
        "settings_verified_by_a_person": SETTINGS.get("verified_by_a_person", False),
        "generated_at": _now(),
    }

    # a listed ETF or stock has no scheme page — the sheet is the series
    if asset_type in ("etf", "stock"):
        points = _nav_points(conn, symbol)
        sheet = {**base, "facts": None, "portfolio": {"state": "pending",
                 "holdings": [], "reason": "a listed instrument has no "
                 "published fund portfolio here"},
                 "nav_chart": points[-LOOKBACK_DAYS:], "returns": {},
                 "performance": {"has_data": False}, "xirr": None}
        if len(points) > 1:
            sheet["returns"] = _point_to_point_returns(points, "nav")
            bench = _benchmark_points(conn, LOOKBACK_DAYS)
            sheet["performance"] = ratios.performance(
                points[-LOOKBACK_DAYS:], bench, RF_PCT, PERIODS, MIN_POINTS)
        else:
            sheet["state"] = "pending"
            sheet["reason"] = "no price history in the ledger yet"
            return sheet
        sheet["state"] = "partial"
        sheet["reason"] = "listed instrument — NAV-based maths only"
        return sheet

    ref = (fund_reference.fetch_fund_page(symbol, holding.get("name"))
           if allow_fetch else
           {"state": "pending", "reason": "reference page not fetched (reads never fetch)"})
    lots = conn.execute(
        "SELECT purchase_date, units, cost_per_unit FROM lots "
        "WHERE holding_id = ? ORDER BY purchase_date ASC", (hid,)).fetchall()

    sheet = {**base, "facts": None, "portfolio": {"state": "pending",
             "holdings": [], "reason": "not fetched yet"},
             "nav_chart": [], "returns": {}, "performance": {"has_data": False},
             "xirr": None, "lots": len(lots)}

    points = _nav_points(conn, symbol)
    if points:
        sheet["nav_chart"] = points[-LOOKBACK_DAYS:]
        sheet["returns"] = _point_to_point_returns(points, "nav")
        bench = _benchmark_points(conn, LOOKBACK_DAYS)
        sheet["performance"] = ratios.performance(
            points[-LOOKBACK_DAYS:], bench, RF_PCT, PERIODS, MIN_POINTS)

    if lots:
        flows = [(l["purchase_date"], -(float(l["units"]) * float(l["cost_per_unit"] or 0)))
                 for l in lots]
        if holding["value"] is not None:
            flows.append((date.today().isoformat(), holding["value"]))
        sheet["xirr"] = _xirr(flows)

    if ref["state"] != "ok":
        sheet["state"] = "partial"
        sheet["reason"] = ref.get("reason", "reference page unavailable")
        if not points:
            sheet["state"] = "pending"
        return sheet

    data = ref["data"]
    sheet["facts"] = _fund_facts_out(data)
    sheet["reference_slug"] = ref.get("slug")
    sheet["portfolio"] = fund_reference.stored_portfolio(symbol)
    # the published return table wins when present; the series is the backup
    if sheet["facts"]["published_returns"]:
        sheet["returns"] = sheet["facts"]["published_returns"]
    sheet["state"] = "ok"
    return sheet


def stock_sheet(conn, symbol: str, allow_fetch: bool = False) -> dict:
    """A directly-held stock or watchlist name: price, series, range,
    fundamentals (yfinance info, cached 24h)."""
    sym = market_data.normalize_symbol(symbol)
    quote = market_data.get_current_price(sym, "stock")
    hist = market_data.stock_history(sym, 365)
    out = {
        "symbol": sym,
        "state": "ok" if (quote.get("has_data") or hist.get("has_data")) else "pending",
        "reason": None if out_ok(quote, hist) else "no price or history could be fetched",
        "quote": quote,
        "generated_at": _now(),
        "benchmark": {"symbol": BENCHMARK_SYMBOL, "name": BENCHMARK_NAME},
    }
    points = hist.get("points") or []
    if points:
        closes = [p["price"] for p in points]
        out["range_52w"] = {"low": min(closes), "high": max(closes)}
        out["returns"] = _point_to_point_returns(
            [{"date": p["date"], "nav": p["price"]} for p in points], "nav")
        bench = _benchmark_points(conn, LOOKBACK_DAYS)
        out["performance"] = ratios.performance(
            [{"date": p["date"], "nav": p["price"]} for p in points],
            bench, RF_PCT, PERIODS, MIN_POINTS)
        # persist the series so the ledger keeps it
        backfill_price_history(sym, "stock")
    sector_map = (_load("sector_for_stocks") or {}).get("sectors") or {}
    out["sector"] = sector_map.get(sym.lower())
    cached = fund_reference._cached(f"yfinfo:{sym}", 1)
    if cached is None and allow_fetch:
        try:
            import yfinance
            info = yfinance.Ticker(sym).info or {}
            cached = {k: info.get(k) for k in ("longName", "sector", "industry",
                                               "marketCap", "trailingPE",
                                               "priceToBook", "returnOnEquity",
                                               "dividendYield", "beta",
                                               "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
                                               "longBusinessSummary")}
            if any(v is not None for v in cached.values()):
                fund_reference._store(f"yfinfo:{sym}", cached)
        except Exception as e:  # noqa: BLE001
            cached = {"note": f"fundamentals unavailable: {e}"}
    out["fundamentals"] = cached
    return out


def out_ok(quote: dict, hist: dict) -> bool:
    return bool(quote.get("has_data") or hist.get("has_data"))


# ---------------------------------------------------------------- review
def _funds_with_portfolios(conn, holdings: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in holdings:
        if (r["type"] or "").lower() not in ("mutual_fund",):
            continue
        stored = fund_reference.stored_portfolio(r["symbol"])
        if stored.get("state") == "ok":
            out[r["symbol"]] = stored["holdings"]
    return out


def _asset_class(holding: dict, facts_by_symbol: dict[str, dict]) -> str:
    """A fund's class comes from its PUBLISHED category string; a gold
    ETF names gold; anything unclassifiable stays honestly unclassified —
    never guessed into equity to flatter the drift table."""
    name = (holding.get("name") or "").lower()
    kind = (holding.get("type") or "").lower()
    if kind == "etf" and ("gold" in name or "goldbees" in name.replace(" ", "")):
        return "commodity"
    cat = f"{facts_by_symbol.get(holding['symbol'], {}).get('category') or ''} " \
          f"{facts_by_symbol.get(holding['symbol'], {}).get('sub_category') or ''}".lower()
    if cat:
        if "multi asset" in cat or "multi-asset" in cat:
            return "multi_asset"
        if "debt" in cat or "liquid" in cat or "arbitrage" in cat:
            return "debt"
        if any(m in cat for m in _EQUITY_CATEGORY_MARKERS):
            return "equity"
    if kind == "etf":
        return "equity" if "gold" not in name else "commodity"
    return "unclassified"


def _lookthrough(conn, holdings: list[dict], funds: dict[str, list[dict]]):
    """The X-ray: every published fund holding weighted by what that fund
    is worth to YOU. HHI and 1/HHI follow (regulators' concentration
    measure — 1/HHI is the 'effective number of stocks')."""
    total_value = sum(r["value"] or 0 for r in holdings if r["value"] is not None)
    covered_value = sum((r["value"] or 0) for r in holdings
                        if r["value"] is not None and r["symbol"] in funds)
    company_weight: dict[str, float] = {}
    company_sector: dict[str, str] = {}
    sector_weight: dict[str, float] = {}
    for sym, rows in funds.items():
        holding = next(h for h in holdings if h["symbol"] == sym)
        share = (holding["value"] or 0) / total_value if total_value else 0
        for row in rows:
            w = share * float(row["weight"] or 0)   # percent of portfolio
            company_weight[row["company"]] = company_weight.get(row["company"], 0) + w
            if row.get("sector"):
                company_sector[row["company"]] = row["sector"]
                sector_weight[row["sector"]] = sector_weight.get(row["sector"], 0) + w
    ranked = sorted(company_weight.items(), key=lambda kv: -kv[1])
    top10 = sum(w for _, w in ranked[:10])
    hhi = round(sum(w * w for _, w in ranked), 1) if ranked else 0.0
    sectors = [{"sector": s, "weight_pct": _round(w)}
               for s, w in sorted(sector_weight.items(), key=lambda kv: -kv[1])]
    return {
        "state": "ok" if ranked else "pending",
        "coverage_pct": _round(covered_value / total_value * 100, 1) if total_value else 0.0,
        "companies": [{"company": c, "weight_pct": _round(w),
                       "sector": company_sector.get(c)}
                      for c, w in ranked[:25]],
        "distinct_companies": len(ranked),
        "hhi": hhi,
        "effective_number_of_stocks": _round(100.0 * 100.0 / hhi, 1) if hhi else None,
        "top10_weight_pct": _round(top10, 1),
        "sectors": sectors,
        "reason": None if ranked else "no fund portfolios stored yet — "
                     "open a fund's Analyse once or POST /analysis/refresh",
    }


def _overlap(funds: dict[str, list[dict]], names: dict[str, str]) -> dict:
    """Pair overlap = Σ min(wA, wB) over the two funds' published
    portfolios (Value Research's measure). Buckets: <20 low, 20-60
    moderate, 60-80 significant, >80 extreme."""
    syms = sorted(funds)
    pairs = []
    matrix: dict[str, dict[str, float | None]] = {s: {} for s in syms}
    for i, a in enumerate(syms):
        matrix[a][a] = 100.0
        for b in syms[i + 1:]:
            wa = {r["company"]: float(r["weight"] or 0) for r in funds[a]}
            wb = {r["company"]: float(r["weight"] or 0) for r in funds[b]}
            shared = set(wa) & set(wb)
            ov = round(sum(min(wa[c], wb[c]) for c in shared), 1)
            matrix[a][b] = ov
            matrix[b][a] = ov
            bucket = ("extreme" if ov > 80 else "significant" if ov > 60
                      else "moderate" if ov >= 20 else "low")
            pairs.append({"a": names.get(a, a), "b": names.get(b, b),
                          "symbol_a": a, "symbol_b": b,
                          "overlap_pct": ov, "bucket": bucket,
                          "shared_companies": len(shared)})
    pairs.sort(key=lambda p: -p["overlap_pct"])
    return {"state": "ok" if len(syms) >= 2 else "pending",
            "symbols": [{"symbol": s, "name": names.get(s, s)} for s in syms],
            "matrix": matrix, "pairs": pairs,
            "reason": None if len(syms) >= 2 else
                      "needs at least two funds with a stored portfolio"}


def _behaviour(conn, holdings: list[dict]) -> dict:
    """Per-fund and whole-portfolio risk ratios vs the benchmark, from the
    ledger's own series — nothing live."""
    bench = _benchmark_points(conn, LOOKBACK_DAYS)
    bench_as_of = bench[-1]["date"] if bench else None
    out = {"benchmark": {"symbol": BENCHMARK_SYMBOL, "name": BENCHMARK_NAME,
                         "risk_free_rate_pct": RF_PCT,
                         "data_as_of": bench_as_of,
                         "return_1y_pct": None, "volatility_pct": None},
           "portfolio": {"has_data": False}, "funds": []}
    if bench:
        bench_daily = ratios.daily_returns([p["close"] for p in bench])
        out["benchmark"]["return_1y_pct"] = ratios.annualised_return_pct(bench_daily, PERIODS)
        out["benchmark"]["volatility_pct"] = ratios.annualised_volatility_pct(bench_daily, PERIODS)
    series = portfolio._portfolio_value_series(conn)
    if series:
        pts = [{"date": d, "nav": v} for d, v in series]
        out["portfolio"] = ratios.performance(pts[-LOOKBACK_DAYS:], bench,
                                              RF_PCT, PERIODS, MIN_POINTS)
    for r in holdings:
        if r["value"] is None:
            continue
        pts = _nav_points(conn, r["symbol"], LOOKBACK_DAYS)
        perf = ratios.performance(pts, bench, RF_PCT, PERIODS, MIN_POINTS)
        out["funds"].append({
            "symbol": r["symbol"], "name": r["name"], "weight_pct":
            _round((r["weight"] or 0) * 100, 1),
            "return_1y_pct": perf.get("return_1y_pct"),
            "volatility_pct": perf.get("volatility_pct"),
            "beta": perf.get("beta"), "alpha_pct": perf.get("alpha_pct"),
            "sharpe": perf.get("sharpe"), "sortino": perf.get("sortino"),
            "max_drawdown_pct": perf.get("max_drawdown_pct"),
            "r_squared": perf.get("r_squared"),
            "has_data": perf.get("has_data", False),
        })
    out["state"] = "ok" if (out["portfolio"].get("has_data") or out["funds"]) else "pending"
    if not out["portfolio"].get("has_data") and out["state"] == "ok":
        out["state"] = "partial"
    return out


def _plan_of(holding: dict, facts: dict | None) -> str:
    """Direct vs regular: the fetched reference page is authoritative, the
    scheme name is the second witness, the stale direct_regular column
    (which defaults to 'regular' for CAS rows) comes last."""
    plan = ((facts or {}).get("plan_type") or "").lower()
    if plan in ("direct", "regular"):
        return plan
    name = (holding.get("name") or "").lower()
    if "direct" in name:
        return "direct"
    if "regular" in name:
        return "regular"
    return (holding.get("direct_regular") or "regular").lower()


def _expense(conn, holdings: list[dict], facts_by_symbol: dict[str, dict]) -> dict:
    total_value = sum(r["value"] or 0 for r in holdings if r["value"] is not None)
    weighted = 0.0
    covered = 0.0
    rows = []
    for r in holdings:
        if r["value"] is None:
            continue
        facts = facts_by_symbol.get(r["symbol"]) or {}
        ter = facts.get("expense_ratio_pct")
        rows.append({"symbol": r["symbol"], "name": r["name"],
                     "expense_ratio_pct": ter, "plan_type": _plan_of(r, facts),
                     "weight_pct": _round((r["weight"] or 0) * 100, 1)})
        if isinstance(ter, (int, float)):
            weighted += r["value"] * ter
            covered += r["value"]
    return {
        "state": "ok" if covered else "pending",
        "blended_expense_ratio_pct": _round(weighted / covered, 3) if covered else None,
        "coverage_pct": _round(covered / total_value * 100, 1) if total_value else 0.0,
        "regular_plan_total_pct": _round(sum(
            (r["value"] or 0) for r in holdings
            if r["value"] is not None
            and _plan_of(r, facts_by_symbol.get(r["symbol"])) == "regular")
            / total_value * 100, 1) if total_value else None,
        "funds": rows,
        "reason": None if covered else "no expense ratios stored — refresh the fund facts",
    }


def _allocation(conn, holdings: list[dict], facts_by_symbol: dict[str, dict]) -> dict:
    total_value = sum(r["value"] or 0 for r in holdings if r["value"] is not None)
    buckets: dict[str, float] = {}
    for r in holdings:
        if r["value"] is None:
            continue
        buckets[_asset_class(r, facts_by_symbol)] = \
            buckets.get(_asset_class(r, facts_by_symbol), 0) + r["value"]
    split = [{"bucket": k, "value": _round(v),
              "weight_pct": _round(v / total_value * 100, 1) if total_value else 0}
             for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])]
    targets_raw = (SETTINGS.get("target_allocation") or {})
    targets = targets_raw.get("targets") or {}
    drift = []
    if targets and total_value:
        for cls, tgt in targets.items():
            actual = next((s["weight_pct"] for s in split if s["bucket"] == cls), 0.0)
            drift.append({"bucket": cls, "target_pct": tgt,
                          "actual_pct": actual,
                          "drift_pp": _round(actual - float(tgt), 1),
                          "flag": abs(actual - float(tgt)) > DRIFT_FLAG_PP})
    return {
        "state": "ok" if split else "pending",
        "split": split,
        "unclassified_note": ("unclassified buckets are funds whose published "
                              "category was not stored or did not match a known "
                              "class — they are reported, never guessed"),
        "targets": targets,
        "targets_verified_by_a_person": targets_raw.get("verified_by_a_person", False),
        "drift": drift,
        "drift_flag_pp": DRIFT_FLAG_PP,
    }


def _cost_tax(conn, holdings: list[dict]) -> dict:
    """Unrealised capital-gains buckets from lots + the rates from the
    tax rulebook. Realised gains live with the trade journal."""
    today = date.today()
    cg = TAX.get("capital_gains") or {}
    eq = cg.get("listed_equity_and_equity_mutual_funds") or {}
    gold = cg.get("gold_and_unlisted") or {}
    st_ltcg_months = int(eq.get("long_term_after_months", 12))
    gold_lt_months = int(gold.get("long_term_after_months", 24))
    buckets = {"stcg": 0.0, "ltcg": 0.0}
    rows = []
    for r in holdings:
        if r["value"] is None:
            continue
        lots = conn.execute(
            "SELECT purchase_date, units, cost_per_unit FROM lots "
            "WHERE holding_id = ? ORDER BY purchase_date ASC", (r["id"],)).fetchall()
        st = lt = 0.0
        for lot in lots:
            try:
                bought = datetime.strptime(lot["purchase_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            months = (today.year - bought.year) * 12 + today.month - bought.month
            gain = float(lot["units"]) * (float(r["price"]) - float(lot["cost_per_unit"] or 0))
            lt_limit = gold_lt_months if (r["type"] or "").lower() == "etf" \
                and "gold" in (r["name"] or "").lower() else st_ltcg_months
            if months >= lt_limit:
                lt += gain
            else:
                st += gain
        if lots:
            buckets["stcg"] += st
            buckets["ltcg"] += lt
            rows.append({"symbol": r["symbol"], "name": r["name"],
                         "stcg_unrealised": _round(st), "ltcg_unrealised": _round(lt),
                         "lots": len(lots)})
    return {
        "state": "ok" if rows else "pending",
        "rates": {"stcg_pct": eq.get("stcg_rate_pct"), "ltcg_pct": eq.get("ltcg_rate_pct"),
                  "ltcg_annual_exemption": eq.get("ltcg_annual_exemption"),
                  "long_term_after_months": st_ltcg_months,
                  "source_as_of": TAX.get("as_of"),
                  "financial_year": TAX.get("financial_year"),
                  "verified_by_a_person": TAX.get("verified_by_a_person", False)},
        "totals": {"stcg_unrealised": _round(buckets["stcg"]),
                   "ltcg_unrealised": _round(buckets["ltcg"])},
        "holdings": rows,
        "note": None if rows else "no lots stored — import the CAS PDF to build them",
    }


def _actions(holdings, look, overlap, alloc, exp) -> list[dict]:
    """Facts a reviewer would flag first, with the threshold named.
    Advisory-neutral by construction: no buy/sell verb appears here."""
    out: list[dict] = []
    total_value = sum(r["value"] or 0 for r in holdings if r["value"] is not None)
    for r in holdings:
        if r["value"] is None:
            out.append({"flag": "unpriced", "severity": "watch",
                        "symbol": r["symbol"],
                        "detail": f"{r['name']} has no price in the ledger — "
                                  f"it is excluded from every total"})
        elif (r["weight"] or 0) * 100 > SINGLE_FUND_FLAG_PCT:
            out.append({"flag": "single_fund_weight", "severity": "watch",
                        "symbol": r["symbol"],
                        "detail": f"{r['name']} is "
                                  f"{round((r['weight'] or 0) * 100, 1)}% of the "
                                  f"portfolio (threshold {SINGLE_FUND_FLAG_PCT}%)"})
    if look.get("state") == "ok":
        if look["top10_weight_pct"] is not None:
            if look["top10_weight_pct"] > TOP_TEN_FLAG_PCT:
                sev = "flag"
            elif look["top10_weight_pct"] > TOP_TEN_WATCH_PCT:
                sev = "watch"
            else:
                sev = None
            if sev:
                out.append({"flag": "top10_concentration", "severity": sev,
                            "detail": f"the top 10 companies hold "
                                      f"{look['top10_weight_pct']}% of the "
                                      f"portfolio (watch {TOP_TEN_WATCH_PCT}%, "
                                      f"flag {TOP_TEN_FLAG_PCT}%)"})
        if look.get("effective_number_of_stocks"):
            out.append({"flag": "effective_stocks", "severity": "info",
                        "detail": f"the portfolio behaves like about "
                                  f"{look['effective_number_of_stocks']} distinct "
                                  f"stocks (HHI {look['hhi']}) across "
                                  f"{look['distinct_companies']} published names"})
    for p in overlap.get("pairs", []):
        if p["overlap_pct"] > PAIR_OVERLAP_WATCH_PCT:
            out.append({"flag": "pair_overlap", "severity": "watch",
                        "detail": f"{p['a']} and {p['b']} overlap "
                                  f"{p['overlap_pct']}% "
                                  f"({p['bucket']}; watch "
                                  f"{PAIR_OVERLAP_WATCH_PCT}%)"})
    for s in (look.get("sectors") or []):
        if (s["weight_pct"] or 0) > SECTOR_FLAG_PCT:
            out.append({"flag": "sector_weight", "severity": "watch",
                        "detail": f"{s['sector']} is {s['weight_pct']}% of the "
                                  f"look-through equity (threshold "
                                  f"{SECTOR_FLAG_PCT}%)"})
    for d in alloc.get("drift", []):
        if d["flag"]:
            out.append({"flag": "allocation_drift", "severity": "watch",
                        "detail": f"{d['bucket']} sits at {d['actual_pct']}% vs the "
                                  f"{d['target_pct']}% target ({d['drift_pp']:+}pp; "
                                  f"threshold ±{DRIFT_FLAG_PP}pp)"})
    if exp.get("blended_expense_ratio_pct") and \
            exp["blended_expense_ratio_pct"] > EXPENSE_WATCH_PCT:
        out.append({"flag": "blended_expense", "severity": "watch",
                    "detail": f"the blend costs {exp['blended_expense_ratio_pct']}% "
                              f"a year (threshold {EXPENSE_WATCH_PCT}%)"})
    if exp.get("regular_plan_total_pct") and exp["regular_plan_total_pct"] > 0:
        out.append({"flag": "regular_plans", "severity": "info",
                    "detail": f"{exp['regular_plan_total_pct']}% of the portfolio "
                              f"sits in regular plans — a direct plan of the same "
                              f"scheme carries a lower TER"})
    return out


def review(conn, part: str = "all") -> dict:
    """The whole-portfolio review, one section at a time or whole."""
    holdings = portfolio.holdings_with_value(conn)
    funds = _funds_with_portfolios(conn, holdings)
    names = {r["symbol"]: (r["name"] or r["symbol"]) for r in holdings}
    facts_by_symbol: dict[str, dict] = {}
    for r in holdings:
        stored = fund_reference.stored_facts(r["symbol"])
        if stored:
            facts_by_symbol[r["symbol"]] = _fund_facts_out(stored)

    total_value = sum(r["value"] or 0 for r in holdings if r["value"] is not None)
    invested = sum(r["invested"] or 0 for r in holdings if r["value"] is not None)
    hero = {
        "state": "ok" if total_value else "pending",
        "total_value": _round(total_value),
        "invested": _round(invested),
        "gain_loss": _round(total_value - invested),
        "holdings": len(holdings),
        "funds_with_portfolio": len(funds),
        "portfolio_coverage_pct": _round(
            sum((r["value"] or 0) for r in holdings
                if r["value"] is not None and r["symbol"] in funds)
            / total_value * 100, 1) if total_value else 0.0,
        "unpriced": [r["symbol"] for r in holdings if r["value"] is None],
        "settings_verified_by_a_person": SETTINGS.get("verified_by_a_person", False),
    }

    def _flows() -> list[tuple[str, float]]:
        flows: list[tuple[str, float]] = []
        for r in holdings:
            if r["value"] is None:
                continue
            for lot in conn.execute(
                    "SELECT purchase_date, units, cost_per_unit FROM lots "
                    "WHERE holding_id = ?", (r["id"],)).fetchall():
                flows.append((lot["purchase_date"],
                              -(float(lot["units"]) * float(lot["cost_per_unit"] or 0))))
        if total_value:
            flows.append((date.today().isoformat(), total_value))
        return flows

    parts: dict[str, dict] = {}
    if part in ("all", "lookthrough"):
        look = _lookthrough(conn, holdings, funds)
        parts["lookthrough"] = look
    if part in ("all", "overlap"):
        parts["overlap"] = _overlap(funds, names)
    if part in ("all", "behaviour"):
        parts["behaviour"] = _behaviour(conn, holdings)
    if part in ("all", "cost-tax"):
        parts["expense"] = _expense(conn, holdings, facts_by_symbol)
        parts["cost_tax"] = _cost_tax(conn, holdings)
    if part in ("all", "allocation"):
        parts["allocation"] = _allocation(conn, holdings, facts_by_symbol)
    if part in ("all", "actions"):
        look = parts.get("lookthrough") or _lookthrough(conn, holdings, funds)
        ov = parts.get("overlap") or _overlap(funds, names)
        alloc = parts.get("allocation") or _allocation(conn, holdings, facts_by_symbol)
        exp = parts.get("expense") or _expense(conn, holdings, facts_by_symbol)
        parts["actions"] = {"state": "ok",
                            "thresholds": {
                                "single_fund_flag_pct": SINGLE_FUND_FLAG_PCT,
                                "top_ten_watch_pct": TOP_TEN_WATCH_PCT,
                                "top_ten_flag_pct": TOP_TEN_FLAG_PCT,
                                "pair_overlap_watch_pct": PAIR_OVERLAP_WATCH_PCT,
                                "sector_flag_pct": SECTOR_FLAG_PCT,
                                "expense_watch_pct": EXPENSE_WATCH_PCT,
                                "drift_flag_pp": DRIFT_FLAG_PP},
                            "observations": _actions(holdings, look, ov, alloc, exp)}
    if part in ("all", "overview"):
        series = portfolio._portfolio_value_series(conn)
        parts["overview"] = {
            **hero,
            "xirr_pct": _xirr(_flows()),
            "value_series": [{"date": d, "value": _round(v)}
                             for d, v in series[-LOOKBACK_DAYS:]],
        }
    elif part == "hero":
        parts["hero"] = hero
    # A single-part request flattens its section to the top level — the
    # section endpoints are the API the tabs read directly. "all" keeps
    # the named nesting for one-shot callers.
    out: dict = {"state": hero["state"], "generated_at": _now()}
    if part == "all":
        out.update(parts)
    else:
        for section in parts.values():
            if isinstance(section, dict):
                out.update(section)
    return out


def refresh_reference_data() -> dict:
    """Pull the reference page for every MF holding (cached ones return
    instantly). Returns per-symbol states — the 'prime the cache' button."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT symbol, name FROM holdings WHERE archived_at IS NULL "
            "AND type = 'mutual_fund'").fetchall()
    results = {}
    for r in rows:
        try:
            ref = fund_reference.fetch_fund_page(r["symbol"], r["name"])
            results[r["symbol"]] = ref.get("state", "pending")
        except Exception as e:  # noqa: BLE001
            results[r["symbol"]] = f"error: {e}"
    return {"state": "ok", "results": results, "generated_at": _now()}


def sip_calendar(conn) -> dict:
    """SIP rhythm derived from the lots ledger — monthly buy counts and
    amounts by month. Derived from recorded purchases, never assumed."""
    rows = conn.execute(
        "SELECT substr(purchase_date, 1, 7) AS month, "
        "SUM(l.units * l.cost_per_unit) AS amount, COUNT(*) AS buys "
        "FROM lots l JOIN holdings h ON h.id = l.holding_id "
        "WHERE h.archived_at IS NULL AND l.purchase_date > '1971-01-01' "
        "GROUP BY month ORDER BY month ASC").fetchall()
    return {"state": "ok" if rows else "pending",
            "months": [{k: r[k] for k in r.keys()} for r in rows],
            "reason": None if rows else "no dated lots yet — import the CAS PDF"}
