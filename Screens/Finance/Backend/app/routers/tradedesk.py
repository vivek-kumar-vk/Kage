"""Trade Desk endpoints — the four segments of the tab:
  WATCHLIST  tracked names with a live quote
  JOURNAL    swing trades (delivery, never intraday) with per-trade
             capital-gains buckets on close
  IPO        the calendar (groww.in/ipo, cached 24 h) + your own
             UPI-ASBA checklist columns
  GLOBAL     the LRS/TCS math for international investing

Rules this file keeps: a trade is journal of RECORD — closes are
append-style updates (exit price/date), never a rewrite of history; CG
rates come from the tax rulebook file, flagged with its own
verified_by_a_person; the IPO calendar is displayed exactly as
published, and applying is recorded as a checkbox, never advice. [P]
"""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Body, HTTPException

from services import ipo_calendar, market_data
from services.db import connect
from services.reference import load as _load

router = APIRouter()

TAX = (_load("india_income_tax_rules") or {}).get("capital_gains") or {}
_EQ = TAX.get("listed_equity_and_equity_mutual_funds") or {}
_LT_MONTHS = int(_EQ.get("long_term_after_months", 12))
_STCG_PCT = _EQ.get("stcg_rate_pct", 20.0)
_LTCG_PCT = _EQ.get("ltcg_rate_pct", 12.5)
_LTCG_EXEMPTION = float(_EQ.get("ltcg_annual_exemption", 125000.0))

# LRS / TCS constants — RBI LRS ceiling and the TCS rate on overseas
# remittances for investment purposes (Finance Act 2024). Informational
# maths, not tax advice; the UI carries the source and date.
LRS_LIMIT_USD = 250_000
TCS_THRESHOLD_RS = 1_000_000
TCS_RATE_PCT = 20.0


def _dict(row):
    return {k: row[k] for k in row.keys()}


# ---------------------------------------------------------------- watchlist
@router.get("/tradedesk/watchlist")
def watchlist():
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM watchlist WHERE archived_at IS NULL "
            "ORDER BY added_at DESC").fetchall()
    out = []
    for row in rows:
        item = _dict(row)
        quote = market_data.get_current_price(item["symbol"], "stock")
        item["price"] = quote.get("price")
        item["price_source"] = quote.get("source")
        item["priced"] = bool(quote.get("has_data"))
        out.append(item)
    return {"state": "ok" if out else "pending", "items": out,
            "reason": None if out else "the watchlist is empty"}


@router.post("/tradedesk/watchlist")
def add_watchlist(payload: dict = Body(default={})):
    symbol = market_data.normalize_symbol((payload or {}).get("symbol") or "")
    if not symbol:
        raise HTTPException(status_code=422, detail="symbol is required")
    with connect() as db:
        dup = db.execute("SELECT 1 FROM watchlist WHERE symbol = ?", (symbol,)).fetchone()
        if dup:
            raise HTTPException(status_code=409, detail=f"{symbol} is already on the watchlist")
        db.execute(
            "INSERT INTO watchlist(symbol, name, asset_type, notes) VALUES (?,?,?,?)",
            (symbol, payload.get("name"), payload.get("asset_type") or "stock",
             payload.get("notes")))
        db.commit()
    return {"state": "ok", "symbol": symbol}


@router.put("/tradedesk/watchlist/{wid}")
def update_watchlist(wid: int, payload: dict = Body(default={})):
    allowed = {"name", "notes", "asset_type"}
    sets = {k: v for k, v in (payload or {}).items() if k in allowed}
    with connect() as db:
        if not db.execute("SELECT 1 FROM watchlist WHERE id = ?", (wid,)).fetchone():
            raise HTTPException(status_code=404, detail="watchlist item not found")
        if sets:
            cols = ", ".join(f"{k} = ?" for k in sets)
            db.execute(f"UPDATE watchlist SET {cols} WHERE id = ?",
                       (*sets.values(), wid))
            db.commit()
    return {"state": "ok", "id": wid}


@router.delete("/tradedesk/watchlist/{wid}")
def delete_watchlist(wid: int):
    with connect() as db:
        if not db.execute("SELECT 1 FROM watchlist WHERE id = ?", (wid,)).fetchone():
            raise HTTPException(status_code=404, detail="watchlist item not found")
        db.execute("DELETE FROM watchlist WHERE id = ?", (wid,))
        db.commit()
    return {"state": "ok", "deleted": wid}


