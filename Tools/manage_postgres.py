"""Start, stop and inspect Kage's own Postgres cluster.

Kage manages its database itself (wayfinder decision T3): a cluster that
lives in the repo at Start_Inky/pgdata/ (gitignored), on port 5433 so it
never collides with a system Postgres, initialised with trust auth on
localhost only. No Windows service, no admin rights - the same shape as
.venv/. Ctrl+C in Start_Inky stops it with everything else.

USAGE
    python Tools/manage_postgres.py ensure     # init if new, start if down, make the db
    python Tools/manage_postgres.py status
    python Tools/manage_postgres.py stop
    python Tools/manage_postgres.py start
    python Tools/manage_postgres.py init

Needs the Postgres client/server binaries already present (EDB installer
on Windows, `pkg install postgresql` on Termux). It installs nothing.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings_for_tools as cfg  # noqa: E402


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, text=True, capture_output=True, **kw)


def port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex((cfg.PG_HOST, cfg.PG_PORT)) == 0


def is_initialised() -> bool:
    return (cfg.PG_DATA / "PG_VERSION").exists()


def is_running() -> bool:
    proc = _run([cfg.pg_exe("pg_ctl"), "status", "-D", str(cfg.PG_DATA)])
    return proc.returncode == 0


def init() -> None:
    if is_initialised():
        print(f"  cluster already initialised at {cfg.PG_DATA}")
        return
    cfg.PG_DATA.parent.mkdir(parents=True, exist_ok=True)
    print(f"  initdb -> {cfg.PG_DATA}")
    proc = _run(
        [
            cfg.pg_exe("initdb"),
            "-D", str(cfg.PG_DATA),
            "-U", cfg.PG_SUPERUSER,
            "-A", "trust",
            "-E", "UTF8",
            "--locale=C",
        ]
    )
    if proc.returncode != 0:
        sys.exit(f"initdb failed:\n{proc.stdout}\n{proc.stderr}")
    # Pin the cluster to our host/port in its own config, so `pg_ctl
    # start` needs no extra flags and every client agrees.
    conf = cfg.PG_DATA / "postgresql.conf"
    conf.write_text(
        conf.read_text(encoding="utf-8")
        + f"\n# --- Kage ---\nlisten_addresses = '{cfg.PG_HOST}'\nport = {cfg.PG_PORT}\n",
        encoding="utf-8",
    )
    print("  initialised")


def _rotate_log() -> None:
    """Move the server log aside. A force-killed pg_ctl/postgres can leave
    a Windows handle on it; `pg_ctl start` then dies with 'The process
    cannot access the file because it is being used by another process'
    before the server ever starts. A fresh log path sidesteps the lock."""
    if not cfg.PG_LOG.exists():
        return
    try:
        cfg.PG_LOG.rename(cfg.PG_LOG.with_suffix(cfg.PG_LOG.suffix + f".old.{int(time.time())}"))
    except OSError:
        pass  # still locked; pg_ctl -l will retry against it anyway


def _pg_ctl_start() -> subprocess.CompletedProcess:
    # No -w: on Windows `pg_ctl start -w` can hang holding the pipe open
    # even after the server is ready. Fire it, then poll the port
    # ourselves - the same readiness check, without the hang. pg_ctl's
    # own chatter is captured here; the server log goes to -l.
    return _run(
        [cfg.pg_exe("pg_ctl"), "start", "-D", str(cfg.PG_DATA),
         "-l", str(cfg.PG_LOG), "-o", f"-p {cfg.PG_PORT}"]
    )


def start() -> None:
    if not is_initialised():
        init()
    if is_running():
        print(f"  already running on {cfg.PG_HOST}:{cfg.PG_PORT}")
        return
    print(f"  pg_ctl start -> log {cfg.PG_LOG}")
    proc = _pg_ctl_start()
    if proc.returncode != 0 and "being used by another process" in (proc.stdout + proc.stderr):
        print("  server log was locked - rotating it and retrying")
        _rotate_log()
        proc = _pg_ctl_start()
    for _ in range(60):  # up to ~30s
        if port_open():
            print(f"  up on {cfg.PG_HOST}:{cfg.PG_PORT}")
            return
        time.sleep(0.5)
    sys.exit(
        f"Postgres did not come up on {cfg.PG_HOST}:{cfg.PG_PORT}\n"
        f"{proc.stdout}\n{proc.stderr}\nsee {cfg.PG_LOG}"
    )


def stop() -> None:
    if not is_initialised() or not is_running():
        print("  not running")
        return
    proc = _run([cfg.pg_exe("pg_ctl"), "stop", "-D", str(cfg.PG_DATA), "-m", "fast", "-w"])
    print("  stopped" if proc.returncode == 0 else f"  stop failed:\n{proc.stderr}")


def make_db() -> None:
    """Create the litellm database if it is not there yet. Idempotent."""
    check = _run(
        [
            cfg.pg_exe("psql"),
            "-h", cfg.PG_HOST, "-p", str(cfg.PG_PORT), "-U", cfg.PG_SUPERUSER,
            "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{cfg.LITELLM_DB}'",
            "postgres",
        ]
    )
    if check.stdout.strip() == "1":
        print(f"  database '{cfg.LITELLM_DB}' already exists")
        return
    proc = _run(
        [
            cfg.pg_exe("createdb"),
            "-h", cfg.PG_HOST, "-p", str(cfg.PG_PORT), "-U", cfg.PG_SUPERUSER,
            cfg.LITELLM_DB,
        ]
    )
    if proc.returncode != 0:
        sys.exit(f"createdb failed:\n{proc.stdout}\n{proc.stderr}")
    print(f"  created database '{cfg.LITELLM_DB}'")


def status() -> None:
    print(f"  bin        {cfg.PG_BIN or '(PATH)'}")
    print(f"  data       {cfg.PG_DATA}")
    print(f"  address    {cfg.PG_HOST}:{cfg.PG_PORT}")
    print(f"  initialised {is_initialised()}")
    print(f"  running    {is_running()}  (port open: {port_open()})")


def ensure() -> None:
    start()
    make_db()


COMMANDS = {
    "init": init, "start": start, "stop": stop,
    "status": status, "ensure": ensure, "createdb": make_db,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    action = COMMANDS.get(cmd)
    if action is None:
        sys.exit(f"unknown command '{cmd}'. one of: {', '.join(COMMANDS)}")
    action()
