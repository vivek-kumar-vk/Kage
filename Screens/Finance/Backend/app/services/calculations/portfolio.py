"""Portfolio calculations for the Investments tab. Every function takes an open
sqlite3 connection (row_factory = Row) and returns JSON-safe dicts/lists.

All value math reads the `active_holdings` view. Unpriceable assets (bond / other,
or a symbol with no price_history row) are EXCLUDED from value totals and flagged
via `priced`, never counted as 0.  [J/M][P]

Time-series endpoints return an explicit state discriminator:
  {"state": "ok"    , ...}  full series available
  {"state": "partial", ...}  some history, less than the requested window
  {"state": "pending", ...}  no price history yet (backfill has not run)
"""
from __future__ import annotations

_UNPRICEABLE_TYPES = ("bond", "other")


def _latest_price_map(conn) -> dict[str, float]:
    rows = conn.execute("SELECT symbol, price FROM latest_prices").fetchall()
    return {r["symbol"]: float(r["price"]) for r in rows if r["price"] is not None}


def _lots_count(conn, holding_id: int) -> int:
    r = conn.execute(
        "SELECT COUNT(*) FROM lots WHERE holding_id = ?", (holding_id,)
    ).fetchone()
    return int(r[0]) if r else 0


def holdings_with_value(conn) -> list[dict]:
    prices = _latest_price_map(conn)
    out: list[dict] = []
    for h in conn.execute("SELECT * FROM active_holdings ORDER BY symbol").fetchall():
        sym = h["symbol"]
        htype = (h["type"] or "").lower()
        units = float(h["units"] or 0.0)
        avg_cost = float(h["avg_cost"] or 0.0)
        priceable = htype not in _UNPRICEABLE_TYPES and sym in prices
        price = prices.get(sym)
        value = round(units * price, 2) if priceable else None
        invested = round(units * avg_cost, 2)
        out.append(
            {
                "id": h["id"],
                "account_id": h["account_id"],
                "symbol": sym,
                "name": h["name"],
                "type": h["type"],
                "units": units,
                "avg_cost": avg_cost,
                "invested": invested,
                "price": price if priceable else None,
                "value": value,
                "gain_loss": round(value - invested, 2) if value is not None else None,
                "priced": priceable,
                "lots_count": _lots_count(conn, h["id"]),
                "direct_regular": h["direct_regular"] if "direct_regular" in h.keys() else "regular",
                "folio": h["folio"] if "folio" in h.keys() else None,
            }
        )
    total = sum(x["value"] for x in out if x["value"] is not None)
    for x in out:
        x["weight"] = round(x["value"] / total, 4) if (x["value"] and total) else 0.0
    return out


def portfolio_summary(conn) -> dict:
    rows = holdings_with_value(conn)
    priced = [r for r in rows if r["value"] is not None]
    value = round(sum(r["value"] for r in priced), 2)
    invested = round(sum(r["invested"] for r in priced), 2)
    return {
        "total_value": value,
        "invested": invested,
        "gain_loss": round(value - invested, 2),
        "holdings": len(rows),
        "unpriced": [r["symbol"] for r in rows if r["value"] is None],
    }


def _portfolio_value_series(conn) -> list[tuple[str, float]]:
    """Daily portfolio value = sum over holdings of units * price_on_that_date.

    Funds publish NAVs on different lags; summing only same-date prices
    makes the whole portfolio dip on any day one fund is missing — a fake
    drawdown that then corrupts volatility and Sharpe. So each fund rides
    on its own LAST KNOWN price between publications, in memory only.
    Nothing is written back: the ledger keeps only published rows (D13.3/
    FD6 — a carried price is never stamped as a quote).
    """
    rows = conn.execute(
        """
        SELECT ph.symbol AS s, ph.date AS d, ph.price AS p, ah.units AS u
        FROM price_history ph
        JOIN active_holdings ah ON ah.symbol = ph.symbol
        WHERE COALESCE(ah.type,'') NOT IN ('bond','other')
        ORDER BY ph.date ASC
        """
    ).fetchall()
    series_by_sym: dict[str, list[tuple[str, float]]] = {}
    units: dict[str, float] = {}
    for r in rows:
        series_by_sym.setdefault(r["s"], []).append((r["d"], float(r["p"])))
        units[r["s"]] = float(r["u"] or 0.0)
    all_dates = sorted({r["d"] for r in rows})
    if not all_dates:
        return []
    # pointer sweep: each fund's latest published price up to each date
    out: list[tuple[str, float]] = []
    idx = {s: 0 for s in series_by_sym}
    last = {s: None for s in series_by_sym}
    for d in all_dates:
        total = 0.0
        for s, pts in series_by_sym.items():
            i = idx[s]
            while i < len(pts) and pts[i][0] <= d:
                last[s] = pts[i][1]
                i += 1
            idx[s] = i
            if last[s] is not None:
                total += units[s] * last[s]
        out.append((d, total))
    return out


