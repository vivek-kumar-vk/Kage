"""The full analysis behind one fund's button on the Investments tab.

WHAT ONE CALL PRODUCES
    analyse_a_fund.analyse(amfi_code) answers, for one scheme:

        the holdings ledger  - every stock the fund owns, with its
                               sector, its instrument and its share of
                               the fund's assets
        the asset split      - Equity / Debt / Cash
        the market cap split - Large / Mid / Small / unknown
        sector allocation    - how the equity sits across businesses
        weighted P/E and P/B - weighted by each stock's asset weight
        advanced ratios      - beta, alpha, Sharpe, Sortino, volatility,
                               max drawdown, 1-year return

WHERE EACH NUMBER COMES FROM
    stock weights       mfdata.in   (via fetch_fund_facts.holdings)
    a stock's sector    Reference_Data/sector_for_stocks.json (hand map)
    cap / P/E / P/B     Yahoo Finance (via fetch_stock_facts.facts_for)
    NAV history         mfapi.in     (via fetch_fund_facts.nav_history)
    benchmark history   Yahoo Finance (via fetch_market_facts.index_history)
    ratio arithmetic    compute_the_ratios.performance - pure maths

THE HONESTY RULES
    Cash is a residual: whatever weight the published equity list does
    not explain. It is labelled as such. A stock whose cap or P/E could
    not be fetched lands in "unknown", never in a guessed bucket. A fund
    with no published portfolio comes back has_data false with the
    reason named.

WHAT IS WRITTEN DOWN
    Saved_Records/fund_profiles/<amfi_code>.json - the latest analysis,
    so opening the modal never re-pays for the web calls.
    Saved_Records/fund_analysis_ledger.csv - one row per fund per day,
    frozen columns (Column_Contracts v13+), so a later portfolio review
    can watch these numbers drift month by month.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\analyse_a_fund.py <amfi_code>
"""

from __future__ import annotations

import csv
import json
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
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_the_sector_map                     # noqa: E402
import compute_the_ratios                       # noqa: E402
import fetch_fund_facts                         # noqa: E402
import fetch_market_facts                       # noqa: E402
import fetch_stock_facts                        # noqa: E402
from find_the_overlap import tidy_a_name        # noqa: E402

SAVED_RECORDS = SCREEN / "Saved_Records"
PROFILES_DIR = SAVED_RECORDS / "fund_profiles"
LEDGER = SAVED_RECORDS / "fund_analysis_ledger.csv"
SETTINGS_FILE = SCREEN / "Reference_Data" / "fund_analysis_settings.json"

# Frozen column contract: fund_analysis_ledger (Column_Contracts v13+).
COLUMNS = [
    "date", "amfi_code", "scheme_name", "as_of",
    "equity_pct", "debt_pct", "cash_pct",
    "large_cap_pct", "mid_cap_pct", "small_cap_pct", "unknown_mcap_pct",
    "top_sector", "top_sector_pct", "pe", "pb",
    "beta", "alpha_pct", "sharpe", "sortino",
    "return_1y_pct", "volatility_pct", "max_drawdown_pct",
    "classified_coverage_pct", "source",
]

UNKNOWN_BUCKET = "unknown"


def read_settings() -> dict:
    """The reference file, or honest defaults when it is missing."""
    defaults = {
        "benchmark_symbol": "^NSEI", "benchmark_name": "NIFTY 50",
        "risk_free_rate_pct": 5.5, "lookback_days": 365,
        "min_points_for_ratios": 60, "trading_days_per_year": 252,
        "market_cap_thresholds_cr": {"large_cap_min_cr": 75000,
                                     "mid_cap_min_cr": 25000},
        "verified_by_a_person": False,
    }
    if not SETTINGS_FILE.exists():
        return defaults
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except ValueError:
        return defaults
    merged = {**defaults, **{k: v for k, v in raw.items() if not k.startswith("_")}}
    merged["market_cap_thresholds_cr"] = {
        **defaults["market_cap_thresholds_cr"],
        **(raw.get("market_cap_thresholds_cr") or {}),
    }
    return merged


