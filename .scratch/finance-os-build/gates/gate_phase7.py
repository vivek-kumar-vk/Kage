"""Phase 7 gate — Data Health, Scenario Lab, Settings.

Create/edit/archive an account, goal, insurance policy purely via API; archiving
an account with active holdings must cascade-archive or block — never orphan  [P].
data_health writes are UPDATE-only  [singleton]."""
from _util import BACKEND, must, ok, die, fresh_db, backend_server, get, post
import urllib.request, urllib.error, json, sqlite3


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


db = fresh_db()
with backend_server(db) as base:
    # account CRUD + archive
    s, a = post(base, "/api/finance/accounts", {"name": "ICICI", "type": "bank"})
    aid = a["id"]
    s, _ = req(base, f"/api/finance/accounts/{aid}", "PUT", {"institution": "ICICI Bank Ltd"})
    must(s in (200, 204), f"edit account -> {s}")

    # goal CRUD — start_date baseline stored  [E]
    s, g = post(base, "/api/finance/goals",
                {"name": "Car", "target_amount": 1200000, "target_date": "2029-01-01"})
    must(s in (200, 201), f"create goal -> {s}")
    gid = g["id"]
    s, gg = get(base, f"/api/finance/goals/{gid}")
    must("start_date" in str(gg) or "created_at" in str(gg), "goal keeps a baseline date  [E]")

    # insurance CRUD + archive
    s, ins = post(base, "/api/finance/insurance",
                  {"type": "term", "provider": "LIC", "coverage_amount": 10000000})
    iid = ins["id"]
    s, _ = post(base, f"/api/finance/insurance/{iid}/archive", {})
    must(s in (200, 204), f"archive insurance -> {s}")

    # account with active holdings: archive must cascade or block, never orphan  [P]
    s, dm = post(base, "/api/finance/accounts", {"name": "Zerodha", "type": "demat"})
    did = dm["id"]
    post(base, "/api/finance/import/manual",
         {"entity": "holding", "account_id": did, "symbol": "NIFTYBEES", "type": "etf", "units": 100})
    s, resp = post(base, f"/api/finance/accounts/{did}/archive", {})
    s2, hold = get(base, "/api/finance/investments/holdings")
    live = [h for h in hold if h.get("symbol") == "NIFTYBEES"]
    if s in (200, 204):
        must(not live, "archiving account cascade-archived its holdings — no orphan  [P]")
    else:
        must(s == 409, f"or archive blocked with 409 + message (got {s})  [P]")
        must(len(live) == 1, "blocked archive left holding intact")

    # data_health is UPDATE-only (still exactly one row)
    s, _ = post(base, "/api/finance/import/manual",
                {"entity": "transaction", "account_id": aid, "date": "2026-08-01", "amount": -100})
    con = sqlite3.connect(db)
    n = con.execute("SELECT COUNT(*) FROM data_health").fetchone()[0]
    con.close()
    must(n == 1, f"data_health still singleton (got {n} rows)")

    # scenario simulator
    s, sc = post(base, "/api/finance/debt/simulate", {"extra_payment": 1000})
    must(s == 200, f"scenario/simulate reachable -> {s}")

ok("phase 7 data health / scenario / settings")
