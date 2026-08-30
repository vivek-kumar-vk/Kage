from pathlib import Path

HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent
PROJECT_ROOT = HERE.parents[2]

SCREEN_NAME = "agents"
SCREEN_LABEL = "AGENT DECK"

HOST = "127.0.0.1"
PORT = 8004
API_PREFIX = "/api/agents"

PAGE = SCREEN / "Page" / "page_for_agents.html"
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
USE_NEXT_UI = True

DB_PATH = HERE / "agents.db"
AI_AGENTS_DIR = SCREEN / "AI_Agents"
