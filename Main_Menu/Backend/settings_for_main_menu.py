"""Settings for the main menu screen.

Everything adjustable lives here, so you never go hunting through the
server file to change a port or a folder name.
"""

from pathlib import Path

# ---------------------------------------------------------------------
# WHERE THINGS ARE
# ---------------------------------------------------------------------
# This file sits at  Main_Menu/Backend/settings_for_main_menu.py
HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Main_Menu folder
PROJECT_ROOT = HERE.parents[1]              # the inky folder

# ---------------------------------------------------------------------
# WHO THIS SCREEN IS
# ---------------------------------------------------------------------
SCREEN_NAME = "main_menu"
SCREEN_LABEL = "Main Menu"

# ---------------------------------------------------------------------
# SERVING
# ---------------------------------------------------------------------
# Each screen gets its own port, so you can start one on its own while
# working on it without the others running. The main menu is 8000
# because it is the one you open first.
PORT = 8000
HOST = "127.0.0.1"      # 127.0.0.1, not 0.0.0.0 - nothing else on the
                        # network can reach this. Local means local.

# The page this screen serves.
PAGE = SCREEN / "Page" / "page_for_main_menu.html"

# Colours, fonts and background art are shared by every screen so they
# cannot drift apart.
LOOK_AND_FEEL = PROJECT_ROOT / "Shared_By_All_Screens" / "Look_And_Feel"
FONTS_DIR = LOOK_AND_FEEL / "Fonts"

# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------
API_PREFIX = "/api/main_menu"

# ---------------------------------------------------------------------
# EXTERNAL LINKS IN THE MENU
# ---------------------------------------------------------------------
# A menu pill that points at something INKY does not itself serve, so it
# has no Backend/settings file and no port of its own. Keyed by the
# Screens/ folder name (discovery still reports it in the usual place);
# the value is the absolute URL the pill links to.
EXTERNAL_LINKS = {
    "Models": "http://127.0.0.1:8003/ui",   # LiteLLM's own dashboard
}

# The folders the /dev/changed-since endpoint fingerprints: this
# screen's own code plus everything shared. Data folders are excluded
# inside code_change_monitor.py, so ordinary clicks never look
# like code changes.
MONITORED_FOLDERS = [SCREEN, PROJECT_ROOT / "Shared_By_All_Screens"]

# ---------------------------------------------------------------------
# SVELTE PILOT FLAG
# ---------------------------------------------------------------------
# False by default: the hand-drawn HTML page is served exactly as it
# always was, and nothing else in this screen behaves one bit
# differently. True (and the built app present) swaps the page served
# at / for the Svelte 5 pilot under Page/svelte_app/dist - every
# /api route keeps working either way. Rollback is flipping this to
# False, or git checkout of the pre-main-menu-svelte commit.
USE_SVELTE = True

# Where the pilot's built output must sit for the flag to have an
# effect. A flag turned on with no build present falls back to the
# ordinary page rather than serving a blank screen.
SVELTE_DIST = SCREEN / "Page" / "svelte_app" / "dist"

# ---------------------------------------------------------------------
# NEXT.JS REBUILD FLAG (Phase 12.3)
# ---------------------------------------------------------------------
# Same on/off pattern as USE_SVELTE above, one rung newer: False by
# default means every existing page behaves exactly as it always did.
# True (and the static export present) swaps the page served at / for
# the Next.js rebuild under Page/next_app/out - every /api route keeps
# working either way. Rollback is flipping this to False, or git
# checkout of the pre-main-menu-next commit.
USE_NEXT_UI = True

# Where the rebuilt UI's static export must sit for the flag to have
# an effect (`npm run build` writes it there). A flag turned on with
# no build present falls back rather than serving a blank screen -
# honest beats broken, same rule as above.
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
