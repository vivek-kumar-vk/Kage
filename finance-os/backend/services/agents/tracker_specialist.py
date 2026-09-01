"""Tracker specialist — deterministic detectors over the transaction list. The
injected LLM client (if any) only writes the narrative. No FastAPI here, no
module-level LLM import.  [I]
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from services.db import connect


def _parse(d: str | None):
    try:
        return _dt.date.fromisoformat(str(d)[:10])
    except (TypeError, ValueError):
        return None


class RecurringDetector:
    """Same payee, 3+ hits, roughly-monthly cadence, similar amount."""

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def detect(self, txns: list[dict]) -> list[dict]:
        by_payee: dict[str, list[dict]] = {}
        for t in txns:
            key = (t.get("description") or "").strip().lower()
            if key:
                by_payee.setdefault(key, []).append(t)
        out = []
        for payee, group in by_payee.items():
            if len(group) < 3:
                continue
            amounts = [abs(float(g.get("amount") or 0)) for g in group]
            avg = sum(amounts) / len(amounts)
            if avg == 0 or max(abs(a - avg) for a in amounts) > 0.25 * avg:
                continue
            dates = sorted(d for d in (_parse(g.get("date")) for g in group) if d)
            if len(dates) >= 2:
                gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
                if not (20 <= sum(gaps) / len(gaps) <= 40):
                    continue
            out.append({"payee": payee, "occurrences": len(group),
                        "avg_amount": round(avg, 2)})
        return sorted(out, key=lambda x: -x["occurrences"])


class LeakFinder:
    """Leak of the week — the discretionary category burning the most cash."""

    _DISCRETIONARY = {"entertainment", "shopping", "food"}

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def find(self, txns: list[dict]) -> dict:
        spend: dict[str, float] = {}
        for t in txns:
            amt = float(t.get("amount") or 0)
            cat = (t.get("category") or "other").lower()
            if amt < 0 and cat in self._DISCRETIONARY:
                spend[cat] = spend.get(cat, 0.0) + (-amt)
        if not spend:
            return {"leak": None, "amount": 0.0}
        cat, amt = max(spend.items(), key=lambda kv: kv[1])
        return {"leak": cat, "amount": round(amt, 2)}


class BudgetDrift:
    """Month-over-month change in total expense."""

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def detect(self, txns: list[dict]) -> dict:
        by_month: dict[str, float] = {}
        for t in txns:
            amt = float(t.get("amount") or 0)
            d = _parse(t.get("date"))
            if amt < 0 and d:
                key = d.strftime("%Y-%m")
                by_month[key] = by_month.get(key, 0.0) + (-amt)
        months = sorted(by_month)
        if len(months) < 2:
            return {"drift": 0.0, "current": by_month.get(months[-1], 0.0) if months else 0.0}
        cur, prev = by_month[months[-1]], by_month[months[-2]]
        return {"drift": round(cur - prev, 2), "current": round(cur, 2),
                "previous": round(prev, 2)}


def run_all(llm_client: Any | None = None) -> dict:
    with connect() as conn:
        txns = [{k: r[k] for k in r.keys()}
                for r in conn.execute("SELECT * FROM transactions").fetchall()]
    return {
        "recurring": RecurringDetector(llm_client).detect(txns),
        "leak": LeakFinder(llm_client).find(txns),
        "drift": BudgetDrift(llm_client).detect(txns),
    }