# ---------------------------------------------------------------- journal
def _trade_view(row) -> dict:
    t = _dict(row)
    if t.get("exit_price") is not None and t.get("exit_date"):
        gross = (float(t["exit_price"]) - float(t["entry_price"])) * float(t["qty"])
        net = gross - float(t["charges"] or 0)
        entry = datetime.strptime(t["entry_date"], "%Y-%m-%d").date()
        exit_d = datetime.strptime(t["exit_date"], "%Y-%m-%d").date()
        months = (exit_d.year - entry.year) * 12 + exit_d.month - entry.month
        long_term = months >= _LT_MONTHS
        t["status"] = "closed"
        t["pnl"] = round(net, 2)
        t["cg_bucket"] = "ltcg" if long_term else "stcg"
        t["holding_days"] = (exit_d - entry).days
        rate = _LTCG_PCT if long_term else _STCG_PCT
        t["est_tax_rs"] = round(max(0.0, net) * rate / 100.0, 2)
        t["cg_rate_pct"] = rate
    else:
        t["status"] = "open"
        t["pnl"] = None
        t["cg_bucket"] = None
        t["est_tax_rs"] = None
    return t


@router.get("/tradedesk/trades")
def list_trades():
    with connect() as db:
        rows = db.execute("SELECT * FROM trades ORDER BY entry_date DESC, id DESC").fetchall()
    trades = [_trade_view(r) for r in rows]
    realized_st = sum(t["pnl"] for t in trades
                      if t["status"] == "closed" and t["cg_bucket"] == "stcg")
    realized_lt = sum(t["pnl"] for t in trades
                      if t["status"] == "closed" and t["cg_bucket"] == "ltcg")
    lt_taxable = max(0.0, realized_lt - _LTCG_EXEMPTION)
    return {
        "state": "ok" if trades else "pending",
        "trades": trades,
        "summary": {
            "open": sum(1 for t in trades if t["status"] == "open"),
            "closed": sum(1 for t in trades if t["status"] == "closed"),
            "realized_stcg": round(realized_st, 2),
            "realized_ltcg": round(realized_lt, 2),
            "ltcg_exemption_rs": _LTCG_EXEMPTION,
            "est_tax_rs": round(max(0.0, realized_st) * _STCG_PCT / 100.0
                                + lt_taxable * _LTCG_PCT / 100.0, 2),
            "rates_as_of": (_load("india_income_tax_rules") or {}).get("as_of"),
            "verified_by_a_person":
                (_load("india_income_tax_rules") or {}).get("verified_by_a_person", False),
        },
        "reason": None if trades else "no trades journalled yet",
    }


@router.post("/tradedesk/trades")
def add_trade(payload: dict = Body(default={})):
    required = ("symbol", "qty", "entry_price", "entry_date")
    missing = [k for k in required if not (payload or {}).get(k)]
    if missing:
        raise HTTPException(status_code=422, detail=f"missing: {', '.join(missing)}")
    with connect() as db:
        cur = db.execute(
            "INSERT INTO trades(symbol, name, asset_type, exchange, qty, entry_price, "
            "entry_date, charges, thesis, notes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (market_data.normalize_symbol(payload["symbol"]), payload.get("name"),
             payload.get("asset_type") or "stock", payload.get("exchange") or "NSE",
             float(payload["qty"]), float(payload["entry_price"]),
             str(payload["entry_date"]), float(payload.get("charges") or 0),
             payload.get("thesis"), payload.get("notes")))
        db.commit()
        tid = cur.lastrowid
    return {"state": "ok", "id": tid}


