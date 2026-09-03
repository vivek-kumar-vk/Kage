"""Reference data for the Analyse drawer — what a fund OWNS and what it
COSTS, plus stock fundamentals. One fetch per fund per month, cached in
`ref_cache` and persisted to `fund_facts` / `fund_portfolios`.

Source: Groww's public fund pages. The page is a Next.js app that embeds
its data as a <script id="__NEXT_DATA__"> JSON blob; props.pageProps.
mfServerSideData carries the facts (expense ratio, AUM, managers, risk,
benchmark, min SIP, exit load), the published portfolio (company, sector,
weight, market value, portfolio date), return stats, SIP returns, peers
and the PROS/CONS analysis. No key, no login — a plain GET.

SLUG RESOLUTION, in order (the search API 404s — verified 2026-09-02):
  1. MANUAL_OVERRIDES — codes whose page slug is NOT the current scheme
     name (Groww sometimes keeps the fund's launch-era name in the URL).
  2. name-slugify the scheme name into the candidate forms Groww uses
     (<base>-direct-growth / -direct-plan-growth / -regular-growth ...).
  3. the AMC page, which embeds every scheme of that fund house with its
     scheme_code -> search_id mapping (cached 30 days).
Every resolved page carries its own scheme_code; a fetch whose code does
not match the requested AMFI code is DISCARDED — a near-miss page must
never be presented as the fund's facts.

Honesty: a fund whose page cannot be resolved gets state "pending" with
the reason — NAV maths (mfapi, already in price_history) still works for
it; only the reference facts are missing. Nothing is ever manufactured.
"""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

from services.db import connect

PAGE_TTL_DAYS = 30          # portfolios are published monthly
AMC_TTL_DAYS = 30
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# slugs that are NOT the current scheme name (verified against the live
# site 2026-09-02). Extend freely — the resolver still runs after this.
MANUAL_OVERRIDES: dict[str, str] = {
    "122639": "parag-parikh-long-term-value-fund-direct-growth",
    "154082": "jioblackrock-sector-rotation-fund-direct-growth",
}

_STOP_WORDS = {"direct", "regular", "plan", "growth", "option", "idcw"}


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _cached(key: str, ttl_days: int) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT payload, fetched_at FROM ref_cache WHERE key = ?",
                         (key,)).fetchone()
    if not row:
        return None
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(row["fetched_at"])
        if age.days >= ttl_days:
            return None
        return json.loads(row["payload"])
    except (ValueError, TypeError):
        return None


def _store(key: str, payload: dict) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO ref_cache(key, payload, fetched_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET payload=excluded.payload, "
            "fetched_at=excluded.fetched_at",
            (key, json.dumps(payload),
             datetime.now(timezone.utc).isoformat(timespec="seconds")))
        db.commit()


