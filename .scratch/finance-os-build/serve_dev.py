#!/usr/bin/env python
"""serve_dev.py — keep a viewable Finance OS up while run_build.py works.

Runs forever alongside the build. Cheap (no `next dev`): it serves the FastAPI
backend on :8000 against a persistent, seeded DB, and mirrors the frontend's
static export (`frontend/out/`) into `backend/static/` whenever a fresh
`next build` lands (phase 2 gate onward), so FastAPI serves the real UI too.

  open  http://127.0.0.1:8000/finance   (redirects there from /)
  API   http://127.0.0.1:8000/api/finance/health

What it does on a loop (every ~20s):
  * (re)create finance-os/backend/data/finance.db from schema.sql + light seed
    data when the schema exists and the db is missing/older than the schema
  * start `uvicorn main:app --port 8000 --reload` once backend/main.py exists
  * bounce uvicorn + re-mirror static when a `progress/phaseN-progress.md`
    gains a new "PHASE * DONE" line (new routers / pages become visible)
  * mirror frontend/out -> backend/static when out/ changes

Stop with Ctrl-C (or TaskStop). Safe to run before the build starts.
"""
from __future__ import annotations
import os, sys, time, sqlite3, subprocess, shutil, pathlib, datetime, threading, http.server, socketserver, re

REPO = pathlib.Path(__file__).resolve().parents[2]
FOS = REPO / "finance-os"
BACKEND = FOS / "backend"
SCHEMA = BACKEND / "scripts" / "schema.sql"
DB = BACKEND / "data" / "finance.db"
OUT = FOS / "frontend" / "out"
STATIC = BACKEND / "static"
PROG = pathlib.Path(__file__).resolve().parent / "progress"
PORT = 8000


def log(msg: str) -> None:
    print(f"[serve_dev {datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


SEED = """
INSERT INTO accounts (name,type,institution) VALUES
 ('HDFC Bank','bank','HDFC'),('Zerodha','demat','Zerodha'),('Cash','cash',NULL);
INSERT INTO salary (monthly_gross,monthly_net,effective_date) VALUES (180000,140000,date('now','-6 months'));
INSERT INTO transactions (account_id,date,description,amount,category,type,source) VALUES
 (1,date('now','-20 days'),'Salary credit',140000,'income','income','manual'),
 (1,date('now','-18 days'),'Rent',-35000,'rent','expense','manual'),
 (1,date('now','-12 days'),'Groceries',-6200,'food','expense','manual'),
 (1,date('now','-8 days'),'SIP - Nifty Index',-15000,'investment','investment','manual'),
 (3,date('now','-5 days'),'Dining out',-2400,'food','expense','manual');
INSERT INTO holdings (account_id,symbol,name,type,units,avg_cost,benchmark) VALUES
 (2,'NIFTYBEES','Nippon Nifty BeES','etf',400,180.5,'^NSEI'),
 (2,'120716','Parag Parikh Flexi Cap Direct','mutual_fund',1250,62.3,NULL);
INSERT INTO goals (name,target_amount,current_amount,target_date,start_date,priority) VALUES
 ('Emergency Fund',600000,250000,date('now','+12 months'),date('now','-6 months'),1),
 ('Car',1200000,300000,date('now','+36 months'),date('now','-2 months'),2);
INSERT INTO debts (lender,type,outstanding,interest_rate,emi,remaining_months) VALUES
 ('HDFC Credit Card','credit_card',85000,42,8000,12);
INSERT INTO insurance (type,provider,coverage_amount,premium) VALUES
 ('term','LIC',10000000,18000);
"""


def rebuild_db() -> None:
    if not SCHEMA.exists():
        return
    if DB.exists() and DB.stat().st_mtime >= SCHEMA.stat().st_mtime:
        return
    DB.parent.mkdir(parents=True, exist_ok=True)
    for p in DB.parent.glob("finance.db*"):
        p.unlink()
    con = sqlite3.connect(DB)
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        try:
            con.executescript(SEED)
        except sqlite3.Error as e:
            log(f"seed skipped ({e})")
        con.commit()
        log(f"rebuilt {DB.name} from schema + seed")
    finally:
        con.close()


def mirror_static() -> None:
    if not OUT.is_dir():
        return
    newest = max((f.stat().st_mtime for f in OUT.rglob("*") if f.is_file()), default=0)
    stamp = STATIC / ".mirrored_at"
    if stamp.exists() and stamp.stat().st_mtime >= newest:
        return
    if STATIC.exists():
        shutil.rmtree(STATIC)
    shutil.copytree(OUT, STATIC)
    stamp.write_text(str(newest))
    log("mirrored frontend/out -> backend/static")


PHASE_NAMES = {
    "0": "Foundations — schema, db helper, shared constants, scaffold",
    "1": "Ingestion & CRUD backend — importers, upsert, price backfill",
    "2": "Overview tab — API client, nav, 9 cards, Three.js hero",
    "3": "Investments tab — holdings, visuals, quality panel",
    "4": "Debt tab — payoff plan, simulate",
    "5": "Tracker tab — transactions, recurring, insights",
    "6": "Learning & RAG — FAISS index, learning UI",
    "7": "Data Health / Scenario / Settings",
    "8": "Night worker, backups, build pipeline",
}


def status_html() -> bytes:
    rows = []
    done = 0
    for i in range(9):
        f = PROG / f"phase{i}-progress.md"
        state, detail = "pending", ""
        if f.exists():
            txt = f.read_text(encoding="utf-8", errors="replace")
            if "DONE" in txt and f"PHASE {i} DONE" in txt:
                m = re.search(rf"PHASE {i} DONE.*", txt)
                state, detail, = ("done", m.group(0) if m else "")
                done += 1
            else:
                state = "running"
                last = [ln for ln in txt.splitlines() if ln.strip()]
                detail = last[-1][:160] if last else ""
        colour = {"done": "#00ff87", "running": "#f9a800", "pending": "#555"}[state]
        rows.append(
            f'<tr><td style="color:{colour}">&#9679; P{i}</td>'
            f'<td>{PHASE_NAMES[str(i)]}</td>'
            f'<td style="color:{colour}">{state}</td>'
            f'<td style="color:#888;font:12px monospace">{detail}</td></tr>')
    body = f"""<!doctype html><html><head><meta charset=utf-8>
<meta http-equiv=refresh content=15>
<title>Finance OS — build in progress</title>
<style>body{{background:#0a0a0a;color:#e5e7eb;font:15px Inter,system-ui,sans-serif;margin:0;padding:40px}}
h1{{font-weight:700;letter-spacing:.02em}} .dot{{width:8px;height:8px;border-radius:50%;background:#00ff87;box-shadow:0 0 6px #00ff87;display:inline-block;margin-right:8px}}
table{{border-collapse:collapse;margin-top:24px;width:100%;max-width:1100px}} td{{padding:8px 14px;border-bottom:1px solid #1e1e1e}}
.bar{{height:6px;background:#1e1e1e;border-radius:3px;overflow:hidden;max-width:1100px;margin-top:8px}}
.bar>i{{display:block;height:100%;background:#e10600;width:{done/9*100:.0f}%}}</style></head>
<body><h1><span class=dot></span>FINANCE OS — building</h1>
<div style="color:#888">{done}/9 phases complete · this page auto-refreshes · the real app replaces it once Phase 2 lands</div>
<div class=bar><i></i></div>
<table>{''.join(rows)}</table>
<p style="color:#555;margin-top:30px;font:12px monospace">served by serve_dev.py placeholder · http://127.0.0.1:8000</p>
</body></html>"""
    return body.encode("utf-8")


class _StatusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(status_html())

    def log_message(self, *a):  # silence
        pass


class _Placeholder:
    def __init__(self):
        self.srv = None
        self.thr = None

    def start(self):
        if self.srv:
            return
        try:
            self.srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), _StatusHandler)
            self.srv.daemon_threads = True
            self.thr = threading.Thread(target=self.srv.serve_forever, daemon=True)
            self.thr.start()
            log(f"placeholder status page live on :{PORT}")
        except OSError as e:
            log(f"placeholder not started ({e})")

    def stop(self):
        if self.srv:
            self.srv.shutdown()
            self.srv.server_close()
            self.srv = None
            log("placeholder stopped (handing :8000 to uvicorn)")


