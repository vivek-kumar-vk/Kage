"""Phase 5 gate — Tracker. Edit+delete a txn; Overview reflects it with no manual refresh.

The 'no manual refresh' contract is a frontend one (cache-version bump + refetch,
built in Phase 2). Here we prove the *data* side: a mutation invalidates the
server-derived Overview numbers immediately."""
from _util import must, ok, die, fresh_db, backend_server, get, post
import urllib.request, urllib.error, json
from check_frontend_hygiene import check as _fe_hygiene
from check_backend_hygiene import check as _be_hygiene
_be_hygiene()
_fe_hygiene()

db = fresh_db()


def req(base, path, method, body=None):
    r = urllib.request.Request(base + path, method=method,
                               data=json.dumps(body or {}).encode(),
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


with backend_server(db) as base:
    post(base, "/api/finance/accounts", {"name": "HDFC Bank", "type": "bank"})
    s, tx = post(base, "/api/finance/import/manual", {
        "entity": "transaction", "account_id": 1, "date": "2026-08-10",
        "description": "Swiggy", "amount": -800, "type": "expense", "category": "food"})
    must(s in (200, 201), f"create txn -> {s}: {tx}")
    tid = tx.get("id") if isinstance(tx, dict) else None
    s, cat1 = get(base, "/api/finance/tracker/categories")
    base_food = json.dumps(cat1)

    # edit
    s, _ = req(base, f"/api/finance/tracker/transactions/{tid}", "PUT",
               {"amount": -2000, "category": "food"})
    must(s in (200, 204), f"edit txn -> {s}")
    s, cf = get(base, "/api/finance/overview/cashflow")
    must("2000" in str(cf) or float(cf.get("expenses", 0)) >= 2000, "cashflow reflects edited amount")

    # delete (hard delete allowed in tracker by design)
    s, _ = req(base, f"/api/finance/tracker/transactions/{tid}", "DELETE")
    must(s in (200, 204), f"delete txn -> {s}")
    s, cat2 = get(base, "/api/finance/tracker/categories")
    must(json.dumps(cat2) != base_food or not cat2, "categories recompute after delete")
    s, cf2 = get(base, "/api/finance/overview/cashflow")
    must(float(cf2.get("expenses", 0)) == 0, "Overview cashflow back to 0 after delete, no stale cache")

    s, rec = get(base, "/api/finance/tracker/recurring")
    must(s == 200, f"/tracker/recurring -> {s}")

ok("phase 5 tracker")
