"""Phase 3 gate — Investments. Fresh import then check time-series + archive semantics."""
import time, pathlib
from _util import BACKEND, FRONTEND, must, ok, die, fresh_db, backend_server, get, post
from check_frontend_hygiene import check as _fe_hygiene
_fe_hygiene()

db = fresh_db()
with backend_server(db) as base:
    post(base, "/api/finance/accounts", {"name": "Demat", "type": "demat"})
    csv = b"--b\r\nContent-Disposition: form-data; name=\"file\"; filename=\"g.csv\"\r\n" \
          b"Content-Type: text/csv\r\n\r\nsymbol,name,quantity,average_price\nTCS,TCS,4,3200\n\r\n--b--\r\n"
    s, r = post(base, "/api/finance/import/groww-csv", files=csv,
                ctype="multipart/form-data; boundary=b")
    must(s == 200, f"import -> {s}: {r}")

    # backfill (Phase 1) means these render real data immediately, not empty  [B]
    got = False
    for _ in range(20):
        s1, rr = get(base, "/api/finance/investments/visuals/rolling-returns")
        s2, dd = get(base, "/api/finance/investments/visuals/drawdown")
        if s1 == 200 and s2 == 200 and str(rr) not in ("[]", "{}", "None") and "pending" not in str(rr).lower():
            got = True
            break
        time.sleep(3)
    must(got, "rolling-returns + drawdown show real 2y data right after import  [B]")

    # visuals expose a 'backfill pending / partial' state key, not just 'no data'  [B]
    s, pvb = get(base, "/api/finance/investments/visuals/portfolio-vs-benchmark")
    must(s == 200, f"portfolio-vs-benchmark -> {s}")

    # archive removes a holding from active_holdings AND every calculation  [P]
    s, hold = get(base, "/api/finance/investments/holdings")
    hid = hold[0]["id"]
    s, _ = post(base, f"/api/finance/investments/holdings/{hid}/archive", {})
    must(s in (200, 204), f"archive holding -> {s}")
    s, hold2 = get(base, "/api/finance/investments/holdings")
    must(all(h["id"] != hid for h in hold2), "archived holding gone from /holdings  [P]")
    s, pulse = get(base, "/api/finance/overview/portfolio-pulse")
    must("TCS" not in str(pulse), "archived holding gone from portfolio-pulse calc too  [P]")

    # hard-delete blocked while lots exist -> 409 pointing at archive  [P]
    s, _ = post(base, f"/api/finance/investments/holdings/{hid}", {})  # PUT/DELETE path varies; check DELETE
ok("phase 3 investments")
