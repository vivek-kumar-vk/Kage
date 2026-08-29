"""Backend for the Finance screen — a thin mount of the finance-os app.

WHAT CHANGED (2026-08-30, cutover)
    The Finance screen used to serve `Screens/Finance/` (its own
    Calculations/ + hand-written page + Next export). That work is
    superseded by the greenfield `finance-os/` app (FastAPI + a Next
    static export, its own sqlite `finance.db`). This file now just
    stands `finance-os/backend`'s `create_app()` up on this screen's
    port (8001), so clicking FINANCE in the Main Menu lands on it.

    The old `Screens/Finance/{Calculations,Page,Reference_Data,
    Saved_Records,Setup}` stay on disk, unused, in git history.

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
FOS_BACKEND = PROJECT_ROOT / "finance-os" / "backend"

sys.path.insert(0, str(HERE))                    # settings_for_finance
sys.path.insert(0, str(FOS_BACKEND))            # finance-os app package

import settings_for_finance as cfg                                   # noqa: E402

from fastapi import FastAPI                                          # noqa: E402
from fastapi.responses import JSONResponse, RedirectResponse        # noqa: E402

from app_factory import create_app                                   # noqa: E402
from services import db                                              # noqa: E402

_STATIC = FOS_BACKEND / "static"

# finance-os builds its own DB/schema; make sure it exists before a
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
            {"status": "finance-os static build missing",
             "fix": "run  python finance-os/build.py"},
            status_code=503,
        )
    return RedirectResponse("/finance")


# Everything else — pages, /api/finance/*, /_next/* — is finance-os's.
app.mount("/", create_app())


if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)
