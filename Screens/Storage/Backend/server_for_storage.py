"""The server behind the Storage screen - the repo's one local-disk
storage seam (D11.5).

WHAT THIS FILE DOES
    Boots the seam on its own port, creates KAGE_DATA_DIR if it does not
    exist yet, and serves this screen's own status page.

WHAT THIS FILE MUST NEVER DO
    Import from Shared_By_All_Screens/, or reach into another screen's
    code (Rule 5). Commit anything personal - everything real lives under
    KAGE_DATA_DIR, repo-relative but gitignored (Rule 7.1, D40).

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    .venv\\Scripts\\python Screens\\Storage\\Backend\\server_for_storage.py
    then open http://127.0.0.1:8009
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_storage as cfg  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from db import init_db  # noqa: E402
import seed  # noqa: E402
from services import seam, rag, trader, library  # noqa: E402
from services import spine_api, ingest, structure  # noqa: E402

app = FastAPI(title=cfg.SCREEN_LABEL)

# GET-only CORS for the Main Menu page (8000) and the one-port proxy (9000):
# the Day Plan card reads its agent plan from the library seam cross-origin.
# Everything else about the seam stays same-origin / localhost-only; the
# service binds loopback, so this never leaves the box.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_methods=["GET"],
    allow_headers=["*"],
)

cfg.KAGE_DATA_DIR.mkdir(parents=True, exist_ok=True)
init_db()
seed.run()

app.include_router(seam.router)
app.include_router(rag.router)
app.include_router(trader.router)
app.include_router(library.router)
app.include_router(spine_api.router)
app.include_router(ingest.router)
app.include_router(structure.router)


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
    """One honest snapshot: is the data dir reachable, how many docs, how
    much free space. Every value here is measured, never assumed."""
    try:
        docs = seam.list_docs()
        doc_count = len(docs)
        reachable = True
        problem = None
    except OSError as exc:
        docs, doc_count, reachable, problem = [], 0, False, str(exc)

    free_bytes = None
    try:
        import shutil

        free_bytes = shutil.disk_usage(cfg.KAGE_DATA_DIR).free
    except OSError:
        pass

    last_backup = None
    backup_status_file = cfg.KAGE_DATA_DIR / "_backup_status.json"
    if backup_status_file.is_file():
        try:
            import json
            last_backup = json.loads(backup_status_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            last_backup = {"problem": "backup status file unreadable"}

    return {
        "state": "ok" if reachable else "error",
        "problem": problem,
        "data_dir": str(cfg.KAGE_DATA_DIR),
        "doc_count": doc_count,
        "free_bytes": free_bytes,
        "last_backup": last_backup,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT, log_level="info")
