"""What the Model screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, where it sits in the menu, and what tabs it has. Four facts
    and a list - the entire cost of adding a screen. Nothing in
    Main_Menu or Start_Inky changed to make this appear.

WHAT IS BEHIND IT
    A local model gateway (OmniRoute, its own process) that does
    auto-routing and fallback across model providers, and this screen -
    the place Kage shows that gateway's own dashboard, embedded in an
    iframe within a RUBRIC-themed shell (D10). The backend's
    /api/model/overview health probe gates whether the iframe loads or
    a "gateway unreachable" fallback is shown.

    This screen is a complete independent component - it imports nothing
    from Shared_By_All_Screens/ or Shared_By_All_Agents/.

WORDS
    "Gateway", not "proxy layer" or "LLM router" - the one word for the
    thing every model call goes through.
"""

SCREEN_NAME = "model"        # must match the folder name, lowercased
MENU_LABEL = "MODEL"         # what you actually see in the menu
MENU_ORDER = 3               # menu position (Finance 1, Learning 2, Enhancement 4)

# One tab. This screen shows one thing - the gateway's state.
TABS = [
    {"key": "overview", "label": "Overview", "endpoint": "/api/model/overview"},
]
