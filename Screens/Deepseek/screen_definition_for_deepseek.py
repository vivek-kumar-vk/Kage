"""What the Deepseek screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, where it sits in the menu, and what tabs it has. Nothing in
    Main_Menu or Start_Inky is edited to make this appear - they walk
    the Screens folder and find it (CLAUDE.md Rule 17).

WHAT IS BEHIND IT
    DeepSeek Harness (`dsh`) - DeepSeek AI's open-source agent harness
    (MIT, github.com/deepseek-ai/deepseek-harness), installed globally
    as @deepseek-ai/dsh. It runs as its own process, exactly like the
    model gateway, and this screen is where Kage shows it (D24).

    The point of dsh here is TRACES: its web profile shows every prompt,
    every tool call and every file write an agent makes, step by step.
    That is the whole reason this nav exists - to see what the agents
    are actually doing rather than trusting a summary.

    dsh is NOT started by this screen. Kage never spawns another
    process's server (CLAUDE.md Rule 20); "not running" is a first-class
    state that says so plainly and gives the command to fix it.

WORDS
    "Harness", not "runner" or "agent host" - the word dsh uses for
    itself, and the one the traces belong to.
"""

SCREEN_NAME = "deepseek"      # must match the folder name, lowercased
MENU_LABEL = "DEEPSEEK"       # what you actually see in the menu
MENU_ORDER = 6                # Finance 1, Learning 2, Model 3,
                              # Agent Deck 4, Anime 5, this 6

# One tab. This screen shows one thing - the harness and its traces.
TABS = [
    {"key": "traces", "label": "Traces", "endpoint": "/api/deepseek/overview"},
]
