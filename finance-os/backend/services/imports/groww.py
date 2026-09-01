from __future__ import annotations

import csv
import io


def parse_groww_csv(file_bytes: bytes) -> list[dict]:
    if not file_bytes:
        return []
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8", errors="replace")

    rows = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        symbol = row.get("Symbol") or row.get("symbol") or row.get("Ticker") or ""
        name = row.get("Company Name") or row.get("Name") or row.get("name") or symbol
        units_str = row.get("Quantity") or row.get("Units") or row.get("units") or "0"
        cost_str = row.get("Buy Average") or row.get("Avg Cost") or row.get("Price") or "0"
        date_str = row.get("Date") or row.get("date") or ""

        try:
            units = float(units_str.replace(",", ""))
            cost = float(cost_str.replace(",", ""))
        except ValueError:
            continue

        if not symbol or units == 0:
            continue

        asset_type = "etf" if "etf" in name.lower() else "equity"

        rows.append(
            {
                "symbol": symbol.strip().upper(),
                "name": name.strip(),
                "units": units,
                "cost_per_unit": cost,
                "type": asset_type,
                "purchase_date": date_str[:10] if date_str else "",
                "source": "groww_import",
            }
        )
    return rows