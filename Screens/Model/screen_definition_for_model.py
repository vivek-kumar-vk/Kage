"""What the Model screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, where it sits in the menu, and what tabs it has. Four facts
    and a list - the entire cost of adding a screen. Nothing in
    Main_Menu or Start_Inky changed to make this appear.

WHAT IS BEHIND IT
    A local LiteLLM gateway (its own process, port 8003) that does
    auto-routing and fallback across model providers, and this screen -
    the place Kage shows that gateway's own data (models, usage, cost,
    latency, request logs, health), read from its REST API, never a
    third-party web UI. Wayfinder effort .scratch/model-page-litellm/.

    Scaffold only for now (ticket T2): the page is an honest placeholder
    until the gateway is wired (T3-T6) and the data blocks are designed
    (T7). This screen is a complete independent component - it imports
    nothing from Shared_By_All_Screens/ or Shared_By_All_Agents/.

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
