"""The whole-portfolio review - how a portfolio manager would read
every fund together, not one at a time.

THE QUESTION THIS FILE ANSWERS
    The fund buttons say what each fund owns. This file answers what
    YOU own: across every rupee in every scheme, which companies come
    out of hiding, how concentrated the whole thing is, where the
    sectors and market caps land, what the blend costs to run, how it
    has behaved against the index - and which facts a reviewer would
    flag first.

WHAT IS COMPUTED, AND THE INDUSTRY PRACTICE BEHIND EACH PIECE

    look-through holdings   every fund's published stocks weighted by
                            that fund's value in YOUR portfolio - the
                            "Portfolio X-ray" idea popularised by
                            Morningstar and Value Research
    HHI                     sum of squared portfolio weights across
                            companies; regulators use it for market
                            concentration. 1/HHI is the "effective
                            number of stocks" - a portfolio of 9 funds
                            holding 300 companies may really be 20
    top-10 share            the classic concentration screen; over
                            ~40% of equity in ten names reads as one
                            bet wearing a diversification costume
    pair overlap            min-weight shared stocks between two funds
                            (find_the_overlap.py) - Value Research's
                            overlap measure
    money-weighted splits   asset class / market cap / sector across
                            the whole portfolio, weighted by what you
                            actually hold, not per-fund averages
    weighted expense        what the blend costs per year; direct plans
                            typically sit well under regular plans
    behaviour               beta, alpha, Sharpe, Sortino, drawdown per
                            fund from NAV history vs the benchmark -
                            computed in compute_the_ratios.py
    XIRR                    your true money-weighted return per fund,
                            already computed elsewhere; pulled in here
    time series             rolling 1Y/3Y CAGR curves, drawdown curves,
                            tax-lot holding ages, portfolio-vs-benchmark
                            growth, purchase cashflow, equity share vs
                            the reference formula, cost drag over time,
                            fund correlation matrix and the NAV-ledger
                            value curve - computed in
                            compute_the_time_series.py from stored
                            histories (see that file's header)
    direct holdings         an etf/equity holding row is not a wrapper
                            around other companies - it IS the thing
                            itself, so it enters the look-through,
                            concentration and sector maths at 100% of its
                            own value. A gold ETF (name or symbol carries
                            GOLD/GOLDBEES) classifies under a
                            Commodity/Precious Metals bucket, never under
                            Equity
    direct pricing          an etf/equity row is repriced from the newest
                            close in Saved_Records/equity_price_ledger.csv
                            x its units when a close exists; when none
                            does, its stored snapshot value stands and
                            says so - never zero-filled, never guessed
    allocation drift        actual asset-class weights across EVERYTHING
                            vs targets in fund_analysis_settings.json
                            (the targets carry verified_by_a_person:
                            false until their owner confirms them);
                            drift beyond 5 percentage points absolute is
                            named, and the 5/25 rebalancing rule is given
                            as vocabulary only - informational, never an
                            instruction (C5)
    direct tax lots         FIFO purchase lots for every directly held
                            ETF/share, built from my_investments.csv
                            buys and sells; days held and whether
                            long-term (>365 days). India FY2025-26 equity
                            rates (STCG 20%, LTCG 12.5% above the
                            Rs 1,25,000 exemption) are quoted [UNVERIFIED]
    portfolio XIRR          ONE money-weighted number: every dated
                            cashflow in my_investments.csv against
                            today's total portfolio value

THE HONESTY RULES (unchanged)
    A fund without a published portfolio is named as unanalysed - its
    money stays in the totals but never silently vanishes from, or
    invents, a breakdown. Every observation states its threshold.
    Nothing here recommends buying, selling or switching anything (C5):
    this file reports facts a reviewer could check by hand.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Portfolio_Analysis_Tab\\build_the_portfolio_review.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import analyse_a_fund                           # noqa: E402
import compute_the_ratios                       # noqa: E402
import compute_the_time_series                  # noqa: E402
import compute_the_xirr                         # noqa: E402
import fetch_fund_facts                         # noqa: E402
import fetch_market_facts                       # noqa: E402
import read_portfolio_holdings                  # noqa: E402
import read_what_i_own                          # noqa: E402
from find_the_overlap import overlap_between, tidy_a_name  # noqa: E402

SAVED_RECORDS = SCREEN / "Saved_Records"
REVIEW_FILE = SAVED_RECORDS / "portfolio_review_latest.json"
EQUITY_LEDGER_FILE = SAVED_RECORDS / "equity_price_ledger.csv"

# Observation thresholds - each one is stated next to the observation
# it produces, so nobody has to trust a number without its rule.
SINGLE_STOCK_FLAG_PCT = 10.0      # more than this in one company
TOP_TEN_WATCH_PCT = 25.0          # above this, concentration worth watching
TOP_TEN_FLAG_PCT = 40.0           # above this, concentrated
PAIR_OVERLAP_WATCH_PCT = 40.0     # two funds sharing this much duplication
SECTOR_FLAG_PCT = 30.0            # one sector above this much of equity
EXPENSE_WATCH_PCT = 1.0           # blended cost per year worth noticing

# Direct equities / ETFs (Phase 4). These rows are the instrument
# itself, not a wrapper, so they join the look-through whole.
DIRECT_CATEGORIES = {"etf", "equity"}
GOLD_MARKERS = ("gold", "goldbees")   # a gold ETF names gold or GOLDBEES;
                                      # anything matching lands under the
                                      # commodity bucket, never Equity
COMMODITY_BUCKET = "Commodity / Precious Metals"

# Allocation drift (C5-safe observation, not advice). Targets live in
# fund_analysis_settings.json under target_allocation and are
# [UNVERIFIED] until a person confirms them; only the DRIFT THRESHOLD
# below belongs to this file.
DRIFT_FLAG_PP = 5.0               # absolute pp of drift worth naming

# Direct tax lots. Holding-period rule first (a structural definition),
# then the FY2025-26 equity RATES, which nobody has verified yet - so
# every use prints [UNVERIFIED] next to them.
EQUITY_LONG_TERM_DAYS = 365       # > this many days held == long-term
STCG_RATE_PCT_UNVERIFIED = 20.0   # FY2025-26 equity STCG [UNVERIFIED]
LTCG_RATE_PCT_UNVERIFIED = 12.5   # FY2025-26 equity LTCG [UNVERIFIED]
LTCG_EXEMPTION_RS_UNVERIFIED = 125000.0   # yearly LTCG exemption

# 5/25 rebalancing-band vocabulary (Larry Swedroe's formulation): a band
# of +/-5pp absolute around targets of REBAND_TARGET_MIN_PCT or more,
# +/-25% relative below that. Printed as language, never as a trigger.
REBAND_ABSOLUTE_BAND_PP = 5.0
REBAND_RELATIVE_BAND_PCT = 25.0
REBAND_TARGET_MIN_PCT = 20.0


def read_settings() -> dict:
    return analyse_a_fund.read_settings()


def _funds_from_snapshot() -> list[dict]:
    """Every holding row with its value, tracked or not."""
    try:
        rows = read_portfolio_holdings.read_every_holding()
    except Exception:                                             # noqa: BLE001
        return []
    return rows


def load_profiles() -> dict[str, dict]:
    """Every stored per-fund analysis, keyed by AMFI code."""
    profiles: dict[str, dict] = {}
    if not analyse_a_fund.PROFILES_DIR.exists():
        return profiles
    for path in sorted(analyse_a_fund.PROFILES_DIR.glob("*.json")):
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if profile.get("has_data"):
            profiles[path.stem] = profile
    return profiles


# ---------------------------------------------------------------------
# DIRECT EQUITIES / ETFs - classify them, and price them honestly
# ---------------------------------------------------------------------
def is_gold(name: str, code: str | None = None) -> bool:
    """A gold ETF says gold somewhere in its name or its NSE symbol
    (GOLDBEES). Anything matching lands under Commodity/Precious Metals,
    never under Equity - a gold ETF holds metal, not companies."""
    haystack = f"{name or ''} {code or ''}".lower()
    return any(marker in haystack for marker in GOLD_MARKERS)


def direct_bucket(name: str, code: str | None = None) -> str:
    return COMMODITY_BUCKET if is_gold(name, code) else "Equity"


def direct_transaction_symbol(name: str, code: str,
                              known_identifiers: set[str],
                              ledger_closes: dict[str, dict]) -> str | None:
    """The NSE symbol a directly held ETF/share's transactions live
    under: its own code when that already looks like one, else the
    exchange-suffixed symbol the price ledger resolved for this name.
    A holdings row may carry an ISIN while my_investments.csv carries
    GOLDBEES-style symbols - this is the bridge between the two."""
    if code.upper() in known_identifiers:
        return code.upper()
    row = ledger_closes.get(name.strip().lower()) \
        or ledger_closes.get(code.upper())
    if row:
        base = (row.get("symbol") or "").strip().upper() \
            .removesuffix(".NS").removesuffix(".BO")
        if base in known_identifiers:
            return base
    return None


def _ledger_latest_closes() -> dict[str, dict]:
    """Newest close per key from equity_price_ledger.csv, keyed both by
    lowercase holding name and by NSE symbol (with and without the
    .NS/.BO exchange suffix). Missing file means empty, not a crash.

    Supersedes-aware (Phase-1 W1.2): a row another row's `supersedes`
    points at is history, not truth - corrections win even when they
    share the price date, and ties break toward the row written last.
    """
    rows: list[dict] = []
    if not EQUITY_LEDGER_FILE.exists():
        return {}
    with EQUITY_LEDGER_FILE.open(newline="", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f)
                if (row.get("symbol") or "").strip()]
    displaced = {r.get("supersedes") for r in rows if r.get("supersedes")}
    latest: dict[str, dict] = {}
    for row in rows:
        if row.get("event_id") and row.get("event_id") in displaced:
            continue
        keys = [(row.get("name") or "").strip().lower()]
        symbol = (row.get("symbol") or "").strip().upper()
        keys += [symbol, symbol.removesuffix(".NS").removesuffix(".BO")]
        rank = ((row.get("date") or ""), (row.get("written_at") or ""))
        for key in keys:
            if not key:
                continue
            kept = latest.get(key)
            if kept is None or rank > kept[0]:
                latest[key] = (rank, row)
    return {key: row for key, (_, row) in latest.items()}


def apply_ledger_prices(funds: list[dict]) -> list[dict]:
    """Reprice every etf/equity row from the equity price ledger when a
    close exists: newest close x units. When it does not, the stored
    snapshot value STANDS and carries a note saying so - never zero-
    filled, because a missing price is a gap to name, not a zero to
    wear. Returns the same list with `current`/`pl_*` refreshed in
    memory only; portfolio_holdings.csv itself is untouched here."""
    closes = _ledger_latest_closes()
    for fund in funds:
        if fund.get("category") not in DIRECT_CATEGORIES:
            continue
        code = (fund.get("amfi_code") or "").strip()
        name = fund["scheme_name"]
        row = (closes.get(code.upper())
               or closes.get(name.strip().lower()))
        units = fund.get("units")
        try:
            units = float(units)
        except (TypeError, ValueError):
            units = None
        if row is None or units is None or units <= 0:
            fund["price_note"] = (
                "stored snapshot value kept - no usable "
                f"equity_price_ledger.csv close "
                f"({'no ledger row' if row is None else 'blank/zero units'})")
            continue
        try:
            close = float(row.get("close"))
        except (TypeError, ValueError):
            fund["price_note"] = ("stored snapshot value kept - the "
                                  "ledger close did not parse as a number")
            continue
        value = round(units * close, 2)
        invested = float(fund.get("invested") or 0)
        fund["current"] = value
        fund["pl_abs"] = round(value - invested, 2)
        fund["pl_pct"] = round((value - invested) / invested * 100, 2) \
            if invested else None
        fund["price_note"] = (
            f"priced from equity_price_ledger.csv {row.get('date')} close "
            f"Rs {close} x {units:g} units ({row.get('symbol')}, "
            f"{row.get('source')})")
    return funds



def look_through(funds: list[dict], profiles: dict[str, dict]) -> dict:
    """Company -> rupees, across every fund that has a published
    portfolio. Weighted by each fund's CURRENT value in this portfolio,
    not by invested amount - concentration is about today's money.
    """
    company_money: dict[str, float] = {}
    shown_as: dict[str, str] = {}
    company_bucket: dict[str, str] = {}
    direct_holding_names: set[str] = set()
    total = 0.0
    funds_used: list[str] = []
    unanalysed: list[dict] = []

    for fund in funds:
        value = float(fund.get("current") or 0)
        if value <= 0:
            continue
        code = (fund.get("amfi_code") or "").strip()
        if fund.get("category") in DIRECT_CATEGORIES:
            # An ETF/share row is not a wrapper - it IS the instrument,
            # so it enters the X-ray at 100% of its own value. A gold
            # ETF carries its commodity bucket with it.
            name = fund["scheme_name"]
            funds_used.append(name)
            total += value
            company_money[name] = company_money.get(name, 0.0) + value
            shown_as.setdefault(name, name)
            company_bucket[name] = direct_bucket(name, code)
            direct_holding_names.add(name)
            continue
        profile = profiles.get(code)
        if profile is None:
            if fund.get("category") == "mutual_fund":
                unanalysed.append({"scheme_name": fund["scheme_name"],
                                   "value": round(value, 2),
                                   "reason": "no published portfolio on file"})
            continue
        funds_used.append(fund["scheme_name"])
        total += value
        for row in profile.get("holdings_ledger") or []:
            name = tidy_a_name(row.get("name"))
            weight = float(row.get("assets_pct") or 0)
            if not name or weight <= 0:
                continue
            company_money[name] = company_money.get(name, 0.0) + value * weight / 100.0
            shown_as.setdefault(name, row.get("name") or name)

    if total <= 0 or not company_money:
        return {"has_data": False,
                "note": ("no fund's published portfolio is on file yet - "
                         "run the daily pull when mfdata.in answers"),
                "funds_used": funds_used,
                "unanalysed": unanalysed}

    companies = [{"stock": shown_as.get(n, n),
                  "money": round(m, 2),
                  "percent_of_everything": round(m / total * 100, 2),
                  "held_directly": n in direct_holding_names,
                  "bucket": company_bucket.get(n)}
                 for n, m in company_money.items()]
    companies.sort(key=lambda r: r["percent_of_everything"], reverse=True)

    hhi = sum((c["percent_of_everything"] / 100.0) ** 2 for c in companies)
    top_ten = sum(c["percent_of_everything"] for c in companies[:10])

    return {
        "has_data": True,
        "total_lookthrough_value": round(total, 2),
        "companies_you_own": len(companies),
        "companies": companies,
        "biggest_single_bet": companies[0],
        "top_ten_percent": round(top_ten, 2),
        "hhi": round(hhi, 4),
        # 1/HHI: how many equally-sized bets the portfolio behaves like.
        "effective_number_of_stocks": round(1 / hhi, 1) if hhi > 0 else None,
        "funds_used": funds_used,
        "direct_holdings": sorted(direct_holding_names),
        "unanalysed": unanalysed,
    }


# ---------------------------------------------------------------------
# MONEY-WEIGHTED SPLITS ACROSS THE WHOLE PORTFOLIO
# ---------------------------------------------------------------------
def _weighted_split(funds: list[dict], profiles: dict[str, dict],
                    container_key: str, labels: list[str]) -> dict:
    """Value-weighted merge of one split (asset, market cap) across
    every analysed fund; everything unanalysed lands in 'unknown' with
    its rupee amount named."""
    buckets: dict[str, float] = {}
    known_total = 0.0
    unknown_value = 0.0
    base = 0.0

    for fund in funds:
        value = float(fund.get("current") or 0)
        if value <= 0:
            continue
        base += value
        if fund.get("category") in DIRECT_CATEGORIES:
            # A direct ETF/share is its own asset class: a gold ETF is
            # commodity, anything else equity - no profile needed.
            label = ("commodity_pct" if is_gold(fund["scheme_name"],
                                                fund.get("amfi_code"))
                     else "equity_pct")
            buckets[label] = buckets.get(label, 0.0) + value
            known_total += value
            continue
        profile = profiles.get((fund.get("amfi_code") or "").strip())
        if profile is None:
            unknown_value += value
            buckets["unknown"] = buckets.get("unknown", 0.0) + value
            continue
        container = profile.get(container_key) or {}
        for label in labels:
            pct = container.get(label)
            if pct is None:
                continue
            piece = value * pct / 100.0
            known_total += piece
            buckets[label] = buckets.get(label, 0.0) + piece

    parts = [{"name": k, "money": round(v, 2),
              "percent_of_portfolio": round(v / base * 100, 2) if base else 0.0}
             for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])]
    return {"has_data": base > 0 and known_total > 0,
            "parts": parts,
            "unknown_percent": round(unknown_value / base * 100, 2) if base else 100.0}


def weighted_sector_allocation(funds: list[dict],
                               profiles: dict[str, dict]) -> dict:
    """Sectors across the whole portfolio, money-weighted. Percentages
    are of the ANALYSED funds' value (cash included in the denominator,
    so the numbers add to 100 across sectors plus cash)."""
    import build_the_sector_map
    unclassified = build_the_sector_map.UNCLASSIFIED
    sector_map = build_the_sector_map.read_the_sector_map()

    sector_money: dict[str, float] = {}
    classified_money = 0.0
    analysed_value = 0.0

    for fund in funds:
        value = float(fund.get("current") or 0)
        if value <= 0:
            continue
        if fund.get("category") in DIRECT_CATEGORIES:
            # A directly held ETF/share sits whole in one sector. Gold
            # goes to the commodity bucket by definition; anything else
            # goes through the same layered lookup a fund stock would -
            # curated map first, NSE universe second, honest miss last.
            analysed_value += value
            name = fund["scheme_name"]
            if is_gold(name, fund.get("amfi_code")):
                sector = COMMODITY_BUCKET       # deliberate, not guessed
                classified_money += value
            else:
                sector = build_the_sector_map._lookup_sector(name, sector_map)
                if sector != unclassified:
                    classified_money += value
            sector_money[sector] = sector_money.get(sector, 0.0) + value
            continue
        profile = profiles.get((fund.get("amfi_code") or "").strip())
        if profile is None:
            continue
        analysed_value += value
        split = profile.get("asset_split") or {}
        equity_value = value * float(split.get("equity_pct") or 0) / 100.0
        cash_value = value - equity_value
        if cash_value > 0:
            sector_money["cash & residual"] = \
                sector_money.get("cash & residual", 0.0) + cash_value
        for row in profile.get("holdings_ledger") or []:
            weight = float(row.get("assets_pct") or 0)
            if weight <= 0:
                continue
            piece = equity_value * weight / 100.0
            sector_money[row["sector"]] = \
                sector_money.get(row["sector"], 0.0) + piece
            if row["sector"] != unclassified:
                classified_money += piece

    sectors = [{"name": name, "money": round(money, 2),
                "percent_of_portfolio":
                    round(money / analysed_value * 100, 2) if analysed_value else 0.0}
               for name, money in
               sorted(sector_money.items(), key=lambda kv: -kv[1])]
    stock_money = sum(m for n, m in sector_money.items() if n != "cash & residual")
    coverage = round(classified_money / stock_money * 100, 1) if stock_money else 0.0
    return {"has_data": analysed_value > 0 and bool(sectors),
            "sectors": sectors,
            "analysed_value": round(analysed_value, 2),
            "classified_coverage_pct": coverage,
            "verified_by_a_person":
                build_the_sector_map.read_the_sector_map()["verified_by_a_person"]}


# ---------------------------------------------------------------------
# THE FUND SCORECARD - one row per holding, the numbers that matter
# ---------------------------------------------------------------------
def fund_scorecard(funds: list[dict], profiles: dict[str, dict],
                   settings: dict) -> dict:
    """Value, P/L, XIRR, cost and behaviour for each holding.

    Behaviour ratios come from NAV history vs the benchmark, so they
    work even on a day the holdings source is down; holdings-derived
    fields stay dashes until a profile exists.
    """
    xirr = compute_the_xirr.per_holding_xirr(
        latest_values=compute_the_xirr.snapshot_current_values())
    xirr_by_name = {h["name"]: h for h in (xirr.get("holdings") or [])}

    bench = fetch_market_facts.index_history(settings["benchmark_symbol"],
                                             days=settings["lookback_days"])
    periods = int(settings["trading_days_per_year"])

    rows = []
    for fund in funds:
        value = float(fund.get("current") or 0)
        invested = float(fund.get("invested") or 0)
        code = (fund.get("amfi_code") or "").strip()
        profile = profiles.get(code)
        xirr_row = xirr_by_name.get(fund["scheme_name"])

        perf: dict = {"has_data": False}
        if code and bench.get("has_data"):
            nav = fetch_fund_facts.nav_history(code)
            if nav.get("has_data"):
                perf = compute_the_ratios.performance(
                    nav.get("points", []), bench.get("points", []),
                    risk_free_pct=float(settings["risk_free_rate_pct"]),
                    periods=periods,
                    min_points=int(settings["min_points_for_ratios"]))

        pl_pct = round((value - invested) / invested * 100, 2) if invested else None
        rows.append({
            "scheme_name": fund["scheme_name"],
            "amfi_code": code,
            "category": fund.get("category", ""),
            "invested": round(invested, 2),
            "current": round(value, 2),
            "pl_pct": pl_pct,
            "xirr_pct": xirr_row.get("xirr_pct") if xirr_row else None,
            "expense_ratio": (profile or {}).get("expense_ratio"),
            "beta": perf.get("beta"),
            "alpha_pct": perf.get("alpha_pct"),
            "sharpe": perf.get("sharpe"),
            "sortino": perf.get("sortino"),
            "return_1y_pct": perf.get("return_1y_pct"),
            "volatility_pct": perf.get("volatility_pct"),
            "max_drawdown_pct": perf.get("max_drawdown_pct"),
            "has_holdings": profile is not None,
        })

    rows.sort(key=lambda r: -r["current"])
    return {"has_data": bool(rows), "rows": rows,
            "benchmark": settings["benchmark_name"],
            "xirr_note": None if xirr.get("has_data") else xirr.get("note")}


def overlap_pairs(funds: list[dict], profiles: dict[str, dict]) -> dict:
    """Every analysed pair and how much they are secretly the same fund."""
    analysed = []
    for fund in funds:
        profile = profiles.get((fund.get("amfi_code") or "").strip())
        if profile:
            analysed.append({"name": fund["scheme_name"],
                             "holdings": profile.get("holdings_ledger") or []})
    pairs = []
    for i in range(len(analysed)):
        for j in range(i + 1, len(analysed)):
            a = [{"stock_name": r["name"], "weight_pct": r["assets_pct"]}
                 for r in analysed[i]["holdings"]]
            b = [{"stock_name": r["name"], "weight_pct": r["assets_pct"]}
                 for r in analysed[j]["holdings"]]
            answer = overlap_between(a, b)
            pairs.append({
                "first_fund": analysed[i]["name"],
                "second_fund": analysed[j]["name"],
                "overlap_percent": answer["overlap_percent"],
                "shared_stocks": answer["shared_stocks"],
                "in_plain_words": answer["in_plain_words"],
            })
    pairs.sort(key=lambda p: -p["overlap_percent"])
    return {"has_data": len(analysed) >= 2, "pairs": pairs,
            "funds_compared": len(analysed)}


# ---------------------------------------------------------------------
# OBSERVATIONS - what a reviewer would flag first, each with its rule
# ---------------------------------------------------------------------
def observations(review: dict) -> list[dict]:
    """Threshold-based factual flags. Levels describe how far past a
    published industry norm the number sits - never what to do about
    it (C5). Every observation names its threshold in the text.
    """
    out: list[dict] = []
    look = review.get("look_through") or {}
    sectors = (review.get("sector_allocation") or {}).get("sectors") or []
    pairs = (review.get("overlap") or {}).get("pairs") or []
    scorecard = (review.get("scorecard") or {}).get("rows") or []

    if look.get("has_data"):
        top = look.get("biggest_single_bet")
        if top and top["percent_of_everything"] > SINGLE_STOCK_FLAG_PCT:
            out.append({"level": "flag",
                        "text": (f"{top['stock']} is "
                                 f"{top['percent_of_everything']}% of the analysed "
                                 f"portfolio - past the {SINGLE_STOCK_FLAG_PCT}% "
                                 "single-company screen most X-ray tools use."),
                        "basis": f"single stock > {SINGLE_STOCK_FLAG_PCT}%"})
        elif top:
            out.append({"level": "info",
                        "text": (f"Largest single company ({top['stock']}) is "
                                 f"{top['percent_of_everything']}%, inside the "
                                 f"{SINGLE_STOCK_FLAG_PCT}% screen."),
                        "basis": f"single stock <= {SINGLE_STOCK_FLAG_PCT}%"})

        top_ten = look.get("top_ten_percent")
        if top_ten is not None:
            if top_ten > TOP_TEN_FLAG_PCT:
                level, word = "flag", "past"
            elif top_ten > TOP_TEN_WATCH_PCT:
                level, word = "watch", "above the watch line of"
            else:
                level, word = "info", "under the watch line of"
            out.append({"level": level,
                        "text": (f"The ten biggest companies hold "
                                 f"{top_ten}% {word} "
                                 f"{TOP_TEN_WATCH_PCT}% / {TOP_TEN_FLAG_PCT}%."),
                        "basis": (f"top-10 vs {TOP_TEN_WATCH_PCT}%/"
                                  f"{TOP_TEN_FLAG_PCT}%")})
        eff = look.get("effective_number_of_stocks")
        if eff:
            out.append({"level": "info",
                        "text": (f"Effective number of stocks is {eff} - the "
                                 f"whole portfolio behaves like {eff} equal "
                                 "bets, however many funds it wears."),
                        "basis": "1 / HHI"})

    for pair in pairs:
        if pair["overlap_percent"] >= PAIR_OVERLAP_WATCH_PCT:
            out.append({"level": "watch",
                        "text": (f"{pair['first_fund']} and "
                                 f"{pair['second_fund']} share "
                                 f"{pair['overlap_percent']}% of their weights "
                                 f"across {pair['shared_stocks']} companies - "
                                 "the duplication band most overlap tools "
                                 "flag from 40%."),
                        "basis": f"pair overlap >= {PAIR_OVERLAP_WATCH_PCT}%"})

    for sector in sectors:
        name = sector["name"]
        if name in ("cash & residual",):
            continue
        pct = sector.get("percent_of_portfolio") or 0
        if pct > SECTOR_FLAG_PCT:
            out.append({"level": "flag",
                        "text": (f"{name} is {pct}% of the analysed portfolio - "
                                 f"past the {SECTOR_FLAG_PCT}% single-sector "
                                 "line."),
                        "basis": f"sector > {SECTOR_FLAG_PCT}%"})

    expenses = [r["expense_ratio"] for r in scorecard
                if r.get("expense_ratio") is not None]
    values = [r["current"] or 0 for r in scorecard
              if r.get("expense_ratio") is not None]
    if expenses and sum(values) > 0:
        weighted = sum(e * v for e, v in zip(expenses, values)) / sum(values)
        level = "watch" if weighted > EXPENSE_WATCH_PCT else "info"
        out.append({"level": level,
                    "text": (f"The blend costs about {round(weighted, 2)}% a "
                             f"year in expense ratios "
                             f"({'above' if weighted > EXPENSE_WATCH_PCT else 'within'} "
                             f"the {EXPENSE_WATCH_PCT}% notice line)."),
                    "basis": f"value-weighted expense vs {EXPENSE_WATCH_PCT}%"})

    untracked = [s["scheme_name"] for s in review.get("unanalysed", [])]
    if untracked:
        out.append({"level": "info",
                    "text": (f"No published portfolio on file for: "
                             + ", ".join(untracked)
                             + ". Their money counts in the totals but not in "
                               "any look-through breakdown."),
                    "basis": "unanalysed funds named, not hidden"})

    drift = review.get("allocation_drift") or {}
    rows_by_class = {r["asset_class"]: r
                     for r in (drift.get("rows") or [])}
    tag = drift.get("unverified_badge") or ""
    for cls in drift.get("classes_past_flag_line") or []:
        row = rows_by_class.get(cls) or {}
        badge_text = f" ({tag})" if tag else ""
        out.append({
            "level": "flag",
            "text": (f"{cls} sits at {row.get('actual_pct')}% against a "
                     f"{row.get('target_pct')}% target{badge_text} - "
                     f"{row.get('drift_pp')}pp of drift, past the "
                     f"{DRIFT_FLAG_PP}pp absolute flag line."),
            "basis": (f"abs(actual - target) > {DRIFT_FLAG_PP}pp; "
                      "targets [UNVERIFIED] in "
                      "fund_analysis_settings.json")})

    whole_xirr = review.get("portfolio_xirr") or {}
    if whole_xirr.get("has_data"):
        out.append({"level": "info",
                    "text": (f"The whole portfolio's money-weighted XIRR "
                             f"across {whole_xirr['cashflows_counted']} "
                             f"recorded cashflows is "
                             f"{whole_xirr['xirr_pct']}% a year as of "
                             f"{whole_xirr['valuation_date']}."),
                    "basis": ("XIRR over my_investments.csv flows vs "
                              "today's total value")})

    lots_block = review.get("direct_tax_lots") or {}
    for holding in lots_block.get("holdings") or []:
        all_lots = holding.get("lots") or []
        if not all_lots:
            continue
        long_lots = [l for l in all_lots if l["long_term"]]
        oldest = max(l["days_held"] for l in all_lots)
        out.append({"level": "info",
                    "text": (f"{holding['scheme_name']}: {len(long_lots)} "
                             f"FIFO lot(s) past {EQUITY_LONG_TERM_DAYS} days "
                             f"(long-term) and {len(all_lots) - len(long_lots)} "
                             f"still short-term; oldest held {oldest} days. "
                             f"STCG {STCG_RATE_PCT_UNVERIFIED:g}% / LTCG "
                             f"{LTCG_RATE_PCT_UNVERIFIED:g}% above Rs "
                             f"{LTCG_EXEMPTION_RS_UNVERIFIED:,.0f} are "
                             "[UNVERIFIED] FY2025-26 figures."),
                    "basis": (f"days held > {EQUITY_LONG_TERM_DAYS} == "
                              "long-term; rates [UNVERIFIED]")})

    return out


def _totals(funds: list[dict]) -> dict:
    invested = sum(float(f.get("invested") or 0) for f in funds)
    current = sum(float(f.get("current") or 0) for f in funds)
    return {"invested": round(invested, 2), "current": round(current, 2),
            "pl_abs": round(current - invested, 2),
            "pl_pct": round((current - invested) / invested * 100, 2)
                      if invested else None,
            "how_many_holdings": len(funds)}


# ---------------------------------------------------------------------
# ALLOCATION DRIFT - actual weights vs targets (targets are UNVERIFIED)
# ---------------------------------------------------------------------
def allocation_drift(funds: list[dict], profiles: dict[str, dict],
                     settings: dict) -> dict:
    """Actual asset-class weights across EVERYTHING vs the targets in
    fund_analysis_settings.json. The targets carry
    verified_by_a_person: false until their owner confirms them, so
    every row here reads [UNVERIFIED]. A class drifting past
    DRIFT_FLAG_PP percentage points absolute is named - as a fact about
    distance from a stated target, never as an instruction (C5)."""
    targets_doc = settings.get("target_allocation") or {}
    targets = {k.lower(): float(v) for k, v in
               (targets_doc.get("targets") or {}).items()}
    verified = bool(targets_doc.get("verified_by_a_person"))
    tag = "" if verified else "[UNVERIFIED] "
    if not targets:
        return {"has_data": False,
                "note": ("no target_allocation.targets found in "
                         "fund_analysis_settings.json - nothing to "
                         "drift against")}

    actual: dict[str, float] = {}
    total = 0.0
    for fund in funds:
        value = float(fund.get("current") or 0)
        if value <= 0:
            continue
        total += value
        code = (fund.get("amfi_code") or "").strip()
        if fund.get("category") in DIRECT_CATEGORIES:
            key = ("commodity" if is_gold(fund["scheme_name"], code)
                   else "equity")
            actual[key] = actual.get(key, 0.0) + value
            continue
        split = profiles.get(code, {}).get("asset_split") or {}
        if not split:
            # No published asset split: its money is honestly unknown,
            # never silently filed under equity.
            actual["unknown"] = actual.get("unknown", 0.0) + value
            continue
        for cls in ("equity", "debt", "cash"):
            piece = value * float(split.get(f"{cls}_pct") or 0) / 100.0
            actual[cls] = actual.get(cls, 0.0) + piece

    classes = sorted(set(targets) | set(actual),
                     key=lambda k: -(actual.get(k, 0.0)))
    rows = []
    flagged = []
    for cls in classes:
        actual_pct = round(actual.get(cls, 0.0) / total * 100, 2) \
            if total else None
        target_pct = round(targets[cls], 2) if cls in targets else None
        drift_pp = (round(actual_pct - target_pct, 2)
                    if actual_pct is not None and target_pct is not None
                    else None)
        past = drift_pp is not None and abs(drift_pp) > DRIFT_FLAG_PP
        if past:
            flagged.append(cls)
        # 5/25 vocabulary, printed beside the fact: +/-5pp around a
        # target of REBAND_TARGET_MIN_PCT% or more, +/-25% relative
        # below that. Information only.
        band_pp = (REBAND_ABSOLUTE_BAND_PP
                   if target_pct is not None
                   and target_pct >= REBAND_TARGET_MIN_PCT
                   else (round(target_pct * REBAND_RELATIVE_BAND_PCT / 100, 2)
                         if target_pct is not None else None))
        rows.append({"asset_class": cls,
                     "target_pct": target_pct,
                     "actual_pct": actual_pct,
                     "drift_pp": drift_pp,
                     "band_pp_5_25_rule": band_pp,
                     "past_flag_line": past})
    return {"has_data": total > 0,
            "as_of_total": round(total, 2),
            "verified_by_a_person": verified,
            "unverified_badge": tag.strip(),
            "flag_threshold_pp": DRIFT_FLAG_PP,
            "rows": rows,
            "classes_past_flag_line": flagged}


# ---------------------------------------------------------------------
# PORTFOLIO XIRR - one money-weighted number across everything
# ---------------------------------------------------------------------
def overall_xirr(funds: list[dict], today: date) -> dict:
    """Every dated cashflow in my_investments.csv against today's TOTAL
    portfolio value - one XIRR for the whole book, not per fund.
    Holdings whose value enters without transaction rows are named:
    their money counts in the ending value even though their history is
    elsewhere (external folios), so the number describes all recorded
    flows against everything held today."""
    try:
        transactions = read_what_i_own.read_every_transaction()
    except read_what_i_own.TheRecordsAreWrong as problem:
        return {"has_data": False, "note": str(problem)}
    except FileNotFoundError:
        return {"has_data": False,
                "note": "my_investments.csv does not exist yet"}

    flows = [(row["date"], -float(row["amount"]))
             for row in transactions if row.get("amount")]
    flow_keys = {(row.get("identifier") or "").strip().upper()
                 for row in transactions}
    flow_keys |= {(row.get("name") or "").strip().lower()
                  for row in transactions}

    total_value = 0.0
    without_flows: list[str] = []
    ledger_closes = _ledger_latest_closes()
    for fund in funds:
        value = float(fund.get("current") or 0)
        if value <= 0:
            continue
        total_value += value
        code = (fund.get("amfi_code") or "").strip()
        name = fund["scheme_name"]
        candidates = {code.upper(), name.strip().lower()}
        if fund.get("category") in DIRECT_CATEGORIES:
            # A direct row may carry an ISIN while its transactions
            # live under an NSE symbol - bridge the two before calling
            # it history-less.
            symbol = direct_transaction_symbol(name, code, flow_keys,
                                               ledger_closes)
            if symbol:
                candidates.add(symbol)
        if not (candidates & flow_keys):
            without_flows.append(name)

    if not flows or total_value <= 0:
        return {"has_data": False,
                "note": ("need at least one cashflow and a known total "
                         f"value - got {len(flows)} flow(s) and Rs "
                         f"{round(total_value, 2)}")}
    flows.append((today, total_value))
    rate = compute_the_xirr.xirr(flows, today)
    return {
        "has_data": rate is not None,
        "xirr_pct": round(rate * 100, 2) if rate is not None else None,
        "valuation_date": today.isoformat(),
        "cashflows_counted": len(flows) - 1,
        "first_cashflow": min(when.isoformat() for when, _ in flows[:-1]),
        "total_value_used": round(total_value, 2),
        "value_without_transaction_rows": [
            {"scheme_name": n} for n in sorted(without_flows)],
        "note": ("one money-weighted number across every recorded "
                 "cashflow vs today's whole portfolio. Facts only - "
                 "never a verdict on what to do next (C5)."),
    }


# ---------------------------------------------------------------------
# DIRECT TAX LOTS - FIFO ages for directly held ETFs / shares
# ---------------------------------------------------------------------
def _fifo_open_lots(rows: list[dict]) -> list[dict]:
    """FIFO over one identifier's share rows: each sale consumes the
    oldest buys first; whatever survives is what is still held."""
    lots: list[dict] = []
    for row in sorted(rows, key=lambda r: r["date"]):
        units = float(row.get("units") or 0)
        amount = float(row.get("amount") or 0)
        if amount > 0:
            if units > 0:
                lots.append({"date": row["date"],
                             "units_bought": units,
                             "cost_per_unit": amount / units,
                             "units_open": units})
            continue
        need = abs(units)
        while need > 1e-9 and lots:
            oldest = lots[0]
            take = min(oldest["units_open"], need)
            oldest["units_open"] -= take
            need -= take
            if oldest["units_open"] <= 1e-9:
                lots.pop(0)
    return [lot for lot in lots if lot["units_open"] > 1e-9]


def equity_tax_lots(funds: list[dict], today: date) -> dict:
    """For each DIRECTLY held ETF/share: FIFO purchase lots from
    my_investments.csv, days held per surviving lot, and whether it is
    long-term (> EQUITY_LONG_TERM_DAYS). FY2025-26 equity rates are
    quoted with their [UNVERIFIED] badge attached - labels describe
    AGE only, and never suggest selling anything (C5)."""
    tag = "[UNVERIFIED]"
    rates = {
        "holding_period_long_term_days": EQUITY_LONG_TERM_DAYS,
        "stcg_rate_pct": STCG_RATE_PCT_UNVERIFIED,
        "ltcg_rate_pct": LTCG_RATE_PCT_UNVERIFIED,
        "ltcg_exemption_rs": LTCG_EXEMPTION_RS_UNVERIFIED,
        "source": ("India FY2025-26 capital-gains rules for listed "
                   "equity/equity ETFs"),
        "verified_by_a_person": False,
        "badge": tag,
    }
    try:
        transactions = read_what_i_own.read_every_transaction()
    except read_what_i_own.TheRecordsAreWrong as problem:
        return {"has_data": False, "rates": rates, "note": str(problem)}
    except FileNotFoundError:
        return {"has_data": False, "rates": rates,
                "note": "my_investments.csv does not exist yet"}

    by_identifier: dict[str, list[dict]] = {}
    for row in transactions:
        if row.get("kind") != "share":
            continue
        key = (row.get("identifier") or "").strip().upper()
        if key:
            by_identifier.setdefault(key, []).append(row)

    open_lots = {key: _fifo_open_lots(rows)
                 for key, rows in by_identifier.items()}
    ledger_closes = _ledger_latest_closes()

    def symbol_for(name: str, code: str) -> str | None:
        """Shared ISIN-to-NSE-symbol bridge, closed over this run's
        transaction identifiers and ledger closes."""
        return direct_transaction_symbol(name, code, set(by_identifier),
                                         ledger_closes)

    holdings_out = []
    matched: set[str] = set()
    excluded = []
    for fund in funds:
        if fund.get("category") not in DIRECT_CATEGORIES:
            continue
        code = (fund.get("amfi_code") or "").strip()
        name = fund["scheme_name"]
        symbol = symbol_for(name, code)
        lots_raw = open_lots.get(symbol) if symbol else None
        if not symbol or not lots_raw:
            excluded.append({
                "scheme_name": name,
                "reason": ("no share-kind transaction rows in "
                           "my_investments.csv could be matched to this "
                           "holding - FIFO age left blank, not guessed")})
            continue
        matched.add(symbol)
        lots = []
        for lot in lots_raw:
            days_held = (today - lot["date"]).days
            lots.append({
                "buy_date": lot["date"].isoformat(),
                "units_bought": round(lot["units_bought"], 4),
                "cost_per_unit": round(lot["cost_per_unit"], 4),
                "units_still_open": round(lot["units_open"], 4),
                "cost_basis_open_rs":
                    round(lot["units_open"] * lot["cost_per_unit"], 2),
                "days_held": days_held,
                "long_term": days_held > EQUITY_LONG_TERM_DAYS,
            })
        snapshot_units = fund.get("units")
        fifo_units = sum(l["units_still_open"] for l in lots)
        entry = {
            "scheme_name": name,
            "transaction_identifier": symbol,
            "lots": sorted(lots, key=lambda l: l["buy_date"]),
            "fifo_units_open": round(fifo_units, 4),
            "snapshot_units": round(float(snapshot_units), 4)
                              if snapshot_units not in (None, "") else None,
        }
        if entry["snapshot_units"] is not None and \
                abs(entry["snapshot_units"] - fifo_units) > 0.001:
            entry["units_mismatch_note"] = (
                f"FIFO open units ({fifo_units:g}) differ from the "
                f"holdings snapshot ({entry['snapshot_units']:g}) - both "
                "are reported as-is, neither was adjusted")
        holdings_out.append(entry)

    leftovers = [key for key in sorted(set(open_lots) - matched)
                 if any(l["units_open"] > 1e-9 for l in open_lots[key])]
    return {
        "has_data": bool(holdings_out),
        "as_of": today.isoformat(),
        "rates_and_rules": rates,
        "holdings": holdings_out,
        "excluded_holdings": excluded,
        "open_lots_without_an_open_holding": leftovers,
        "note": (f"{tag} Ages describe how long each FIFO purchase lot "
                 "has been held; the rates quoted are FY2025-26 figures "
                 "nobody has verified yet. Informational only - never a "
                 "suggestion to sell or hold anything (C5)."),
    }


# ---------------------------------------------------------------------
# REBALANCING BANDS - the 5/25 rule as vocabulary, nothing more
# ---------------------------------------------------------------------
def rebalancing_bands(drift: dict) -> dict:
    """The 5/25 rule in its usual words, tied to whichever classes the
    drift table shows past the flag line. Informational ONLY: naming a
    distance is not recommending a trade (C5)."""
    past = drift.get("classes_past_flag_line") or []
    badge = drift.get("unverified_badge") or ""
    return {
        "has_data": bool(drift.get("has_data")),
        "rule": ("5/25 rebalancing bands: an asset class whose weight "
                 f"sits more than {REBAND_ABSOLUTE_BAND_PP:g} percentage "
                 "points from its target is 'outside the band'; below a "
                 f"{REBAND_TARGET_MIN_PCT:g}% target the band is "
                 f"{REBAND_RELATIVE_BAND_PCT:g}% of the target instead"),
        "informational_only": True,
        "c5_note": ("this screen never recommends buying, selling or "
                    "switching - a band is a measuring stick, not an "
                    "instruction"),
        "classes_outside_their_band": [f"{c}{(' ' + badge).rstrip()}"
                                       for c in past],
        "targets_verified_by_a_person": drift.get("verified_by_a_person"),
    }


# ---------------------------------------------------------------------
# THE WHOLE REVIEW, AND WHAT IT WRITES DOWN
# ---------------------------------------------------------------------
def build_review(today: date | None = None) -> dict:
    """Assemble every piece into one review dict and write it down.

    Works in whatever state the sources are: holdings-derived sections
    come from stored profiles (the daily pull's output), behaviour
    ratios from NAV history. A missing piece is an honest gap with its
    reason - never a zero wearing a dash costume.
    """
    today = today or date.today()
    settings = read_settings()
    funds = _funds_from_snapshot()
    # Direct equities/ETFs get repriced from the equity price ledger
    # first, so every downstream number sees the same honest value.
    funds = apply_ledger_prices(funds)
    profiles = load_profiles()

    totals = _totals(funds)
    look = look_through(funds, profiles)
    asset = _weighted_split(funds, profiles, "asset_split",
                            ["equity_pct", "debt_pct", "cash_pct",
                             "commodity_pct"])
    caps = _weighted_split(funds, profiles, "market_cap_split",
                           ["large_cap_pct", "mid_cap_pct",
                            "small_cap_pct", "unknown_mcap_pct"])
    sectors = weighted_sector_allocation(funds, profiles)
    scorecard = fund_scorecard(funds, profiles, settings)
    overlap = overlap_pairs(funds, profiles)

    # Phase 4 metrics: drift vs targets (targets UNVERIFIED), FIFO ages
    # for directly held ETFs/shares, one XIRR across the whole book,
    # and the 5/25 band vocabulary.
    drift = allocation_drift(funds, profiles, settings)
    lots = equity_tax_lots(funds, today)
    whole_xirr = overall_xirr(funds, today)
    bands = rebalancing_bands(drift)

    unanalysed = list(look.get("unanalysed") or [])
    named = {u["scheme_name"] for u in unanalysed}
    for fund in funds:
        code = (fund.get("amfi_code") or "").strip()
        if not code and fund["scheme_name"] not in named:
            unanalysed.append({
                "scheme_name": fund["scheme_name"],
                "value": round(float(fund.get("current") or 0), 2),
                "reason": ("no AMFI code on the holding row, so no "
                           "published portfolio can be matched")})

    review = {
        "has_data": bool(funds),
        "built_on": today.isoformat(),
        "totals": totals,
        "look_through": look,
        "asset_allocation": asset,
        "market_cap_split": caps,
        "sector_allocation": sectors,
        "scorecard": scorecard,
        "overlap": overlap,
        "unanalysed": unanalysed,
        "allocation_drift": drift,
        "direct_tax_lots": lots,
        "portfolio_xirr": whole_xirr,
        "rebalancing_bands": bands,
        "direct_pricing": [
            {"scheme_name": f["scheme_name"],
             "price_note": f.get("price_note")}
            for f in funds if f.get("category") in DIRECT_CATEGORIES],
        "benchmark": settings["benchmark_name"],
        "settings_verified_by_a_person": settings["verified_by_a_person"],
    }
    review["observations"] = observations(review)

    # Time-series block: rolling CAGRs, drawdown curves, tax-lot ages,
    # benchmark growth, cashflow, equity band, cost drag, correlations
    # and the ledger value curve - all from stored series and real rows.
    try:
        review["time_series"] = compute_the_time_series.build_time_series(
            funds=funds, profiles=profiles, settings=settings, today=today)
    except Exception as problem:                                  # noqa: BLE001
        review["time_series"] = {
            "has_data": False,
            "note": f"the time-series block could not be built: {problem}"}

    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    REVIEW_FILE.write_text(json.dumps(review, ensure_ascii=False),
                           encoding="utf-8")
    return review


def read_review() -> dict | None:
    if not REVIEW_FILE.exists():
        return None
    try:
        return json.loads(REVIEW_FILE.read_text(encoding="utf-8"))
    except ValueError:
        return None


def main() -> None:
    review = build_review()
    print("WHOLE-PORTFOLIO REVIEW")
    print("=" * 60)
    t = review["totals"]
    print(f"  holdings          : {t['how_many_holdings']}")
    print(f"  invested / current: Rs {t['invested']} / Rs {t['current']} "
          f"({t['pl_pct']}%)")

    look = review["look_through"]
    if look.get("has_data"):
        print(f"  companies owned   : {look['companies_you_own']} "
              f"(effective N {look['effective_number_of_stocks']}, "
              f"HHI {look['hhi']})")
        print(f"  top 10 share      : {look['top_ten_percent']}%")
        top = look["biggest_single_bet"]
        print(f"  biggest bet       : {top['stock']} "
              f"{top['percent_of_everything']}%")
        print("  top 5 look-through:")
        for c in look["companies"][:5]:
            print(f"    {c['stock']:<32} {c['percent_of_everything']:>6}%  "
                  f"Rs {c['money']}")
    else:
        print(f"  look-through      : {look.get('note')}")

    sectors = review["sector_allocation"]
    if sectors.get("has_data"):
        print("  sector spread     :")
        for s in sectors["sectors"][:8]:
            print(f"    {s['name']:<32} {s['percent_of_portfolio']:>6}%")
        print(f"    classified coverage: {sectors['classified_coverage_pct']}%")

    drift = review.get("allocation_drift") or {}
    if drift.get("has_data"):
        print("  allocation drift  :")
        tag = f" {drift.get('unverified_badge')}" if drift.get("unverified_badge") else ""
        for r in drift.get("rows") or []:
            mark = " <-- past flag line" if r.get("past_flag_line") else ""
            if r.get("drift_pp") is None:
                print(f"    {r['asset_class']:<24} actual "
                      f"{r.get('actual_pct')}%{tag}{mark}")
            else:
                print(f"    {r['asset_class']:<24} actual "
                      f"{r.get('actual_pct')}% vs target "
                      f"{r.get('target_pct')}% ({r.get('drift_pp'):+}pp)"
                      f"{tag}{mark}")
    whole_xirr = review.get("portfolio_xirr") or {}
    if whole_xirr.get("has_data"):
        print(f"  portfolio XIRR    : {whole_xirr['xirr_pct']}% a year "
              f"(all {whole_xirr['cashflows_counted']} recorded cashflows)")
        missing_flows = (whole_xirr.get("value_without_transaction_rows")
                         or [])
        if missing_flows:
            names = ", ".join(h["scheme_name"] for h in missing_flows)
            print(f"    value w/o flows  : {names}")
    lots_block = review.get("direct_tax_lots") or {}
    for holding in lots_block.get("holdings") or []:
        all_lots = holding.get("lots") or []
        if not all_lots:
            continue
        oldest = max(l["days_held"] for l in all_lots)
        long_count = sum(1 for l in all_lots if l["long_term"])
        print(f"  direct FIFO lots  : {holding['scheme_name']} - "
              f"{len(all_lots)} open lot(s), {long_count} long-term, "
              f"oldest {oldest} days [UNVERIFIED rates]")
    bands = review.get("rebalancing_bands") or {}
    outside = bands.get("classes_outside_their_band") or []
    if bands.get("has_data"):
        word = ", ".join(outside) if outside else "none"
        print(f"  5/25 bands        : outside band -> {word} "
              "(informational only)")

    pairs = review["overlap"].get("pairs") or []
    if pairs:
        print("  biggest overlaps  :")
        for p in pairs[:3]:
            print(f"    {p['first_fund'][:26]} x {p['second_fund'][:26]} "
                  f"{p['overlap_percent']}%")

    series = review.get("time_series") or {}
    if series.get("has_data", False) or series.get("ledger_portfolio_value"):
        print("  time series       :")
        bench = series.get("portfolio_vs_benchmark") or {}
        if bench.get("has_data"):
            print(f"    vs benchmark     : {bench['shared_days']} shared days, "
                  f"{bench['first_day']} to {bench['last_day']}")
        ledger = series.get("ledger_portfolio_value") or {}
        if ledger.get("has_data"):
            print(f"    ledger value     : {ledger['days_covered']} day(s), "
                  f"{ledger['ledger_first_day']} to {ledger['ledger_last_day']}")
        drag = series.get("cost_drag") or {}
        if drag.get("has_data"):
            print(f"    cost drag        : Rs {drag['cumulative_rupees_as_of_today']} "
                  f"accrued at {drag['weighted_expense_ratio_pct']}%/yr weighted")
    else:
        print(f"  time series       : {series.get('note', 'no data')}")

    print("  observations      :")
    for o in review["observations"]:
        print(f"    [{o['level'].upper()}] {o['text']}")


if __name__ == "__main__":
    main()



