from __future__ import annotations

import json
import re
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

from services.db import connect

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HOW_LONG_WE_WAIT = 20
FETCH_ATTEMPTS = 3
RETRY_PAUSE_SECONDS = 4

import sys

SOURCE_MFAPI = "mfapi"
SOURCE_AMFI = "amfi_nav"
SOURCE_YF = "yfinance"
SOURCE_BSE = "bse"

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from Shared_By_All_Screens import spine  # noqa: E402


def _emit_fetch(kind: str, source: str, **payload) -> None:
    """One spine fetch event for a market-data source. A failed spine write
    is traced to stderr and re-raised: the record must be loud."""
    try:
        spine.emit("finance", kind, source, payload)
    except spine.SpineWriteError as exc:
        print(f"spine write failed for {kind}/{source}: {exc}", file=sys.stderr)
        raise


def _get(address: str) -> tuple[bool, dict | str]:
    request = urllib.request.Request(address, method="GET")
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "INKY/1.0 (personal finance screen)")
    reason = "no attempt was made"
    for attempt in range(FETCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=HOW_LONG_WE_WAIT) as response:
                return True, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as problem:
            reason = f"the service answered HTTP {problem.code}"
        except urllib.error.URLError as problem:
            reason = f"could not reach the service: {problem.reason}"
        except ValueError:
            return False, "the service sent something that was not JSON"
        except Exception as problem:
            return False, f"unexpected trouble: {problem}"
        if attempt < FETCH_ATTEMPTS - 1:
            time.sleep(RETRY_PAUSE_SECONDS * (attempt + 1))
    return False, reason


_BSE_BASE = "https://api.bseindia.com/BseIndiaAPI/api"
_BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.bseindia.com/",
    "Origin": "https://www.bseindia.com",
    "Accept": "application/json, text/plain, */*",
}


def _bse_get(address: str) -> tuple[bool, dict | list | str]:
    """One GET against api.bseindia.com — it 403s without a browser UA and
    the bseindia.com referer, so it needs its own headered request."""
    request = urllib.request.Request(address, method="GET")
    for name, value in _BSE_HEADERS.items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=HOW_LONG_WE_WAIT) as response:
            return True, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as problem:
        return False, f"BSE answered HTTP {problem.code}"
    except urllib.error.URLError as problem:
        return False, f"could not reach BSE: {problem.reason}"
    except ValueError:
        return False, "BSE sent something that was not JSON"
    except Exception as problem:  # noqa: BLE001
        return False, f"unexpected trouble reaching BSE: {problem}"


def _bse_scrip_code(symbol: str) -> str | None:
    """Resolve an NSE-style ticker to its BSE numeric scrip code, cached in
    ref_cache for 30 days (the mapping is effectively permanent)."""
    sym = normalize_symbol(symbol)
    key = f"bse_scrip_code:{sym}"
    try:
        with connect() as db:
            row = db.execute(
                "SELECT payload, fetched_at FROM ref_cache WHERE key = ?", (key,)
            ).fetchone()
        if row:
            age = datetime.now() - datetime.fromisoformat(row["fetched_at"])
            if age.days < 30:
                return json.loads(row["payload"]) or None
    except (ValueError, TypeError, sqlite3.Error):
        pass  # cache miss / unreadable / busy — fall through to a live lookup
    ok, body = _bse_get(
        f"{_BSE_BASE}/PeerSmartSearch/w?Type=SS&text={urllib.parse.quote(sym)}"
    )
    code = None
    if ok and isinstance(body, str):
        # body is an HTML <li> blob: liclick('544387','DESCO INFRATECH LTD')
        for hit_code, _name in re.findall(r"liclick\('(\d+)','([^']*)'\)", body):
            code = hit_code
            break
    try:  # best-effort — a locked DB must not sink the quote
        with connect() as db:
            db.execute(
                "INSERT INTO ref_cache(key, payload, fetched_at) VALUES (?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET payload=excluded.payload, "
                "fetched_at=excluded.fetched_at",
                (key, json.dumps(code),
                 datetime.now().isoformat(timespec="seconds")),
            )
            db.commit()
    except sqlite3.Error:
        pass
    return code


