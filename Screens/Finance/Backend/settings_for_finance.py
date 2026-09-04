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

# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------
API_PREFIX = "/api/finance"


