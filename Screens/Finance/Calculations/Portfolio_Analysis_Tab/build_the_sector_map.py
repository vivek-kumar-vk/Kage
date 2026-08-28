"""What share of the mutual-fund portfolio sits in which business sector.

WHERE THE DATA COMES FROM
    Two places, both already in this screen:

        each fund's published stock holdings
            fetch_fund_facts.holdings(amfi_code) - mfdata.in's monthly
            snapshot of what the fund owns, stock by stock, with weights.
        what each holding is worth
            the caller hands over fund values, so a 30% weight in a small
            fund counts for less than a 10% weight in a big one.

    A stock's SECTOR comes from Reference_Data/sector_for_stocks.json,
    now in two layers: the hand-curated 'sectors' map a person typed
    (always the override), then a machine-filled 'nse_universe' layer
    built from NSE's index constituent CSVs by fetch_nse_universe.py.
    Both carry verified_by_a_person: false, exactly like the India tax
    rulebook. Every figure built on an unverified sector must be
    printed with that fact attached, not quietly presented as law.

THE HONESTY RULES
    A fund whose holdings cannot be fetched is skipped and named in
    skipped_funds - its money does not silently vanish from the total.
    A stock missing from the reference map lands in "not yet classified"
    rather than being guessed at. When too little of the portfolio can be
    classified, has_data goes false rather than showing a misleading pie.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Portfolio_Analysis_Tab\\build_the_sector_map.py
"""

from __future__ import annotations

import json
import sys
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

import fetch_fund_facts                             # noqa: E402

SECTOR_MAP_FILE = SCREEN / "Reference_Data" / "sector_for_stocks.json"
UNCLASSIFIED = "not yet classified"


def read_the_sector_map() -> dict:
    """Both layers of Reference_Data/sector_for_stocks.json.

    Layer 1 - 'sectors': the hand-curated name -> sector map a person
    typed, which always wins.
    Layer 2 - 'nse_universe': machine-filled from NSE's index
    constituent CSVs (fetch_nse_universe.py), consulted only when layer
    1 misses. Missing file or missing layer is an empty map, not a
    crash.
    """
    if not SECTOR_MAP_FILE.exists():
        return {"sectors": {}, "verified_by_a_person": False,
                "nse_by_name": {}, "nse_by_symbol": {}}
    raw = json.loads(SECTOR_MAP_FILE.read_text(encoding="utf-8"))
    universe = raw.get("nse_universe") or {}
    return {"sectors": raw.get("sectors", {}),
            "verified_by_a_person": bool(raw.get("verified_by_a_person", False)),
            "nse_by_name": universe.get("by_name", {}),
            "nse_by_symbol": universe.get("by_symbol", {})}


def _tidy(name: str) -> str:
    """The same tidy rule every map in this screen keys on."""
    wanted = "".join(c for c in (name or "").strip().lower()
                     if c.isalnum() or c == " ")
    return " ".join(wanted.split())


def _strip_suffix(name: str) -> str:
    """Drop trailing corporate shapes ('ltd', 'limited', ...).

    Fund facts say 'Larsen & Toubro Ltd.' while the curated map says
    'larsen & toubro' - without this, every suffixed name misses the
    exact curated key and the machine layer answers instead of the
    person who deliberately chose that sector.
    """
    words = name.split()
    while words and words[-1] in {"ltd", "ltd.", "limited", "co", "co.",
                                  "company", "corp", "corp.",
                                  "corporation", "india"}:
        words.pop()
    return " ".join(words)


def _curated_exact(sectors: dict, wanted: str) -> str | None:
    """Curated hit on the raw key or its suffix-stripped form."""
    if wanted in sectors:
        return sectors[wanted]
    stripped = _strip_suffix(wanted)
    if stripped != wanted and stripped in sectors:
        return sectors[stripped]
    for known, sector in sectors.items():
        if _strip_suffix(_tidy(known)) == stripped:
            return sector
    return None


def _lookup_sector(stock_name: str, sector_map: dict) -> str:
    """Match a fund facts company name to a sector, in strict order.

    1. curated exact      - what a person typed always wins
    2. NSE universe exact - by tidy company name, then by NSE symbol
    3. curated substring  - only for keys long enough to be unambiguous
    4. not yet classified - the honest answer when nothing matched

    Exact means suffix-tolerant ('... Ltd.' still hits what a person
    typed), otherwise a machine label outranks a human one on a
    technicality. The substring floor matters: without it, "l&t" tidies
    to "lt" and matches "infosys ltd", silently filing a software
    company under Industrials - which is exactly how a lookup helper
    becomes a bug generator. The substring pass deliberately reads ONLY
    the curated layer: fuzzy matching against ~900 machine-filled
    entries is how wrong sectors start looking official.
    """
    wanted = _tidy(stock_name)
    sectors = sector_map["sectors"]
    curated_hit = _curated_exact(sectors, wanted)
    if curated_hit:
        return curated_hit
    nse_names = sector_map.get("nse_by_name") or {}
    for candidate in (wanted, _strip_suffix(wanted)):
        if nse_names.get(candidate):
            return nse_names[candidate]
    nse_symbols = sector_map.get("nse_by_symbol") or {}
    symbol_guess = wanted.replace(" ", "").replace("&", "")
    if symbol_guess and nse_symbols.get(symbol_guess):
        return nse_symbols[symbol_guess]
    for known, sector in sectors.items():
        known_tidy = _tidy(known)
        if len(known_tidy) >= 6 and known_tidy in wanted:
            return sector
    return UNCLASSIFIED


