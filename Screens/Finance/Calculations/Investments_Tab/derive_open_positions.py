"""Derives OPEN and CLOSED positions by netting the transaction log.

WHAT THIS FILE IS
    Reads Screens/Finance/Saved_Records/my_investments.csv (one row per
    buy or sell: columns date,kind,name,identifier,amount,units,notes -
    a SELL is a row with a negative amount or negative units), nets the
    units per identifier FIFO-style, and splits everything into:

        OPEN    identifiers still holding units (units > 0)
        CLOSED  identifiers fully sold out (net units back to zero)

IDENTIFIER CONVENTION (documented per Phase 2, task C)
    For mutual funds the log's `identifier` IS the AMFI scheme code, so
    it lines up with portfolio_holdings.csv's amfi_code column directly.
    For direct equities and ETFs traded on Groww there is no AMFI code,
    so when such a row is appended to portfolio_holdings.csv the NSE
    trading SYMBOL (e.g. GOLDBEES, ITBEES) goes into the amfi_code
    column instead, and the source string says so. No new column was
    added to COLUMNS for this - reusing amfi_code keeps the schema
    unchanged and every existing reader working.

    The one crosswalk needed today: the snapshot carries GoldBeES under
    its ISIN (INF204KB17I5) while the log uses the symbol GOLDBEES;
    SYMBOL_TO_SNAPSHOT_CODE below states that mapping explicitly rather
    than guessing any other one.

PRICING HONESTY
    A derived OPEN position gets `invested` (buy amounts minus the cost
    basis of the units actually sold away) but NO current value - pricing
    comes from the equity price ledger, never guessed here. If such a
    row must be appended, current is left equal to invested ONLY as an
    explicit placeholder and the source string says pricing is pending.

DATA ANOMALIES
    An identifier whose sells exceed its buys in the log can never be
    owned negative - it is excluded from OPEN, reported as a warning,
    and only the portion of its sells that matches real buy lots is ever
    recorded anywhere. Nothing is fabricated to balance it.

REALIZED LOTS
    Every matched sell produces tax-lot rows (FIFO). Share/ETF lots go
    into Saved_Records/realized_capital_gains.csv - its existing header
    already fits them unchanged (the NSE symbol rides in amfi_code, the
    same convention as above; category "Equity"). Mutual-fund
    redemptions are deliberately NOT written here: the broker capital-
    gains xlsx reports already cover them row-for-row and duplicating
    them would double-count.

RUN IT
    cd <repo root>
    .venv\\Scripts\\python.exe Screens\\Finance\\Calculations\\Investments_Tab\\derive_open_positions.py
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":
        sys.path.insert(0, str(_group))
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import read_portfolio_holdings as holdings      # noqa: E402  sibling group

TRANSACTIONS_PATH = SCREEN / "Saved_Records" / "my_investments.csv"
REALIZED_PATH = SCREEN / "Saved_Records" / "realized_capital_gains.csv"

# anything smaller than this counts as fully sold out - float sums drift
EPSILON = 1e-6

# log identifier -> the amfi_code value the snapshot file uses for the
# same holding (ISIN for ETFs). Stated, not inferred.
SYMBOL_TO_SNAPSHOT_CODE = {"GOLDBEES": "INF204KB17I5"}

LONG_TERM_DAYS = 365            # held longer than this books as long-term


# =====================================================================
# READ the transaction log
# =====================================================================
def transactions_path() -> Path:
    return TRANSACTIONS_PATH


def read_transactions() -> dict:
    """Returns {'has_data': bool, 'rows': [...], 'where_from': str}."""
    path = transactions_path()
    if not path.exists():
        return {"has_data": False, "rows": [], "where_from": str(path)}
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for line_number, row in enumerate(csv.DictReader(f), start=2):
            identifier = (row.get("identifier") or "").strip()
            if not identifier:
                continue
            try:
                amount = float(row.get("amount") or "")
                units = float(row.get("units") or "")
            except ValueError:
                raise ValueError(
                    f"{path.name} line {line_number}: amount/units not numbers")
            # a sell shows up as a negative amount OR negative units;
            # quantities are always worked with as positive magnitudes
            rows.append({
                "date": (row.get("date") or "").strip(),
                "kind": (row.get("kind") or "").strip(),
                "name": (row.get("name") or "").strip(),
                "identifier": identifier,
                "amount": amount,
                "units": abs(units),
                "is_sell": amount < 0 or units < 0,
                "line": line_number,
            })
    rows.sort(key=lambda r: r["date"])
    return {
        "has_data": bool(rows),
        "rows": rows,
        "where_from": f"{path} ({len(rows)} transaction rows)",
    }


def _category_for(name: str, kind: str) -> str:
    if kind != "share":
        return kind
    return "etf" if "etf" in name.lower() else "equity"


# =====================================================================
# DERIVE - FIFO match every sell against the buys before it
# =====================================================================
def derive_positions(rows: list[dict]) -> dict:
    """Nets units per identifier. Returns open positions, closed
    positions, matched realized lots, and honest warnings."""
    order: list[str] = []
    state: dict[str, dict] = {}
    warnings: list[str] = []

    for row in rows:
        ident = row["identifier"]
        if ident not in state:
            order.append(ident)
            state[ident] = {
                "identifier": ident, "name": row["name"], "kind": row["kind"],
                "buys": [],               # fifo lots: [date, qty_left, unit_cost]
                "bought_units": 0.0, "bought_amount": 0.0,
                "sold_units": 0.0, "sold_amount": 0.0,
                "last_date": row["date"], "lines": [],
            }
        s = state[ident]
        s["last_date"] = max(s["last_date"], row["date"])
        s["lines"].append(row["line"])

        if not row["is_sell"]:
            s["buys"].append([row["date"], row["units"],
                              row["amount"] / row["units"]])
            s["bought_units"] += row["units"]
            s["bought_amount"] += row["amount"]
            continue

        # ---- a sell: consume fifo lots -------------------------------
        s["sold_units"] += row["units"]
        s["sold_amount"] += abs(row["amount"])
        redeem_price = abs(row["amount"]) / row["units"]
        remaining = row["units"]
        while remaining > EPSILON and s["buys"]:
            lot = s["buys"][0]
            take = min(remaining, lot[1])
            cost_basis = take * lot[2]
            gain = take * redeem_price - cost_basis
            held_days = (date.fromisoformat(row["date"])
                         - date.fromisoformat(lot[0])).days
            s.setdefault("matched", []).append({
                "identifier": ident, "name": row["name"], "kind": row["kind"],
                "purchase_date": lot[0],
                "purchase_price": round(lot[2], 4),
                "matched_quantity": round(take, 3),
                "redeem_date": row["date"],
                "redeem_price": round(redeem_price, 4),
                "gain": round(gain, 2),
                "held_days": held_days,
            })
            lot[1] -= take
            remaining -= take
            if lot[1] <= EPSILON:
                s["buys"].pop(0)
        if remaining > EPSILON:
            warnings.append(
                f"{ident}: a sell of {remaining:g} unit(s) on {row['date']} "
                f"(log line {row['line']}) has no buy lot left in the log - "
                "sells exceed buys. Excluded from open positions; only the "
                "matched part is recorded anywhere.")

    open_positions, closed = [], []
    for ident in order:
        s = state[ident]
        remaining_units = sum(lot[1] for lot in s["buys"])
        matched_cost = sum(m["matched_quantity"] * m["purchase_price"]
                           for m in s.get("matched", []))
        s["remaining_units"] = remaining_units
        s["invested_if_open"] = round(s["bought_amount"] - matched_cost, 2)
        if remaining_units > EPSILON:
            open_positions.append({
                "identifier": ident, "name": s["name"],
                "category": _category_for(s["name"], s["kind"]),
                "units": round(remaining_units, 3),
                "invested": s["invested_if_open"],
                "last_date": s["last_date"],
                "lines": s["lines"],
            })
        elif s["bought_units"] > 0:
            closed.append({
                "identifier": ident, "name": s["name"],
                "category": _category_for(s["name"], s["kind"]),
                "bought_units": round(s["bought_units"], 3),
                "sold_units": round(s["sold_units"], 3),
                "realized_gain": round(sum(m["gain"]
                                           for m in s.get("matched", [])), 2),
                "last_date": s["last_date"],
            })

    realized = [m for ident in order for m in state[ident].get("matched", [])]
    return {
        "has_data": bool(order),
        "open": open_positions,
        "closed": closed,
        "realized": realized,
        "warnings": warnings,
        "where_from": "netted from my_investments.csv, FIFO per identifier",
    }


# =====================================================================
# RECONCILE - log-derived vs the snapshot, never overwrite silently
# =====================================================================
def reconcile_with_snapshot(derived: dict) -> list[dict]:
    """Compares log-derived open units against portfolio_holdings.csv.
    Reports only - writes nothing."""
    snapshot = holdings.read_every_holding()
    by_code = {}
    for h in snapshot:
        by_code[h["amfi_code"]] = h
        # the stated symbol->ISIN crosswalk, so GOLDBEES finds its row
        for sym, code in SYMBOL_TO_SNAPSHOT_CODE.items():
            if code == h["amfi_code"]:
                by_code[sym] = h

    findings = []
    seen_codes = set()
    for pos in derived["open"]:
        snap = by_code.get(pos["identifier"])
        if snap is not None:
            seen_codes.add(snap["amfi_code"])
        findings.append({
            "identifier": pos["identifier"], "log_units": pos["units"],
            "log_last_date": pos["last_date"],
            "snapshot_units": snap["units"] if snap else None,
            "snapshot_date": snap["date"] if snap else None,
            "snapshot_invested": snap["invested"] if snap else None,
            "status": ("match" if snap is not None
                       and abs((snap["units"] or 0) - pos["units"]) <= 0.01
                       else
                       "MISMATCH" if snap is not None
                       else "missing_from_snapshot"),
        })
    for h in snapshot:
        if h["amfi_code"] in seen_codes \
                or h["amfi_code"] in SYMBOL_TO_SNAPSHOT_CODE.values():
            continue          # already reported via its log identifier
        findings.append({
            "identifier": h["scheme_name"], "log_units": None,
            "log_last_date": None,
            "snapshot_units": h["units"], "snapshot_date": h["date"],
            "snapshot_invested": h["invested"],
            "status": "snapshot_only_no_log_rows",
        })
    return findings


# =====================================================================
# WRITE - only what the log proves
# =====================================================================
def append_missing_open_holdings(derived: dict, findings: list[dict]) -> list[dict]:
    """Adds open equity/ETF rows the snapshot lacks, via add_holding().
    The NSE symbol goes in amfi_code (see module docstring). current is
    set equal to invested ONLY as a placeholder - pricing comes from the
    equity price ledger, never from here."""
    status_by_ident = {f["identifier"]: f["status"] for f in findings}
    added = []
    for pos in derived["open"]:
        if status_by_ident.get(pos["identifier"]) != "missing_from_snapshot":
            continue
        source = (
            f"derived from my_investments.csv transaction lines "
            f"{pos['lines']} ({pos['identifier']}): {pos['units']} units "
            f"netted FIFO, last activity {pos['last_date']}. amfi_code "
            f"column carries the NSE symbol per Investments_Tab convention. "
            f"current = invested placeholder only - price from the equity "
            f"price ledger, not yet priced."
        )
        row = holdings.add_holding(
            pos["name"], amfi_code=pos["identifier"], category=pos["category"],
            units=pos["units"], invested=pos["invested"],
            current=pos["invested"],       # placeholder, see docstring
            source=source,
        )
        added.append(row)
    return added


REALIZED_COLUMNS = [
    "scheme_name", "amfi_code", "category", "purchase_date",
    "purchase_price", "matched_quantity", "redeem_date", "redeem_price",
    "short_term_gain", "long_term_gain", "financial_year", "source",
]


def _financial_year(redeem_date: str) -> str:
    d = date.fromisoformat(redeem_date)
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def record_realized_share_lots(derived: dict) -> dict:
    """Appends matched SHARE/ETF sell lots to realized_capital_gains.csv.
    Its existing header already fits - no column change was needed.
    Mutual-fund redemptions stay out (broker gains reports own them).
    Dedup is multiplicity-aware: two different lots can share scheme,
    dates AND quantity (e.g. two same-day buys sold together), so a lot
    is skipped only when the file already holds that key as many times
    as this derivation produces it."""
    lots = [m for m in derived["realized"] if m["kind"] == "share"]
    if not lots:
        return {"written": 0, "skipped_existing": 0,
                "where_from": str(REALIZED_PATH)}
    REALIZED_PATH.parent.mkdir(parents=True, exist_ok=True)

    def key_of(name, pdate, rdate, qty):
        return (name, pdate, rdate, round(float(qty), 3))

    already = Counter()
    if REALIZED_PATH.exists():
        with REALIZED_PATH.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                already[key_of(r.get("scheme_name"), r.get("purchase_date"),
                               r.get("redeem_date"),
                               r.get("matched_quantity"))] += 1
    new_rows, skipped = [], 0
    pending = Counter()
    for m in lots:
        st = m["gain"] if m["held_days"] < LONG_TERM_DAYS else 0.0
        lt = 0.0 if m["held_days"] < LONG_TERM_DAYS else m["gain"]
        k = key_of(m["name"], m["purchase_date"], m["redeem_date"],
                   m["matched_quantity"])
        seen_so_far = already[k] + pending[k]
        pending[k] += 1
        if seen_so_far >= pending[k]:
            skipped += 1
            continue
        new_rows.append({
            "scheme_name": m["name"], "amfi_code": m["identifier"],
            "category": "Equity",
            "purchase_date": m["purchase_date"],
            "purchase_price": m["purchase_price"],
            "matched_quantity": m["matched_quantity"],
            "redeem_date": m["redeem_date"],
            "redeem_price": m["redeem_price"],
            "short_term_gain": st, "long_term_gain": lt,
            "financial_year": _financial_year(m["redeem_date"]),
            "source": (f"FIFO-matched from my_investments.csv "
                       f"(Groww Stocks order history), derived "
                       f"{date.today().isoformat()}"),
        })
    if new_rows:
        file_is_new = not REALIZED_PATH.exists()
        with REALIZED_PATH.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=REALIZED_COLUMNS)
            if file_is_new:
                w.writeheader()
            w.writerows(new_rows)
    return {"written": len(new_rows), "skipped_existing": skipped,
            "where_from": str(REALIZED_PATH)}


# =====================================================================
# REPORT
# =====================================================================
def main() -> None:
    tx = read_transactions()
    print("OPEN / CLOSED POSITIONS FROM THE TRANSACTION LOG")
    print(f"  where from: {tx['where_from']}")
    print()
    if not tx["has_data"]:
        print("  my_investments.csv has no rows yet - nothing to derive.")
        return

    derived = derive_positions(tx["rows"])

    for w in derived["warnings"]:
        print(f"  [WARNING] {w}")
    if derived["warnings"]:
        print()

    print(f"  OPEN positions ({len(derived['open'])}):")
    for p in derived["open"]:
        print(f"    {p['identifier']:<14}{p['category']:<8}"
              f"units {p['units']:>10,.3f}   invested {p['invested']:>10,.2f}"
              f"   last activity {p['last_date']}")
    print()
    print(f"  CLOSED positions ({len(derived['closed'])}):")
    for c in derived["closed"]:
        print(f"    {c['identifier']:<14}bought {c['bought_units']:>9,.3f},"
              f" sold {c['sold_units']:>9,.3f},"
              f" realized {c['realized_gain']:>9,.2f},"
              f" last activity {c['last_date']}")
    print()

    print("RECONCILIATION: log-derived vs portfolio_holdings.csv snapshot")
    print("  (report only - the snapshot is never overwritten silently)")
    findings = reconcile_with_snapshot(derived)
    for f in findings:
        if f["log_units"] is not None:
            print(f"    {f['identifier']:<14}{f['status']:<24}"
                  f"log {f['log_units']:>10,.3f} (to {f['log_last_date']})"
                  f"  vs snapshot {f['snapshot_units']} "
                  f"(dated {f['snapshot_date']})")
            if (f["status"] == "match"
                    and f["snapshot_invested"] is not None):
                pos = next(p for p in derived["open"]
                           if p["identifier"] == f["identifier"])
                diff = round(f["snapshot_invested"] - pos["invested"], 2)
                if abs(diff) > 0.01:
                    print(f"    {'':<14}invested differs too: snapshot "
                          f"{f['snapshot_invested']:,.2f} vs log-derived "
                          f"{pos['invested']:,.2f} (diff {diff:+,.2f})")
        else:
            print(f"    {f['identifier']:<44}{f['status']:<26}"
                  f"snapshot {f['snapshot_units']} units, dated "
                  f"{f['snapshot_date']} - no rows in the log "
                  "(external statement holding, left untouched)")
    print()

    added = append_missing_open_holdings(derived, findings)
    if added:
        print(f"APPENDED {len(added)} missing holding row(s):")
        for r in added:
            print(f"    {r['scheme_name']} ({r['amfi_code']}) "
                  f"{r['units']} units, invested {r['invested']}")
    else:
        print("APPENDED ROWS: none needed - every log-derived open position "
              "is already in the snapshot (or was excluded as anomalous).")
    print()

    recorded = record_realized_share_lots(derived)
    skip_note = (f", skipped {recorded['skipped_existing']} already on disk"
                 if recorded.get("skipped_existing") else "")
    print(f"REALIZED LOTS: wrote {recorded['written']} share lot(s) to "
          f"realized_capital_gains.csv{skip_note}")
    mf_count = len([m for m in derived["realized"] if m["kind"] != "share"])
    if mf_count:
        print(f"    ({mf_count} mutual-fund lot(s) derived but not written - "
              "the broker capital-gains reports already carry them)")
    print()

    summary = holdings.a_summary_for_the_screen()
    print("FINAL COMPLETE HOLDINGS LIST (portfolio_holdings.csv)")
    if not summary["has_data"]:
        print(f"  {summary['note']}")
        return
    for h in summary["holdings"]:
        units = "-" if h["units"] is None else f"{h['units']:g}"
        print(f"  {h['scheme_name']:<55}{h['category']:<12}"
              f"units {units:>10}  "
              f"invested {h['invested']:>10,.2f}  "
              f"current {h['current']:>10,.2f}")
    print()
    print(f"  total invested {summary['total_invested']:,.2f}")
    print(f"  total current  {summary['total_current']:,.2f}")


if __name__ == "__main__":
    main()
