"""The one place Learning reaches the OFFICE screen. HTTP only (Rule 5).

Interview-day preemption (D38): Today asks Office whether an interview is
scheduled for today so it can surface the prep pack and step the study
plan back. Office being down is a first-class state, never a guessed
"no interview" (Rule 8 / Rule 22).

Stdlib urllib on purpose — one localhost GET does not earn a new
dependency on the Learning screen.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import settings_for_learning as cfg
from services.common import today_str

OK = "ok"
OFFLINE = "office offline"
BAD = "office returned an unusable response"


def fetch_interviews_today() -> tuple[str, list[dict]]:
    """(state, interviews). The list is meaningful only when state == OK.

    Filters Office's interview list to today's still-`pending` rows and
    keeps just the fields Today renders."""
    url = cfg.OFFICE_URL.rstrip("/") + "/api/office/interviews"
    try:
        with urllib.request.urlopen(url, timeout=cfg.OFFICE_TIMEOUT_S) as resp:
            if getattr(resp, "status", 200) != 200:
                return BAD, []
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError):
        return OFFLINE, []
    except ValueError:
        return BAD, []

    rows = data.get("interviews") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return BAD, []

    today = today_str()
    out = []
    for r in rows:
        if r.get("outcome") != "pending":
            continue
        if (r.get("scheduled_at") or "")[:10] != today:
            continue
        out.append({
            "company": r.get("company"),
            "role": r.get("role"),
            "round": r.get("round"),
            "scheduled_at": r.get("scheduled_at"),
            "mode": r.get("mode"),
            "prep_pack": r.get("prep_pack") or "",
        })
    out.sort(key=lambda x: x["scheduled_at"] or "")
    return OK, out