@router.put("/tradedesk/trades/{tid}/close")
def close_trade(tid: int, payload: dict = Body(default={})):
    exit_price = (payload or {}).get("exit_price")
    exit_date = (payload or {}).get("exit_date") or date.today().isoformat()
    if exit_price is None:
        raise HTTPException(status_code=422, detail="exit_price is required")
    try:
        datetime.strptime(str(exit_date), "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=422, detail="exit_date must be YYYY-MM-DD")
    with connect() as db:
        row = db.execute("SELECT * FROM trades WHERE id = ?", (tid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="trade not found")
        if row["exit_price"] is not None:
            raise HTTPException(status_code=409,
                                detail="trade already closed — the journal does not rewrite history")
        extra = ""
        params: list = [float(exit_price), str(exit_date)]
        if payload.get("exit_charges") is not None:
            extra = ", charges = charges + ?"
            params.append(float(payload["exit_charges"]))
        db.execute(f"UPDATE trades SET exit_price = ?, exit_date = ?{extra} "
                   f"WHERE id = ?", (*params, tid))
        db.commit()
    return {"state": "ok", "id": tid}


@router.delete("/tradedesk/trades/{tid}")
def delete_trade(tid: int):
    with connect() as db:
        if not db.execute("SELECT 1 FROM trades WHERE id = ?", (tid,)).fetchone():
            raise HTTPException(status_code=404, detail="trade not found")
        db.execute("DELETE FROM trades WHERE id = ?", (tid,))
        db.commit()
    return {"state": "ok", "deleted": tid}


# ---------------------------------------------------------------- IPO
@router.get("/tradedesk/ipo")
def ipo_list():
    calendar = ipo_calendar.fetch_calendar()
    with connect() as db:
        mine = {_dict(r)["name"]: _dict(r)
                for r in db.execute("SELECT * FROM ipos").fetchall()}
    for group in ("open", "upcoming", "closed"):
        for row in calendar.get(group) or []:
            mine_row = mine.get(row["name"])
            row["applied"] = bool(mine_row["applied"]) if mine_row else False
            row["upi_mandate"] = mine_row["upi_mandate"] if mine_row else None
            row["notes"] = mine_row["notes"] if mine_row else None
    return calendar


@router.post("/tradedesk/ipo/checklist")
def ipo_checklist(payload: dict = Body(default={})):
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    fields = {"applied": int(bool(payload.get("applied"))),
              "upi_mandate": payload.get("upi_mandate"),
              "notes": payload.get("notes")}
    sets = {k: v for k, v in fields.items() if v is not None}
    if not sets:
        raise HTTPException(status_code=422,
                            detail="nothing to update — send applied / upi_mandate / notes")
    with connect() as db:
        db.execute(
            f"INSERT INTO ipos(name, {', '.join(sets)}) VALUES (?, {', '.join('?' for _ in sets)}) "
            f"ON CONFLICT(name) DO UPDATE SET {', '.join(f'{k} = excluded.{k}' for k in sets)}, "
            f"updated_at = CURRENT_TIMESTAMP",
            (name, *sets.values()))
        db.commit()
    return {"state": "ok", "name": name}


# ---------------------------------------------------------------- global
@router.get("/tradedesk/global")
def global_planner(planned_inr: float | None = None):
    """The LRS/TCS math for a planned overseas investment. TCS is a
    collection at source, not a final tax — it is creditable against the
    year's income-tax and shows up in Form 26AS. The Nasdaq-100 note is
    structural: the RBI's $7bn overseas-MF cap for Indian funds has been
    frozen, so overseas exposure runs through listed ETFs instead."""
    fx = market_data.usd_inr()
    rate = fx.get("price")
    out = {
        "state": "ok" if rate else "pending",
        "usd_inr": rate,
        "fx_where_from": fx.get("source") or fx.get("where_from"),
        "lrs_limit_usd": LRS_LIMIT_USD,
        "lrs_limit_inr": round(LRS_LIMIT_USD * rate) if rate else None,
        "tcs": {"rate_pct": TCS_RATE_PCT,
                "threshold_rs": TCS_THRESHOLD_RS,
                "creditable_note": "TCS is not a lost rupee — it is advance "
                                   "tax creditable in the ITR (Form 26AS)"},
        "nasdaq_100_note": "the RBI's $7bn overseas-mutual-fund cap has been "
                           "frozen since 2022 — overseas index exposure runs "
                           "through listed ETFs (e.g. a NIFTY-beating Nasdaq-100 "
                           "ETF), and their price can sit at a premium to NAV; "
                           "the premium is a real cost",
        "reason": None if rate else "the FX rate could not be fetched",
    }
    if rate and planned_inr:
        planned_usd = planned_inr / rate
        tcs_payable = max(0.0, planned_inr - TCS_THRESHOLD_RS) * TCS_RATE_PCT / 100.0
        out["planned"] = {
            "inr": planned_inr,
            "usd": round(planned_usd, 2),
            "within_lrs": planned_usd <= LRS_LIMIT_USD,
            "tcs_payable_rs": round(tcs_payable, 2),
            "tcs_applies": planned_inr > TCS_THRESHOLD_RS,
            "total_cash_needed_rs": round(planned_inr + tcs_payable, 2),
            "note": "the threshold is per financial year across ALL your LRS "
                    "remittances, not per investment — V1 does not track your "
                    "prior remittances, so this assumes none so far",
        }
    return out
