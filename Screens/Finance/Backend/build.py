"""Build the static frontend and stage it for FastAPI to serve.

  python Screens/Finance/Backend/build.py

Runs `next build` (which, with `output: 'export'`, emits
`Screens/Finance/Page/next_app/out/`), then mirrors that to
`Screens/Finance/Backend/app/static/`, which is what the server actually
serves. Exits non-zero on any failure.
Replaces the prose "copy the export" step.  [O]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# This file sits at  Screens/Finance/Backend/build.py
BACKEND = Path(__file__).resolve().parent
SCREEN = BACKEND.parent
FRONTEND = SCREEN / "Page" / "next_app"
OUT = FRONTEND / "out"
STATIC = BACKEND / "app" / "static"

_IS_WIN = sys.platform == "win32"


def _run(cmd: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(cmd)}  (cwd={cwd})", flush=True)
    # npm / npx are .cmd shims on Windows -> shell=True so they resolve on PATH
    r = subprocess.run(cmd, cwd=str(cwd), shell=_IS_WIN)
    if r.returncode != 0:
        sys.exit(f"command failed ({r.returncode}): {' '.join(cmd)}")


def main() -> int:
    if not FRONTEND.is_dir():
        sys.exit(f"no frontend dir at {FRONTEND}")

    # prefer a local next binary; fall back to npx
    next_bin = FRONTEND / "node_modules" / ".bin" / ("next.cmd" if _IS_WIN else "next")
    if next_bin.exists():
        _run([str(next_bin), "build"], cwd=FRONTEND)
    else:
        _run(["npx", "--yes", "next", "build"], cwd=FRONTEND)

    if not OUT.is_dir():
        sys.exit(f"next build did not produce {OUT} (is output:'export' set in next.config.js?)")

    if STATIC.exists():
        shutil.rmtree(STATIC)
    shutil.copytree(OUT, STATIC)
    index = STATIC / "index.html"
    if not index.is_file():
        sys.exit(f"expected {index} after copy")
    print(f"staged {sum(1 for _ in STATIC.rglob('*'))} files -> {STATIC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
