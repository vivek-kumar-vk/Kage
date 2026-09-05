import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent
PROJECT_ROOT = HERE.parents[2]
SCREEN_NAME = "learning"
SCREEN_LABEL = "Learning"
HOST = "127.0.0.1"
PORT = 8003
API_PREFIX = "/api/learning"
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
USE_NEXT_UI = True

# The launcher reads PAGE to decide whether to print "page ready" or
# "data only, page not written yet". This screen's page is the Next
# export's index.html, so point at it - without this the launcher called
# a fully working screen unbuilt on every start.
PAGE = NEXT_DIST / "index.html"
DB_PATH = HERE / "learning.db"

# The OFFICE screen (M7, :8011) — read over HTTP for interview-day
# preemption (D38). A real env var wins; the default is Office's own port.
OFFICE_URL = os.getenv("OFFICE_URL", "http://127.0.0.1:8011")
OFFICE_TIMEOUT_S = 4.0
