"""What the Hermes screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, where it sits in the menu, and what tabs it has. Nothing in
    Main_Menu or Start_Inky is edited to make this appear - they walk
    the Screens folder and find it (CLAUDE.md Rule 17).

WHAT IS BEHIND IT
    Hermes Agent (Nous Research) - installed at
    %LOCALAPPDATA%\hermes, driven by the `hermes` CLI. It already
    carries a fleet of profiles, each one a Bot with its own SOUL.md
    persona, its own model choice and its own chat history (D25).

    That history IS the bot's memory - it is what "training the agent"
    means here. No fine-tuning, no weights: a profile accumulates what
    it has learned across sessions, and the ledger files it maintains
    are the visible part of that.

    This screen reads the Hermes install and reports it. It does not
    run the agent - `hermes -p <profile> chat` does, in a terminal, and
    the profile is the thing that persists.

WORDS
    "Profile", not "bot config" - the word Hermes uses, and the unit
    that owns a persona, a model and a memory all at once.
"""

SCREEN_NAME = "hermes"        # must match the folder name, lowercased
MENU_LABEL = "HERMES"         # what you actually see in the menu
MENU_ORDER = 7                # Finance 1, Learning 2, Model 3, Agent Deck 4,
                              # Anime 5, Deepseek 6, this 7

# One tab. This screen shows one thing - the profile fleet and its state.
TABS = [
    {"key": "profiles", "label": "Profiles", "endpoint": "/api/hermes/overview"},
]
