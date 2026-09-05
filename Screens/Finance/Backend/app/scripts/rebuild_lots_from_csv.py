"""Rebuild the `lots` table from my_investments.csv.

Reads purchase transactions from a CSV, matches them to existing holdings,
and inserts lot rows into a SQLite database. Idempotent via the UNIQUE
constraint on (holding_id, purchase_date, units, cost_per_unit).

Why this exists: `backfill_from_old_records.py` section 3 wrote holdings with
mode="set_snapshot", and only mode="add_lot" writes a lot. `lots` therefore
sat at 0, which is the single root cause of the null XIRR and the flat
net-worth ridge (backfill_snapshots.py values history from `lots`).

Usage:
  python rebuild_lots_from_csv.py --db finance.db --csv my_investments.csv
  python rebuild_lots_from_csv.py --db finance.db --csv my_investments.csv --apply
"""

import argparse
import csv
import sqlite3
from pathlib import Path


# CSV identifier -> holdings.symbol, for positions the CSV tickers under a
# different code than the ISIN `holdings.symbol` carries. Each entry verified
# by hand: CSV net units for the alias match `holdings.units` for the target.
ALIASES = {
    "GOLDBEES": "INF204KB17I5",  # Nippon India ETF Gold BeES; CSV net 81.0 == holdings.units
}


def lot_units_by_holding(cur):
    """Total units in `lots` per holding, read from the DB itself.

    Read from the table rather than accumulated from this run's inserts:
    on a re-run every insert is an ignored duplicate, and a run-local
    counter would then report every holding as a MISMATCH at -holdings.units.
    """
    return {
        hid: total
        for hid, total in cur.execute(
            "SELECT holding_id, SUM(units) FROM lots GROUP BY holding_id"
        ).fetchall()
    }


def main():
    parser = argparse.ArgumentParser(description="Rebuild lots table from CSV")
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument("--csv", required=True, help="Path to investments CSV")
    parser.add_argument("--apply", action="store_true", help="Commit changes (default is dry-run)")
    args = parser.parse_args()

    db_path = Path(args.db)
    csv_path = Path(args.csv)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    lots_before = cur.execute("SELECT COUNT(*) FROM lots").fetchone()[0]

    holdings_rows = cur.execute("SELECT id, symbol, name, units FROM holdings").fetchall()
    holdings_by_symbol = {}
    holdings_by_name = {}
    holdings_units = {}
    for hid, sym, name, units in holdings_rows:
        holdings_by_symbol[sym] = {"id": hid, "symbol": sym, "name": name}
        if name:
            holdings_by_name[name.strip().lower()] = {"id": hid, "symbol": sym, "name": name}
        holdings_units[hid] = units or 0.0

    skipped = []
    unmatched = []
    symbol_stats = {}
    inserted_count = 0

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = (row.get("date") or "").strip()
            name = (row.get("name") or "").strip()
            identifier = (row.get("identifier") or "").strip()
            amount_str = (row.get("amount") or "").strip()
            units_str = (row.get("units") or "").strip()

            if not date:
                skipped.append({"date": "?", "name": name, "reason": "missing date"})
                continue

            try:
                amount = float(amount_str)
            except ValueError:
                skipped.append({"date": date, "name": name, "reason": "invalid amount"})
                continue

            if not units_str:
                skipped.append({"date": date, "name": name, "reason": "missing units"})
                continue
            try:
                units = float(units_str)
            except ValueError:
                skipped.append({"date": date, "name": name, "reason": "invalid units"})
                continue

            if units == 0:
                skipped.append({"date": date, "name": name, "reason": "zero units"})
                continue
            if amount <= 0:
                skipped.append({"date": date, "name": name, "reason": "sell or zero amount"})
                continue

            cost_per_unit = round(amount / units, 6)

            h_info = holdings_by_symbol.get(identifier)
            if not h_info:
                h_info = holdings_by_symbol.get(ALIASES.get(identifier))
            if not h_info:
                h_info = holdings_by_name.get(name.strip().lower())

            if not h_info:
                unmatched.append({"date": date, "name": name, "identifier": identifier})
                continue

            hid = h_info["id"]
            sym = identifier if identifier in holdings_by_symbol else h_info["symbol"]
            h_name = h_info["name"]

            if sym not in symbol_stats:
                symbol_stats[sym] = {
                    "id": hid,
                    "name": h_name,
                    "read": 0,
                    "inserted": 0,
                    "skipped_dup": 0,
                }
            symbol_stats[sym]["read"] += 1

            res = cur.execute(
                "INSERT OR IGNORE INTO lots(holding_id, purchase_date, units, cost_per_unit, source) VALUES (?,?,?,?,?)",
                (hid, date, units, cost_per_unit, "csv_rebuild"),
            )
            if res.rowcount == 1:
                symbol_stats[sym]["inserted"] += 1
                inserted_count += 1
            else:
                symbol_stats[sym]["skipped_dup"] += 1

    # Read the resulting totals back out of the table, inside the transaction.
    lot_units = lot_units_by_holding(cur)
    lots_after = cur.execute("SELECT COUNT(*) FROM lots").fetchone()[0]

    print(f"lots before: {lots_before}")
    print(f"lots after:  {lots_after}   (inserted {inserted_count})")
    print()

    header = (
        f"{'Symbol':<12} {'Name':<40} {'Read':>5} {'Ins':>5} {'SkipDup':>8} "
        f"{'LotUnits':>11} {'HoldUnits':>11} {'Delta':>11}"
    )
    print(header)
    print("-" * len(header))

    mismatches = []
    for sym in sorted(symbol_stats.keys()):
        s = symbol_stats[sym]
        hid = s["id"]
        l_units = lot_units.get(hid, 0.0) or 0.0
        h_units = holdings_units.get(hid, 0.0)
        delta = l_units - h_units
        raw_name = s["name"] or ""
        name_short = (raw_name[:37] + "...") if len(raw_name) > 40 else raw_name
        print(
            f"{sym:<12} {name_short:<40} {s['read']:>5} {s['inserted']:>5} "
            f"{s['skipped_dup']:>8} {l_units:>11.3f} {h_units:>11.3f} {delta:>11.3f}"
        )
        if abs(delta) > 0.001:
            mismatches.append((sym, delta))

    print()
    for sym, delta in mismatches:
        print(f"MISMATCH: {sym} lot units differ from holdings.units by {delta:.3f}")

    if skipped:
        print("\nSkipped rows:")
        for r in skipped:
            print(f"  {r['date']} | {r['name']} | reason: {r['reason']}")

    if unmatched:
        print("\nUnmatched rows:")
        for r in unmatched:
            print(f"  {r['date']} | {r['name']} | identifier: {r['identifier']}")

    if args.apply:
        conn.commit()
    else:
        conn.rollback()
        print("\nDRY RUN — nothing written. Re-run with --apply.")

    conn.close()

    if unmatched or mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
