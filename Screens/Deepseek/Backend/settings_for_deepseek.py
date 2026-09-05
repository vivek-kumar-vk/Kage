"""Settings for the Deepseek screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.

This screen is a complete independent component (CLAUDE.md Rule 5): it
imports nothing from Shared_By_All_Screens/ and reaches into no other
screen's code. The few values the launcher needs by convention -
SCREEN_NAME, PORT, HOST, PAGE - are plain module attributes.
"""

import os
from pathlib import Path

# This file sits at  Screens/Deepseek/Backend/settings_for_deepseek.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Deepseek folder
PROJECT_ROOT = HERE.parents[2]              # the repo root

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "deepseek"
SCREEN_LABEL = "Deepseek"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Own port, see CLAUDE.md's Ports table.
PORT = 8008
HOST = "127.0.0.1"          # local means local

PAGE = SCREEN / "Page" / "page_for_deepseek.html"

# ---------------------------------------------------------------------
# THE HARNESS IT REPORTS ON
# ---------------------------------------------------------------------
# dsh's web profile serves its UI here. This is dsh's own default; it is
# not a Kage port, and Kage never starts it (Rule 20).
HARNESS_BASE_URL = os.environ.get("DSH_BASE_URL", "http://127.0.0.1:3080")

# Where dsh keeps its own state. $DSH_HOME if set, else ~/.dsh - the
# same rule dsh itself follows.
DSH_HOME = Path(os.environ.get("DSH_HOME", Path.home() / ".dsh"))
DSH_SETTINGS = DSH_HOME / "settings.yaml"
DSH_PROFILES = DSH_HOME / "profiles"
DSH_SESSIONS = DSH_HOME / "sessions"

# The command that starts it, shown verbatim on the page when it is down.
START_COMMAND = "dsh web"

# ---------------------------------------------------------------------
# THE GATEWAY THE HARNESS CALLS THROUGH
# ---------------------------------------------------------------------
# dsh reaches DeepSeek models through the OmniRoute gateway rather than
# DeepSeek's cloud API directly, so there is one place model access is
# configured and no second API key to hold (D24.1).
GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://127.0.0.1:8010")


# The gateway's list endpoints need its API key. It lives in the repo-root
# .env (gitignored). This screen stays independent - it does not import a
# shared loader, just reads the one line it needs. Env wins so a host can
# override without touching .env.
def _gateway_key() -> str:
    if os.environ.get("GATEWAY_API_KEY"):
        return os.environ["GATEWAY_API_KEY"]
    env_file = PROJECT_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GATEWAY_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


GATEWAY_API_KEY = _gateway_key()

# The dsh provider id this screen expects to find in dsh's settings.yaml,
# written there by Setup/install_dsh_provider.py.
HARNESS_PROVIDER = "omniroute"

API_PREFIX = "/api/deepseek"
