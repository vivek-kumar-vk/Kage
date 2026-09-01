"""AGENT DECK screen definition.

Local agent workspace screen. One tab: Workspace. The board is one room inside the workspace.
"""

SCREEN_NAME = "agents"
MENU_LABEL  = "AGENT DECK"
MENU_ORDER  = 4
TABS = [
    {"key": "workspace", "label": "Workspace", "endpoint": "/api/agents/workspace"},
]
