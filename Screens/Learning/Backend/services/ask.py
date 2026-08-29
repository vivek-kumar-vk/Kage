from fastapi import APIRouter
from pydantic import BaseModel

import settings_for_learning as cfg

router = APIRouter()


class AskRequest(BaseModel):
    query: str


@router.post(cfg.API_PREFIX + "/ask")
def ask_question(body: AskRequest):
    return {
        "state": "pending",
        "answer": None,
        "sources": [],
    }
