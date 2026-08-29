import importlib
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import startup
from services import db

ROUTERS = ["overview", "investments", "debt", "tracker", "learning", "health",
           "accounts", "goals", "insurance", "salary", "imports", "entities", "settings"]


def create_app() -> FastAPI:
    app = FastAPI(title="Finance OS")
    app.add_middleware(startup.PassthroughAuth)

    @app.on_event("startup")
    def _boot():
        db.init_db()
        startup.check_encrypted_volume(db.DB_PATH.parent)

    for name in ROUTERS:
        try:
            mod = importlib.import_module(f"routers.{name}")
        except ImportError:
            continue
        app.include_router(mod.router, prefix="/api/finance")

    @app.get("/api/finance/health")
    def _health():
        return {"status": "ok"}

    here = pathlib.Path(__file__).parent
    static = here / "static"
    if static.is_dir():
        app.mount("/assets", StaticFiles(directory=static), name="assets")

    @app.get("/{full_path:path}")
    def _spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        # 1) an exact static asset (_next/*, fonts, favicon, *.txt, ...)
        exact = (static / full_path).resolve()
        if static in exact.parents and exact.is_file():
            return FileResponse(exact)
        # 2) a route -> its exported .html, then index.html (SPA deep-link fallback)
        for cand in (static / f"{full_path}.html", static / full_path / "index.html",
                     static / "index.html"):
            if cand.is_file():
                return FileResponse(cand)
        raise HTTPException(status_code=404)

    return app