def get_bse_price(symbol: str) -> dict:
    """Fallback quote straight from BSE — the only source that carries the
    SME board, where Yahoo has neither a .NS nor a .BO line."""
    code = _bse_scrip_code(symbol)
    if not code:
        return {"has_data": False, "symbol": symbol, "where_from": "bseindia",
                "note": "no BSE scrip code for this ticker"}
    ok, body = _bse_get(
        f"{_BSE_BASE}/getScripHeaderData/w?Quotetype=EQ&scripcode={code}"
    )
    if not ok or not isinstance(body, dict):
        return {"has_data": False, "symbol": symbol, "where_from": "bseindia",
                "note": body if isinstance(body, str) else "BSE sent no quote"}
    raw = ((body.get("CurrRate") or {}).get("LTP")
           or (body.get("Header") or {}).get("LTP")
           or (body.get("Header") or {}).get("PrevClose"))
    try:
        price = float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return {"has_data": False, "symbol": symbol, "where_from": "bseindia",
                "note": "BSE quote had no usable price"}
    if price <= 0:
        return {"has_data": False, "symbol": symbol, "where_from": "bseindia",
                "note": "BSE shows no trade (SME scrips are often circuit-locked)"}
    return {
        "has_data": True,
        "symbol": symbol,
        "price": price,
        "currency": "INR",
        "source": f"bseindia:{code}",
        "as_of": (body.get("Header") or {}).get("Ason"),
        "cached": False,
    }


def _amfi_navall_text(today: date | None = None) -> tuple[bool, str]:
    today = today or date.today()
    stamp = today.strftime("%Y%m%d")
    path = CACHE_DIR / f"amfi_navall_{stamp}.txt"
    if path.exists():
        try:
            return True, path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    request = urllib.request.Request(
        "https://www.amfiindia.com/spages/NAVAll.txt", method="GET"
    )
    request.add_header("User-Agent", "INKY/1.0 (personal finance screen)")
    _emit_fetch("fetch_attempted", SOURCE_AMFI)
    try:
        with urllib.request.urlopen(request, timeout=HOW_LONG_WE_WAIT) as response:
            text = response.read().decode("utf-8", errors="replace")
    except Exception as problem:
        _emit_fetch("fetch_failed", SOURCE_AMFI,
                    error=f"could not reach amfiindia.com: {problem}"[:300])
        return False, f"could not reach amfiindia.com: {problem}"
    if "Scheme Code" not in text[:2000] and ";" not in text[:2000]:
        _emit_fetch("fetch_failed", SOURCE_AMFI,
                    error="amfiindia.com answered with something that is not NAVAll.txt"[:300])
        return False, "amfiindia.com answered with something that is not NAVAll.txt"
    for old in CACHE_DIR.glob("amfi_navall_*.txt"):
        if old.name != path.name:
            try:
                old.unlink()
            except OSError:
                pass
    path.write_text(text, encoding="utf-8")
    _emit_fetch("fetch_succeeded", SOURCE_AMFI,
                data_as_of=f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}", items=1)
    return True, text


def _amfi_latest_nav(amfi_code: str, today: date | None = None) -> dict:
    worked, text = _amfi_navall_text(today)
    if not worked:
        return {"has_data": False, "where_from": "amfiindia.com", "note": text}
    code = (amfi_code or "").strip()
    best = None
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6 or parts[0] != code:
            continue
        raw_nav, raw_date = parts[-2], parts[-1]
        if not raw_nav or not raw_date:
            continue
        try:
            nav_value = float(raw_nav)
        except ValueError:
            continue
        published = None
        for shape in ("%d-%b-%Y", "%d-%m-%Y", "%d-%B-%Y"):
            try:
                published = datetime.strptime(raw_date, shape).date()
                break
            except ValueError:
                continue
        row = {
            "scheme_name": parts[3],
            "nav": nav_value,
            "nav_date": published.isoformat() if published else raw_date,
        }
        best = row
    if best is None:
        return {
            "has_data": False,
            "where_from": "amfiindia.com",
            "note": f"scheme code {code} is not in today's NAVAll.txt",
        }
    return {
        "has_data": True,
        "amfi_code": amfi_code,
        "scheme_name": best["scheme_name"],
        "fund_house": "",
        "nav": best["nav"],
        "nav_date": best["nav_date"],
        "where_from": "amfiindia.com NAVAll.txt",
    }


