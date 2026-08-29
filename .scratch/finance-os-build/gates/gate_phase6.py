"""Phase 6 gate — Learning & RAG. Retrieval relevant; ZERO user financial data in chunks."""
from _util import BACKEND, must, ok, die, fresh_db, backend_server, get, post
import pathlib

vs = BACKEND / "data" / "vector_store"
db = fresh_db()
with backend_server(db) as base:
    # seed a holding + a transaction with identifying text, then confirm RAG never returns it
    post(base, "/api/finance/accounts", {"name": "SecretBank AXJ", "type": "bank"})
    post(base, "/api/finance/import/manual", {
        "entity": "transaction", "account_id": 1, "date": "2026-08-01",
        "description": "PAYMENT TO DR MEHTA CLINIC", "amount": -5000, "type": "expense"})

    s, topics = get(base, "/api/finance/learning/topics")
    must(s == 200 and topics, f"/learning/topics -> {s}")

    s, res = get(base, "/api/finance/learning/topic/1")
    must(s == 200, f"/learning/topic/1 -> {s}")
    blob = str(res).lower()
    for leak in ["secretbank axj", "dr mehta", "clinic"]:
        must(leak not in blob, f"no user financial data in retrieved chunk: '{leak}'  [RAG security]")

    s, pers = get(base, "/api/finance/learning/personalized")
    must(s == 200, f"/learning/personalized -> {s}")
    must("secretbank" not in str(pers).lower() and "dr mehta" not in str(pers).lower(),
         "personalized lessons carry no identifying financial data")

ok("phase 6 learning & RAG")
