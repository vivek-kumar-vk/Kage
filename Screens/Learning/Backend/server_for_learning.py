from pathlib import Path
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings_for_learning as cfg
from db import init_db
import seed
from services import today, plan, recall, ask

app = FastAPI(title=cfg.SCREEN_LABEL)

init_db()
seed.run()

app.include_router(today.router)
app.include_router(plan.router)
app.include_router(recall.router)
app.include_router(ask.router)


@app.get("/")
def root():
    if cfg.USE_NEXT_UI:
        index_path = cfg.NEXT_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

    return JSONResponse(
        {
            "status": "not built yet",
            "api_routes": [
                cfg.API_PREFIX + "/today",
                cfg.API_PREFIX + "/plan",
                cfg.API_PREFIX + "/topics",
                cfg.API_PREFIX + "/sessions",
                cfg.API_PREFIX + "/recall",
                cfg.API_PREFIX + "/reviews/{id}/grade",
                cfg.API_PREFIX + "/ask",
            ],
        }
    )


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
            return FileResponse(candidate)

    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
