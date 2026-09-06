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
LOOK_AND_FEEL = SCREEN / "Look_And_Feel"
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
# Empty: the "Models" pill pointed at an external admin dashboard.
# Replaced by a real, discovered Screens/Model/ screen that reads the
# gateway's REST API into Kage's own UI instead.
EXTERNAL_LINKS: dict[str, str] = {}

# The folders the /dev/changed-since endpoint fingerprints: this
# screen's own code plus everything shared. Data folders are excluded
# inside code_change_monitor.py, so ordinary clicks never look
# like code changes.
MONITORED_FOLDERS = [SCREEN, PROJECT_ROOT / "Shared_By_All_Screens"]  # Look_And_Feel moved into SCREEN (item 8); Shared_By_All_Screens is now just the launcher+menu port-discovery/restart-signal code this screen imports, plus the noticeboard

# ---------------------------------------------------------------------
# NEXT.JS REBUILD FLAG (Phase 12.3)
# ---------------------------------------------------------------------
# False by default means every existing page behaves exactly as it always did.
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

# ---------------------------------------------------------------------
# EMAIL CARD (D22) - the working Email panel in the home grid
# ---------------------------------------------------------------------
# The mailbox itself is read-only Gmail (OAuth, scope gmail.readonly).
# Everything personal - token, credentials, SQLite store, digest sender
# list - lives in Email_Data/ next to this file, which is gitignored
# (CLAUDE.md Rule 7: nothing personal in git).
import os

EMAIL_DATA_DIR = HERE / "Email_Data"

# How often the background loop polls Gmail. Env wins so a hosted box
# (Termux 24/7) can poll less aggressively without a code change.
EMAIL_SYNC_MINUTES = int(os.environ.get("EMAIL_SYNC_MINUTES", "5"))

# The categorizer / digest brain: one `claude -p` run per batch, then the
# session ends. Model alias as accepted by the Claude Code CLI.
EMAIL_BRAIN_MODEL = os.environ.get("EMAIL_CLAUDE_MODEL", "sonnet")
EMAIL_CLAUDE_TIMEOUT = int(os.environ.get("EMAIL_CLAUDE_TIMEOUT", "180"))

# Newsletter digest: once a day the brain summarizes new mail from the
# senders listed in Email_Data/digest_senders.json and posts the summary
# into the Agent Deck as a note from this agent profile.
EMAIL_DIGEST_AGENT = os.environ.get("EMAIL_DIGEST_AGENT", "KB_Librarian_Agent")
EMAIL_DIGEST_HOUR = int(os.environ.get("EMAIL_DIGEST_HOUR", "8"))

# Where the digest is POSTed. Default: the Agent Deck screen's own
# settings file (one port, written once - Rule 16); env wins for hosting.
try:
    from Shared_By_All_Screens.read_screen_settings import web_address
    EMAIL_DECK_URL = os.environ.get(
        "AGENTS_BASE_URL",
        web_address(PROJECT_ROOT / "Screens" / "Agents"),
    )
except Exception:
    EMAIL_DECK_URL = os.environ.get("AGENTS_BASE_URL", "http://127.0.0.1:8004")

# The agent ring (2026-09-06): the roster + unread counts the home page's
# ring nodes show, read live from the same screen the digest posts to.
# One base URL, resolved once here - never hardcoded in the server file.
AGENTS_SCREEN_URL = EMAIL_DECK_URL
AGENTS_ROSTER_TIMEOUT = float(os.environ.get("AGENTS_ROSTER_TIMEOUT", "3"))

# The name printed on the card footer, next to the account address.
EMAIL_OWNER_NAME = os.environ.get("EMAIL_OWNER_NAME", "SINGH")

# Opt-in fixture for reviewing the card before Gmail is connected
# (D12.2 pattern: opt-in, labelled simulated, never presented as real).
EMAIL_DEMO = os.environ.get("EMAIL_DEMO", "") == "1"

# Local port used only while the OAuth consent tab is open.
EMAIL_OAUTH_PORT = int(os.environ.get("EMAIL_OAUTH_PORT", "8788"))


