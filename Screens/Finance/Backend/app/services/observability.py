"""Request/error observability for this screen only (PLAN item 7).

An in-memory ring buffer of the last N requests this process handled — no
new storage, no shared module (Rule 5). Restarting the backend clears it;
that is honest, not a bug: this is a live window, not a history.
"""

import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware

WINDOW = 200
_requests: deque = deque(maxlen=WINDOW)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            _requests.append(
                {
                    "path": request.url.path,
                    "status": 500,
                    "duration_ms": round((time.monotonic() - started) * 1000),
                }
            )
            raise
        _requests.append(
            {
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
        return response


def summary() -> dict:
    rows = list(_requests)
    errors = [r for r in rows if r["status"] >= 500]
    durations = [r["duration_ms"] for r in rows]
    return {
        "state": "ok",
        "window": len(rows),
        "errors": len(errors),
        "error_rate_pct": round((len(errors) / len(rows)) * 100, 1) if rows else None,
        "avg_duration_ms": round(sum(durations) / len(durations)) if durations else None,
    }
