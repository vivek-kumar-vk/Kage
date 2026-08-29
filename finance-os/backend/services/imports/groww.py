"""Parse a Groww holdings CSV -> list of holding dicts. Tolerant of header
variants (symbol/isin, quantity/units, average_price/avg cost)."""
from __future__ import annotations

import csv
import io


def _num(v, default=0.0):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _pick(row, *names):
    low = {(k or "").lower().strip(): v for k, v in row.items()}
    for n in names:
        if low.get(n) not in (None, ""):
            return low[n]
    return None


def parse_groww_csv(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8", "replace")
    out: list[dict] = []
    for row in csv.DictReader(io.StringIO(text)):
        sym = _pick(row, "symbol", "isin", "scrip", "ticker")
        if not sym:
            continue
        out.append({
            "symbol": str(sym).strip().upper(),
            "name": _pick(row, "name", "company", "scheme", "instrument") or None,
            "units": _num(_pick(row, "quantity", "units", "qty", "shares")),
            "cost_per_unit": _num(_pick(row, "average_price", "avg_price",
                                        "cost per unit", "avg cost", "buy average")),
            "type": "stock",
            "purchase_date": _pick(row, "purchase date", "date", "buy date") or "1970-01-01",
            "source": "groww",
        })
    return out
