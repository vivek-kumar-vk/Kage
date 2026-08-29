"""Investment specialist — deterministic analysis over the holdings/price data.
The injected LLM client (if any) is used ONLY to turn the computed facts into a
narrative string; every number here is computed locally. No module-level LLM
import.  [I]
"""
from __future__ import annotations

from typing import Any

from services.calculations import portfolio
from services.db import connect


class HoldingsAnalyzer:
    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def analyze(self) -> dict:
        with connect() as conn:
            summary = portfolio.portfolio_summary(conn)
            rows = portfolio.holdings_with_value(conn)
        summary["holdings_detail"] = rows
        summary["narrative"] = self._narrative(summary)
        return summary

    def _narrative(self, summary: dict) -> str:
        if self.llm_client is None:
            return (
                f"Portfolio value {summary['total_value']:.0f} on invested "
                f"{summary['invested']:.0f} ({summary['gain_loss']:+.0f})."
            )
        try:
            return str(self.llm_client.summarize(summary))
        except Exception:
            return ""


class QualityChecker:
    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def check(self) -> dict:
        with connect() as conn:
            rows = portfolio.holdings_with_value(conn)
            conc = portfolio.concentration(conn)
        flags = []
        for r in rows:
            if (r.get("direct_regular") or "regular") == "regular":
                flags.append({"symbol": r["symbol"], "flag": "regular_plan"})
            if r["weight"] and r["weight"] > 0.25:
                flags.append({"symbol": r["symbol"], "flag": "concentration"})
        return {"top5_weight": conc["top5_weight"], "flags": flags}


class AllocationDrift:
    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def drift(self, targets: dict[str, float] | None = None) -> dict:
        targets = targets or {}
        with connect() as conn:
            alloc = portfolio.asset_allocation(conn)
        actual = {a["bucket"]: a["weight"] for a in alloc["allocation"]}
        buckets = set(actual) | set(targets)
        return {
            "drift": [
                {
                    "bucket": b,
                    "actual": round(actual.get(b, 0.0), 4),
                    "target": round(targets.get(b, 0.0), 4),
                    "delta": round(actual.get(b, 0.0) - targets.get(b, 0.0), 4),
                }
                for b in sorted(buckets)
            ]
        }