def rolling_returns(conn, window_days: int = 30) -> dict:
    series = _portfolio_value_series(conn)
    if not series:
        return {"state": "pending", "window_days": window_days, "series": []}
    if len(series) <= window_days:
        return {"state": "partial", "window_days": window_days, "series": []}
    out = []
    for i in range(window_days, len(series)):
        d, v = series[i]
        _, v0 = series[i - window_days]
        ret = (v / v0 - 1.0) if v0 else 0.0
        out.append({"date": d, "return": round(ret, 6)})
    return {"state": "ok", "window_days": window_days, "series": out}


def drawdown(conn) -> dict:
    series = _portfolio_value_series(conn)
    if not series:
        return {"state": "pending", "series": []}
    peak = series[0][1] or 0.0
    out = []
    for d, v in series:
        peak = max(peak, v)
        dd = (v / peak - 1.0) if peak else 0.0
        out.append({"date": d, "drawdown": round(dd, 6)})
    state = "ok" if len(series) > 1 else "partial"
    return {"state": state, "max_drawdown": round(min(x["drawdown"] for x in out), 6),
            "series": out}


def portfolio_vs_benchmark(conn) -> dict:
    series = _portfolio_value_series(conn)
    if not series:
        return {"state": "pending", "portfolio": [], "benchmark": []}
    base = series[0][1] or 1.0
    port = [{"date": d, "index": round((v / base) * 100.0, 4)} for d, v in series]
    bench_rows = conn.execute(
        """
        SELECT ph.date AS d, ph.price AS p
        FROM price_history ph
        JOIN benchmarks b ON b.symbol = ph.symbol
        ORDER BY ph.date ASC
        """
    ).fetchall()
    if bench_rows:
        b0 = float(bench_rows[0]["p"] or 1.0)
        bench = [{"date": r["d"], "index": round((float(r["p"]) / b0) * 100.0, 4)}
                 for r in bench_rows]
        return {"state": "ok", "portfolio": port, "benchmark": bench}
    return {"state": "partial", "portfolio": port, "benchmark": []}


def asset_allocation(conn) -> dict:
    rows = holdings_with_value(conn)
    buckets: dict[str, float] = {}
    for r in rows:
        if r["value"] is None:
            continue
        key = (r["type"] or "unknown").lower()
        buckets[key] = buckets.get(key, 0.0) + r["value"]
    total = sum(buckets.values())
    return {
        "state": "ok" if buckets else "pending",
        "allocation": [
            {"bucket": k, "value": round(v, 2),
             "weight": round(v / total, 4) if total else 0.0}
            for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])
        ],
    }


def concentration(conn) -> dict:
    rows = [r for r in holdings_with_value(conn) if r["value"] is not None]
    if not rows:
        return {"state": "pending", "top5_weight": 0.0, "holdings": []}
    rows.sort(key=lambda r: -r["value"])
    total = sum(r["value"] for r in rows)
    top5 = sum(r["value"] for r in rows[:5])
    return {
        "state": "ok",
        "top5_weight": round(top5 / total, 4) if total else 0.0,
        "holdings": [{"symbol": r["symbol"], "weight": r["weight"]} for r in rows],
    }
