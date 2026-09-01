"""Shared helpers for gate_phaseN.py. Executable phase gates for Finance OS V1.

Each gate exits 0 on pass, non-zero on fail (run_build.py halts the run on
non-zero). Gates are deliberately dependency-light: stdlib + a live uvicorn.
"""
from __future__ import annotations
import contextlib, os, socket, sqlite3, subprocess, sys, time, json, pathlib, tempfile, shutil
import urllib.request, urllib.error

REPO = pathlib.Path(__file__).resolve().parents[3]          # B:/inky_code
BACKEND = REPO / "finance-os" / "backend"
FRONTEND = REPO / "finance-os" / "frontend"


def die(msg: str) -> "NoReturn":
    print(f"GATE FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> "NoReturn":
    print(f"GATE PASS: {msg}")
    sys.exit(0)


def must(cond: bool, msg: str) -> None:
    if not cond:
        die(msg)
    print(f"  ok: {msg}")


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def fresh_db() -> str:
    """Copy finance-os schema into a throwaway db, return its path.
    Applies backend/scripts/schema.sql (or services/schema.sql) if present,
    else expects backend to create the schema on startup against FINANCE_DB."""
    d = tempfile.mkdtemp(prefix="finos-gate-")
    dbp = os.path.join(d, "finance.db")
    for cand in (BACKEND / "scripts" / "schema.sql", BACKEND / "services" / "schema.sql",
                 BACKEND / "schema.sql"):
        if cand.exists():
            con = sqlite3.connect(dbp)
            con.executescript(cand.read_text(encoding="utf-8"))
            con.commit()
            con.close()
            break
    return dbp


@contextlib.contextmanager
def backend_server(db_path: str | None = None, wait_s: int = 40):
    """Start `uvicorn main:app` from finance-os/backend on a free port with
    FINANCE_DB pointed at db_path. Yields base URL http://127.0.0.1:PORT ."""
    port = free_port()
    env = dict(os.environ)
    if db_path:
        env["FINANCE_DB"] = db_path
        env["FINANCE_OS_DB"] = db_path
    env["FINANCE_OS_SKIP_NIGHT"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(port), "--log-level", "warning"],
        cwd=str(BACKEND), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(wait_s * 2):
            if proc.poll() is not None:
                out = proc.stdout.read() if proc.stdout else ""
                die(f"backend exited early rc={proc.returncode}\n{out[-2000:]}")
            try:
                with urllib.request.urlopen(base + "/api/finance/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            die("backend did not become healthy in time")
        yield base
    finally:
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(timeout=10)


def get(base: str, path: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(base + path, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def post(base: str, path: str, body: dict | None = None, files: bytes | None = None,
         ctype: str = "application/json") -> tuple[int, object]:
    data = files if files is not None else (json.dumps(body or {}).encode("utf-8"))
    req = urllib.request.Request(base + path, data=data, method="POST",
                                 headers={"Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8")
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def grep_repo(pattern: str, root: pathlib.Path, exts=(".py",)) -> list[str]:
    hits = []
    for p in root.rglob("*"):
        if p.suffix in exts and p.is_file():
            try:
                for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if pattern in ln:
                        hits.append(f"{p.relative_to(REPO)}:{i}: {ln.strip()}")
            except Exception:
                pass
    return hits
