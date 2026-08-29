"""Settings for the Enhancement screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.
"""

from pathlib import Path

# ---------------------------------------------------------------------
# WHERE THINGS ARE
# ---------------------------------------------------------------------
# This file sits at  Screens/Enhancement/Backend/settings_for_enhancement.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Enhancement folder
PROJECT_ROOT = HERE.parents[2]              # the inky folder

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "enhancement"
SCREEN_LABEL = "Enhancement"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Each screen gets its own port, so you can start one on its own while
# working on it without the others running. Finance is 8001, Learning is
# 8002, Models is 8005 - this is the next one.
PORT = 8004
HOST = "127.0.0.1"      # 127.0.0.1, not 0.0.0.0 - nothing else on the
                        # network can reach this. Local means local.

# The page this screen serves.
PAGE = SCREEN / "Page" / "page_for_enhancement.html"

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
API_PREFIX = "/api/enhancement"

# The folders the /dev/changed-since endpoint fingerprints: this
# screen's own code plus everything shared. Data folders are excluded
# inside code_change_monitor.py, so ordinary clicks never look
# like code changes.
WATCHED_FOLDERS = [SCREEN, PROJECT_ROOT / "Shared_By_All_Screens"]

# ---------------------------------------------------------------------
# SVELTE PILOT FLAG
# ---------------------------------------------------------------------
# False by default: the hand-drawn HTML page is served exactly as it
# always was, and nothing else in this screen behaves one bit
# differently. True (and the built app present) swaps the page served
# at / for the Svelte 5 pilot under Page/svelte_app/dist - every
# /api route keeps working either way. Rollback is flipping this to
# False, or git checkout of the pre-enhancement-svelte commit.
USE_SVELTE = False

# Where the pilot's built output must sit for the flag to have an
# effect. A flag turned on with no build present falls back to the
# ordinary page rather than serving a blank screen.
SVELTE_DIST = SCREEN / "Page" / "svelte_app" / "dist"

# ---------------------------------------------------------------------
# NEXT.JS REBUILD FLAG (Phase 12.4)
# ---------------------------------------------------------------------
# Same on/off pattern as USE_SVELTE above, one rung newer: False by
# default means every existing page behaves exactly as it always did.
# True (and the static export present) swaps the page served at / for
# the Next.js rebuild under Page/next_app/out - every /api route keeps
# working either way. Rollback is flipping this to False, or git
# checkout of the pre-enhancement-next commit.
USE_NEXT_UI = True

# Where the rebuilt UI's static export must sit for the flag to have
# an effect (`npm run build` writes it there). A flag turned on with
# no build present falls back rather than serving a blank screen -
# honest beats broken, same rule as above.
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