def phase_done_marker() -> str:
    marks = []
    if PROG.is_dir():
        for f in sorted(PROG.glob("phase*-progress.md")):
            txt = f.read_text(encoding="utf-8", errors="replace")
            marks.append(f"{f.name}:{txt.count('PHASE') and txt.count('DONE')}")
    return "|".join(marks)


def start_uvicorn() -> subprocess.Popen | None:
    if not (BACKEND / "main.py").exists():
        return None
    env = dict(os.environ, FINANCE_DB=str(DB), FINANCE_OS_DB=str(DB),
               FINANCE_OS_SKIP_NIGHT="1")
    log(f"starting uvicorn on :{PORT}")
    # no --reload: keeps RAM low next to llama + node build; new routers/pages
    # appear at the phase-boundary bounce instead (which is what "see it after
    # each phase" means anyway).
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(PORT),
         "--host", "127.0.0.1", "--log-level", "warning"],
        cwd=str(BACKEND), env=env)


def main() -> None:
    log(f"watching {FOS}  — open http://127.0.0.1:{PORT}/  (status page now, real app after Phase 2)")
    proc: subprocess.Popen | None = None
    ph = _Placeholder()
    ph.start()
    last_marker = ""
    while True:
        try:
            rebuild_db()
            mirror_static()
            marker = phase_done_marker()
            have_backend = (BACKEND / "main.py").exists()
            if not have_backend:
                ph.start()  # no-op if already running
            elif proc is None:
                ph.stop()
                proc = start_uvicorn()
            elif proc.poll() is not None:
                log("uvicorn exited — restarting")
                proc = start_uvicorn()
            elif marker != last_marker:
                log("phase boundary detected — bouncing uvicorn to load new routers")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except Exception:
                    proc.kill()
                proc = start_uvicorn()
            last_marker = marker
        except Exception as e:  # noqa: BLE001
            log(f"loop error (non-fatal): {e!r}")
        time.sleep(20)


if __name__ == "__main__":
    main()
