"""One liveness + dependency probe, served as /health by every FastAPI screen.

WHAT THIS IS
    The Phase-1 observability foundation (roadmap W1.3). Each screen
    registers its real data sources once, and GET /health answers:

        {
          "process": "alive",
          "status": "ok" | "degraded",
          "screen": "finance",
          "dependencies": {"saved_records": "ok", ...}
        }

THE ONE HONESTY RULE
    "Alive" never means "healthy". A process that answers while its
    data folder is missing is DEGRADED, and the failing dependency says
    so - down (path gone) or stale (present but older than the age its
    screen declared). A green process light over an empty filing
    cabinet is the exact lie this endpoint exists to refuse.

WHY THESE FIELD NAMES
    Chosen to map 1:1 onto future OpenTelemetry span attributes when
    Phase-2 arrives; no Prometheus/Grafana, no new dependencies - this
    module is stdlib plus FastAPI only.

HOW A SCREEN USES IT (two lines in server_for_<name>.py):

        import health_check                                  # on sys.path
        health_check.register(app, "finance", saved_records=...)

REVERSIBILITY
    Remove the registrations and the module goes inert - nothing else
    imports it, nothing stores anything.
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI


def _state(path, max_age_s: float | None) -> str:
    """ok | down | stale for one dependency path."""
    if callable(path):
        try:
            path = path()
        except Exception:                                 # noqa: BLE001
            return "down"      # a source that cannot even be asked is down
    if path is None:
        return "down"
    if not Path(path).exists():
        return "down"
    if max_age_s is not None:
        try:
            age = time.time() - Path(path).stat().st_mtime
        except OSError:
            return "down"
        if age > max_age_s:
            return "stale"
    return "ok"


def snapshot(screen: str, dependencies: dict) -> dict:
    """The /health body.

    `dependencies` maps name -> path | (path[, max_age_s]) | callable.
    Paths are resolved at REQUEST time - a screen whose settings move
    mid-flight reports where its data lives now, not where it lived
    when the process started.
    """
    states = {}
    for name, spec in dependencies.items():
        if isinstance(spec, tuple):
            path, max_age_s = spec
        else:
            path, max_age_s = spec, None
        states[name] = _state(path, max_age_s)
    return {
        "process": "alive",
        "status": "ok" if all(v == "ok" for v in states.values())
        else "degraded",
        "screen": screen,
        "dependencies": states,
    }


def register(app: FastAPI, screen: str, **dependencies) -> None:
    """Mount GET /health on a screen's app. Two lines per server.

    Each keyword is a dependency name; its value is a filesystem Path,
    a (path, max_age_seconds) tuple, or a zero-argument callable
    returning either - callables resolve at request time so the probe
    always reports where the data lives NOW.
    """
    @app.get("/health")
    def health() -> dict:
        return snapshot(screen, dependencies)