# ---------------------------------------------------------------------
# CALENDAR CARD (D23) - Google Calendar + the WakaTime switch
# ---------------------------------------------------------------------
# Same shape as the Email card above: read/write Google Calendar over
# OAuth, a local SQLite mirror, a short-lived agent that proposes.
# Everything personal - OAuth client, token, SQLite, WakaTime key -
# lives in Calendar_Data/ next to this file, which is gitignored
# (CLAUDE.md Rule 7).
CALENDAR_DATA_DIR = HERE / "Calendar_Data"

# Which Google calendar the card mirrors and the agent writes to.
# "primary" is the account's own calendar.
CALENDAR_ID = os.environ.get("CALENDAR_ID", "primary")

# How often the background loop pulls Google. Env wins so a hosted box
# can poll less aggressively without a code change.
CALENDAR_SYNC_MINUTES = int(os.environ.get("CALENDAR_SYNC_MINUTES", "10"))

# How far either side of today the mirror keeps. The month grid never
# asks for more than this, so a scroll past the edge says "not synced"
# instead of silently showing an empty month (Rule 8).
CALENDAR_DAYS_BACK = int(os.environ.get("CALENDAR_DAYS_BACK", "120"))
CALENDAR_DAYS_AHEAD = int(os.environ.get("CALENDAR_DAYS_AHEAD", "120"))

# --- the learning agent -----------------------------------------------
# It reads the day's real signals and PROPOSES calendar events and day
# notes. Writing to Google fires phone notifications, so a proposal is
# never written on its own: CALENDAR_AUTO_WRITE stays False until the
# owner has watched what it proposes and turned it on deliberately.
CALENDAR_AUTO_WRITE = os.environ.get("CALENDAR_AUTO_WRITE", "") == "1"

# Which brain runs it. "claude_cli" is the Email card's proven path -
# one `claude -p` per batch, already logged in, no key in .env.
# "omniroute" sends the same prompt to the gateway on 8010, which is
# where Hermes and DeepSeek arrive (PLAN item 3).
CALENDAR_AGENT_BACKEND = os.environ.get("CALENDAR_AGENT_BACKEND", "claude_cli")
CALENDAR_AGENT_MODEL = os.environ.get("CALENDAR_AGENT_MODEL", "sonnet")
CALENDAR_AGENT_TIMEOUT = int(os.environ.get("CALENDAR_AGENT_TIMEOUT", "240"))

# The gateway, read from its own runner's port (Rule 16) with an env
# override for hosting. Unreachable is a first-class state (Rule 20).
OMNIROUTE_BASE_URL = os.environ.get("OMNIROUTE_BASE_URL", "http://127.0.0.1:8010")

# The nightly learning run, local hour of day.
CALENDAR_AGENT_HOUR = int(os.environ.get("CALENDAR_AGENT_HOUR", "22"))

# Local port used only while the OAuth consent tab is open. Must differ
# from the Email card's, so both can be connected in one sitting.
CALENDAR_OAUTH_PORT = int(os.environ.get("CALENDAR_OAUTH_PORT", "8789"))

# ---------------------------------------------------------------------
# WAKATIME (the other half of the Calendar card's switch)
# ---------------------------------------------------------------------
# Auth is the plain API key over HTTP Basic (base64), not OAuth: this is
# one local user reading his own stats, so the consent dance buys
# nothing. The key is read from Calendar_Data/wakatime.json (gitignored)
# or the env; absent means the card says "not connected" (Rule 8).
WAKATIME_API_BASE = os.environ.get("WAKATIME_API_BASE", "https://wakatime.com/api/v1")
WAKATIME_KEY_FILE = CALENDAR_DATA_DIR / "wakatime.json"
WAKATIME_API_KEY_ENV = os.environ.get("WAKATIME_API_KEY", "")
WAKATIME_TIMEOUT = int(os.environ.get("WAKATIME_TIMEOUT", "20"))

# The free plan only exposes 7 days of history. The pipeline snapshots
# each day's summary into the local store so history accumulates from
# today forward regardless of plan - the one thing that must not wait.
WAKATIME_SNAPSHOT_ENABLED = os.environ.get("WAKATIME_SNAPSHOT", "1") == "1"
