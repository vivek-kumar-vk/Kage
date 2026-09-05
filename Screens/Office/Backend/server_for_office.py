"""The server behind the OFFICE screen (M7, D17.4).

WHAT THIS FILE DOES
    Boots office.db, seeds a few example rows on a fresh db, serves the
    hand-rolled status page, and mounts the five tab routers.

WHAT THIS FILE MUST NEVER DO
    Import from Shared_By_All_Screens/, reach into another screen's code,
    or automate a job portal (D17.4). It talks to Learning over HTTP only.

RUN IT ON ITS OWN
    cd <repo root>
    .venv\\Scripts\\python Screens\\Office\\Backend\\server_for_office.py
    then open http://127.0.0.1:8011
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_office as cfg  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from db import init_db  # noqa: E402
import seed  # noqa: E402
from services import (  # noqa: E402
    overview, applications, interviews, work_log, resume_readiness,
)

app = FastAPI(title=cfg.SCREEN_LABEL)

init_db()
seed.run()

for r in (overview, applications, interviews, work_log, resume_readiness):
    app.include_router(r.router)


@app.get("/")
def page():
    if not cfg.PAGE.is_file():
        return JSONResponse(
            {"status": "page missing", "expected": str(cfg.PAGE)},
            status_code=503,
        )
    return FileResponse(cfg.PAGE)


@app.get(cfg.API_PREFIX + "/status")
def status():
    """One honest snapshot for the menu's health probe."""
    try:
        from db import connect

        conn = connect()
        try:
            apps = conn.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]
            ivs = conn.execute("SELECT COUNT(*) c FROM interviews").fetchone()["c"]
            logs = conn.execute("SELECT COUNT(*) c FROM work_log").fetchone()["c"]
        finally:
            conn.close()
        return {
            "state": "ok",
            "db": str(cfg.DB_PATH),
            "applications": apps,
            "interviews": ivs,
            "work_log_entries": logs,
        }
    except Exception as exc:  # noqa: BLE001 - a broken db is a real state
        return {"state": "error", "problem": str(exc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT, log_level="info")
