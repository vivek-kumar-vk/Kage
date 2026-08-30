"""Settings for the Model screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.

This screen is a complete independent component (AGENTS.md rule 4 / D-W6):
it does NOT read Shared_By_All_Screens/read_screen_settings.py or any
other shared module. The few values the launcher needs by convention -
SCREEN_NAME, PORT, HOST, PAGE - are plain module attributes it can read
without importing anything of ours.
"""

from pathlib import Path

# This file sits at  Screens/Model/Backend/settings_for_model.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Model folder
PROJECT_ROOT = HERE.parents[2]              # the repo root

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "model"
SCREEN_LABEL = "Model"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Own port, so this screen can be worked on alone. 8004 is Enhancement;
# this screen takes 8005.
PORT = 8005
HOST = "127.0.0.1"          # local means local

# The page this screen serves. D10: a RUBRIC-themed shell that iframes
# OmniRoute's own dashboard.
PAGE = SCREEN / "Page" / "page_for_model.html"

# ---------------------------------------------------------------------
# THE GATEWAY IT REPORTS ON
# ---------------------------------------------------------------------
# The model gateway (OmniRoute or similar OpenAI-compatible endpoint).
# Base URL only - the server file owns which endpoints it reads.
# Overridable by env for the phone host later.
import os

GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://127.0.0.1:8003")

# The gateway's admin/list endpoints may need an API key. It lives in
# the repo-root .env (gitignored). This screen stays independent - it
# does not import Tools/ or any shared loader, just reads the one line
# it needs itself. Env wins so a host can override without touching .env.
def _gateway_key() -> str:
    if os.environ.get("GATEWAY_API_KEY"):
        return os.environ["GATEWAY_API_KEY"]
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GATEWAY_API_KEY=") and "=" in line:
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


GATEWAY_API_KEY = _gateway_key()

# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------
API_PREFIX = "/api/model"

# ---------------------------------------------------------------------
# NEXT.JS REBUILD FLAG (parity with the other screens; wired in T7)
# ---------------------------------------------------------------------
# False + no build present -> the hand-written page is served. True with
# a real export under Page/next_app/out swaps it in; honest beats broken.
USE_NEXT_UI = False
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
