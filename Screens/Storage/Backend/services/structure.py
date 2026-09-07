"""Structure documents (B-03): serve the three generated JSON files.

The files under kage-data/structure/ are built by
Start_Inky/generate_structure_docs.py from code and databases, never by
hand (STORAGE_TAB_SPEC.md section 1). This router only reads them and, on
POST, re-runs the generator as a subprocess of that same script. A missing
file is an honest "never" state, not an empty document.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import settings_for_storage as cfg  # noqa: E402

router = APIRouter()

_REPO_ROOT = Path(__file__).resolve().parents[4]
_GENERATOR = _REPO_ROOT / "Start_Inky" / "generate_structure_docs.py"
_STRUCTURE_DIR = cfg.KAGE_DATA_DIR / "structure"

_DOCS = {"code": "code_structure", "agents": "agent_tree", "data": "data_schema"}


def _read(name: str):
    path = _STRUCTURE_DIR / f"{name}.json"
    if not path.exists():
        return JSONResponse(
            status_code=200,
            content={"state": "never", "problem": "not generated yet"},
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"state": "error", "problem": f"structure read failed: {exc}"},
        )


@router.get(cfg.API_PREFIX + "/structure/code")
def code():
    return _read(_DOCS["code"])


@router.get(cfg.API_PREFIX + "/structure/agents")
def agents():
    return _read(_DOCS["agents"])


@router.get(cfg.API_PREFIX + "/structure/data")
def data():
    return _read(_DOCS["data"])


@router.post(cfg.API_PREFIX + "/structure/regenerate")
def regenerate():
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(_GENERATOR),
             "--repo-root", str(_REPO_ROOT),
             "--out-dir", str(_STRUCTURE_DIR)],
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return JSONResponse(
            status_code=503,
            content={"state": "error", "problem": "generator exceeded 30s"},
        )
    seconds = round(time.time() - started, 2)
    if proc.returncode != 0:
        problem = (proc.stderr or proc.stdout or "generator failed").strip()[:300]
        return JSONResponse(
            status_code=503,
            content={"state": "error", "problem": problem},
        )
    doc = _read(_DOCS["code"])
    generated_at = doc.get("generated_at") if isinstance(doc, dict) else None
    return {"state": "ok", "generated_at": generated_at, "seconds": seconds}
