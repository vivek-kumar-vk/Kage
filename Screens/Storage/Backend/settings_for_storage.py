"""Settings for the Storage screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.

This screen is a complete independent component (CLAUDE.md Rule 5): it
imports nothing from Shared_By_All_Screens/ and reaches into no other
screen's code.
"""

import os
from pathlib import Path

# This file sits at  Screens/Storage/Backend/settings_for_storage.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Storage folder
PROJECT_ROOT = HERE.parents[2]              # the repo root

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "storage"
SCREEN_LABEL = "Storage"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
PORT = 8009
HOST = "127.0.0.1"          # local means local

PAGE = SCREEN / "Page" / "page_for_storage.html"

# ---------------------------------------------------------------------
# .env (repo-root, gitignored) - real env vars always win
# ---------------------------------------------------------------------
def _dotenv_values():
    env_path = PROJECT_ROOT / ".env"
    values = {}
    try:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except OSError:
        pass
    return values


_DOTENV = _dotenv_values()


def _env(key, default=""):
    return os.getenv(key) or _DOTENV.get(key) or default


# ---------------------------------------------------------------------
# THE ONE STORAGE ROOT (D11.5, D40) - plain files, repo-relative and
# gitignored (Rule 7.1) so the whole project - code and data - is one
# self-contained folder when hosted on the phone (Termux).
# ---------------------------------------------------------------------
KAGE_DATA_DIR = Path(_env("KAGE_DATA_DIR", str(PROJECT_ROOT / "kage-data"))).expanduser()
TRASH_DIR = KAGE_DATA_DIR / ".trash"

# A logical path may only carry these extensions - the format the
# content is stored as, not a free-form file type.
ALLOWED_EXTENSIONS = {".md", ".txt", ".json"}
MAX_PATH_DEPTH = 6

# ---------------------------------------------------------------------
# RAG - embeddings via OmniRoute (D11.5.1), never Ollama (the intended
# host is Termux, which has neither Node nor Ollama)
# ---------------------------------------------------------------------
OMNIROUTE_URL = _env("OMNIROUTE_URL", "http://127.0.0.1:8003")
GATEWAY_API_KEY = _env("GATEWAY_API_KEY")
STORAGE_EMBED_MODEL = _env("STORAGE_EMBED_MODEL")

RAG_INDEX_PATH = HERE / "index" / "rag.sqlite"
CHUNK_WORDS = 180
CHUNK_OVERLAP_WORDS = 20

API_PREFIX = "/api/storage"
