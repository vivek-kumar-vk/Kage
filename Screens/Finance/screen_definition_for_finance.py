"""What the Finance screen is.

Four facts and nothing else: its name, what the menu calls it, where it
sits in the menu, and what tabs it has.

The main menu reads this file. It never hardcodes a screen name, and
this file never imports anything from another screen.

A tab here is a name and a web address. It is not code that draws
anything - the page fetches these addresses and draws itself.
"""

SCREEN_NAME = "finance"          # must match the folder name, lowercased
MENU_LABEL = "FINANCE"           # what you actually see in the menu
MENU_ORDER = 1                   # menu position. Lower comes first

# Five tabs — the finance-os app's own nav (2026-08-30 cutover). Each
# endpoint is a representative address on that tab; the page renders its
# own full tab strip.
TABS = [
    {"key": "overview",     "label": "Overview",     "endpoint": "/api/finance/overview/net-worth"},
    {"key": "investments",  "label": "Investments",  "endpoint": "/api/finance/investments/holdings"},
    {"key": "debt",         "label": "Debt",         "endpoint": "/api/finance/debt"},
    {"key": "tracker",      "label": "Tracker",      "endpoint": "/api/finance/tracker/transactions"},
    {"key": "learning",     "label": "Learning",     "endpoint": "/api/finance/learning/topics"},
]
