"""Transaction ingest with dedup on (account_id, date, amount, description).
(The schema has no normalized_key column — that composite is the natural key.)"""
from __future__ import annotations

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
