"""Settings for the Finance screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.
"""

from pathlib import Path

# ---------------------------------------------------------------------
# WHERE THINGS ARE
# ---------------------------------------------------------------------
# This file sits at  Screens/Finance/Backend/settings_for_finance.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Finance folder
PROJECT_ROOT = HERE.parents[2]              # the inky folder

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "finance"
SCREEN_LABEL = "Finance"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Each screen gets its own port, so you can start one on its own while
# working on it without the others running.
PORT = 8001
HOST = "127.0.0.1"      # 127.0.0.1, not 0.0.0.0 - nothing else on the
                        # network can reach this. Local means local.

# The page this screen serves. Not written yet - until it is, the server
# hands over a plain "not built yet" page instead.
PAGE = SCREEN / "Page" / "page_for_finance.html"

# Everything this screen owns.
CALCULATIONS = SCREEN / "Calculations"
SAVED_RECORDS = SCREEN / "Saved_Records"

# Colours, fonts and background art are shared by every screen so they
# cannot drift apart.
LOOK_AND_FEEL = PROJECT_ROOT / "Shared_By_All_Screens" / "Look_And_Feel"
FONTS_DIR = LOOK_AND_FEEL / "Fonts"

# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------
API_PREFIX = "/api/finance"

# The folders the /dev/changed-since endpoint fingerprints: this
# screen's own code plus everything shared. Data folders are excluded
# inside code_change_monitor.py, so ordinary clicks never look
# like code changes.
WATCHED_FOLDERS = [SCREEN, PROJECT_ROOT / "Shared_By_All_Screens"]

# ---------------------------------------------------------------------
# NEXT.JS REBUILD FLAG (Phase 12.4) - RETIRED 2026-08-30
# ---------------------------------------------------------------------
# The Finance screen no longer serves anything under Screens/Finance/.
# server_for_finance.py mounts finance-os/backend's create_app()
# instead, which serves its own Next static export. These two settings
# are dead; server_for_finance.py does not read them. Kept only so an
# older tool that imports this module does not KeyError.
USE_NEXT_UI = False
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"