def _sector_map():
    return build_the_sector_map.read_the_sector_map()


# ---------------------------------------------------------------------
# THE HOLDINGS LEDGER
# ---------------------------------------------------------------------
def holdings_ledger(facts: dict) -> list[dict]:
    """One row per published holding: name, sector, instrument, assets.

    The sector comes from the hand-curated map; an unmatched stock says
    'not yet classified' rather than being filed under something close.
    """
    sector_map = _sector_map()
    rows = []
    for row in facts.get("holdings") or []:
        name = (row.get("stock_name") or "").strip()
        if not name:
            continue
        try:
            weight = float(row.get("weight_pct") or 0)
        except (TypeError, ValueError):
            weight = 0.0
        rows.append({
            "name": name,
            "sector": build_the_sector_map._lookup_sector(name, sector_map),
            "instrument": "equity",
            "assets_pct": round(weight, 2),
        })
    rows.sort(key=lambda r: r["assets_pct"], reverse=True)
    return rows


# ---------------------------------------------------------------------
# SPLITS AND ALLOCATIONS
# ---------------------------------------------------------------------
def asset_split(equity_rows: list[dict]) -> dict:
    """Equity is what the published list explains; cash is what is left.

    Debt would need a debt-holdings feed no free source publishes for
    these schemes, so it stays an explicit zero-with-a-reason unless one
    ever appears.
    """
    total_equity = round(sum(r["assets_pct"] for r in equity_rows), 2)
    cash = round(max(0.0, 100.0 - total_equity), 2)
    return {
        "equity_pct": min(total_equity, 100.0),
        "debt_pct": 0.0,
        "cash_pct": cash,
        "_note": ("cash is the part of the fund the published equity "
                  "list does not explain - a residual, not a counted "
                  "number; debt needs a feed no free source carries"),
    }


def sector_allocation(equity_rows: list[dict]) -> dict:
    """Weights regrouped by sector, biggest first."""
    buckets: dict[str, float] = {}
    for row in equity_rows:
        buckets[row["sector"]] = round(
            buckets.get(row["sector"], 0.0) + row["assets_pct"], 2)
    ranked = [{"name": name, "assets_pct": pct}
              for name, pct in sorted(buckets.items(),
                                      key=lambda kv: kv[1], reverse=True)]
    classified = sum(pct for name, pct in buckets.items()
                     if name != build_the_sector_map.UNCLASSIFIED)
    total = sum(pct for pct in buckets.values())
    return {
        "sectors": ranked,
        "classified_coverage_pct": round(classified / total * 100, 1) if total else 0.0,
        "verified_by_a_person": _sector_map()["verified_by_a_person"],
    }


def market_cap_split(equity_rows: list[dict], settings: dict) -> dict:
    """Large / Mid / Small by each stock's absolute market cap.

    SEBI defines caps by AMFI rank, which moves twice a year; absolute
    crore thresholds are a standing approximation (the settings file
    says so). A stock Yahoo could not size lands in 'unknown' with its
    weight - never silently dropped, never guessed.
    """
    thresholds = settings["market_cap_thresholds_cr"]
    large_min = float(thresholds.get("large_cap_min_cr", 75000))
    mid_min = float(thresholds.get("mid_cap_min_cr", 25000))

    buckets = {"large_cap": 0.0, "mid_cap": 0.0, "small_cap": 0.0,
               UNKNOWN_BUCKET: 0.0}
    per_stock: dict[str, dict] = {}
    seen: dict[str, dict] = {}

    for row in equity_rows:
        tidy = tidy_a_name(row["name"])
        facts = seen.get(tidy)
        if facts is None:
            facts = fetch_stock_facts.facts_for(row["name"])
            seen[tidy] = facts
        cap = facts.get("market_cap_cr")
        if cap is None:
            bucket = UNKNOWN_BUCKET
        elif cap >= large_min:
            bucket = "large_cap"
        elif cap >= mid_min:
            bucket = "mid_cap"
        else:
            bucket = "small_cap"
        buckets[bucket] = round(buckets[bucket] + row["assets_pct"], 2)
        per_stock[row["name"]] = {
            "bucket": bucket, "market_cap_cr": cap,
            "symbol": facts.get("symbol"),
        }

    resolved = 100.0 - buckets[UNKNOWN_BUCKET]
    return {
        "large_cap_pct": buckets["large_cap"],
        "mid_cap_pct": buckets["mid_cap"],
        "small_cap_pct": buckets["small_cap"],
        "unknown_mcap_pct": buckets[UNKNOWN_BUCKET],
        "resolved_coverage_pct": round(resolved, 1),
        "_note": ("thresholds are absolute crores standing in for SEBI's "
                  "rank-based definition - unverified"),
        "per_stock": per_stock,
    }


