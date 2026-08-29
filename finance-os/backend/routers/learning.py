"""Learning tab. Mounted by app_factory with prefix /api/finance
-> /api/finance/learning/*.

Only PUBLIC educational content is ever served. `/personalized` reads the SHAPE
of the portfolio/debt (counts, booleans) to CHOOSE lessons, but every byte
returned is a whole public document from `backend/content/`.  [RAG security]
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services import rag
from services.agents.learning_specialist import Personalizer

router = APIRouter(prefix="/learning")


@router.get("/topics")
def list_topics():
    return {"topics": rag.topics()}


@router.get("/topic/{topic_id}")
def get_topic(topic_id: int):
    t = rag.topic(topic_id)
    if t is None:
        raise HTTPException(status_code=404, detail="topic not found")
    return t


@router.get("/search")
def search(q: str, k: int = 5):
    return {"query": q, "results": rag.retrieve(q, k)}


@router.get("/personalized")
def personalized():
    p = Personalizer()
    return {"lessons": p.lessons()}
