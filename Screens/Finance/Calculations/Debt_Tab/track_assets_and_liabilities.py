"""What I own and what I owe, outside the surplus formula.

WHY THIS IS SEPARATE FROM THE SURPLUS/NOTICEBOARD NUMBERS
    calculate_surplus.py already knows about the two loans that move
    the monthly surplus (the personal debt and the education loan) and
    the fixed bills, because those are hand-entered on the noticeboard
    and change the answer to "how much is left this month".

    This file answers a different, slower question: across everything
    I own and owe - insurance, subscriptions, FDs, a bank balance, a
    loan EMI - what does my situation actually look like, and what does
    it cost me every month. Nothing here feeds back into the surplus
    formula automatically; a double-counted EMI would be a worse bug
    than a screen that asks you to enter it in two places for two
    different questions.

Saved_Records/assets_and_liabilities.csv
    date_added,kind,category,name,monthly_amount,value,notes

    kind             asset | liability
    category         asset: bank_balance | fixed_deposit | provident_fund |
                       real_estate | gold | other
                       liability, borrowed money (debt): loan | secured_loan |
                       consumer_credit | credit_card
                       liability, not borrowed money: insurance_premium |
                       subscription | other_recurring
    monthly_amount   what it costs or contributes every month; blank if
                       it is not a recurring item
    value            current value (asset) or current outstanding
                      (liability); blank if not known

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Debt_Tab\\track_assets_and_liabilities.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
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

from Shared_By_All_Screens.read_and_write_numbers import write_state  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COLUMNS = ["date_added", "kind", "category", "name", "monthly_amount", "value", "notes"]

ASSET_CATEGORIES = {"bank_balance", "fixed_deposit", "provident_fund", "real_estate", "gold", "other"}
LIABILITY_CATEGORIES = {
    # Borrowed money - the accounting definition of debt.
    "loan",              # an unstructured or personal loan (e.g. family/personal debt)
    "secured_loan",      # collateralised borrowing, e.g. Groww loan against pledged mutual funds
    "consumer_credit",   # a consumer-durable / EMI card line, e.g. Bajaj Finance EMI card
    "credit_card",       # revolving card balance
    # Obligations that are NOT borrowed money - liabilities without being debt.
    "insurance_premium",
    "subscription",
    "other_recurring",
}
# The line the page draws between "debt" and "other liabilities" is this
# set, nothing prose-y - a category either names borrowed money or it
# does not (Wikipedia: debt is "an obligation to pay borrowed money").
DEBT_CATEGORIES = {"loan", "secured_loan", "consumer_credit", "credit_card"}


class TheRecordsAreWrong(Exception):
    """Raised when a row cannot be trusted. Never guessed around."""


def records_path() -> Path:
    return SCREEN / "Saved_Records" / "assets_and_liabilities.csv"


def start_the_records_if_missing() -> Path:
    where = records_path()
    where.parent.mkdir(parents=True, exist_ok=True)
    if not where.exists():
        with where.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(COLUMNS)
    return where


def _number(text: str, where: str, field: str) -> float | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        raise TheRecordsAreWrong(f"{where}: {field} '{text}' is not a number")


def read_every_row() -> list[dict]:
    """Return the rows, checked. A bad row stops the read and names itself."""
    where = records_path()
    if not where.exists():
        return []

    rows = []
    with where.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise TheRecordsAreWrong("assets_and_liabilities.csv is missing columns: " + ", ".join(missing))

        for line_number, row in enumerate(reader, start=2):
            if not any((row.get(c) or "").strip() for c in COLUMNS):
                continue
            where_line = f"assets_and_liabilities.csv line {line_number}"

            kind = (row.get("kind") or "").strip().lower()
            if kind not in ("asset", "liability"):
                raise TheRecordsAreWrong(f"{where_line}: kind is '{kind}'. It must be asset or liability.")

            category = (row.get("category") or "").strip().lower()
            allowed = ASSET_CATEGORIES if kind == "asset" else LIABILITY_CATEGORIES
            if category not in allowed:
                raise TheRecordsAreWrong(
                    f"{where_line}: category '{category}' is not valid for kind={kind}. "
                    f"Allowed: {', '.join(sorted(allowed))}"
                )

            name = (row.get("name") or "").strip()
            if not name:
                raise TheRecordsAreWrong(f"{where_line}: no name given")

            rows.append({
                "date_added": (row.get("date_added") or "").strip(),
                "kind": kind, "category": category, "name": name,
                "monthly_amount": _number(row.get("monthly_amount"), where_line, "monthly_amount"),
                "value": _number(row.get("value"), where_line, "value"),
                "notes": (row.get("notes") or "").strip(),
            })
    return rows


def publish_to_noticeboard(summary: dict) -> None:
    """Hand the two totals to the noticeboard, the only channel out of
    this screen (C8, ADR-010). Main Menu's home cards read them from
    there; this file never hears back from Main Menu at all.

    Deliberately NOT called from a_summary_for_the_screen() itself: that
    function has to stay a pure read, because tests call it against a
    fixture ledger, and a write buried inside it would overwrite the
    real noticeboard with fixture numbers every time the test suite
    runs. The server route calls this, once, after it has a real
    summary - see server_for_finance.py's /liabilities endpoint.
    """
    if summary["has_data"]:
        write_state({
            "total_assets": summary["total_assets"],
            "total_liabilities": summary["total_liabilities"],
        })
    else:
        write_state({"total_assets": None, "total_liabilities": None})


def a_summary_for_the_screen() -> dict:
    """Net worth, and what the liabilities cost every month.

    Every total is has_data-guarded: an empty ledger says so plainly
    rather than showing a net worth of zero, which would be a real
    figure claiming to be measured.
    """
    rows = read_every_row()
    if not rows:
        return {"has_data": False, "note": (
            "Saved_Records/assets_and_liabilities.csv has nothing in it yet. "
            "Add one row per thing you own or owe and this fills in."
        )}

    assets = [r for r in rows if r["kind"] == "asset"]
    liabilities = [r for r in rows if r["kind"] == "liability"]

    # The page draws one hard line inside the liabilities: borrowed
    # money (debt) vs every other obligation. The line is the category
    # set above - not a judgement made in prose.
    for r in liabilities:
        r["is_debt"] = r["category"] in DEBT_CATEGORIES

    assets_known = [r for r in assets if r["value"] is not None]
    liabilities_known = [r for r in liabilities if r["value"] is not None]

    total_assets = sum(r["value"] for r in assets_known)
    total_liabilities = sum(r["value"] for r in liabilities_known)
    total_debt = sum(r["value"] for r in liabilities_known if r["is_debt"])
    other_liabilities = total_liabilities - total_debt

    monthly_by_category: dict[str, float] = defaultdict(float)
    for r in liabilities:
        if r["monthly_amount"] is not None:
            monthly_by_category[r["category"]] += r["monthly_amount"]

    return {
        "has_data": True,
        "net_worth": {
            "value": round(total_assets - total_liabilities, 2),
            "complete": len(assets_known) == len(assets) and len(liabilities_known) == len(liabilities),
            "assets_missing_a_value": len(assets) - len(assets_known),
            "liabilities_missing_a_value": len(liabilities) - len(liabilities_known),
        },
        "total_assets": round(total_assets, 2),
        "total_liabilities": round(total_liabilities, 2),
        "monthly_recurring_liabilities": round(sum(monthly_by_category.values()), 2),
        "monthly_by_category": {k: round(v, 2) for k, v in sorted(monthly_by_category.items())},
        "debt_split": {
            "borrowed_total": round(total_debt, 2),
            "other_total": round(other_liabilities, 2),
            "borrowed_missing_a_value": len([r for r in liabilities if r["is_debt"] and r["value"] is None]),
            "other_missing_a_value": len([r for r in liabilities if not r["is_debt"] and r["value"] is None]),
        },
        "assets": sorted(assets, key=lambda r: (r["value"] or 0), reverse=True),
        "liabilities": sorted(
            liabilities,
            key=lambda r: (not r["is_debt"], r["value"] or 0),
            reverse=True,
        ),
        "note": (
            "These monthly figures are informational and are never added into "
            "the surplus formula automatically - enter a figure on the "
            "noticeboard by hand if it should change what Overview shows, so "
            "nothing is counted twice."
        ),
    }


def main() -> None:
    start_the_records_if_missing()
    summary = a_summary_for_the_screen()
    print("ASSETS AND LIABILITIES")
    print()
    if not summary["has_data"]:
        print(f"  {summary['note']}")
        return
    print(f"  net worth            Rs {summary['net_worth']['value']:,.2f}"
         + ("" if summary["net_worth"]["complete"] else "  (incomplete - some values are blank)"))
    print(f"  total assets          Rs {summary['total_assets']:,.2f}")
    print(f"  total liabilities     Rs {summary['total_liabilities']:,.2f}")
    print(f"  monthly recurring     Rs {summary['monthly_recurring_liabilities']:,.2f}")


if __name__ == "__main__":
    main()
