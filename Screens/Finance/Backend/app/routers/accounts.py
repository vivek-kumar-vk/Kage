"""Accounts CRUD — stdlib sqlite3 via services.db.connect(). Soft-delete only."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.db import connect

router = APIRouter()


class AccountIn(BaseModel):
    name: str
    type: str
    institution: str | None = None
    currency: str = "INR"


class AccountPatch(BaseModel):
    name: str | None = None
    type: str | None = None
    institution: str | None = None
    currency: str | None = None
    archived_at: str | None = None


def _dict(row):
    return {k: row[k] for k in row.keys()}


@router.get("/accounts")
def list_accounts(include_archived: bool = False):
    q = "SELECT * FROM accounts"
    if not include_archived:
        q += " WHERE archived_at IS NULL"
    with connect() as db:
        return [_dict(r) for r in db.execute(q + " ORDER BY id").fetchall()]


@router.post("/accounts", status_code=201)
def create_account(body: AccountIn):
    with connect() as db:
        try:
            cur = db.execute(
                "INSERT INTO accounts(name,type,institution,currency) VALUES (?,?,?,?)",
                (body.name, body.type, body.institution, body.currency),
            )
            db.commit()
        except Exception as e:  # UNIQUE(name) etc.
            raise HTTPException(status_code=409, detail=str(e))
        row = db.execute("SELECT * FROM accounts WHERE id=?", (cur.lastrowid,)).fetchone()
    return _dict(row)


@router.get("/accounts/{account_id}")
def get_account(account_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="account not found")
    return _dict(row)


@router.patch("/accounts/{account_id}")
def update_account(account_id: int, body: AccountPatch):
    fields = {k: v for k, v in body.dict().items() if v is not None}
    with connect() as db:
        if not db.execute("SELECT 1 FROM accounts WHERE id=?", (account_id,)).fetchone():
            raise HTTPException(status_code=404, detail="account not found")
        if fields:
            sets = ", ".join(f"{k}=?" for k in fields)
            db.execute(f"UPDATE accounts SET {sets} WHERE id=?",
                       (*fields.values(), account_id))
            db.commit()
        row = db.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    return _dict(row)


@router.delete("/accounts/{account_id}", status_code=204)
def archive_account(account_id: int):
    with connect() as db:
        db.execute("UPDATE accounts SET archived_at=CURRENT_TIMESTAMP WHERE id=?",
                   (account_id,))
        db.commit()
