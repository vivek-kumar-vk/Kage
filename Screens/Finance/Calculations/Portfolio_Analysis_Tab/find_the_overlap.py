"""Works out how much two mutual funds are secretly the same fund.

This is arguably the single most valuable file in the Finance screen,
and it contains no model, no prompt and no network call. Overlap is
arithmetic. Asking a language model to compute it would be slower, cost
an allowance, and produce a number nobody could reproduce - Tier 0 in
practice: the router never sees this work.

Vocabulary, so the numbers mean one thing only:

    weight          percent of a fund's net assets held in one stock
    common_weight   for a stock in both funds, the smaller of the two weights
    overlap_percent the sum of common_weight across every shared stock

Overlap of 62% between two funds means 62 paise of every rupee put into
the second fund buys shares you already own through the first.
"""

from __future__ import annotations

from collections import defaultdict


def tidy_a_name(raw: str | None) -> str:
    """Fund houses spell the same company five ways. Normalise before
    comparing, or the overlap number will be quietly, confidently wrong."""
    name = (raw or "").strip().lower()
    for noise in (" limited", " ltd.", " ltd", " (india)", " india",
                 " corporation", " corp.", " corp", " company", " co.",
                 " & co", " plc", " inc.", " inc"):
        name = name.replace(noise, "")
    name = name.replace("&", "and").replace(".", "").replace(",", "")
    return " ".join(name.split())


def overlap_between(holdings_a: list[dict], holdings_b: list[dict]) -> dict:
    """holdings_a / holdings_b: list of {"stock_name": str, "weight_pct": float}

    Every number in the result can be recomputed by hand from the
    shared list, which is the point.
    """
    a = _collapse_duplicates(holdings_a)
    b = _collapse_duplicates(holdings_b)

    shared = []
    for name in sorted(set(a) & set(b)):
        common = min(a[name]["weight"], b[name]["weight"])
        shared.append({
            "stock": a[name]["shown_as"], "weight_in_first": round(a[name]["weight"], 2),
            "weight_in_second": round(b[name]["weight"], 2), "counts_as_overlap": round(common, 2),
        })
    shared.sort(key=lambda r: r["counts_as_overlap"], reverse=True)
    total = sum(row["counts_as_overlap"] for row in shared)

    only_in_first = sorted(
        ({"stock": a[n]["shown_as"], "weight": round(a[n]["weight"], 2)} for n in set(a) - set(b)),
        key=lambda r: r["weight"], reverse=True)
    only_in_second = sorted(
        ({"stock": b[n]["shown_as"], "weight": round(b[n]["weight"], 2)} for n in set(b) - set(a)),
        key=lambda r: r["weight"], reverse=True)

    return {
        "overlap_percent": round(total, 2), "shared_stocks": len(shared), "shared": shared,
        "only_in_first": only_in_first, "only_in_second": only_in_second,
        "in_plain_words": _say_what_it_means(total, len(shared)),
    }


def _collapse_duplicates(holdings: list[dict] | None) -> dict:
    """One row per company, weights added, original spelling remembered."""
    tidy = defaultdict(lambda: {"weight": 0.0, "shown_as": ""})
    for row in holdings or []:
        name = tidy_a_name(row.get("stock_name"))
        if not name:
            continue
        try:
            weight = float(row.get("weight_pct") or 0)
        except (TypeError, ValueError):
            continue
        tidy[name]["weight"] += weight
        if not tidy[name]["shown_as"]:
            tidy[name]["shown_as"] = (row.get("stock_name") or "").strip()
    return tidy


def _say_what_it_means(total: float, count: int) -> str:
    """Descriptive, never advice - CHECK_HUMAN would reject this text if
    it recommended anything, and it must not (C5)."""
    rounded = round(total)
    if total >= 60:
        return (f"{rounded}% of these two funds is the same {count} companies. "
               "Money added to the second buys mostly what the first already holds.")
    if total >= 35:
        return f"{rounded}% is shared across {count} companies. Meaningful common ground, with real differences either side."
    if total >= 15:
        return f"{rounded}% is shared. These funds mostly hold different companies."
    return f"{rounded}% is shared across {count} companies. These two funds have very little in common."


def look_through_the_whole_portfolio(funds: list[dict], direct_shares: list[dict] | None = None) -> dict:
    """funds: list of {"name", "amount_invested", "holdings": [...]}
    direct_shares: list of {"stock_name", "amount_invested"}

    Answers the question the fund-by-fund view cannot: across
    everything I own, how much of my money sits in one company? This
    is where a person discovers they hold 11% of one bank through four
    funds that each looked diversified on its own.
    """
    money_per_company: dict[str, float] = defaultdict(float)
    shown_as: dict[str, str] = {}
    total_money = 0.0

    for fund in funds or []:
        amount = float(fund.get("amount_invested") or 0)
        total_money += amount
        for row in fund.get("holdings") or []:
            name = tidy_a_name(row.get("stock_name"))
            if not name:
                continue
            try:
                weight = float(row.get("weight_pct") or 0)
            except (TypeError, ValueError):
                continue
            money_per_company[name] += amount * weight / 100.0
            shown_as.setdefault(name, (row.get("stock_name") or "").strip())

    for share in direct_shares or []:
        name = tidy_a_name(share.get("stock_name"))
        if not name:
            continue
        amount = float(share.get("amount_invested") or 0)
        money_per_company[name] += amount
        total_money += amount
        shown_as.setdefault(name, (share.get("stock_name") or "").strip())

    if total_money <= 0:
        return {"has_data": False, "companies": [],
               "note": "No amounts were recorded, so no percentages can be shown."}

    companies = [
        {"stock": shown_as.get(name, name), "money": round(money, 2),
         "percent_of_everything": round(money / total_money * 100, 2)}
        for name, money in money_per_company.items()
    ]
    companies.sort(key=lambda r: r["money"], reverse=True)
    top_ten = sum(row["percent_of_everything"] for row in companies[:10])

    return {
        "has_data": True, "total_invested": round(total_money, 2),
        "companies_you_own": len(companies), "companies": companies,
        "top_ten_percent": round(top_ten, 2),
        "biggest_single_bet": companies[0] if companies else None,
    }


def what_you_do_not_own(companies_you_own: list[dict], index_constituents: list[dict]) -> dict:
    """The other half of the diversification question: what is in the
    index and absent from everything I hold. Ranks by index weight,
    which is a fact, and stops there - choosing among them is a
    person's job (C5)."""
    owned = {tidy_a_name(row["stock"]) for row in (companies_you_own or [])}
    missing = [
        {"stock": row.get("stock_name"), "weight_in_index": round(float(row.get("weight_pct") or 0), 2)}
        for row in (index_constituents or [])
        if tidy_a_name(row.get("stock_name")) not in owned
    ]
    missing.sort(key=lambda r: r["weight_in_index"], reverse=True)
    return {"count": len(missing), "not_owned": missing,
           "note": "These sit in the index and in none of your funds or shares. That is an observation about coverage, not a list to buy."}
