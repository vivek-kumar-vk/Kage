"""Tracker tab — transactions are individually correctable, so HARD DELETE is
allowed here (unlike accounts/holdings). Mounted by app_factory with prefix
/api/finance -> /api/finance/tracker/*.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from services.db import connect

router = APIRouter(prefix="/tracker")

# Source of truth: finance-os/shared/constants/categories.py (kept in sync here
# because that package is not on the backend import path).
TRANSACTION_CATEGORIES = (
    "food", "transport", "utilities", "rent", "health", "entertainment",
    "shopping", "education", "investment", "income", "transfer",
    "debt_payment", "other",
)


def _db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _row(conn, tid: int):
    return conn.execute("SELECT * FROM transactions WHERE id = ?", (tid,)).fetchone()


@router.get("/transactions")
def list_transactions(date_from: str | None = None, date_to: str | None = None,
                      category: str | None = None, account_id: int | None = None,
                      conn=Depends(_db)):
    sql = "SELECT * FROM transactions WHERE 1=1"
    args: list = []
    if date_from:
        sql += " AND date >= ?"; args.append(date_from)
    if date_to:
        sql += " AND date <= ?"; args.append(date_to)
    if category:
        sql += " AND category = ?"; args.append(category)
    if account_id:
        sql += " AND account_id = ?"; args.append(account_id)
    sql += " ORDER BY date DESC, id DESC"
    return [{k: r[k] for k in r.keys()} for r in conn.execute(sql, args).fetchall()]


@router.get("/transactions/{tid}")
def get_transaction(tid: int, conn=Depends(_db)):
    r = _row(conn, tid)
    if not r:
        raise HTTPException(status_code=404, detail="transaction not found")
    return {k: r[k] for k in r.keys()}


@router.put("/transactions/{tid}")
def update_transaction(tid: int, payload: dict = Body(default={}), conn=Depends(_db)):
    if not _row(conn, tid):
        raise HTTPException(status_code=404, detail="transaction not found")
    p = payload or {}
    if "category" in p and p["category"] not in TRANSACTION_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"bad category '{p['category']}'")
    allowed = {"date", "description", "amount", "category", "type", "account_id"}
    sets = {k: v for k, v in p.items() if k in allowed}
    if sets:
        cols = ", ".join(f"{k} = ?" for k in sets)
        conn.execute(f"UPDATE transactions SET {cols} WHERE id = ?",
                     (*sets.values(), tid))
        conn.commit()
    return get_transaction(tid, conn)


@router.delete("/transactions/{tid}")
def delete_transaction(tid: int, conn=Depends(_db)):
    if not _row(conn, tid):
        raise HTTPException(status_code=404, detail="transaction not found")
    conn.execute("DELETE FROM transactions WHERE id = ?", (tid,))
    conn.commit()
    return {"state": "ok", "deleted": tid}


@router.get("/categories")
def categories(conn=Depends(_db)):
    rows = conn.execute(
        "SELECT COALESCE(category,'uncategorised') AS category, "
        "SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS spent, "
        "SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS received, "
        "COUNT(*) AS n "
        "FROM transactions GROUP BY COALESCE(category,'uncategorised') "
        "ORDER BY spent DESC"
    ).fetchall()
    return {
        "state": "ok" if rows else "pending",
        "categories": [
            {"category": r["category"], "spent": round(float(r["spent"] or 0), 2),
             "received": round(float(r["received"] or 0), 2), "count": r["n"]}
            for r in rows
        ],
    }


@router.get("/recurring")
def recurring(conn=Depends(_db)):
    rows = conn.execute(
        "SELECT LOWER(TRIM(description)) AS payee, COUNT(*) AS n, "
        "AVG(amount) AS avg_amount, MIN(date) AS first_seen, MAX(date) AS last_seen "
        "FROM transactions WHERE description IS NOT NULL AND TRIM(description) <> '' "
        "GROUP BY LOWER(TRIM(description)) HAVING COUNT(*) >= 3 ORDER BY n DESC"
    ).fetchall()
    return {
        "state": "ok",
        "recurring": [
            {"payee": r["payee"], "occurrences": r["n"],
             "avg_amount": round(float(r["avg_amount"] or 0), 2),
             "first_seen": r["first_seen"], "last_seen": r["last_seen"]}
            for r in rows
        ],
    }


@router.get("/trends")
def trends(conn=Depends(_db)):
    rows = conn.execute(
        "SELECT strftime('%Y-%m', date) AS month, "
        "SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS income, "
        "SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS expense "
        "FROM transactions GROUP BY strftime('%Y-%m', date) ORDER BY month ASC"
    ).fetchall()
    series = [
        {"month": r["month"], "income": round(float(r["income"] or 0), 2),
         "expense": round(float(r["expense"] or 0), 2)}
        for r in rows
    ]
    return {"state": "ok" if series else "pending", "series": series}


@router.get("/insights")
def insights(conn=Depends(_db)):
    out: list[dict] = []
    top = conn.execute(
        "SELECT category, SUM(-amount) AS s FROM transactions WHERE amount < 0 "
        "AND category IS NOT NULL GROUP BY category ORDER BY s DESC LIMIT 1"
    ).fetchone()
    if top and top["s"]:
        out.append({"title": "Top spend category",
                    "detail": f"{top['category']} — {round(float(top['s']), 2)}"})
    unc = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE category IS NULL OR category = ''"
    ).fetchone()[0]
    if unc:
        out.append({"title": "Uncategorised transactions",
                    "detail": f"{unc} need a category"})
    return {"state": "ok", "insights": out}
