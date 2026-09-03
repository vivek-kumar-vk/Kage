"""Debt specialist — wraps the deterministic calculators. The injected LLM
client (if any) only turns computed facts into the Action / Reason / Learn
narrative; every number is computed locally. No module-level LLM import.  [I]
"""
from __future__ import annotations

from typing import Any

from services.calculations import debt as calc
from services.db import connect


class DebtSpecialist:
    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def assess(self) -> dict:
        with connect() as conn:
            debts = calc.list_debts(conn)
            plan = calc.payoff_plan(conn, method="avalanche")
            sim = calc.simulate(conn, extra_payment=5000)
        facts = {
            "total_outstanding": plan["total_outstanding"],
            "order": [s["lender"] for s in plan["steps"]],
            "sample_extra_5000": sim,
        }
        if not debts:
            arl = {
                "action": "No action needed",
                "reason": "You have no active debt.",
                "learn": "Keep it that way — pay any new card in full each cycle.",
            }
        else:
            top = calc.avalanche_order(debts)[0]
            base = calc.learning("credit_card" if top.get("type") == "credit_card"
                                 else "avalanche")
            arl = {
                "action": f"{base['action']} — start with {top['lender']}",
                "reason": base["reason"],
                "learn": self._narrative(base["learn"], facts),
            }
        return {"facts": facts, **arl}

    def _narrative(self, base_text: str, facts: dict) -> str:
        if self.llm_client is None:
            return base_text
        try:
            return str(self.llm_client.summarize({"base": base_text, "facts": facts}))
        except Exception:
            return base_text
