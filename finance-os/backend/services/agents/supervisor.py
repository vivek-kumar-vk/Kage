"""Agent supervisor — routes a user question to specialist sub-agents and
enforces the privacy boundary. Takes an INJECTED llm client; this module never
imports an LLM SDK at import time."""
from __future__ import annotations

_BLOCKED_KEYS = ("pan", "aadhaar", "account_number", "account number",
                 "acct_no", "cvv", "password", "otp")


def sanitize_for_cloud_llm(payload):
    """Recursively drop keys that must never leave the machine (PAN, bank
    account number, ...). Safe on dicts, lists, and scalars."""
    if isinstance(payload, dict):
        return {k: sanitize_for_cloud_llm(v) for k, v in payload.items()
                if str(k).lower() not in _BLOCKED_KEYS}
    if isinstance(payload, (list, tuple)):
        return [sanitize_for_cloud_llm(v) for v in payload]
    return payload


class Supervisor:
    def __init__(self, llm=None):
        self.llm = llm

    def ask(self, question: str, context=None) -> dict:
        if self.llm is None:
            return {"answer": "(no llm client wired)", "used_context": bool(context)}
        safe = sanitize_for_cloud_llm(context or {})
        return {"answer": self.llm.complete(question, safe), "used_context": bool(context)}
