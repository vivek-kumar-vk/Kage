"""Learning specialist — deterministic. `Retriever` wraps the local RAG index;
`Personalizer` picks PUBLIC lesson slugs from the SHAPE of the portfolio/debt
(counts and booleans only — never names, descriptions, or amounts that identify
anything). No FastAPI, no module-level LLM import.  [I][RAG security]
"""
from __future__ import annotations

from typing import Any

from services import rag
from services.db import connect


class Retriever:
    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        return rag.retrieve(query, k)


class Personalizer:
    """Maps a private SHAPE -> public lesson slugs. The SHAPE is read here, but
    only aggregate counts leave this class; the returned lessons are whole public
    documents."""

    def __init__(self, llm_client: Any | None = None):
        self.llm_client = llm_client

    def shape(self) -> dict:
        with connect() as db:
            regular_funds = db.execute(
                "SELECT COUNT(*) FROM active_holdings "
                "WHERE COALESCE(direct_regular,'regular') = 'regular' "
                "AND COALESCE(type,'') IN ('mutual_fund','etf')"
            ).fetchone()[0]
            high_rate_debt = db.execute(
                "SELECT COUNT(*) FROM debts WHERE status='active' "
                "AND archived_at IS NULL AND COALESCE(interest_rate,0) >= 24"
            ).fetchone()[0]
            any_debt = db.execute(
                "SELECT COUNT(*) FROM debts WHERE status='active' AND archived_at IS NULL"
            ).fetchone()[0]
            expense = db.execute(
                "SELECT COALESCE(SUM(-amount),0) FROM transactions WHERE amount < 0"
            ).fetchone()[0]
            income = db.execute(
                "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE amount > 0"
            ).fetchone()[0]
            holdings = db.execute("SELECT COUNT(*) FROM active_holdings").fetchone()[0]
        return {
            "regular_plan_funds": int(regular_funds),
            "high_rate_debt": int(high_rate_debt),
            "any_debt": int(any_debt),
            "negative_cashflow": bool(income - expense < 0),
            "holdings": int(holdings),
        }

    def lesson_slugs(self, shape: dict | None = None) -> list[str]:
        s = shape or self.shape()
        picks: list[str] = []
        if s["high_rate_debt"] or s["any_debt"]:
            picks.append("debt-avalanche-vs-snowball")
        if s["regular_plan_funds"]:
            picks.append("direct-vs-regular-plans")
            picks.append("expense-ratio-and-ter")
        if s["negative_cashflow"]:
            picks.append("emergency-fund-basics")
        if s["holdings"] == 0:
            picks.append("index-investing-basics")
        if not picks:
            picks = ["index-investing-basics", "emergency-fund-basics"]
        seen: set[str] = set()
        return [p for p in picks if not (p in seen or seen.add(p))]

    def lessons(self) -> list[dict]:
        out = []
        for slug in self.lesson_slugs():
            t = rag.topic_by_slug(slug)
            if t:
                out.append({"slug": slug, "title": t["title"], "content": t["content"]})
        return out
