"""What the OFFICE screen is.

WHAT THIS FILE IS
    The only thing the main menu needs to know about this screen: its
    name, menu position, and its tabs. Nothing in Main_Menu or Start_Inky
    is edited to make this appear - they walk the Screens folder and find
    it (CLAUDE.md Rule 17).

WHAT IS BEHIND IT
    The job-hunt workbench (D17.4, M7). Its own FastAPI + SQLite
    (office.db, gitignored). Five tabs: the apply funnel, the pipeline,
    interview prep, the daily work log, and resume readiness.

    RESUME READINESS enforces the no-inflation rule mechanically (D17.5):
    a skill is resume-defensible only at >=2 Good/Easy recall ratings,
    read live from the Learning screen over HTTP (Rule 5) and mirrored
    locally with a fetched_at. Learning down => the tab says so, it never
    guesses defensible.

    NO PORTAL AUTOMATION, EVER (D17.4). The agents that will live here
    (M8, Tailor/Preparer/Reporter) prep; the owner clicks Apply.
"""

SCREEN_NAME = "office"           # must match the folder name, lowercased
MENU_LABEL = "OFFICE"
MENU_ORDER = 10                  # after OpenClaw (9)

TABS = [
    {"key": "overview",   "label": "Overview",   "endpoint": "/api/office/overview"},
    {"key": "pipeline",   "label": "Pipeline",   "endpoint": "/api/office/applications"},
    {"key": "prep",       "label": "Interview Prep", "endpoint": "/api/office/interviews"},
    {"key": "worklog",    "label": "Work Log",   "endpoint": "/api/office/work-log"},
    {"key": "readiness",  "label": "Resume Readiness", "endpoint": "/api/office/resume-readiness"},
]
