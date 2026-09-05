"""Settings for the OFFICE screen.

Everything adjustable lives here - port, db path, the Learning address
the readiness tab reads, the apply target.

This screen is a complete independent component (CLAUDE.md Rule 5): it
imports nothing from Shared_By_All_Screens/ and reaches into no other
screen's code. It talks to Learning only over HTTP.
"""

import os
from pathlib import Path

# This file sits at  Screens/Office/Backend/settings_for_office.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Office folder
PROJECT_ROOT = HERE.parents[2]              # the repo root

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "office"
SCREEN_LABEL = "Office"

# ---------------------------------------------------------------------
# SERVING  (D43: Office's reservation moved 8010 -> 8011)
# ---------------------------------------------------------------------
PORT = 8011
HOST = "127.0.0.1"          # local means local

PAGE = SCREEN / "Page" / "page_for_office.html"
DB_PATH = HERE / "office.db"
SCHEMA_PATH = HERE / "schema.sql"


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
# The Learning screen - read over HTTP for resume-defensibility (D17.5).
# Default is Learning's own port (D43: 8003).
# ---------------------------------------------------------------------
LEARNING_URL = _env("LEARNING_URL", "http://127.0.0.1:8003")
LEARNING_TIMEOUT_S = 4.0

# ---------------------------------------------------------------------
# Funnel
# ---------------------------------------------------------------------
APPLY_TARGET_PER_DAY = int(_env("OFFICE_APPLY_TARGET", "2"))

# Pipeline stages, in order. The last two are terminal.
STAGES = ["saved", "applied", "screen", "interview", "offer", "reject"]

API_PREFIX = "/api/office"
