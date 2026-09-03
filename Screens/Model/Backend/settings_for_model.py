"""Settings for the Model screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.

This screen is a complete independent component (CLAUDE.md Rule 5 / D-W6):
it does NOT read Shared_By_All_Screens/read_screen_settings.py or any
other shared module. The few values the launcher needs by convention -
SCREEN_NAME, PORT, HOST - are plain module attributes it can read
without importing anything of ours.

This screen serves its own small page (Page/page_for_model.html).
It used to 307-redirect straight to the gateway's dashboard, which made
the tab a dead end whenever the gateway was down - the browser left Kage
and landed on a connection error with no way back. The page now embeds
the dashboard when the gateway answers and explains itself when it does
not.
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
# Own port, so this screen can be worked on alone. See
# Start_Inky/ports_for_inky.json for the whole map.
PORT = 8005
HOST = "127.0.0.1"          # local means local

# The page this screen serves. The launcher reads this attribute to say
# "page ready" instead of "data only" - see
# Shared_By_All_Screens/read_screen_settings.py.
PAGE = SCREEN / "Page" / "page_for_model.html"

# ---------------------------------------------------------------------
# THE GATEWAY IT REPORTS ON
# ---------------------------------------------------------------------
# The model gateway (OmniRoute or similar OpenAI-compatible endpoint).
# Base URL only - the server file owns which endpoints it reads.
# Overridable by env for the phone host later.
import os

GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://localhost:8003")

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
