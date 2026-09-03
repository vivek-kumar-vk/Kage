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

# The page this screen serves: the Next static export, mirrored into
# Backend/app/static by Backend/build.py. server_for_finance.py mounts
# the app, which serves that export itself; PAGE exists only so the
# launcher can print "page ready" instead of "not built yet".
PAGE = HERE / "app" / "static" / "index.html"

# The Next.js source the export is built from (`npm run build` there,
# then Backend/build.py mirrors out/ into app/static/).
NEXT_SOURCE = SCREEN / "Page" / "next_app"

# Private records this screen still owns (gitignored).
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
WATCHED_FOLDERS = [SCREEN, PROJECT_ROOT / "Shared_By_All_Screens"]  # the shared tree is now just Look_And_Feel + the noticeboard


