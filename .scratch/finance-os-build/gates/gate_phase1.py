"""Phase 1 gate — ingestion & CRUD. Spins up the backend against a fresh DB."""
import time, pathlib, sys
from _util import REPO, BACKEND, must, ok, die, fresh_db, backend_server, get, post, grep_repo

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
db = fresh_db()

# --- static: specialists must not import an LLM client at module level  [I] ---
spec_dir = BACKEND / "services" / "agents"
bad = []
for p in spec_dir.glob("*_specialist.py") if spec_dir.exists() else []:
    head = "\n".join(p.read_text(encoding="utf-8").splitlines()[:40])
    if any(k in head for k in ("import openai", "from openai", "Ollama(", "import ollama", "litellm")):
        bad.append(p.name)
must(not bad, "no module-level LLM import in specialists  [I]: " + ", ".join(bad))

# --- static: upsert_holding exposes a mode param  [C] ---
up = BACKEND / "services" / "calculations" / "holdings_upsert.py"
must(up.exists(), "holdings_upsert.py exists")
src = up.read_text(encoding="utf-8")
must("mode" in src and ("set_snapshot" in src or "add_lot" in src),
     "upsert_holding has add_lot vs set_snapshot mode  [C]")

with backend_server(db) as base:
    # CRUD smoke
    s, _ = post(base, "/api/finance/accounts", {"name": "Groww Demat", "type": "demat"})
    must(s in (200, 201), f"create account -> {s}")

    # double Groww CSV import: units set once, no crash, avg_cost stable  [C]
    csv = (FIX / "groww_sample.csv").read_bytes() if (FIX / "groww_sample.csv").exists() else \
        b"symbol,name,quantity,average_price\nINFY,Infosys,10,1500\n"
    body = b"--b\r\nContent-Disposition: form-data; name=\"file\"; filename=\"g.csv\"\r\n" \
           b"Content-Type: text/csv\r\n\r\n" + csv + b"\r\n--b--\r\n"
    s1, r1 = post(base, "/api/finance/import/groww-csv", files=body, ctype="multipart/form-data; boundary=b")
    must(s1 == 200, f"first groww import -> {s1}: {r1}")
    s2, r2 = post(base, "/api/finance/import/groww-csv", files=body, ctype="multipart/form-data; boundary=b")
    must(s2 == 200, f"second (idempotent) groww import -> {s2}: {r2}")
    s, hold = get(base, "/api/finance/investments/holdings")
    infy = [h for h in hold if h.get("symbol", "").startswith("INFY")]
    must(len(infy) == 1, f"exactly one INFY holding after double import (got {len(infy)})  [C]")
    must(abs(float(infy[0]["units"]) - 10) < 1e-6, f"units set to 10 not doubled (got {infy[0]['units']})  [C]")

    # background backfill populated price_history within ~30s  [B]
    got = False
    for _ in range(15):
        s, r = get(base, "/api/finance/investments/visuals/rolling-returns")
        if s == 200 and r and (isinstance(r, dict) and r.get("series") or isinstance(r, list) and r):
            got = True
            break
        time.sleep(2)
    must(got, "price_history backfilled for new symbol via background task  [B]")

    # bond excluded from portfolio value, never a ₹0 row  [J/M]
    post(base, "/api/finance/import/manual",
         {"entity": "holding", "account_id": 1, "symbol": "SGB2031", "type": "bond", "units": 5})
    s, pulse = get(base, "/api/finance/overview/portfolio-pulse")
    txt = str(pulse)
    must("SGB2031" not in txt or "excluded" in txt.lower(),
         "bond holding excluded from portfolio value, not shown as ₹0  [J/M]")

ok("phase 1 ingestion & CRUD")