def _parse_point_day(raw) -> date | None:
    """The NAV feed writes dd-mm-yyyy; tests and ledgers write ISO.
    Both parse here, or the point is skipped."""
    if raw is None:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(raw), fmt).date()
        except ValueError:
            continue
    return None


def _chart_points(nav: dict) -> list[dict]:
    """The NAV series for drawing: sorted by day (the live feed arrives
    newest first), every point kept - the chart on the page is canvas-
    based and handles thousands of points with real date-axis spacing,
    so downsampling would only throw away real history. A gap the
    source skipped stays a gap - nothing is interpolated."""
    rows: list[tuple[date, dict]] = []
    for p in (nav.get("points") or []):
        day = _parse_point_day(p.get("date"))
        try:
            value = float(p.get("nav"))
        except (TypeError, ValueError):
            continue
        if day is not None and value > 0:
            rows.append((day, {"date": p["date"], "nav": round(value, 4)}))
    if not rows:
        return []
    rows.sort(key=lambda r: r[0])
    return [row for _, row in rows]


def weighted_pe_pb(equity_rows: list[dict]) -> dict:
    """Asset-weighted P/E and P/B across the stocks Yahoo could price.

    A loss-making company has no meaningful P/E and is left out of that
    average rather than entering as zero - a zero would flatter it.
    Coverage is reported so a thin average is visible as thin.
    """
    pe_weight, pb_weight = 0.0, 0.0
    pe_sum, pb_sum = 0.0, 0.0
    total_weight = sum(r["assets_pct"] for r in equity_rows)

    seen: dict[str, dict] = {}
    for row in equity_rows:
        tidy = tidy_a_name(row["name"])
        facts = seen.get(tidy)
        if facts is None:
            facts = fetch_stock_facts.facts_for(row["name"])
            seen[tidy] = facts
        weight = row["assets_pct"]
        if facts.get("pe"):
            pe_sum += weight * float(facts["pe"])
            pe_weight += weight
        if facts.get("pb"):
            pb_sum += weight * float(facts["pb"])
            pb_weight += weight

    def _avg(total: float, weight: float) -> float | None:
        return round(total / weight, 2) if weight > 0 else None

    return {
        "pe": _avg(pe_sum, pe_weight),
        "pb": _avg(pb_sum, pb_weight),
        "pe_coverage_pct": round(pe_weight / total_weight * 100, 1) if total_weight else 0.0,
        "pb_coverage_pct": round(pb_weight / total_weight * 100, 1) if total_weight else 0.0,
        "_note": ("weighted by asset weight across the stocks whose "
                  "figures could be fetched; coverage says how much of "
                  "the fund each average actually covers"),
    }


