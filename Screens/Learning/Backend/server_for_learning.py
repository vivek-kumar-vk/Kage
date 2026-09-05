from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_learning as cfg
from db import init_db
import seed
from services import today, sessions, path, room, recall, insights, crew, observability, skills

app = FastAPI(title=cfg.SCREEN_LABEL)
app.add_middleware(observability.ObservabilityMiddleware)

init_db()
seed.run()

for router in (today, sessions, path, room, recall, insights, crew, observability, skills):
    app.include_router(router.router)


# The exported HTML shells point at hash-named _next/* chunks, so a stale
# shell loads stale JS - and stale JS is what makes a shipped fix (e.g.
# the shallow-history tab nav) look like it never landed. The shells are
# tiny; make the browser revalidate them every time. Hashed _next/*
# assets keep their default cacheable behaviour - the hash busts them.
NO_CACHE = {"Cache-Control": "no-cache"}


@app.get("/")
def root():
    if cfg.USE_NEXT_UI:
        index_path = cfg.NEXT_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path, headers=NO_CACHE)

    return JSONResponse(
        {
            "status": "not built yet",
            "api_routes": [
                cfg.API_PREFIX + "/today",
                cfg.API_PREFIX + "/session/start",
                cfg.API_PREFIX + "/path",
                cfg.API_PREFIX + "/room/{id}",
                cfg.API_PREFIX + "/recall",
                cfg.API_PREFIX + "/insights",
                cfg.API_PREFIX + "/crew",
            ],
        }
    )


# D17.1 — the owner's PII corpus (gitignored Context/, never committed),
# served to localhost screens over HTTP (Office M7 reads it; CLAUDE.md Rule 5 — no
# shared folder). Filename allowlist only; nothing else under Context/ exists
# to this API.
CONTEXT_DIR = Path(__file__).resolve().parent.parent / "Context"
CONTEXT_ALLOWLIST = {
    "fourteen_week_plan": "Fourteen_Week_Plan_Seeded_Into_INKY.md",
    "master_context": "Master_Context.md",
    "resume": "Resume_ATS.md",
}


@app.get(cfg.API_PREFIX + "/context/{name}")
def context_doc(name: str):
    filename = CONTEXT_ALLOWLIST.get(name)
    if not filename:
        raise HTTPException(status_code=404, detail="unknown context doc")
    path = CONTEXT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="context doc missing on disk")
    return FileResponse(path, media_type="text/markdown; charset=utf-8")


@app.get("/{full_path:path}")
def static_or_page(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)

    root = cfg.NEXT_DIST
    exact = (root / full_path).resolve()

    if root in exact.parents and exact.is_file():
        return FileResponse(exact)

    candidates = (
        root / (full_path + ".html"),
        root / full_path / "index.html",
        root / "index.html",
    )

    for candidate in candidates:
        if candidate.is_file():
            return FileResponse(candidate, headers=NO_CACHE)

    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
