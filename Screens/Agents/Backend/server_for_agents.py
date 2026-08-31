import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

import settings_for_agents as cfg
from db import init_db
import seed
from services import agents, board, events


@asynccontextmanager
async def lifespan(_app):
    events.start_demo()
    yield
    events.stop_demo()


app = FastAPI(title=cfg.SCREEN_LABEL, lifespan=lifespan)

init_db()
seed.run()

app.include_router(board.router)
app.include_router(agents.router)
app.include_router(events.router)


@app.get("/")
async def root():
    if cfg.USE_NEXT_UI and (cfg.NEXT_DIST / "index.html").exists():
        return FileResponse(cfg.NEXT_DIST / "index.html")
    elif cfg.PAGE.exists():
        return FileResponse(cfg.PAGE)
    else:
        return JSONResponse({
            "status": "not built yet",
            "api_routes": [
                "/api/agents/workspace",
                "/api/agents/agents",
                "/api/agents/rooms",
                "/api/agents/ideas",
            ]
        })


@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")

    exact = (cfg.NEXT_DIST / full_path).resolve()
    try:
        if cfg.NEXT_DIST in exact.parents and exact.is_file():
            return FileResponse(exact)
    except (OSError, RuntimeError):
        pass

    html_path = cfg.NEXT_DIST / (full_path + ".html")
    if html_path.is_file():
        return FileResponse(html_path)

    index_path = cfg.NEXT_DIST / full_path / "index.html"
    if index_path.is_file():
        return FileResponse(index_path)

    fallback = cfg.NEXT_DIST / "index.html"
    if fallback.exists():
        return FileResponse(fallback)

    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
