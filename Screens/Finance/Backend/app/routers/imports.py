"""Import endpoints. Heavy work (price backfill) is scheduled as a BackgroundTask
— never run inline in the request."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from services.calculations.backfill import backfill_price_history
from services.calculations.holdings_upsert import upsert_holding
from services.db import connect
from services.imports.cas import parse_cas
from services.imports.groww import parse_groww_csv

router = APIRouter()


def _account(db, name, atype):
    row = db.execute("SELECT id FROM accounts WHERE name=?", (name,)).fetchone()
    if row:
        return row["id"]
    return db.execute("INSERT INTO accounts(name,type) VALUES (?,?)", (name, atype)).lastrowid


@router.post("/import/groww-csv")
async def import_groww_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    rows = parse_groww_csv(await file.read())
    if not rows:
        raise HTTPException(status_code=422, detail="no holdings parsed")
    fresh: list[tuple[str, str]] = []
    with connect() as db:
        acc_id = _account(db, "Groww", "demat")
        for r in rows:
            had_prices = db.execute(
                "SELECT 1 FROM price_history WHERE symbol=? LIMIT 1", (r["symbol"],)
            ).fetchone()
            upsert_holding(acc_id, r["symbol"], name=r["name"], type=r["type"],
                           units=r["units"], cost_per_unit=r["cost_per_unit"],
                           source="groww", purchase_date=r["purchase_date"],
                           mode="add_lot", conn=db)
            if not had_prices:
                fresh.append((r["symbol"], r["type"]))
        db.commit()
    for sym, atype in fresh:
        background_tasks.add_task(backfill_price_history, sym, atype)
    return {"state": "ok", "holdings": len(rows), "backfill_queued": len(fresh)}


@router.post("/import/cas")
async def import_cas(file: UploadFile = File(...), pan: str | None = None):
    result = parse_cas(await file.read(), pan)
    rows = result.get("rows", [])
    lots = result.get("lots", [])
    as_of = result.get("as_of", "")
    with connect() as db:
        acc_id = _account(db, "CAS", "demat")
        ids: dict[str, int] = {}
        for r in rows:
            symbol = r.get("amfi_code") or r.get("isin")
            if not symbol:
                continue
            units = r.get("units") or 0
            invested = r.get("invested")
            cpu = (invested / units) if (invested and units and r.get("full_cost_coverage")) else None
            hid = upsert_holding(acc_id, symbol, name=r.get("name"),
                                 type="mutual_fund", units=units,
                                 cost_per_unit=cpu,
                                 mode="set_snapshot", conn=db)
            ids[symbol] = hid
            if r.get("folio"):
                db.execute("UPDATE holdings SET folio = ? WHERE id = ?",
                           (r["folio"], hid))
        # purchase lots from the CAS's own transaction history (a demat
        # CAS carries none — the count below says so honestly)
        lots_written = 0
        for lot in lots:
            hid = ids.get(lot["key"])
            if hid is None:
                continue
            cur = db.execute(
                "INSERT OR IGNORE INTO lots(holding_id, purchase_date, units, "
                "cost_per_unit, source) VALUES (?,?,?,?, 'cas')",
                (hid, lot["purchase_date"], lot["units"], lot["cost_per_unit"]))
            lots_written += cur.rowcount or 0
        if as_of:
            db.execute(
                "UPDATE data_health SET cas_last_import = ? WHERE id = 1",
                (as_of,))
        db.commit()
    return {
        "state": "ok",
        "holdings": len(rows),
        "lots_written": lots_written,
        "transactions_in_statement": len(lots),
        "as_of": as_of,
        "skipped_stale": len(result.get("skipped_stale", [])),
        "unmatched": len(result.get("unmatched", [])),
        "note": result.get("note"),
    }


_MANUAL_TABLES = {"debt": "debts", "insurance": "insurance", "goal": "goals",
                  "salary": "salary", "transaction": "transactions"}


@router.post("/import/manual")
def import_manual(payload: dict):
    entity = (payload or {}).get("entity")
    if entity == "holding":
        with connect() as db:
            upsert_holding(payload["account_id"], payload["symbol"],
                           name=payload.get("name"), type=payload.get("type"),
                           units=payload.get("units", 0),
                           cost_per_unit=payload.get("cost_per_unit"),
                           mode="set_snapshot", conn=db)
            db.commit()
        return {"state": "ok"}

    table = _MANUAL_TABLES.get(entity)
    if not table:
        raise HTTPException(status_code=400,
                            detail=f"unsupported entity '{entity}'")
    fields = {k: v for k, v in payload.items() if k != "entity"}
    if not fields:
        raise HTTPException(status_code=422, detail="empty body")
    cols = ", ".join(fields)
    marks = ", ".join("?" for _ in fields)
    with connect() as db:
        try:
            cur = db.execute(
                f"INSERT INTO {table}({cols}) VALUES ({marks})",
                tuple(fields.values()),
            )
            db.commit()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(e))
    return {"state": "ok", "id": cur.lastrowid}
