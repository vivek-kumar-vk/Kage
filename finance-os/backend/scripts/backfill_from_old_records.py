"""One-shot, idempotent backfill of the old Finance Screen records into finance.db.

Reads the gitignored CSV/JSON copies under ``backend/data/backfill/`` (the user
drops the old ``Saved_Records/`` + ``Reference_Data/`` there) and loads them.
Re-running inserts nothing new.  Uses only ``services.db.connect`` and the
existing helpers.  Exits non-zero if a required CSV is missing.
"""
from __future__ import annotations

import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.calculations.holdings_upsert import upsert_holding
from services.db import connect
from services.imports.transactions import dedupe_transaction

BACKFILL_DIR = Path(__file__).resolve().parents[1] / "data" / "backfill"
RECORDS_DIR = BACKFILL_DIR / "Saved_Records"
NOTICEBOARD = (
    Path(__file__).resolve().parents[3]
    / "Shared_By_All_Screens"
    / "Current_Numbers"
    / "all_current_numbers.md"
)

REQUIRED = ["my_investments.csv", "portfolio_holdings.csv"]

NOTICEBOARD_DEFAULTS = {
    "edu_loan_outstanding": "654750",
    "edu_loan_rate": "10.70",
    "edu_loan_emi": "13286",
    "uncle_remaining": "106000",
    "uncle_monthly": "10000",
    "slice_limit": "28000",
    "slice_closing_balance": "0",
    "epf_balance": "60000",
    "epf_monthly": "1800",
    "nps_balance": "3060.48",
    "health_cover_amount": "2000000",
    "health_cover_annual_premium": "9573",
    "accident_cover_amount": "1000000",
    "accident_cover_annual_premium": "1140",
    "restoration_owed": "26000",
    "income": "70000",
}

MISSING_INFO = [
    "term_life_cover",
    "epf_balance_verification",
    "epf_employer_share",
    "nps_monthly_contribution",
    "uncle_loan_interest_assumption",
    "bajaj_finance_emi_card_outstanding",
    "abundance_small_cap_exact_fund_name",
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def read_noticeboard() -> dict[str, str]:
    data = dict(NOTICEBOARD_DEFAULTS)
    if not NOTICEBOARD.exists():
        return data
    pattern = re.compile(r"^\s*([A-Za-z0-9_]+)\s*:\s*([-\d.]+)")
    for line in NOTICEBOARD.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            data[m.group(1)] = m.group(2)
    return data


def _rows(name: str) -> list[dict]:
    path = RECORDS_DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _f(value: str | None, default: float = 0.0) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError, AttributeError):
        return default


def account_id(db, name: str, atype: str, institution: str | None = None) -> int:
    cur = db.execute(
        "INSERT OR IGNORE INTO accounts (name, type, institution) VALUES (?, ?, ?)",
        (name, atype, institution),
    )
    inserted = cur.rowcount or 0
    row = db.execute("SELECT id FROM accounts WHERE name = ?", (name,)).fetchone()
    return row["id"], inserted


def note_once(db, holding_id, note_type: str, content: str) -> int:
    exists = db.execute(
        "SELECT id FROM research_notes WHERE IFNULL(holding_id, -1) = IFNULL(?, -1) "
        "AND note_type = ? AND content = ?",
        (holding_id, note_type, content),
    ).fetchone()
    if exists:
        return 0
    db.execute(
        "INSERT INTO research_notes (holding_id, note_type, content) VALUES (?, ?, ?)",
        (holding_id, note_type, content),
    )
    return 1


def debt_once(db, lender, dtype, outstanding, rate, emi) -> int:
    if db.execute("SELECT id FROM debts WHERE lender = ?", (lender,)).fetchone():
        return 0
    db.execute(
        "INSERT INTO debts (lender, type, outstanding, interest_rate, emi) "
        "VALUES (?, ?, ?, ?, ?)",
        (lender, dtype, outstanding, rate, emi),
    )
    return 1


