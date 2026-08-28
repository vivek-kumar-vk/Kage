"""Start the local LiteLLM gateway - the one door every model call goes
through, doing auto-routing and fallback across providers.

WHAT IT DOES
    1. loads Tools/.. /.env  (secrets: master key, provider keys, DB url)
    2. makes sure Kage's Postgres cluster is up and has the litellm db
    3. execs `litellm --config Tools/litellm_config.yaml` on port 8003

    The proxy runs Prisma migrations against Postgres on first start by
    itself - nothing to do here for that.

WHY A .py AND NOT ONLY A .bat
    Windows runs it through run_litellm.bat; a phone host (Termux) runs
    this file directly. One place for the logic, thin wrappers per OS.

RUN IT
    Windows:  Tools\run_litellm.bat
    direct :  .venv/Scripts/python Tools/run_litellm.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings_for_tools as cfg  # noqa: E402
import manage_postgres  # noqa: E402


def load_env(path: Path) -> None:
    """Minimal .env loader - KEY=VALUE per line, # comments, no export,
    no quotes stripping beyond a surrounding pair. Existing environment
    wins, so a real host can override any single value."""
    if not path.exists():
        sys.exit(
            f"no {path} - copy .env.example to .env and set LITELLM_MASTER_KEY "
            "(and DATABASE_URL if not the default)."
        )
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def ensure_prisma_client(scripts_on_path: str) -> None:
    """LiteLLM talks to Postgres through a Prisma client that must be
    *generated* from its schema first. Recent litellm builds no longer do
    this on startup - they just fail with "Unable to find Prisma
    binaries". Generate it here if it is missing, so a fresh clone works.

    The check is a marker file, not an import: `prisma generate` copies
    the schema into the installed package, and importing the ungenerated
    stub client can hang.
    """
    try:
        import prisma

        generated = (Path(prisma.__file__).resolve().parent / "schema.prisma").exists()
    except Exception:  # noqa: BLE001
        generated = False
    if generated:
        return

    import litellm

    schema = Path(litellm.__file__).resolve().parent / "proxy" / "schema.prisma"
    if not schema.exists():
        sys.exit(f"cannot find litellm's prisma schema at {schema}")

    env = dict(os.environ)
    if scripts_on_path and scripts_on_path not in env.get("PATH", ""):
        env["PATH"] = scripts_on_path + os.pathsep + env.get("PATH", "")
    env.setdefault("PYTHONUTF8", "1")

    print("[run_litellm] generating the Prisma client (first run) ...")
    result = subprocess.run(
        ["prisma", "generate", f"--schema={schema}"],
        env=env, text=True, capture_output=True,
    )
    if result.returncode != 0:
        sys.exit(
            "prisma generate failed:\n"
            f"{result.stdout}\n{result.stderr}\n"
            "Is Node available? `pip install prisma` provides the CLI."
        )
    print("[run_litellm] Prisma client generated")


def venv_litellm() -> str:
    root = cfg.PROJECT_ROOT / ".venv"
    for candidate in (root / "Scripts" / "litellm.exe", root / "bin" / "litellm"):
        if candidate.exists():
            return str(candidate)
    # Not in the venv - fall back to `python -m litellm` on whatever
    # Python is running this, so the error is about litellm, not a path.
    return ""


def main() -> None:
    load_env(cfg.ENV_FILE)

    if not os.environ.get("LITELLM_MASTER_KEY"):
        sys.exit("LITELLM_MASTER_KEY is not set (check .env).")
    os.environ.setdefault("DATABASE_URL", cfg.DEFAULT_DATABASE_URL)
    os.environ.setdefault("STORE_MODEL_IN_DB", "true")
    # Kage runs one gateway worker (laptop and phone alike), so the
    # per-worker rate-limit / budget / router-state that Redis would
    # share is already correct. Silence the "no Redis" banner rather
    # than run a cache nobody needs.
    os.environ.setdefault("LITELLM_DISABLE_NO_REDIS_WARNING", "true")

    print("[run_litellm] ensuring Postgres is up ...")
    manage_postgres.ensure()

    # LiteLLM's banner uses box-drawing glyphs; on a cp1252 console that
    # raises UnicodeEncodeError and kills startup. Force UTF-8 I/O.
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    # LiteLLM shells out to the `prisma` CLI (a script in the venv) to run
    # DB migrations. Exec'ing litellm.exe directly does not put the venv's
    # Scripts/ dir on PATH, so make sure it is there.
    scripts_dir = str((cfg.PROJECT_ROOT / ".venv" / "Scripts"))
    bin_dir = str((cfg.PROJECT_ROOT / ".venv" / "bin"))
    on_path = ""
    for d in (scripts_dir, bin_dir):
        if Path(d).is_dir():
            on_path = d
            if d not in os.environ.get("PATH", ""):
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")

    ensure_prisma_client(on_path)

    exe = venv_litellm()
    cmd = (
        [exe] if exe
        else [sys.executable, "-m", "litellm"]
    ) + [
        "--config", str(cfg.LITELLM_CONFIG),
        "--host", cfg.LITELLM_HOST,
        "--port", str(cfg.LITELLM_PORT),
    ]
    print(f"[run_litellm] {' '.join(cmd)}")
    print(f"[run_litellm] UI -> http://{cfg.LITELLM_HOST}:{cfg.LITELLM_PORT}/ui")
    try:
        code = subprocess.call(cmd)
    except KeyboardInterrupt:
        code = 0
    # Ctrl+C stops the gateway; take its database down with it (T3: the
    # cluster's lifetime is tied to Start_Inky). Kept behind a flag so a
    # future second consumer of this Postgres can opt out.
    if os.environ.get("KAGE_KEEP_POSTGRES", "").lower() not in ("1", "true", "yes"):
        print("[run_litellm] stopping Postgres ...")
        manage_postgres.stop()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
