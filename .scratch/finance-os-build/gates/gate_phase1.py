"""Phase 1 gate — ingestion & CRUD. Spins the backend against a fresh DB and
exercises ONLY what Phase 1 delivers: accounts CRUD, the Groww CSV import
(idempotent), the weighted-avg upsert, and the background price backfill.

Cross-surface checks (rolling-returns, portfolio-pulse, bond exclusion) live in
the Phase 2 / Phase 3 gates, where the routers they need exist."""
import sqlite3
import time

from _util import BACKEND, backend_server, fresh_db, get, must, ok, post

db = fresh_db()

# --- static: specialists never import an LLM SDK at module level  [I] ---
spec_dir = BACKEND / "services" / "agents"
bad = []
for p in (list(spec_dir.glob("*specialist*.py")) if spec_dir.exists() else []):
    head = "\n".join(p.read_text(encoding="utf-8").splitlines()[:40])
    if any(k in head for k in ("import openai", "from openai", "Ollama(",
                               "import ollama", "litellm", "llama_cpp")):
        bad.append(p.name)
must(not bad, "no module-level LLM import in specialists  [I]: " + ", ".join(bad))

# --- static: upsert_holding exposes a mode param  [C] ---
up = BACKEND / "services" / "calculations" / "holdings_upsert.py"
must(up.exists(), "holdings_upsert.py exists")
src = up.read_text(encoding="utf-8")
must("mode" in src and "set_snapshot" in src and "add_lot" in src,
     "upsert_holding has add_lot vs set_snapshot mode  [C]")

with backend_server(db) as base:
    # accounts CRUD
    s, body = post(base, "/api/finance/accounts", {"name": "Groww Demat", "type": "demat"})
    must(s in (200, 201), f"create account -> {s}: {body}")
    s, rows = get(base, "/api/finance/accounts")
    must(s == 200 and any(r.get("name") == "Groww Demat" for r in rows),
         f"new account shows in GET /accounts -> {s}: {rows}")

    # double Groww CSV import: units set once, not doubled  [C]
    csv = b"symbol,name,quantity,average_price\nINFY,Infosys,10,1500\n"
    multipart = (b"--b\r\nContent-Disposition: form-data; name=\"file\"; "
                 b"filename=\"g.csv\"\r\nContent-Type: text/csv\r\n\r\n" + csv + b"\r\n--b--\r\n")
    ct = "multipart/form-data; boundary=b"
    s1, r1 = post(base, "/api/finance/import/groww-csv", files=multipart, ctype=ct)
    must(s1 == 200, f"first groww import -> {s1}: {r1}")
    s2, r2 = post(base, "/api/finance/import/groww-csv", files=multipart, ctype=ct)
    must(s2 == 200, f"second (idempotent) groww import -> {s2}: {r2}")

    # verify against the DB directly (no investments router in Phase 1)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    infy = con.execute("SELECT units, avg_cost FROM holdings WHERE symbol='INFY'").fetchall()
    must(len(infy) == 1, f"exactly one INFY holding after double import (got {len(infy)})  [C]")
    must(abs(float(infy[0]["units"]) - 10) < 1e-6,
         f"INFY units set to 10, not doubled (got {infy[0]['units']})  [C]")
    lots = con.execute("SELECT COUNT(*) FROM lots l JOIN holdings h ON h.id=l.holding_id "
                       "WHERE h.symbol='INFY'").fetchone()[0]
    must(lots == 1, f"exactly one INFY lot after double import (got {lots})  [C]")

    # background backfill populated price_history for the new symbol  [B]
    got = 0
    for _ in range(15):
        got = con.execute("SELECT COUNT(*) FROM price_history WHERE symbol='INFY'").fetchone()[0]
        if got:
            break
        time.sleep(2)
    con.close()
    must(got > 0, "price_history backfilled for INFY via background task  [B]")

ok("phase 1 ingestion & CRUD")
