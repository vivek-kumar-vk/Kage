"""upsert_holding — the ONE place holdings are created / merged.

  mode="set_snapshot"  a CAS statement is a point-in-time snapshot -> OVERWRITE units
  mode="add_lot"       a broker trade / CSV row is an ADDITION -> weighted-average-cost
                       merge + a dedup'd row in `lots`

Idempotency [C]: a re-imported broker CSV produces the *same* lot key
(holding_id, purchase_date, units, cost_per_unit). If the lot already exists the
whole call is a no-op — units are NOT added twice.
"""
from __future__ import annotations

from services.db import connect


def _existing(db, account_id, symbol):
    return db.execute(
        "SELECT id, units, avg_cost FROM holdings WHERE account_id=? AND symbol=?",
        (account_id, symbol),
    ).fetchone()


def upsert_holding(account_id, symbol, *, name=None, type=None, units=0.0,
                   cost_per_unit=None, currency="INR", source=None,
                   purchase_date=None, mode="add_lot", conn=None):
    own = conn is None
    db = conn or connect()
    try:
        units = float(units or 0)
        cpu = None if cost_per_unit is None else float(cost_per_unit)
        row = _existing(db, account_id, symbol)

        if row is None:
            cur = db.execute(
                "INSERT INTO holdings(account_id,symbol,name,type,units,avg_cost,currency) "
                "VALUES (?,?,?,?,?,?,?)",
                (account_id, symbol, name, type, units, cpu or 0.0, currency),
            )
            holding_id = cur.lastrowid
        else:
            holding_id = row["id"]

        if mode == "set_snapshot":
            if row is not None:
                db.execute("UPDATE holdings SET units=? WHERE id=?", (units, holding_id))
        elif mode == "add_lot":
            pd = purchase_date or "1970-01-01"
            lot = db.execute(
                "INSERT OR IGNORE INTO lots(holding_id,purchase_date,units,cost_per_unit,source) "
                "VALUES (?,?,?,?,?)",
                (holding_id, pd, units, cpu or 0.0, source),
            )
            if (lot.rowcount or 0) == 0:
                # duplicate lot -> idempotent no-op (also undo the fresh-insert units)
                if row is None:
                    db.execute("UPDATE holdings SET units=0 WHERE id=?", (holding_id,))
                if own:
                    db.commit()
                return holding_id
            if row is not None:  # fold the new lot into the existing holding
                total = float(row["units"]) + units
                if cpu is None:
                    avg = row["avg_cost"]
                elif total == 0:
                    avg = 0.0
                else:
                    avg = ((float(row["units"]) * float(row["avg_cost"])) +
                           (units * cpu)) / total
                db.execute("UPDATE holdings SET units=?, avg_cost=? WHERE id=?",
                           (total, avg, holding_id))
        else:
            raise ValueError(f"unknown mode {mode!r}")

        if own:
            db.commit()
        return holding_id
    finally:
        if own:
            db.close()
