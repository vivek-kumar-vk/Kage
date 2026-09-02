from __future__ import annotations

import datetime as _dt


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date_text(value) -> str:
    """casparser emits datetime.date for CAS-type statements and strings
    for NSDL ones — both land as ISO text, or empty."""
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, str):
        for shape in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return _dt.datetime.strptime(value.strip(), shape).date().isoformat()
            except ValueError:
                continue
    return ""


def parse_cas(file_bytes: bytes, pan: str | None = None) -> dict:
    if not file_bytes:
        return {"rows": [], "as_of": "", "skipped_stale": [], "unmatched": []}

    try:
        import casparser
    except ImportError:
        return {
            "rows": [],
            "as_of": "",
            "skipped_stale": [],
            "unmatched": [],
            "note": "casparser not installed",
        }

    try:
        raw = casparser.read_cas_pdf(file_bytes, pan or "", output="dict")
        data = raw.model_dump() if hasattr(raw, "model_dump") else raw
    except Exception as e:
        return {
            "rows": [],
            "as_of": "",
            "skipped_stale": [],
            "unmatched": [],
            "note": f"parse error: {e}",
        }

    to_text = (data.get("statement_period") or {}).get("to")
    as_of = _date_text(to_text) if to_text else ""

    entries = []
    for account in data.get("accounts") or []:
        account_name = account.get("name") or account.get("type") or "unnamed"
        for mf in account.get("mutual_funds") or []:
            entries.append(
                {
                    "account": account_name,
                    "raw_name": mf.get("name") or "",
                    "amfi_code": (mf.get("amfi") or "").strip(),
                    "isin": (mf.get("isin") or "").strip(),
                    "folio": (mf.get("folio") or "").strip() or None,
                    "units": _num(mf.get("balance")),
                    "current": _num(mf.get("value")),
                    "total_cost": _num(mf.get("total_cost")),
                }
            )

    groups: dict[str, list[dict]] = {}
    for e in entries:
        key = e["amfi_code"] or e["isin"] or f"__no_id__::{e['raw_name']}"
        groups.setdefault(key, []).append(e)

    rows = []
    for group in groups.values():
        units = sum(g["units"] for g in group if g["units"] is not None)
        current = sum(g["current"] for g in group if g["current"] is not None)
        costs = [g["total_cost"] for g in group]
        full_cost = all(c is not None for c in costs)
        total_cost = sum(costs) if full_cost else None
        rows.append(
            {
                "amfi_code": next((g["amfi_code"] for g in group if g["amfi_code"]), ""),
                "isin": next((g["isin"] for g in group if g["isin"]), ""),
                "name": next((g["raw_name"] for g in group), ""),
                "folio": next((g["folio"] for g in group if g["folio"]), None),
                "units": round(units, 4),
                "current": round(current, 2),
                "invested": round(total_cost, 2) if total_cost is not None else None,
                "full_cost_coverage": full_cost and len(group) == 1,
                "accounts": sorted({g["account"] for g in group}),
            }
        )

    # Purchase lots: a FOLIO-type CAS carries the full scheme transaction
    # history (Scheme.transactions); an NSDL demat CAS carries balances
    # only — for those, lots stay empty and the import says so honestly.
    lots: list[dict] = []
    for folio in data.get("folios") or []:
        for scheme in folio.get("schemes") or []:
            key = (scheme.get("amfi") or "").strip() or (scheme.get("isin") or "").strip()
            for tx in scheme.get("transactions") or []:
                units = _num(tx.get("units"))
                amount = _num(tx.get("amount"))
                day = _date_text(tx.get("date"))
                # a purchase leg: positive units with a real amount and date
                if not key or not day or not units or units <= 0 \
                        or not amount or amount <= 0:
                    continue
                cost = round(amount / units, 6)
                if cost <= 0:
                    continue
                lots.append({
                    "key": key, "purchase_date": day,
                    "units": round(units, 4), "cost_per_unit": cost,
                    "description": (tx.get("description") or "").strip(),
                })

    return {"rows": rows, "as_of": as_of, "lots": lots,
            "skipped_stale": [], "unmatched": []}
