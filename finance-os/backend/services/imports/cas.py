from __future__ import annotations

from datetime import datetime


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
    as_of = ""
    if to_text:
        try:
            as_of = datetime.strptime(to_text, "%d-%b-%Y").date().isoformat()
        except ValueError:
            pass

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
                    "units": float(mf["balance"]) if mf.get("balance") is not None else None,
                    "current": float(mf["value"]) if mf.get("value") is not None else None,
                    "total_cost": float(mf["total_cost"]) if mf.get("total_cost") is not None else None,
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
                "units": round(units, 4),
                "current": round(current, 2),
                "invested": round(total_cost, 2) if total_cost is not None else None,
                "full_cost_coverage": full_cost and len(group) == 1,
                "accounts": sorted({g["account"] for g in group}),
            }
        )

    return {"rows": rows, "as_of": as_of, "skipped_stale": [], "unmatched": []}