def insurance_once(db, itype, provider, coverage, premium) -> int:
    if db.execute(
        "SELECT id FROM insurance WHERE type = ? AND IFNULL(provider, '') = IFNULL(?, '')",
        (itype, provider),
    ).fetchone():
        return 0
    db.execute(
        "INSERT INTO insurance (type, provider, coverage_amount, premium) "
        "VALUES (?, ?, ?, ?)",
        (itype, provider, coverage, premium),
    )
    return 1


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    if not RECORDS_DIR.exists():
        print(f"backfill: {RECORDS_DIR} not found", file=sys.stderr)
        sys.exit(1)
    missing = [n for n in REQUIRED if not (RECORDS_DIR / n).exists()]
    if missing:
        print(f"backfill: required file(s) missing: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    nb = read_noticeboard()
    ins: dict[str, int] = {}
    skip: dict[str, int] = {}

    def bump(d, k, n=1):
        d[k] = d.get(k, 0) + n

    with connect() as db:
        # 1. accounts -------------------------------------------------------- #
        for name, atype, inst in (
            ("Groww", "demat", "Groww"),
            ("CAS", "demat", "NSDL/CDSL"),
            ("Mutual Fund Folios", "external", "AMC/RTA"),
            ("Bank", "savings", None),
        ):
            _, made = account_id(db, name, atype, inst)
            bump(ins if made else skip, "accounts")
        db.commit()

        groww_id = db.execute("SELECT id FROM accounts WHERE name='Groww'").fetchone()["id"]
        folio_id = db.execute(
            "SELECT id FROM accounts WHERE name='Mutual Fund Folios'"
        ).fetchone()["id"]
        bank_id = db.execute("SELECT id FROM accounts WHERE name='Bank'").fetchone()["id"]

        # 2. transactions — my_investments.csv ----------------------------- #
        for r in _rows("my_investments.csv"):
            acc = groww_id if r.get("kind") == "share" else folio_id
            amount = _f(r.get("amount"))
            desc = f"{r.get('kind', '')} {r.get('name', '')} [{r.get('identifier', '')}]".strip()
            ttype = "sell" if amount < 0 else "buy"
            made = dedupe_transaction(
                acc, r.get("date"), amount, desc, "investment", ttype, "backfill", conn=db
            )
            bump(ins if made else skip, "transactions")
        db.commit()

        # 3. holdings + lots — portfolio_holdings.csv --------------------- #
        for r in _rows("portfolio_holdings.csv"):
            symbol = (r.get("amfi_code") or r.get("scheme_name") or "").strip()
            if not symbol:
                bump(skip, "holdings")
                continue
            units = _f(r.get("units"))
            invested = _f(r.get("invested"))
            cpu = (invested / units) if units else 0.0
            already = db.execute(
                "SELECT id FROM holdings WHERE account_id = ? AND symbol = ?",
                (folio_id, symbol),
            ).fetchone()
            hid = upsert_holding(
                folio_id,
                symbol,
                name=r.get("scheme_name"),
                type=r.get("category") or "mutual_fund",
                units=units,
                cost_per_unit=cpu,
                source="backfill",
                mode="set_snapshot",
                conn=db,
            )
            bump(skip if already else ins, "holdings")
            pledged = (r.get("pledged_units") or "").strip()
            if pledged:
                bump(
                    ins if note_once(db, hid, "pledged_units", pledged) else skip,
                    "research_notes",
                )
        db.commit()

        # 4. SIPs — active_sips.csv -------------------------------------- #
        for r in _rows("active_sips.csv"):
            scheme = (r.get("scheme_name") or "").strip()
            if not scheme:
                continue
            content = f"{scheme}|{_f(r.get('monthly_amount'))}"
            bump(ins if note_once(db, None, "sip", content) else skip, "research_notes")
        db.commit()

        # 5. assets & liabilities -------------------------------------- #
        for r in _rows("assets_and_liabilities.csv"):
            name = (r.get("name") or "").strip()
            value = (r.get("value") or "").strip()
            if r.get("kind") == "asset":
                if not value:
                    bump(skip, "research_notes")
                    continue
                bump(
                    ins if note_once(db, None, "asset_value", f"{name}|{value}") else skip,
                    "research_notes",
                )
            elif r.get("kind") == "liability":
                if not value:
                    bump(skip, "debts")
                    continue
                bump(
                    ins
                    if debt_once(
                        db,
                        name,
                        r.get("category") or "liability",
                        _f(value),
                        0.0,
                        _f(r.get("monthly_amount")),
                    )
                    else skip,
                    "debts",
                )
        db.commit()

        # 5b. authoritative debts from the noticeboard ----------------- #
        for lender, dtype, out_key, rate_key, emi_key in (
            ("SBI Education Loan", "education_loan", "edu_loan_outstanding", "edu_loan_rate", "edu_loan_emi"),
            ("Uncle", "personal_loan", "uncle_remaining", None, "uncle_monthly"),
            ("Slice", "revolving_credit", "slice_closing_balance", None, None),
        ):
            made = debt_once(
                db,
                lender,
                dtype,
                _f(nb.get(out_key)),
                _f(nb.get(rate_key)) if rate_key else 0.0,
                _f(nb.get(emi_key)) if emi_key else 0.0,
            )
            bump(ins if made else skip, "debts")
        db.commit()

        # 6. debt payments — debt_payments_record.csv ----------------- #
        for r in _rows("debt_payments_record.csv"):
            payment = _f(r.get("payment"))
            if not payment:
                continue
            desc = f"debt payment: {r.get('account', '')}".strip()
            made = dedupe_transaction(
                bank_id, r.get("date"), -abs(payment), desc, "debt_payment",
                "outflow", "backfill", conn=db,
            )
            bump(ins if made else skip, "transactions")
        db.commit()

        # 7. realized gains — realized_capital_gains.csv -------------- #
        for r in _rows("realized_capital_gains.csv"):
            content = (
                f"{r.get('scheme_name', '')}|STCG:{_f(r.get('short_term_gain'))}"
                f"|LTCG:{_f(r.get('long_term_gain'))}|FY:{r.get('financial_year', '')}"
                f"|redeem:{r.get('redeem_date', '')}"
            )
            bump(
                ins if note_once(db, None, "realized_gain", content) else skip,
                "research_notes",
            )
        db.commit()

        # 8. monthly summary + salary ------------------------------- #
        latest_month = ""
        for r in _rows("monthly_summary_all_months.csv"):
            month = (r.get("month") or "").strip()
            if not month:
                continue
            latest_month = max(latest_month, month)
            cur = db.execute(
                "INSERT OR IGNORE INTO snapshots (date, net_worth) VALUES (?, ?)",
                (f"{month}-01", None),
            )
            bump(ins if (cur.rowcount or 0) else skip, "snapshots")
        income = _f(nb.get("income"))
        eff = date.today().isoformat()
        if db.execute(
            "SELECT id FROM salary WHERE effective_date = ? AND monthly_net = ?",
            (eff, income),
        ).fetchone():
            bump(skip, "salary")
        else:
            db.execute(
                "INSERT INTO salary (monthly_gross, monthly_net, effective_date) "
                "VALUES (?, ?, ?)",
                (income, income, eff),
            )
            bump(ins, "salary")
        db.commit()

        # 8b. retirement + insurance + restoration notes ------------- #
        bump(
            ins
            if note_once(
                db, None, "epf",
                f"balance:{nb.get('epf_balance')}|monthly:{nb.get('epf_monthly')}|VERIFY",
            )
            else skip,
            "research_notes",
        )
        bump(
            ins if note_once(db, None, "nps", f"balance:{nb.get('nps_balance')}") else skip,
            "research_notes",
        )
        bump(
            ins
            if note_once(
                db, None, "restoration_owed",
                f"{nb.get('restoration_owed')}|14000 small-cap + 12000 UTI Nifty Next 50, "
                "redeemed 2026 for an emergency",
            )
            else skip,
            "research_notes",
        )
        bump(
            ins
            if insurance_once(
                db, "health", "existing_policy",
                _f(nb.get("health_cover_amount")), _f(nb.get("health_cover_annual_premium")),
            )
            else skip,
            "insurance",
        )
        bump(
            ins
            if insurance_once(
                db, "accident", "existing_policy",
                _f(nb.get("accident_cover_amount")), _f(nb.get("accident_cover_annual_premium")),
            )
            else skip,
            "insurance",
        )
        bump(
            ins if insurance_once(db, "term_life", "none", 0.0, 0.0) else skip,
            "insurance",
        )
        db.commit()

        # 9. data_health ------------------------------------------- #
        holding_dates = [
            r.get("date", "") for r in _rows("portfolio_holdings.csv") if r.get("date")
        ]
        cas_last = max(holding_dates) if holding_dates else None
        db.execute(
            "UPDATE data_health SET cas_last_import = ?, sms_last_import = ?, "
            "missing_info = ?, health_score = ? WHERE id = 1",
            (cas_last, latest_month + "-01" if latest_month else None,
             ", ".join(MISSING_INFO), "partial"),
        )
        db.commit()

    # summary -------------------------------------------------------- #
    print(f"backfill from {RECORDS_DIR}")
    print(f"  noticeboard: {'read' if NOTICEBOARD.exists() else 'DEFAULTS (file not found)'}")
    print("  data_health: updated (singleton row)")
    print(f"  {'table':<18}{'inserted':>10}{'skipped':>10}")
    for key in sorted(set(ins) | set(skip)):
        print(f"  {key:<18}{ins.get(key, 0):>10}{skip.get(key, 0):>10}")


if __name__ == "__main__":
    main()
