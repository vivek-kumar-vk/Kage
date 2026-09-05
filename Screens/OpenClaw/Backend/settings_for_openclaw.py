"""Settings for the OpenClaw screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port.

This screen is a complete independent component (CLAUDE.md Rule 5): it
imports nothing from Shared_By_All_Screens/ and reaches into no other
screen's code. The few values the launcher needs by convention -
SCREEN_NAME, PORT, HOST, PAGE - are plain module attributes.
"""

import os
from pathlib import Path

# This file sits at  Screens/OpenClaw/Backend/settings_for_openclaw.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the OpenClaw folder
PROJECT_ROOT = HERE.parents[2]              # the repo root

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "openclaw"
SCREEN_LABEL = "OpenClaw"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Own port, see CLAUDE.md's Ports table.
PORT = 8006
HOST = "127.0.0.1"          # local means local

PAGE = SCREEN / "Page" / "page_for_openclaw.html"

# ---------------------------------------------------------------------
# THE OPENCLAW GATEWAY THIS SCREEN EMBEDS/REPORTS ON
# ---------------------------------------------------------------------
# OpenClaw (github.com/openclaw/openclaw) runs its own gateway - the
# Control UI and the /healthz probe live on this one address. 18789 is
# OpenClaw's own default port, not a Kage port; Kage never starts it
# from inside this screen (Rule 20) - Start_Inky/run_openclaw.py does,
# as its own process. The screen embeds it when it is up and says so
# plainly when it is not.
GATEWAY_BASE_URL = os.environ.get("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789")

# The command that starts it, shown verbatim on the page when it is down.
GATEWAY_START_COMMAND = ("openclaw gateway run --port 18789 --bind loopback "
                         "--auth none --allow-unconfigured")

API_PREFIX = "/api/openclaw"
