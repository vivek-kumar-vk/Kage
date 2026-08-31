import os
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


def _dotenv_values():
    """Fallback env for runs outside Start_Everything. Real env vars always win (D6)."""
    env_path = PROJECT_ROOT / ".env"
    values = {}
    try:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                values.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except OSError:
        pass
    return values


_DOTENV = _dotenv_values()


def _env(key, default=""):
    return os.getenv(key) or _DOTENV.get(key) or default


# --- OmniRoute gateway (D6 / D12): the one LLM seam for agent asks ---
OMNIROUTE_URL = _env("OMNIROUTE_URL", "http://127.0.0.1:8003")
GATEWAY_API_KEY = _env("GATEWAY_API_KEY")
OMNIROUTE_MODEL = _env("OMNIROUTE_MODEL")

# Ambient demo activity on the event stream. Always labeled sim=1 (honest state).
# Off by default (public repo) — set AGENTS_DEMO_EVENTS=1 to make the office look busy.
DEMO_EVENTS = _env("AGENTS_DEMO_EVENTS", "0").lower() in {"1", "true", "yes", "on"}