def latest_nav(amfi_code: str) -> dict:
    worked, payload = _get(f"https://api.mfapi.in/mf/{amfi_code}/latest")
    if not worked:
        fallback = _amfi_latest_nav(amfi_code)
        if fallback.get("has_data"):
            return fallback
        return {
            "has_data": False,
            "amfi_code": amfi_code,
            "where_from": "mfapi.in + amfiindia.com",
            "note": f"{payload}; AMFI fallback also failed: {fallback.get('note')}",
        }
    entries = payload.get("data") or []
    if not entries:
        return {
            "has_data": False,
            "amfi_code": amfi_code,
            "where_from": "mfapi.in",
            "note": "the service knows this code but published no NAV",
        }
    return {
        "has_data": True,
        "amfi_code": amfi_code,
        "scheme_name": (payload.get("meta") or {}).get("scheme_name", ""),
        "fund_house": (payload.get("meta") or {}).get("fund_house", ""),
        "nav": float(entries[0]["nav"]),
        "nav_date": entries[0]["date"],
        "where_from": "mfapi.in",
    }


def nav_history(amfi_code: str, days: int | None = None) -> dict:
    worked, payload = _get(f"https://api.mfapi.in/mf/{amfi_code}")
    if not worked:
        return {
            "has_data": False,
            "amfi_code": amfi_code,
            "where_from": "mfapi.in",
            "note": payload,
        }
    entries = payload.get("data") or []
    points = [{"date": row["date"], "nav": float(row["nav"])} for row in entries]
    if days is not None:
        points = points[:days]
    return {
        "has_data": bool(entries),
        "amfi_code": amfi_code,
        "scheme_name": (payload.get("meta") or {}).get("scheme_name", ""),
        "points": points,
        "where_from": "mfapi.in",
    }


def find_a_scheme(name_fragment: str) -> dict:
    worked, payload = _get(
        f"https://api.mfapi.in/mf/search?q={urllib.parse.quote(name_fragment)}"
    )
    if not worked:
        return {"has_data": False, "where_from": "mfapi.in", "note": payload}
    return {
        "has_data": bool(payload),
        "where_from": "mfapi.in",
        "matches": [
            {"amfi_code": row.get("schemeCode"), "name": row.get("schemeName")}
            for row in (payload or [])[:25]
        ],
    }


def normalize_symbol(symbol: str, asset_type: str | None = None) -> str:
    return (symbol or "").strip().upper().replace(" ", "")


def get_last_cached_price(symbol: str, *, now: date | None = None) -> dict | None:
    now = now or date.today()
    with connect() as db:
        row = db.execute(
            "SELECT price, currency, source, date FROM price_history "
            "WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            (normalize_symbol(symbol),),
        ).fetchone()
    if row:
        as_of = row["date"]
        age_days = (now - date.fromisoformat(as_of)).days
        return {
            "has_data": True,
            "symbol": symbol,
            "price": row["price"],
            "currency": row["currency"],
            "source": row["source"],
            "cached": True,
            "as_of": as_of,
            "age_days": age_days,
            "stale": age_days > 2,
        }
    return None


def _yahoo_symbol(symbol: str) -> str:
    """Yahoo lists NSE equities under '<SYMBOL>.NS'. A bare ticker only
    resolves for indices (^NSEI) and FX pairs (USDINR=X), which carry
    their own prefixes — leave those untouched."""
    sym = normalize_symbol(symbol)
    if "." in sym or sym.startswith("^") or sym.endswith("=X"):
        return sym
    return f"{sym}.NS"


