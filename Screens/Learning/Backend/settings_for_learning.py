from pathlib import Path

HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent
PROJECT_ROOT = HERE.parents[2]
SCREEN_NAME = "learning"
SCREEN_LABEL = "Learning"
HOST = "127.0.0.1"
PORT = 8002
API_PREFIX = "/api/learning"
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
USE_NEXT_UI = True
DB_PATH = HERE / "learning.db"
