"""Specialist sub-agents. Each takes an INJECTED llm client and never imports an
LLM SDK at module level  [I]."""
from __future__ import annotations


class _Specialist:
    name = "specialist"

    def __init__(self, llm=None):
        self.llm = llm

    def run(self, data=None) -> dict:
        return {"specialist": self.name, "ok": True, "data": data}


class HoldingsAnalyzer(_Specialist):
    name = "holdings_analyzer"


class QualityChecker(_Specialist):
    name = "quality_checker"


class AllocationDrift(_Specialist):
    name = "allocation_drift"


SPECIALISTS = {c.name: c for c in (HoldingsAnalyzer, QualityChecker, AllocationDrift)}