def get_stock_price(symbol: str) -> dict:
    cached = get_last_cached_price(symbol)
    try:
        import yfinance
    except ImportError:
        # No Yahoo client — BSE's own API still answers (and it's the only
        # source for the SME board anyway).
        bse = get_bse_price(symbol)
        if bse.get("has_data"):
            return bse
        if cached:
            return cached
        return {
            "has_data": False,
            "symbol": symbol,
            "where_from": "bseindia",
            "note": bse.get("note") or "yfinance not installed",
        }

    try:
        sym = normalize_symbol(symbol)
        # .NS (NSE) first, then the bare ticker, then .BO — Yahoo lists BSE
        # equities, including most of the SME board, under '<SYMBOL>.BO'.
        cands = [_yahoo_symbol(symbol), sym]
        if "." not in sym:
            cands.append(f"{sym}.BO")
        info = None
        for cand in cands:
            try:
                info = yfinance.Ticker(cand).info or {}
            except Exception:  # noqa: BLE001
                info = None
            if info and (info.get("regularMarketPrice") or info.get("previousClose")):
                break
        if not info:
            info = {}
        price = info.get("regularMarketPrice") or info.get("previousClose")
        if price is None:
            # Yahoo carries neither board for this ticker — ask BSE directly.
            bse = get_bse_price(symbol)
            if bse.get("has_data"):
                return bse
            if cached:
                return cached
            return {
                "has_data": False,
                "symbol": symbol,
                "where_from": "yfinance+bseindia",
                "note": bse.get("note") or "no price found",
            }
        return {
            "has_data": True,
            "symbol": symbol,
            "price": float(price),
            "currency": "INR",
            "source": "yfinance",
            "cached": False,
        }
    except Exception as e:
        bse = get_bse_price(symbol)
        if bse.get("has_data"):
            return bse
        if cached:
            return cached
        return {
            "has_data": False,
            "symbol": symbol,
            "where_from": "yfinance+bseindia",
            "note": str(e),
        }


def stock_history(symbol: str, days: int = 90) -> dict:
    try:
        import yfinance
    except ImportError:
        return {
            "has_data": False,
            "where_from": "yfinance",
            "note": "yfinance not installed",
        }
    try:
        hist = yfinance.Ticker(_yahoo_symbol(symbol)).history(period=f"{days}d")
        if hist.empty:
            return {
                "has_data": False,
                "symbol": symbol,
                "where_from": "yfinance",
                "note": "no history",
            }
        points = [
            {"date": idx.strftime("%Y-%m-%d"), "price": float(row["Close"])}
            for idx, row in hist.iterrows()
        ]
        return {
            "has_data": True,
            "symbol": symbol,
            "points": points,
            "where_from": "yfinance",
        }
    except Exception as e:
        return {
            "has_data": False,
            "symbol": symbol,
            "where_from": "yfinance",
            "note": str(e),
        }


def get_current_price(symbol: str, asset_type: str) -> dict:
    sym = normalize_symbol(symbol)
    if asset_type in ("mutual_fund", "etf"):
        res = latest_nav(sym)
        if res.get("has_data"):
            return {
                "has_data": True,
                "symbol": sym,
                "price": res["nav"],
                "currency": "INR",
                "source": res["where_from"],
                "cached": False,
            }
    elif asset_type in ("stock", "equity"):
        return get_stock_price(sym)

    cached = get_last_cached_price(sym)
    if cached:
        return cached
    return {
        "has_data": False,
        "symbol": sym,
        "where_from": "none",
        "note": "no data and no cache",
    }


def _source_of(name: str | None) -> str | None:
    name = (name or "").lower()
    if "mfapi" in name:
        return SOURCE_MFAPI
    if "amfi" in name:
        return SOURCE_AMFI
    if "yfinance" in name:
        return SOURCE_YF
    if "bse" in name:
        return SOURCE_BSE
    return None


