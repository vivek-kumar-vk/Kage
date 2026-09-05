"""The one place OFFICE reaches the Learning screen. HTTP only (Rule 5).

Learning owns the ground truth for resume-defensibility (D17.5). This
fetches it; resume_readiness.py mirrors the result into office.db with a
fetched_at and an honest state string.
"""

from __future__ import annotations

import httpx

import settings_for_office as cfg

# state strings the readiness tab renders verbatim
OK = "ok"
UNREACHABLE = "learning screen unreachable"
ENDPOINT_MISSING = "endpoint missing"
BAD_RESPONSE = "learning returned an unusable response"


def fetch_skills() -> tuple[str, list[dict]]:
    """(state, skills). skills only meaningful when state == OK.

    Never raises - a down Learning screen is a first-class state here,
    not an error (Rule 8)."""
    url = cfg.LEARNING_URL.rstrip("/") + "/api/learning/skills"
    try:
        resp = httpx.get(url, timeout=cfg.LEARNING_TIMEOUT_S)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
        return UNREACHABLE, []
    except httpx.HTTPError:
        return UNREACHABLE, []

    if resp.status_code == 404:
        return ENDPOINT_MISSING, []
    if resp.status_code >= 500:
        return UNREACHABLE, []
    if resp.status_code != 200:
        return BAD_RESPONSE, []

    try:
        data = resp.json()
        skills = data["skills"]
        assert isinstance(skills, list)
    except (ValueError, KeyError, AssertionError):
        return BAD_RESPONSE, []

    return OK, skills
