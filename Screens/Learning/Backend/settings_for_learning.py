"""Settings for the Learning screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.
"""

from pathlib import Path

# ---------------------------------------------------------------------
# WHERE THINGS ARE
# ---------------------------------------------------------------------
# This file sits at  Screens/Learning/Backend/settings_for_learning.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Learning folder
PROJECT_ROOT = HERE.parents[2]              # the inky folder

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "learning"
SCREEN_LABEL = "Learning"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Each screen gets its own port, so you can start one on its own while
# working on it without the others running.
PORT = 8002
HOST = "127.0.0.1"      # 127.0.0.1, not 0.0.0.0 - nothing else on the
                        # network can reach this. Local means local.

# The page this screen serves. Not written yet - until it is, the server
# hands over a plain "not built yet" page instead.
PAGE = SCREEN / "Page" / "page_for_learning.html"

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
API_PREFIX = "/api/learning"

# The folders the /dev/changed-since endpoint fingerprints: this
# screen's own code plus everything shared. Data folders are excluded
# inside code_change_monitor.py, so ordinary clicks never look
# like code changes.
WATCHED_FOLDERS = [SCREEN, PROJECT_ROOT / "Shared_By_All_Screens"]

# ---------------------------------------------------------------------
# NEXT.JS REBUILD FLAG (Phase 12.4)
# ---------------------------------------------------------------------
# Same on/off pattern as Main_Menu's (Phase 12.3), Enhancement's and
# Models' (Phase 12.4) USE_NEXT_UI flags: False by default means every
# existing page behaves exactly as it always did. True (and the static
# export present) swaps the page served at / for the Next.js rebuild
# under Page/next_app/out - every /api route keeps working either way.
# Rollback is flipping this to False, or git checkout of the
# pre-learning-next commit.
USE_NEXT_UI = True

# Where the rebuilt UI's static export must sit for the flag to have
# an effect (`npm run build` writes it there). A flag turned on with
# no build present falls back rather than serving a blank screen -
# honest beats broken, same rule as above.
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