def batch_refresh(symbols: list[str], budget_s: int = 120) -> dict:
    results: dict[str, float | None] = {}
    failures: list[dict] = []
    start = time.time()
    tallies: dict[str, dict] = {}

    def _tally(source: str) -> dict:
        # First mark of a source is its fetch_attempted: emitted before the
        # source's first request where this function drives it, and lazily
        # when the request happens inside a primitive this file cannot wrap.
        if source not in tallies:
            tallies[source] = {"ok": 0, "failed": 0, "dates": [], "first_error": None}
            _emit_fetch("fetch_attempted", source)
        return tallies[source]

    spine_failure = None
    with connect() as db:
        for sym in symbols:
            if time.time() - start > budget_s:
                break
            try:
                res = get_current_price(sym, "stock")
                # A cached hit is not a quote: yfinance 404s on every AMFI code, so
                # without this the NAV feed is never consulted once any history
                # exists, and the stale cached price gets re-stamped as today.
                if not res.get("has_data") or res.get("cached"):
                    mfapi = _tally(SOURCE_MFAPI)  # latest_nav's first request is mfapi
                    nav = latest_nav(sym)
                    if nav.get("has_data"):
                        mfapi["ok"] += 1
                        if nav.get("nav_date"):
                            mfapi["dates"].append(nav["nav_date"])
                        res = {
                            "has_data": True,
                            "price": nav["nav"],
                            "currency": "INR",
                            "source": nav["where_from"],
                            # AMFI/mfapi publish with a lag — keep the NAV's own date
                            "quote_date": nav.get("nav_date"),
                        }
                    elif not res.get("has_data"):
                        res = nav

                if res.get("has_data"):
                    results[sym] = res["price"]
                    if res.get("cached"):
                        continue  # nothing new to record
                    try:
                        # Stamping every quote "today" would fabricate a fresh point
                        # on a stale NAV, and a duplicate price makes the day change
                        # read a false 0.00. Store the quote under its own date.
                        quote_date = _iso_date(res.get("quote_date") or "") or date.today().isoformat()
                        db.execute(
                            "INSERT OR IGNORE INTO price_history "
                            "(symbol, date, price, source, currency) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (
                                normalize_symbol(sym),
                                quote_date,
                                res["price"],
                                res.get("source", "unknown"),
                                res.get("currency", "INR"),
                            ),
                        )
                    except Exception as exc:
                        print(f"price_history insert failed for {sym}: {exc}",
                              file=sys.stderr)
                        failures.append({"symbol": sym, "note": f"insert failed: {exc}"})
                    else:
                        source_name = _source_of(res.get("source"))
                        if source_name:
                            tally = _tally(source_name)
                            tally["ok"] += 1
                            tally["dates"].append(quote_date)
                else:
                    results[sym] = None
                    note = res.get("note", "unknown error")
                    failures.append({"symbol": sym, "note": note})
                    source_name = _source_of(res.get("where_from") or res.get("source"))
                    if source_name:
                        tally = _tally(source_name)
                        tally["failed"] += 1
                        if tally["first_error"] is None:
                            tally["first_error"] = note
            except spine.SpineWriteError as exc:
                # Data first, then the record: the failure re-raises after commit.
                spine_failure = exc
                break
        db.commit()

    for source, tally in tallies.items():
        if tally["ok"] >= 1:
            data_as_of = max(tally["dates"]) if tally["dates"] else None
            _emit_fetch("fetch_succeeded", source,
                        data_as_of=data_as_of, items=tally["ok"])
        else:
            _emit_fetch("fetch_failed", source,
                        error=(tally["first_error"] or "no successful request")[:300])
    if spine_failure is not None:
        raise spine_failure
    return {"prices": results, "failures": failures}


_ISIN_RE = re.compile(r"^INF[0-9A-Z]{9}$")


def is_isin(symbol: str) -> bool:
    return bool(_ISIN_RE.match(normalize_symbol(symbol)))