# ---------------------------------------------------------------------
# THE WHOLE ANALYSIS, AND WHAT IT WRITES DOWN
# ---------------------------------------------------------------------
def analyse(amfi_code: str, force: bool = False,
            today: date | None = None) -> dict:
    """Everything one fund's button shows. Writes the profile JSON and
    appends (today's) ledger row. `force` re-pays for web calls even
    when a profile from an earlier hour exists.
    """
    today = today or date.today()
    code = str(amfi_code).strip()

    facts = fetch_fund_facts.holdings(code)
    if not facts.get("has_data"):
        return {"has_data": False, "amfi_code": code,
                "note": facts.get("note", "no published portfolio could be fetched"),
                "where_from": facts.get("where_from")}

    equity_rows = holdings_ledger(facts)
    settings = read_settings()
    periods = int(settings["trading_days_per_year"])

    nav = fetch_fund_facts.nav_history(code)
    # The chart gets the full scheme history since inception; the ratio
    # window above stays at its own setting. One fetch feeds both - the
    # cache holds the whole series and each caller trims on the way out.
    nav_full = fetch_fund_facts.nav_history(code, how_many_days=None)
    bench = fetch_market_facts.index_history(settings["benchmark_symbol"],
                                             days=settings["lookback_days"])
    if bench.get("has_data"):
        performance = compute_the_ratios.performance(
            nav.get("points", []), bench.get("points", []),
            risk_free_pct=float(settings["risk_free_rate_pct"]),
            periods=periods,
            min_points=int(settings["min_points_for_ratios"]))
    else:
        performance = {"has_data": False, "note": bench.get("note"),
                       "benchmark": settings["benchmark_name"]}

    splits = asset_split(equity_rows)
    caps = market_cap_split(equity_rows, settings)
    sectors = sector_allocation(equity_rows)
    valuations = weighted_pe_pb(equity_rows)
    chart_points = _chart_points(nav_full)
    latest = chart_points[-1] if chart_points else {}

    answer = {
        "has_data": bool(equity_rows),
        "amfi_code": code,
        "scheme_name": facts.get("scheme_name", ""),
        "as_of": facts.get("as_of", "unknown"),
        "fetched_on": today.isoformat(),
        "expense_ratio": facts.get("expense_ratio"),
        "holdings_ledger": equity_rows,
        "asset_split": splits,
        "market_cap_split": {k: v for k, v in caps.items() if k != "per_stock"},
        "sector_allocation": sectors,
        "valuations": valuations,
        "performance": performance,
        # For the performance tab's line chart and NAV figure - stored in
        # the profile so opening the modal never re-fetches the history.
        "nav_history": {"points": chart_points,
                        "where_from": nav.get("where_from")},
        "latest_nav": latest.get("nav"),
        "latest_nav_date": latest.get("date"),
        "benchmark": {"symbol": settings["benchmark_symbol"],
                      "name": settings["benchmark_name"],
                      "risk_free_rate_pct": settings["risk_free_rate_pct"]},
        "settings_verified_by_a_person": settings["verified_by_a_person"],
        "where_from": {"holdings": facts.get("where_from"),
                       "nav_history": nav.get("where_from"),
                       "company_facts": "yfinance"},
        "notes": [splits["_note"], caps["_note"], valuations["_note"]],
    }
    if not answer["has_data"]:
        answer["note"] = "the published portfolio listed no holdings"

    _write_profile(answer)
    _append_ledger_row(answer, today)
    return answer


def profile_path(amfi_code: str) -> Path:
    return PROFILES_DIR / f"{str(amfi_code).strip()}.json"


def _write_profile(analysis: dict) -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = profile_path(analysis["amfi_code"])
    path.write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")


def read_profile(amfi_code: str) -> dict | None:
    """The stored analysis, or None when this fund was never analysed."""
    path = profile_path(amfi_code)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def read_the_ledger() -> list[dict]:
    """Every recorded analysis row, oldest first. Empty when never run."""
    if not LEDGER.exists():
        return []
    with LEDGER.open(newline="", encoding="utf-8") as f:
        rows = [row for row in csv.DictReader(f)
                if (row.get("amfi_code") or "").strip()]
    rows.sort(key=lambda r: (r["amfi_code"], r["date"]))
    return rows


