"""What the Learning screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about the study screen:
    its name, where it sits in the menu, and what tabs it has.

    Four facts and a list. That is the entire cost of adding a screen.
    Nothing in Main_Menu or Start_Inky changed to make this appear.

WHAT IS BEHIND IT
    Built 2026-08-20 (ADR-063, M9). Four calculation modules, a real
    page, real records (its own guide was deleted 2026-08-28 along with
    every other guide in the repo).

    Carried a fifth tab, Enhancement, from 2026-08-20 to 2026-08-22
    (ADR-064), then it moved out to become its own screen (ADR-067) - see
    Screens/Enhancement/. Same reasoning as this file's own docstring:
    that board was never Learning-specific, so it does not belong nested
    one level inside a screen it only sometimes concerned.

    Dropped to three tabs 2026-08-24 (ADR-100): Study merged into Plan.
    Learning now starts from a topic's own START LEARNING button, not a
    separate tab a click away from it.

WORDS
    Plain English on purpose. "Learning task", never "Quest".
    "Progress", never "XP". The game feel comes from how it looks, never
    from what it is called. See ADR-030.
"""

SCREEN_NAME = "learning"         # must match the folder name, lowercased
MENU_LABEL = "LEARNING"          # what you actually see in the menu
MENU_ORDER = 2                   # menu position. Finance is 1

# Five tabs (the menu's maximum). The room player is a detail route off
# Path, not its own tab - a room is a place inside the journey.
TABS = [
    {"key": "today",    "label": "Today",    "endpoint": "/api/learning/today"},
    {"key": "path",     "label": "Path",     "endpoint": "/api/learning/path"},
    {"key": "recall",   "label": "Recall",   "endpoint": "/api/learning/recall"},
    {"key": "insights", "label": "Insights", "endpoint": "/api/learning/insights"},
    {"key": "crew",     "label": "Crew",     "endpoint": "/api/learning/crew"},
]
