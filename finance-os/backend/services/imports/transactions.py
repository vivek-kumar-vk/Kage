"""Transaction ingest with dedup on (account_id, date, amount, description).
(The schema has no normalized_key column — that composite is the natural key.)"""
from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

from services.calculations.xirr import xirr
from services.db import connect


def dedupe_transaction(account_id, date, amount, description=None, category=None,
                       type=None, source=None, conn=None) -> bool:
    """Insert the transaction unless an identical one already exists.
    Returns True if a row was inserted, False if it was a duplicate."""
    own = conn is None
    db = conn or connect()
    try:
        dup = db.execute(
            "SELECT id FROM transactions WHERE account_id=? AND date=? AND amount=? "
            "AND IFNULL(description,'')=IFNULL(?,'')",
            (account_id, date, amount, description),
        ).fetchone()
        if dup:
            return False
        db.execute(
            "INSERT INTO transactions(account_id,date,amount,description,category,type,source) "
            "VALUES (?,?,?,?,?,?,?)",
            (account_id, date, amount, description, category, type, source),
        )
        if own:
            db.commit()
        return True
    finally:
        if own:
            db.close()


# --- Ported from the old compute_the_xirr.py / my_investments.csv reader -------


def parse_transaction_rows(file_bytes: bytes, source: str) -> list[dict]:
    """Read the old my_investments.csv shape
    (date,kind,name,identifier,amount,units,notes) into transaction dicts."""
    if not file_bytes:
        return []
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8", errors="replace")

    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            amount = float(row.get("amount", 0) or 0)
            units = float(row.get("units", 0) or 0)
        except ValueError:
            continue
        rows.append(
            {
                "date": row.get("date", ""),
                "kind": row.get("kind", ""),
                "name": row.get("name", ""),
                "identifier": row.get("identifier", ""),
                "amount": amount,
                "units": abs(units),
                "is_sell": amount < 0 or units < 0,
                "source": source,
            }
        )
    return rows


def assemble_xirr_cashflows(
    transactions: list[dict], current_value: float, valuation_date: date | None = None
) -> list[tuple[Decimal, Decimal]] | None:
    if not transactions:
        return None
    flows = []
    base_date = None
    for tx in transactions:
        try:
            d = date.fromisoformat(tx["date"])
        except ValueError:
            continue
        if base_date is None or d < base_date:
            base_date = d
        flows.append((d, Decimal(str(-tx["amount"]))))

    if not flows or base_date is None:
        return None

    val_date = valuation_date or date.today()
    flows.append((val_date, Decimal(str(current_value))))
    return [(Decimal((d - base_date).days), amt) for d, amt in flows]


def compute_xirr(
    transactions: list[dict], current_value: float, valuation_date: date | None = None
) -> float | None:
    cashflows = assemble_xirr_cashflows(transactions, current_value, valuation_date)
    if not cashflows:
        return None
    return xirr(cashflows)
