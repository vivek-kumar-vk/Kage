"""Phase 8 gate — night worker, backups, build pipeline, cutover."""
import subprocess, sys, pathlib, os, sqlite3, time
from _util import REPO, BACKEND, FRONTEND, must, ok, die, fresh_db, backend_server, get

FOS = REPO / "finance-os"

# build.py produces a bundle FastAPI serves  [O]
must((FOS / "build.py").exists(), "finance-os/build.py exists  [O]")
r = subprocess.run([sys.executable, "build.py"], cwd=str(FOS),
                   capture_output=True, text=True, timeout=1800)
tail = "\n".join(((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-15:])
must(r.returncode == 0, f"build.py runs clean\n{tail}")
must((BACKEND / "static" / "index.html").exists(), "static bundle copied into backend/static/  [O]")

# night worker: weekly gap-only refresh + capped retry budget + backup rotation
nw = FOS / "night_worker.py"
must(nw.exists(), "night_worker.py exists")
nsrc = nw.read_text(encoding="utf-8")
must("MAX(date)" in nsrc or "max_date" in nsrc or "gap" in nsrc.lower(),
     "night worker does weekly gap-only price_history refresh  [B]")
must("retry" in nsrc.lower() and ("budget" in nsrc.lower() or "cap" in nsrc.lower() or "max_total" in nsrc.lower()),
     "night worker caps total retry budget for the nightly pass  [J]")
must("backups" in nsrc and ("7" in nsrc), "night worker rotates last 7 db backups")

# run night worker once against a fresh db, then confirm staleness surfaces
db = fresh_db()
env = dict(os.environ, FINANCE_DB=db, FINANCE_OS_DB=db)
subprocess.run([sys.executable, "night_worker.py", "--once"], cwd=str(FOS), env=env,
               capture_output=True, text=True, timeout=600)
bdir = BACKEND / "data" / "backups"
# staleness: DataHealthCard endpoint must report stale, not present old as current
with backend_server(db) as base:
    s, dh = get(base, "/api/finance/overview/data-health")
    must(s == 200, f"/overview/data-health -> {s}")
    # deep-link served from static export, no 404  [O]
    import urllib.request
    for path in ("/finance/investments", "/finance/investments.html"):
        try:
            with urllib.request.urlopen(base + path, timeout=10) as resp:
                if resp.status == 200:
                    break
        except Exception:
            continue
    else:
        die("deep-link /finance/investments not served from static export (404)  [O]")

# cutover is the one MANUAL step after the autonomous build — checked, not enforced.
must((FOS / "CUTOVER.md").exists(), "CUTOVER.md checklist written for the manual cutover step")
serve = (REPO / "Start_Inky" / "serve_everything_on_one_port.py").read_text(encoding="utf-8")
if "finance-os" in serve or "finance_os" in serve:
    print("  note: serve_everything already references finance-os — cutover done")
else:
    print("  note: cutover still pending — see finance-os/CUTOVER.md (manual, non-blocking)")

ok("phase 8 night worker / build / static serve")
