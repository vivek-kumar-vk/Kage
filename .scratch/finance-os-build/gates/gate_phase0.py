"""Phase 0 gate — foundations & shared contracts. Static + sqlite checks, no server."""
import sqlite3, pathlib, sys, os, subprocess, tempfile
from _util import REPO, BACKEND, FRONTEND, must, ok, die, fresh_db, grep_repo

FOS = REPO / "finance-os"
must(FOS.is_dir(), "finance-os/ tree exists")
for p in ["backend/main.py", "backend/services/db.py", "backend/requirements.txt",
          "frontend/package.json", "frontend/next.config.js", "DECISIONS.md"]:
    must((FOS / p).exists(), f"{p} exists")

# schema applies cleanly + required objects present
db = fresh_db()
con = sqlite3.connect(db)
names = {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
for t in ["accounts", "transactions", "holdings", "lots", "goals", "debts",
          "insurance", "salary", "snapshots", "data_health", "price_history"]:
    must(t in names, f"table {t} created")
must("latest_prices" in names, "view latest_prices created")
must("active_holdings" in names, "view active_holdings created  [P downstream]")
row = con.execute("SELECT COUNT(*) FROM data_health WHERE id=1").fetchone()[0]
must(row == 1, "data_health singleton row id=1 seeded")

# FK enforcement: insert child with missing parent must be rejected
con.execute("PRAGMA foreign_keys = ON")
try:
    con.execute("INSERT INTO transactions(account_id,date,amount) VALUES (99999,'2026-01-01',-10)")
    con.commit()
    die("FK-violating insert was NOT rejected  [D]")
except sqlite3.IntegrityError:
    print("  ok: FK-violating insert rejected  [D]")
con.close()

# no bare sqlite3.connect( outside db.py  [D downstream]
bad = [h for h in grep_repo("sqlite3.connect(", BACKEND) if "/services/db.py:" not in h.replace("\\", "/")]
must(not bad, "no bare sqlite3.connect( outside services/db.py  [D]\n    " + "\n    ".join(bad))

# .gitignore covers sensitive paths
gi_files = [REPO / ".gitignore", FOS / ".gitignore"]
gi = "\n".join(f.read_text(encoding="utf-8") for f in gi_files if f.exists())
for frag in ["finance.db", "backups", "vector_store", ".env"]:
    must(frag in gi, f".gitignore covers '{frag}'  [Q]")

# shared category enum reachable from both sides
sh = list((FOS / "shared").rglob("categor*")) + list((FOS / "backend").rglob("categor*")) \
    + list((FOS / "frontend").rglob("categor*"))
must(len(sh) >= 2, "shared txn-category constant present for backend AND frontend  [A]\n    found: "
     + ", ".join(str(p.relative_to(FOS)) for p in sh))

# app import smoke: main.py must import (catches create_app mismatch, leftover
# relative imports, missing modules) BEFORE phase 1 depends on a live server
_env = dict(os.environ, FINANCE_DB=str(pathlib.Path(tempfile.mkdtemp(prefix="finos-p0-")) / "finance.db"))
_r = subprocess.run([sys.executable, "-c", "import main; main.app"],
                    cwd=str(BACKEND), env=_env, capture_output=True, text=True, timeout=60)
must(_r.returncode == 0, "backend/main.py imports clean (create_app + app)\n    "
     + (_r.stderr.strip()[-1200:] or _r.stdout.strip()[-800:]))

ok("phase 0 foundations")
