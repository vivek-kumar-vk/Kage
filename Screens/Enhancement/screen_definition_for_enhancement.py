"""What the Enhancement screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, where it sits in the menu, and what tabs it has.

    Four facts and a list. That is the entire cost of adding a screen.
    Nothing in Main_Menu or Start_Inky changed to make this appear.

WHAT IS BEHIND IT
    Promoted 2026-08-22 (ADR-067) out of Learning's Enhancement tab
    (ADR-064), at the user's request - a running idea-capture board for
    the whole project, not just Learning. Same data, same
    manage_enhancement_ideas.py module, moved folder rather than
    duplicated (its own guide was deleted 2026-08-28 along with every
    other guide in the repo).

WORDS
    "Idea", never "ticket" or "backlog item" - this is a place to not
    lose a thought, not a project tracker (ADR-030's plain-English rule).
"""

SCREEN_NAME = "enhancement"      # must match the folder name, lowercased
MENU_LABEL = "ENHANCEMENT"       # what you actually see in the menu
MENU_ORDER = 4                   # menu position, right below Models (3)

# One tab. This screen does one thing - a screen needing six tabs is two
# screens; a screen doing one thing does not need five to look finished.
TABS = [
    {"key": "board", "label": "Board", "endpoint": "/api/enhancement/ideas"},
]
