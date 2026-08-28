"""Where the shared local infrastructure lives - the LiteLLM gateway and
the Postgres cluster behind it.

One place for every path and port, so nothing else has to guess. Every
value can be overridden by an environment variable (the phone host, or a
second checkout, sets those); the defaults are what a fresh clone uses.

This file is plain data + a tiny bit of discovery. It imports nothing of
ours.
"""

from __future__ import annotations

import os
from pathlib import Path

# Tools/settings_for_tools.py  ->  repo root is one up.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------
# POSTGRES - a project-managed cluster, not a system service (T3)
# ---------------------------------------------------------------------
def _find_pg_bin() -> str:
    """The folder holding pg_ctl / initdb / psql.

    Order: KAGE_PG_BIN env -> the newest C:\\Program Files\\PostgreSQL\\NN
    -> empty string (meaning "trust PATH"). No install is done here; the
    binaries are expected to exist already (EDB installer, apt, pkg).
    """
    override = os.environ.get("KAGE_PG_BIN")
    if override:
        return override
    windows_root = Path(r"C:\Program Files\PostgreSQL")
    if windows_root.is_dir():
        versions = sorted(
            (p for p in windows_root.iterdir() if (p / "bin" / "initdb.exe").exists()),
            key=lambda p: p.name,
            reverse=True,
        )
        if versions:
            return str(versions[0] / "bin")
    return ""  # fall back to whatever is on PATH


PG_BIN = _find_pg_bin()
PG_DATA = Path(os.environ.get("KAGE_PGDATA", PROJECT_ROOT / "Start_Inky" / "pgdata"))
PG_HOST = os.environ.get("KAGE_PG_HOST", "127.0.0.1")
# 5433, not the default 5432, so a system Postgres can coexist untouched.
PG_PORT = int(os.environ.get("KAGE_PG_PORT", "5433"))
PG_SUPERUSER = os.environ.get("KAGE_PG_SUPERUSER", "postgres")
PG_LOG = PG_DATA / "server.log"

# The database LiteLLM keeps its spend logs / keys / model table in.
LITELLM_DB = os.environ.get("KAGE_LITELLM_DB", "litellm")

# The DSN LiteLLM (Prisma) connects with. The cluster is initialised with
# trust auth on localhost only, so no password by default; a real host
# sets DATABASE_URL itself.
DEFAULT_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql://{PG_SUPERUSER}@{PG_HOST}:{PG_PORT}/{LITELLM_DB}",
)

# ---------------------------------------------------------------------
# LITELLM GATEWAY
# ---------------------------------------------------------------------
LITELLM_HOST = os.environ.get("LITELLM_HOST", "127.0.0.1")
LITELLM_PORT = int(os.environ.get("LITELLM_PORT", "8003"))
LITELLM_CONFIG = Path(
    os.environ.get("LITELLM_CONFIG", PROJECT_ROOT / "Tools" / "litellm_config.yaml")
)

# The one file secrets live in. Never committed (.gitignore).
ENV_FILE = PROJECT_ROOT / ".env"


def pg_exe(name: str) -> str:
    """Absolute path to a Postgres executable, or its bare name if PG_BIN
    is unset (then it must be on PATH)."""
    if PG_BIN:
        return str(Path(PG_BIN) / name)
    return name
