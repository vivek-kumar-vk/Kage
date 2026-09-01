import logging
import os
import pathlib
import subprocess

from starlette.middleware.base import BaseHTTPMiddleware


class PassthroughAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await call_next(request)


def check_encrypted_volume(db_dir) -> None:
    try:
        db_dir = pathlib.Path(db_dir)
        if os.name == "nt":
            anchor = db_dir.anchor or "C:\\"
            res = subprocess.run(["manage-bde", "-status", anchor],
                                 capture_output=True, text=True, timeout=10)
            if "Percentage Encrypted: 100" not in (res.stdout or ""):
                logging.warning("DB dir %s may not be on an encrypted volume", db_dir)
        else:
            res = subprocess.run(["cryptsetup", "status", str(db_dir)],
                                 capture_output=True, text=True, timeout=10)
            if "is active" not in (res.stdout or ""):
                logging.warning("DB dir %s may not be on an encrypted volume", db_dir)
    except Exception:
        logging.warning("encrypted-volume check skipped (non-fatal)")