def backfill_benchmark(symbol: str = "^NSEI", years: int = 5) -> dict:
    """Pull a benchmark index's daily closes into price_history so every
    portfolio-vs-benchmark draw reads the local ledger, never a live call."""
    res = stock_history(symbol, years * 366)
    if not res.get("has_data"):
        return {"state": "pending", "note": res.get("note")}
    with connect() as db:
        for p in res["points"]:
            db.execute(
                "INSERT OR IGNORE INTO price_history "
                "(symbol, date, price, source, currency) VALUES (?, ?, ?, ?, ?)",
                (normalize_symbol(symbol), p["date"], p["price"],
                 "yfinance", "INR"),
            )
        db.commit()
    return {"state": "ok", "symbol": symbol, "rows": len(res["points"])}


def usd_inr() -> dict:
    """The rupee's dollar price — the one FX rate the global planner needs."""
    return get_stock_price("USDINR=X")


def _amfi_row_by_isin(isin: str, today: date | None = None) -> dict | None:
    """Resolve a listed ETF held by ISIN to its AMFI NAVAll row (the file
    carries the ISIN column, so no hard-coded symbol map is needed)."""
    worked, text = _amfi_navall_text(today)
    if not worked:
        return None
    target = normalize_symbol(isin)
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 6:
            continue
        if target in (parts[1], parts[2]):
            try:
                nav_value = float(parts[-2])
            except (TypeError, ValueError):
                continue
            return {
                "scheme_code": parts[0],
                "scheme_name": parts[3],
                "nav": nav_value,
                "nav_date": parts[-1],
            }
    return None


def history_for(symbol: str, asset_type: str | None, days: int | None = None) -> dict:
    """Real historical price points for one holding symbol. Mutual funds go to
    mfapi by AMFI code; ISIN-coded listed ETFs resolve through the AMFI file to
    their scheme code first; anything else tries yfinance as a last resort."""
    sym = normalize_symbol(symbol)
    if asset_type in ("mutual_fund", "etf") or is_isin(sym):
        code = sym
        if is_isin(sym) or asset_type == "etf":
            row = _amfi_row_by_isin(sym) if is_isin(sym) else None
            if row and row["scheme_code"].isdigit():
                code = row["scheme_code"]
            elif asset_type == "etf":
                # ETF whose symbol is neither an AMFI code nor a resolvable ISIN
                return stock_history(sym if not is_isin(sym) else sym, days=days or 180)
        res = nav_history(code, days=days)
        if res.get("has_data"):
            return {
                "has_data": True,
                "symbol": sym,
                "points": [
                    {"date": _iso_date(p["date"]), "price": p["nav"]}
                    for p in res["points"]
                ],
                "where_from": res["where_from"],
            }
        if res.get("note"):
            return {"has_data": False, "symbol": sym, "where_from": res["where_from"],
                    "note": res["note"]}
    return stock_history(sym, days=days or 180)


def _iso_date(raw: str) -> str:
    """mfapi dates look like '18-Aug-2026' -> ISO; ISO input passes through."""
    for shape in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(raw).strip(), shape).date().isoformat()
        except ValueError:
            continue
    return str(raw)[:10]


def refresh_holdings(budget_s: int = 120, with_history: bool = False) -> dict:
    """Refresh latest prices for every active holding (optionally pulling real
    history first). One entry point for the market router and the nightly job."""
    with connect() as db:
        rows = db.execute(
            "SELECT symbol, COALESCE(type,'') AS type FROM active_holdings"
        ).fetchall()
    symbols = [r["symbol"] for r in rows]
    types = {r["symbol"]: r["type"] for r in rows}

    history: dict[str, int] = {}
    if with_history:
        start = time.time()
        with connect() as db:
            for sym in symbols:
                if time.time() - start > budget_s:
                    break
                res = history_for(sym, types.get(sym))
                added = 0
                if res.get("has_data"):
                    for p in res["points"]:
                        try:
                            cur = db.execute(
                                "INSERT OR IGNORE INTO price_history "
                                "(symbol, date, price, source, currency) VALUES (?,?,?,?,?)",
                                (sym, p["date"], float(p["price"]),
                                 res.get("where_from", "history"), "INR"),
                            )
                            added += cur.rowcount or 0
                        except Exception:
                            continue
                db.commit()
                history[sym] = added

    out = batch_refresh(symbols, budget_s=budget_s)
    out["history_rows"] = history
    return out