def sector_breakdown(funds: list[dict]) -> dict:
    """Aggregate sector weights across the whole MF portfolio.

    funds: [{"scheme_name": str, "amfi_code": str, "value": float}]
        value is what that fund is worth today (rupees).

    Every returned weight is money-weighted, recomputable by hand from
    the per-fund rows, and carries the unverified flag upward so no one
    downstream can present it as checked when it is not.
    """
    sector_map = read_the_sector_map()
    sector_money: dict[str, float] = {}
    stock_money: dict[str, float] = {}
    skipped_funds, used_funds = [], []
    classified_money = 0.0
    total_with_holdings = 0.0

    for fund in funds:
        code = (fund.get("amfi_code") or "").strip()
        value = float(fund.get("value") or 0)
        if not code or value <= 0:
            continue
        facts = fetch_fund_facts.holdings(code)
        if not facts.get("has_data"):
            skipped_funds.append({"scheme_name": fund["scheme_name"],
                                  "note": facts.get("note", "no holdings data")})
            continue
        used_funds.append({"scheme_name": fund["scheme_name"], "value": value})
        total_with_holdings += value
        for row in facts.get("holdings", []):
            weight = float(row.get("weight_pct") or 0)
            money_here = value * weight / 100.0
            stock = row.get("stock_name") or ""
            if not stock or money_here <= 0:
                continue
            stock_money[stock] = stock_money.get(stock, 0.0) + money_here
            sector = _lookup_sector(stock, sector_map)
            sector_money[sector] = sector_money.get(sector, 0.0) + money_here
            if sector != UNCLASSIFIED:
                classified_money += money_here

    def ranked(source: dict, top: int | None = None) -> list[dict]:
        ordered = sorted(source.items(), key=lambda kv: kv[1], reverse=True)
        if top is not None:
            ordered = ordered[:top]
        base = total_with_holdings or 1.0
        return [{"name": name,
                 "money": round(money, 2),
                 "percent_of_portfolio": round(money / base * 100, 2)}
                for name, money in ordered]

    enough_classified = (
        total_with_holdings > 0 and classified_money / total_with_holdings >= 0.5
    )
    coverage_pct = (round(classified_money / total_with_holdings * 100, 1)
                    if total_with_holdings else 0.0)
    return {
        "has_data": bool(used_funds) and enough_classified,
        "reason": None if used_funds else "no fund's holdings could be fetched",
        "classified_coverage_pct": coverage_pct,
        "coverage_note": (
            f"{classified_money:.0f} of {total_with_holdings:.0f} rupees "
            f"of fetched holdings could be matched to a sector "
            f"({coverage_pct}% - curated overrides first, then NSE's "
            f"{len(sector_map.get('nse_by_name') or {})}-company universe)"
        ) if used_funds else None,
        "verified_by_a_person": sector_map["verified_by_a_person"],
        "sectors": ranked(sector_money),
        "top_stocks": ranked(stock_money, top=15),
        "funds_used": [f["scheme_name"] for f in used_funds],
        "skipped_funds": skipped_funds,
    }


def main() -> None:
    import read_portfolio_holdings
    try:
        holdings = read_portfolio_holdings.read_every_holding()
    except Exception as problem:                                      # noqa: BLE001
        print(f"could not read the holdings snapshot: {problem}")
        return
    funds = [{"scheme_name": h["scheme_name"], "amfi_code": h["amfi_code"],
              "value": h["current"] or 0}
             for h in holdings if h.get("category") == "mutual_fund"]
    answer = sector_breakdown(funds)

    print("SECTOR MAP")
    print("=" * 50)
    if not answer["has_data"]:
        print(f"  {answer['reason']}")
        return
    print(f"  {answer['coverage_note']}")
    flag = "" if answer["verified_by_a_person"] else "  [UNVERIFIED]"
    print()
    for row in answer["sectors"][:10]:
        print(f"  {row['name']:<32}{row['percent_of_portfolio']:>7.2f}%{flag}")


if __name__ == "__main__":
    main()
