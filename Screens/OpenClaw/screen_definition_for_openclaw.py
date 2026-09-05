"""What the OpenClaw screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, where it sits in the menu, and what tabs it has. Nothing in
    Main_Menu or Start_Inky is edited to make this appear - they walk
    the Screens folder and find it (CLAUDE.md Rule 17).

WHAT IS BEHIND IT
    OpenClaw (github.com/openclaw/openclaw) - a local AI gateway that
    connects models, tools and messaging channels through one process.
    Installed with `npm install -g openclaw`, run as its own gateway
    process (Start_Inky/run_openclaw.py), same pattern as Hermes and the
    DeepSeek Harness: Kage reports on it, it does not run inside Kage.

WORDS
    "Gateway", not "bot" or "assistant" - the one process every OpenClaw
    channel/tool call goes through, same word used for OmniRoute.
"""

SCREEN_NAME = "openclaw"        # must match the folder name, lowercased
MENU_LABEL = "OPENCLAW"         # what you actually see in the menu
MENU_ORDER = 9                  # appended after Storage (8)

# One tab. This screen shows one thing - the gateway's live health.
TABS = [
    {"key": "overview", "label": "Overview", "endpoint": "/api/openclaw/overview"},
]
