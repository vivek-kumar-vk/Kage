"""Backend for the Finance screen — a thin mount of the Finance app.

WHAT CHANGED (2026-08-30, cutover)
    The Finance screen used to serve its own Calculations/ +
    hand-written page + Next export. That work was superseded by the
    greenfield app (FastAPI + a Next static export, its own sqlite
    `finance.db`) built at the repo root as `finance-os/`. This file
    stands that app's `create_app()` up on this screen's port (8001),
    so clicking FINANCE in the Main Menu lands on it.

    Moved 2026-09-03: the app now lives under this screen at
    `Backend/app/` + `Page/next_app/`, so Finance is one folder like
    every other screen. The dead Calculations/, Page/ and Setup/ trees
    were deleted; they remain in git history.

HOW ROUTING WORKS
    finance-os's `app_factory.create_app()` already serves, all at `/`:
      /api/finance/*      the routers (overview, investments, debt, ...)
      /finance, /finance/investments, ...   the exported pages
      /_next/*, favicon, fonts              exact static assets
      deep links           <path>.html then index.html fallback
    We add one route: `/` -> the Overview page directly, skipping the
    flaky root `redirect('/finance')` that the static export produces.

HOW TO RUN IT ON ITS OWN
    cd <repo root>
    python Screens\\Finance\\Backend\\server_for_finance.py
    then open http://127.0.0.1:8001
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Screens/Finance/Backend
PROJECT_ROOT = HERE.parents[2]                   # the inky folder
# The app itself. It used to live at the repo root as `finance-os/`;
# it now sits under this screen like every other screen's code, in the
# same Backend/app shape the Anime screen already uses for its server.
APP_DIR = HERE / "app"

sys.path.insert(0, str(HERE))                    # settings_for_finance
sys.path.insert(0, str(APP_DIR))                 # the app package

import settings_for_finance as cfg                                   # noqa: E402

from fastapi import FastAPI                                          # noqa: E402
from fastapi.responses import JSONResponse, RedirectResponse        # noqa: E402

from app_factory import create_app                                   # noqa: E402
from services import db                                              # noqa: E402

_STATIC = APP_DIR / "static"

# The app builds its own DB/schema; make sure it exists before a
# request hits it (the sub-app's startup event does not always fire
# when mounted inside a parent).
db.init_db()

app = FastAPI(title=cfg.SCREEN_LABEL)


@app.get("/")
def landing():
    """Land on the Overview page. A server redirect, not the static
    export's own root `redirect('/finance')` (which exports as an
    __next_error__ page)."""
    if not (_STATIC / "finance.html").is_file():
        return JSONResponse(
            {"status": "the Finance static build is missing",
             "fix": "run  python Screens/Finance/Backend/build.py"},
            status_code=503,
        )
    return RedirectResponse("/finance")


# Everything else — pages, /api/finance/*, /_next/* — is the app's.
app.mount("/", create_app())


if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