def _append_ledger_row(analysis: dict, today: date) -> None:
    """One row per fund per day - same day, same fund replaces.

    History across days is kept so a later portfolio review can watch a
    fund's beta or cash drag drift month over month with a file behind
    every point.
    """
    stamp = today.isoformat()
    perf = analysis.get("performance") or {}
    caps = analysis.get("market_cap_split") or {}
    splits = analysis.get("asset_split") or {}
    valuations = analysis.get("valuations") or {}
    sectors = (analysis.get("sector_allocation") or {}).get("sectors") or []
    top = sectors[0] if sectors else {}

    row = {
        "date": stamp,
        "amfi_code": analysis["amfi_code"],
        "scheme_name": analysis.get("scheme_name", ""),
        "as_of": analysis.get("as_of", ""),
        "equity_pct": splits.get("equity_pct"),
        "debt_pct": splits.get("debt_pct"),
        "cash_pct": splits.get("cash_pct"),
        "large_cap_pct": caps.get("large_cap_pct"),
        "mid_cap_pct": caps.get("mid_cap_pct"),
        "small_cap_pct": caps.get("small_cap_pct"),
        "unknown_mcap_pct": caps.get("unknown_mcap_pct"),
        "top_sector": top.get("name", ""),
        "top_sector_pct": top.get("assets_pct"),
        "pe": valuations.get("pe"),
        "pb": valuations.get("pb"),
        "beta": perf.get("beta"),
        "alpha_pct": perf.get("alpha_pct"),
        "sharpe": perf.get("sharpe"),
        "sortino": perf.get("sortino"),
        "return_1y_pct": perf.get("return_1y_pct"),
        "volatility_pct": perf.get("volatility_pct"),
        "max_drawdown_pct": perf.get("max_drawdown_pct"),
        "classified_coverage_pct": (analysis.get("sector_allocation") or {})
                                    .get("classified_coverage_pct"),
        "source": analysis.get("where_from", {}).get("holdings", ""),
    }

    kept = [r for r in read_the_ledger()
            if not (r["amfi_code"] == row["amfi_code"] and r["date"] == stamp)]
    kept.append(row)
    kept.sort(key=lambda r: (r["amfi_code"], r["date"]))

    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(kept)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: analyse_a_fund.py <amfi_code>")
        return
    answer = analyse(sys.argv[1])
    print(f"FUND ANALYSIS - {answer.get('scheme_name', sys.argv[1])}")
    print("=" * 60)
    if not answer["has_data"]:
        print(f"  could not analyse it: {answer.get('note')}")
        return
    print(f"  portfolio as of          : {answer['as_of']}")
    split = answer["asset_split"]
    print(f"  equity / debt / cash     : {split['equity_pct']}% / "
          f"{split['debt_pct']}% / {split['cash_pct']}%")
    caps = answer["market_cap_split"]
    print(f"  large / mid / small / unk: {caps['large_cap_pct']}% / "
          f"{caps['mid_cap_pct']}% / {caps['small_cap_pct']}% / "
          f"{caps['unknown_mcap_pct']}%")
    for sector in answer["sector_allocation"]["sectors"][:5]:
        print(f"  sector                   : {sector['name']:<28} "
              f"{sector['assets_pct']}%")
    valuations = answer["valuations"]
    print(f"  weighted P/E / P/B       : {valuations['pe']} / {valuations['pb']}")
    perf = answer["performance"]
    if perf.get("has_data"):
        print(f"  beta / alpha             : {perf['beta']} / {perf['alpha_pct']}%")
        print(f"  sharpe / sortino         : {perf['sharpe']} / {perf['sortino']}")
        print(f"  1y return / volatility   : {perf['return_1y_pct']}% / "
              f"{perf['volatility_pct']}%")
        print(f"  max drawdown             : {perf['max_drawdown_pct']}%")
    else:
        print(f"  ratios                   : {perf.get('note')}")
    print(f"  ledger rows written      : see {LEDGER.name}")


if __name__ == "__main__":
    main()
