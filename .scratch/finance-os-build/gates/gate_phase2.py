"""Phase 2 gate — Overview + wiring primitives (H/N deps). Static + fresh-DB API."""
import subprocess, pathlib, sys, math
from _util import REPO, BACKEND, FRONTEND, must, ok, die, fresh_db, backend_server, get, grep_repo

FE = FRONTEND
api = (FE / "lib" / "api.ts")
must(api.exists(), "lib/api.ts exists")
src = api.read_text(encoding="utf-8")
must("version" in src.lower() and ("subscribe" in src or "useSyncExternalStore" in src or "listener" in src),
     "api.ts has a cache-version counter subscribers read  [G/N]")
must("refetch" in src, "useFinanceData exposes refetch  [G/N]")

nw = list((FE / "components").rglob("NetWorthCard.tsx"))
must(nw, "NetWorthCard.tsx exists")
nwsrc = nw[0].read_text(encoding="utf-8")
must("Math.max(...values, 0)" not in nwsrc and "Math.max(...values,0)" not in nwsrc,
     "sparkline drops the forced 0 in Math.max  [F]")
must("|| 1" in nwsrc or "|| 1)" in nwsrc or "|| 1 " in nwsrc, "sparkline keeps (max-min)||1 guard  [F]")

must(list((FE / "components").rglob("FormModal.tsx")), "<FormModal> wrapper exists  [H]")
hooks = grep_repo("useSubmit", FE, exts=(".ts", ".tsx"))
must(hooks, "useSubmit hook present  [H]")

# frontend static export builds
r = subprocess.run(["npx", "next", "build"], cwd=str(FE), shell=(sys.platform == "win32"),
                   capture_output=True, text=True, timeout=1800)
tail = "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-15:])
must(r.returncode == 0, f"next build (static export) succeeds\n{tail}")
must((FE / "out").is_dir(), "frontend/out/ produced by build")

# overview endpoints do not crash / emit NaN on a fresh empty DB
db = fresh_db()
with backend_server(db) as base:
    for ep in ["net-worth", "cashflow", "portfolio-pulse", "emergency-fund",
               "debt-status", "surplus-allocation", "goals", "top-actions", "data-health"]:
        s, body = get(base, f"/api/finance/overview/{ep}")
        must(s == 200, f"/overview/{ep} -> {s} on empty DB")
        must("NaN" not in str(body) and "Infinity" not in str(body),
             f"/overview/{ep} has no NaN/Infinity  [F]")

ok("phase 2 overview")
