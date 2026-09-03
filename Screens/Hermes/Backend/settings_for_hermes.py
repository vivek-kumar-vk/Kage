"""Settings for the Hermes screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.

This screen is a complete independent component (CLAUDE.md Rule 5): it
imports nothing from Shared_By_All_Screens/ and reaches into no other
screen's code. The few values the launcher needs by convention -
SCREEN_NAME, PORT, HOST, PAGE - are plain module attributes.
"""

import os
from pathlib import Path

# This file sits at  Screens/Hermes/Backend/settings_for_hermes.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Hermes folder
PROJECT_ROOT = HERE.parents[2]              # the repo root

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "hermes"
SCREEN_LABEL = "Hermes"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Own port. 8008 was reserved for an Office screen that was never built;
# that reservation moved to 8010 when this screen took the slot (D17.5).
PORT = 8008
HOST = "127.0.0.1"          # local means local

PAGE = SCREEN / "Page" / "page_for_hermes.html"

# ---------------------------------------------------------------------
# THE INSTALL IT REPORTS ON
# ---------------------------------------------------------------------
# Hermes keeps everything under one folder. On Windows that is
# %LOCALAPPDATA%\hermes; HERMES_HOME overrides it, which is how the
# phone host will point at a different install later.
def _hermes_home() -> Path:
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"])
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / "hermes"
    return Path.home() / ".hermes"


HERMES_HOME = _hermes_home()
HERMES_CONFIG = HERMES_HOME / "config.yaml"
HERMES_PROFILES = HERMES_HOME / "profiles"
HERMES_GATEWAY_STATE = HERMES_HOME / "gateway_state.json"

# Per-profile files this screen reads. Names come from Hermes itself.
PROFILE_CONFIG_NAME = "config.yaml"
PROFILE_SOUL_NAME = "SOUL.md"

# ---------------------------------------------------------------------
# THE GATEWAY PROFILES CALL THROUGH
# ---------------------------------------------------------------------
# Hermes profiles reach models through the OmniRoute gateway, declared
# as a custom_provider so all profiles share one model list (D25.1).
GATEWAY_BASE_URL = os.environ.get("GATEWAY_BASE_URL", "http://127.0.0.1:8003")
GATEWAY_PROVIDER_NAME = "omniroute"

# ---------------------------------------------------------------------
# THE DASHBOARD THIS SCREEN EMBEDS
# ---------------------------------------------------------------------
# `hermes dashboard` serves Hermes's own web UI here. This is Hermes's
# own default port, not a Kage port, and Kage never starts it from
# inside this screen (Rule 20) - Start_Inky/run_hermes_dashboard.py does,
# as its own process. The screen embeds it when it is up and says so
# plainly when it is not.
DASHBOARD_BASE_URL = os.environ.get("HERMES_DASHBOARD_URL",
                                    "http://127.0.0.1:9119")

# The command that starts it, shown verbatim on the page when it is down.
DASHBOARD_START_COMMAND = "hermes dashboard"

API_PREFIX = "/api/hermes"