def _get(url: str) -> tuple[bool, str]:
    """One GET with the browser UA. Returns (worked, body_or_reason)."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", _UA)
    req.add_header("Accept", "text/html,application/xhtml+xml")
    try:
        with urllib.request.urlopen(req, timeout=25, context=_ssl_context()) as r:
            return True, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, f"could not reach the site: {e}"


def _page_props(url: str, cache_key: str, ttl_days: int) -> dict | None:
    """props.pageProps out of a Groww page, daily-to-monthly cached."""
    cached = _cached(cache_key, ttl_days)
    if cached is not None:
        return cached
    worked, body = _get(url)
    if not worked:
        return None
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>',
        body, re.S)
    if not match:
        return None
    try:
        blob = json.loads(match.group(1))
    except ValueError:
        return None
    props = (blob.get("props") or {}).get("pageProps") or {}
    if props:
        _store(cache_key, props)
    return props or None


# ---------------------------------------------------------------- slugs
def slugify_base(name: str) -> str:
    text = (name or "").lower().replace("'", "").replace("&", "and")
    words = re.sub(r"[^a-z0-9]+", " ", text).split()
    while words and words[-1] in _STOP_WORDS:
        words.pop()
    return "-".join(words)


def _slug_candidates(name: str) -> list[str]:
    base = slugify_base(name)
    # Groww's URLs carry the plan even when the scheme name is sloppy
    # about it — both forms are tried, the name's own marker first.
    direct = [f"{base}-direct-growth", f"{base}-direct-plan-growth",
              f"{base}-direct-plan-growth-option"]
    regular = [f"{base}-regular-growth", f"{base}-regular-plan-growth",
               f"{base}-regular-plan-growth-option"]
    if "regular" in (name or "").lower():
        return regular + direct
    return direct + regular


def _amc_scheme_map(amc_slug: str) -> dict[str, str]:
    """scheme_code -> search_id for every scheme the AMC page embeds."""
    url = f"https://groww.in/mutual-funds/amc/{amc_slug}"
    props = _page_props(url, f"amc:{amc_slug}", AMC_TTL_DAYS)
    if not props:
        return {}
    text = json.dumps(props)
    pairs = re.findall(r'"scheme_code"\s*:\s*"?(\d{5,6})"?.{0,240}?"search_id"\s*:\s*"([^"]+)"',
                       text)
    return dict(pairs)


def resolve_slug(amfi_code: str, scheme_name: str | None,
                 fund_house: str | None = None) -> str | None:
    code = (amfi_code or "").strip()
    if code in MANUAL_OVERRIDES:
        return MANUAL_OVERRIDES[code]
    tried: list[str] = []
    for cand in _slug_candidates(scheme_name or ""):
        url = f"https://groww.in/mutual-funds/{cand}"
        worked, reason = _get(url)
        if worked:
            return cand
        tried.append(f"{cand} ({reason})")
    # AMC enumeration as the last automatic resort
    if fund_house:
        amc = slugify_base(fund_house)
        if amc.endswith("-mutual-fund"):
            amc += "s"
        elif not amc.endswith("-mutual-funds"):
            amc += "-mutual-funds"
        slugs = _amc_scheme_map(amc)
        if code in slugs:
            return slugs[code]
    return None


# ---------------------------------------------------------------- fund page
def _mf_data(props: dict) -> dict | None:
    data = props.get("mfServerSideData")
    if isinstance(data, dict) and data.get("scheme_code"):
        return data
    return None


def fetch_fund_page(amfi_code: str, scheme_name: str | None = None,
                    fund_house: str | None = None,
                    force: bool = False) -> dict:
    """The mfServerSideData dict for one scheme, or a pending-state dict.

    A cached page is trusted only if it still resolves to this scheme —
    the stored slug is tried first, then the resolver.
    """
    code = (amfi_code or "").strip()
    with connect() as db:
        row = db.execute("SELECT slug, data, fetched_at FROM fund_facts "
                         "WHERE amfi_code = ?", (code,)).fetchone()
    if row and not force:
        try:
            cached = json.loads(row["data"])
        except ValueError:
            cached = None
        if cached:
            return {"state": "ok", "data": cached, "slug": row["slug"],
                    "fetched_at": row["fetched_at"], "cached": True}

    slug = (row["slug"] if row else None) or resolve_slug(code, scheme_name, fund_house)
    if not slug:
        # last resort: ask mfapi which fund house this scheme belongs to
        # and enumerate that AMC's page (cached 30 days) for the code
        try:
            from services import market_data
            house = (market_data.latest_nav(code) or {}).get("fund_house")
            if house:
                slug = resolve_slug(code, scheme_name, house)
        except Exception:  # noqa: BLE001
            slug = None
    if not slug:
        return {"state": "pending",
                "reason": f"no Groww page found for scheme {code} — "
                          f"facts and portfolio are unavailable, NAV maths still works"}
    url = f"https://groww.in/mutual-funds/{slug}"
    props = _page_props(url, f"fund:{slug}", PAGE_TTL_DAYS)
    data = _mf_data(props) if props else None
    if data is None:
        return {"state": "pending",
                "reason": f"the Groww page for {slug} carried no fund data "
                          f"(layout change or upstream block)"}
    if str(data.get("scheme_code")) != code:
        return {"state": "pending",
                "reason": f"page {slug} is scheme {data.get('scheme_code')}, "
                          f"not {code} — discarded"}
    _persist_fund(code, slug, data)
    return {"state": "ok", "data": data, "slug": slug,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cached": False}


def _persist_fund(code: str, slug: str, data: dict) -> None:
    """fund_facts (whole JSON) + fund_portfolios (one row per holding)."""
    hold_rows = data.get("holdings") or []
    as_of = ""
    for h in hold_rows:
        raw = h.get("portfolio_date") if isinstance(h, dict) else None
        if raw:
            as_of = str(raw)[:10]
            break
    with connect() as db:
        db.execute(
            "INSERT INTO fund_facts(amfi_code, slug, source, data, portfolio_as_of, fetched_at) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(amfi_code) DO UPDATE SET "
            "slug=excluded.slug, source=excluded.source, data=excluded.data, "
            "portfolio_as_of=excluded.portfolio_as_of, fetched_at=excluded.fetched_at",
            (code, slug, "groww", json.dumps(data, ensure_ascii=False), as_of,
             datetime.now(timezone.utc).isoformat(timespec="seconds")))
        db.execute("DELETE FROM fund_portfolios WHERE amfi_code = ?", (code,))
        for h in hold_rows:
            company = (h.get("company_name") or "").strip()
            try:
                weight = float(h.get("corpus_per") or 0)
            except (TypeError, ValueError):
                weight = 0.0
            if not company or weight <= 0:
                continue
            db.execute(
                "INSERT OR IGNORE INTO fund_portfolios"
                "(amfi_code, company, sector, weight, instrument, isin, as_of) "
                "VALUES (?,?,?,?,?,?,?)",
                (code, company, (h.get("sector_name") or "").strip() or None,
                 weight, (h.get("nature_name") or h.get("instrument_name") or "").strip() or None,
                 (h.get("isin") or "").strip() or None, as_of))
        db.commit()


def stored_portfolio(amfi_code: str) -> dict:
    """The persisted portfolio rows for one fund, or pending."""
    with connect() as db:
        rows = db.execute(
            "SELECT company, sector, weight, instrument, isin, as_of "
            "FROM fund_portfolios WHERE amfi_code = ? ORDER BY weight DESC",
            ((amfi_code or "").strip(),)).fetchall()
    if not rows:
        return {"state": "pending", "holdings": [],
                "reason": "no published portfolio stored for this scheme"}
    return {"state": "ok", "as_of": rows[0]["as_of"],
            "holdings": [{k: r[k] for k in r.keys()} for r in rows]}


def stored_facts(amfi_code: str) -> dict | None:
    with connect() as db:
        row = db.execute("SELECT slug, data, fetched_at FROM fund_facts "
                         "WHERE amfi_code = ?", ((amfi_code or "").strip(),)).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row["data"])
    except ValueError:
        return None
    return {"slug": row["slug"], "fetched_at": row["fetched_at"], **data}


# ---------------------------------------------------------------- stocks
STOCK_OVERRIDES: dict[str, str] = {
    # symbol -> groww stock slug (the URL is the company name, not the ticker)
}


def fetch_stock_page(slug: str) -> dict:
    """pageProps of a Groww stock page (fundamentals, similarAssets,
    fundsInvested). Cached 7 days; None when the page is not there."""
    return _page_props(f"https://groww.in/stocks/{slug}",
                       f"stock:{slug}", 7) or {}
