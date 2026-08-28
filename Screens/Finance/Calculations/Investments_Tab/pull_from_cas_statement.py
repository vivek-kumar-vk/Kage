"""Reads a CAS (Consolidated Account Statement) PDF and reconciles it
against portfolio_holdings.csv - units and current value only.

WHY THIS EXISTS
    Every month the manual routine was: open the Groww app, read units
    and current value off the screen for each fund, type them into
    portfolio_holdings.csv by hand. A CAS is the same numbers, issued by
    the depository (CDSL/NSDL) rather than one broker's app, covering
    every fund you hold - not just the ones bought through Groww.

WHAT A CAS CAN AND CANNOT TELL YOU (read this before trusting the output)
    A CAS reports, per fund, per account it is held under: units
    (`balance`), the NAV used, and the resulting `value`. For a fund
    held IN DEMAT FORM (dematerialised - this file's Groww entries),
    CDSL does not carry your original cost - `total_cost` comes back
    None for every one of them. Cost only appears for a fund held the
    older way, as a folio registered directly with the AMC/RTA outside
    demat (this file's "Mutual Fund Folios" pseudo-account).

    So this script updates `units` and `current` from the CAS. It NEVER
    writes `invested` from the CAS unless every single account
    contributing to that fund's total reported a real total_cost - one
    demat leg with no cost silently understates the true invested
    amount, which is worse than leaving the old figure alone. Rule 12:
    empty (or old-but-honest) beats fake.

THE STALENESS GUARD (the whole reason this defaults to a dry run)
    A CAS you receive today can still describe last month, or the month
    before. If portfolio_holdings.csv already has a row dated AFTER the
    CAS's own statement-period end, this script leaves that row alone
    and says why - overwriting a fresher hand-checked number with an
    older document would be a regression wearing an automation's
    clothes.

WHAT IT NEVER DOES
    - Guess an amfi_code. If the CAS's code for a fund does not match
      any existing row's code, and no other identifier (ISIN, for the
      one row that uses ISIN in its amfi_code column) matches either,
      the fund is reported as unmatched. A person resolves it, the same
      rule import_from_broker_statements.py already follows.
    - Add a brand-new holding row. add_holding() requires an invested
      amount; a CAS cannot always supply one honestly, so a fund found
      only in the CAS is reported for the person to add by hand.
    - Write anything unless run with --apply. Without it, this only
      prints what it would do.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\pull_from_cas_statement.py            # dry run, prints only
    python Screens\\Finance\\Calculations\\Investments_Tab\\pull_from_cas_statement.py --apply     # writes the safe updates

WHERE IT READS FROM
    My_Investement_details/*.pdf   - the CAS PDF(s), newest by file
                                     mtime wins if more than one exists
    Secrets_Keys/cas_pan.txt       - the CAS password (this account's
                                     PAN), one line, gitignored
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import read_portfolio_holdings                  # noqa: E402

SOURCE_DIR = PROJECT_ROOT / "My_Investement_details"
PAN_FILE = PROJECT_ROOT / "Secrets_Keys" / "cas_pan.txt"


class TheCasCouldNotBeRead(Exception):
    """Raised when there is nothing safe to parse - never guessed past."""


def _find_the_pan() -> str:
    if not PAN_FILE.exists():
        raise TheCasCouldNotBeRead(
            f"{PAN_FILE.relative_to(PROJECT_ROOT)} does not exist. Put the "
            "CAS password (this account's PAN) there, one line, before "
            "running this script."
        )
    pan = PAN_FILE.read_text(encoding="utf-8").strip()
    if not pan:
        raise TheCasCouldNotBeRead(f"{PAN_FILE.relative_to(PROJECT_ROOT)} is empty.")
    return pan


def _find_the_newest_cas_pdf() -> Path:
    if not SOURCE_DIR.exists():
        raise TheCasCouldNotBeRead(
            f"{SOURCE_DIR.relative_to(PROJECT_ROOT)} does not exist. Drop "
            "the CAS PDF there before running this script."
        )
    pdfs = sorted(SOURCE_DIR.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not pdfs:
        raise TheCasCouldNotBeRead(
            f"No .pdf found in {SOURCE_DIR.relative_to(PROJECT_ROOT)}."
        )
    return pdfs[0]


def _parse_cas(pdf_path: Path, pan: str) -> dict:
    import casparser  # imported here only - nothing at server startup needs this
    raw = casparser.read_cas_pdf(str(pdf_path), pan, output="dict")
    return raw.model_dump()


def _statement_end_date(data: dict) -> str:
    """The CAS's own 'as of' date, as YYYY-MM-DD. This - never today's
    date - is what gets compared against each row's existing date and
    written as the new date on any row this script updates."""
    to_text = (data.get("statement_period") or {}).get("to")
    if not to_text:
        raise TheCasCouldNotBeRead("This CAS has no statement_period.to - cannot date it.")
    return datetime.strptime(to_text, "%d-%b-%Y").date().isoformat()


def _every_mutual_fund_entry(data: dict) -> list[dict]:
    """Flattens every mutual_fund line out of every account in the CAS -
    demat accounts and the 'Mutual Fund Folios' pseudo-account alike."""
    entries = []
    for account in data.get("accounts") or []:
        account_name = account.get("name") or account.get("type") or "unnamed account"
        for mf in account.get("mutual_funds") or []:
            entries.append({
                "account": account_name,
                "raw_name": mf.get("name") or "",
                "amfi_code": (mf.get("amfi") or "").strip(),
                "isin": (mf.get("isin") or "").strip(),
                "units": float(mf["balance"]) if mf.get("balance") is not None else None,
                "current": float(mf["value"]) if mf.get("value") is not None else None,
                "total_cost": float(mf["total_cost"]) if mf.get("total_cost") is not None else None,
            })
    return entries


def _aggregate_by_identity(entries: list[dict]) -> list[dict]:
    """One holding can span more than one account (a demat leg plus an
    external folio leg) - portfolio_holdings.csv already keeps that as
    ONE row, so entries sharing an identity are summed the same way.
    Identity is amfi_code when every contributing entry has one, else
    ISIN. Nothing here is matched by name - names differ wildly between
    what a CAS prints and what the CSV already uses."""
    groups: dict[str, list[dict]] = {}
    for e in entries:
        key = e["amfi_code"] or e["isin"]
        if not key:
            key = f"__no_identifier__::{e['raw_name']}"
        groups.setdefault(key, []).append(e)

    aggregated = []
    for key, group in groups.items():
        units = sum(g["units"] for g in group if g["units"] is not None)
        current = sum(g["current"] for g in group if g["current"] is not None)
        costs = [g["total_cost"] for g in group]
        full_cost_coverage = all(c is not None for c in costs)
        total_cost = sum(costs) if full_cost_coverage else None
        aggregated.append({
            "identity": key,
            "amfi_code": next((g["amfi_code"] for g in group if g["amfi_code"]), ""),
            "isin": next((g["isin"] for g in group if g["isin"]), ""),
            "raw_names": sorted({g["raw_name"] for g in group}),
            "accounts": sorted({g["account"] for g in group}),
            "units": round(units, 4),
            "current": round(current, 2),
            "total_cost": round(total_cost, 2) if total_cost is not None else None,
            "full_cost_coverage": full_cost_coverage,
        })
    return aggregated


def _reconcile(cas_funds: list[dict], as_of: str, existing: list[dict]) -> dict:
    """The matching, staleness-guard and update-shaping logic - pure,
    no file I/O, so it can be tested without a real CAS PDF or PAN."""
    by_amfi = {h["amfi_code"]: h for h in existing if h["amfi_code"]}

    updates, skipped_stale, unmatched_cas, matched_no_change = [], [], [], []

    for fund in cas_funds:
        row = by_amfi.get(fund["amfi_code"]) if fund["amfi_code"] else None
        if row is None and fund["isin"]:
            # the one row-shape (an ETF) that keeps an ISIN in the amfi_code column
            row = next((h for h in existing if h["amfi_code"] == fund["isin"]), None)

        if row is None:
            unmatched_cas.append(fund)
            continue

        existing_date = row.get("date") or ""
        if existing_date and existing_date >= as_of:
            skipped_stale.append({"fund": fund, "row": row, "as_of": as_of})
            continue

        change = {
            "scheme_name": row["scheme_name"],
            "amfi_code": row["amfi_code"],
            "as_of": as_of,
            "old_units": row["units"], "new_units": fund["units"],
            "old_current": row["current"], "new_current": fund["current"],
            "invested_touched": False,
        }
        if fund["full_cost_coverage"] and len(fund["accounts"]) == 1:
            # only ever trusted when the WHOLE holding lives in one account
            # a CAS actually priced end to end - a combined demat+folio
            # holding never qualifies, by design (see module docstring)
            change["invested_touched"] = True
            change["old_invested"] = row["invested"]
            change["new_invested"] = fund["total_cost"]
        updates.append(change)

    matched_amfis = {u["amfi_code"] for u in updates} | \
        {s["row"]["amfi_code"] for s in skipped_stale}
    unmatched_existing = [h for h in existing
                          if h["category"] == "mutual_fund" and h["amfi_code"] not in matched_amfis]

    return {
        "as_of": as_of,
        "updates": updates,
        "skipped_stale": skipped_stale,
        "unmatched_cas_funds": unmatched_cas,
        "unmatched_existing_rows": unmatched_existing,
    }


def build_the_report(pdf_path: Path | None = None) -> dict:
    pan = _find_the_pan()
    pdf_path = pdf_path or _find_the_newest_cas_pdf()
    data = _parse_cas(pdf_path, pan)
    as_of = _statement_end_date(data)
    cas_funds = _aggregate_by_identity(_every_mutual_fund_entry(data))
    existing = read_portfolio_holdings.read_every_holding()

    report = _reconcile(cas_funds, as_of, existing)
    report["pdf"] = str(pdf_path.relative_to(PROJECT_ROOT))
    return report


def apply_the_report(report: dict) -> int:
    written = 0
    for u in report["updates"]:
        changes = {"date": u["as_of"], "units": u["new_units"], "current": u["new_current"]}
        if u["invested_touched"]:
            changes["invested"] = u["new_invested"]
        read_portfolio_holdings.update_holding(u["scheme_name"], u["amfi_code"], changes)
        written += 1
    return written


def main() -> None:
    apply = "--apply" in sys.argv
    try:
        report = build_the_report()
    except TheCasCouldNotBeRead as problem:
        print(f"CANNOT READ THE CAS: {problem}")
        return

    print("CAS RECONCILIATION")
    print("=" * 60)
    print(f"  statement : {report['pdf']}")
    print(f"  as of     : {report['as_of']}")
    print()

    if report["updates"]:
        print(f"  {'WOULD UPDATE' if not apply else 'UPDATING'} "
              f"({len(report['updates'])}):")
        for u in report["updates"]:
            print(f"    {u['scheme_name'][:45]:<45} units {u['old_units']} -> {u['new_units']}   "
                  f"current {u['old_current']} -> {u['new_current']}"
                  + ("   invested " + str(u['old_invested']) + " -> " + str(u['new_invested'])
                     if u["invested_touched"] else "   (invested left as-is - no full cost basis in this CAS)"))
    else:
        print("  nothing to update.")
    print()

    if report["skipped_stale"]:
        print(f"  SKIPPED - existing row is already this date or newer ({len(report['skipped_stale'])}):")
        for s in report["skipped_stale"]:
            print(f"    {s['row']['scheme_name'][:45]:<45} row dated {s['row']['date']}, "
                  f"this CAS is dated {s['as_of']}")
    print()

    if report["unmatched_cas_funds"]:
        print(f"  IN THE CAS BUT NO MATCHING ROW ({len(report['unmatched_cas_funds'])}) - add by hand, "
              "invested amount unknown to this script:")
        for f in report["unmatched_cas_funds"]:
            print(f"    amfi={f['amfi_code'] or '(none)'} isin={f['isin']} "
                  f"units={f['units']} current={f['current']}  [{', '.join(f['raw_names'])}]")
    print()

    if report["unmatched_existing_rows"]:
        print(f"  IN YOUR RECORDS BUT NOT IN THIS CAS ({len(report['unmatched_existing_rows'])}) - left untouched:")
        for h in report["unmatched_existing_rows"]:
            print(f"    {h['scheme_name']} (amfi={h['amfi_code'] or '(none)'})")

    if apply:
        print()
        n = apply_the_report(report)
        print(f"  WROTE {n} row(s) to portfolio_holdings.csv")
    elif report["updates"]:
        print()
        print("  Dry run only - nothing written. Re-run with --apply to write the updates above.")


if __name__ == "__main__":
    main()
