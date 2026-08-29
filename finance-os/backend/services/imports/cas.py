"""CAS (NSDL / CDSL) PDF parse.

The PAN is the PDF password. It is used ONLY to open the file here and is never
logged and never passed to any LLM (local or cloud). Stub-safe: if pdfplumber or
the file is unavailable it returns [] rather than raising."""
from __future__ import annotations

import io


def parse_cas(file_bytes: bytes, pan: str | None = None) -> list[dict]:
    try:
        import pdfplumber  # noqa: PLC0415
    except Exception:
        return []

    pwd = (pan or "").strip().upper() or None
    rows: list[dict] = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes), password=pwd) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    for r in table:
                        cells = [c for c in (r or []) if c]
                        if len(cells) < 3:
                            continue
                        # column mapping is refined in a later pass; keep the shape
                        rows.append({
                            "symbol": str(cells[0]).strip().upper(),
                            "name": str(cells[1]).strip(),
                            "units": _num(cells[2]),
                            "cost_per_unit": _num(cells[3]) if len(cells) > 3 else None,
                            "type": "mutual_fund",
                            "source": "cas",
                        })
    except Exception:
        return rows
    return rows


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0
