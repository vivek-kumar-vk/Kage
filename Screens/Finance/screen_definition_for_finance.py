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

# Four tabs (was five). The Chat tab and its /api/finance/chat route
# were removed 2026-08-24; asking survives in the Investments and
# Portfolio Analysis "Ask INKY" strips. Four is under the declared
# maximum of five.
TABS = [
    {"key": "overview",     "label": "Overview",            "endpoint": "/api/finance/command"},
    {"key": "investments",  "label": "Investments",         "endpoint": "/api/finance/investments"},
    {"key": "portfolio",    "label": "Portfolio Analysis",  "endpoint": "/api/finance/portfolio-analysis"},
    {"key": "debt",         "label": "Debt & Liabilities",  "endpoint": "/api/finance/debt"},
]
