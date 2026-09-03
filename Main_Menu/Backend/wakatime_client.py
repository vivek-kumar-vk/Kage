"""WakaTime for the Calendar card's second mode (D23).

Auth is the plain API key over HTTP Basic - the key, base64-encoded, in
an Authorization header. That is WakaTime's own documented scheme and it
is the right one here: one local user reading his own stats. OAuth buys
nothing when there is no third party to consent, and its app secret is
one more thing to leak.

The key is read from Calendar_Data/wakatime.json (gitignored):

    {"api_key": "waka_..."}

or from the WAKATIME_API_KEY environment variable. Neither present means
the card says "not connected" - it never shows a zero as if it were a
real total (Rule 8).

The free plan only exposes 7 days of history. That is why every read of
the last week is also written into the local store: history accumulates
from the day this is switched on, regardless of plan.
"""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

import settings_for_main_menu as cfg


class WakaTimeError(RuntimeError):
    """A failure said in one sentence the card can print."""


def api_key() -> str:
    """Env first (a hosted box sets it), then the gitignored file."""
    if cfg.WAKATIME_API_KEY_ENV:
        return cfg.WAKATIME_API_KEY_ENV.strip()
    path = cfg.WAKATIME_KEY_FILE
    if not path.exists():
        return ""
    try:
        return str(json.loads(path.read_text(encoding="utf-8"))
                   .get("api_key", "")).strip()
    except (ValueError, OSError):
        return ""


def key_state():
    if api_key():
        return {"state": "ok", "detail": ""}
    return {"state": "missing",
            "detail": f"no API key - write one into {cfg.WAKATIME_KEY_FILE.name} "
                      f"or set WAKATIME_API_KEY"}


def _get(path, params=None):
    key = api_key()
    if not key:
        raise WakaTimeError(key_state()["detail"])
    url = f"{cfg.WAKATIME_API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    encoded = base64.b64encode(key.encode("utf-8")).decode("ascii")
    request = urllib.request.Request(url, headers={
        "Authorization": f"Basic {encoded}",
        "Accept": "application/json",
        "User-Agent": "Kage/1.0 (+local)",
    })
    try:
        with urllib.request.urlopen(request, timeout=cfg.WAKATIME_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise WakaTimeError("WakaTime rejected the API key (401)")
        if exc.code == 402:
            raise WakaTimeError("this range needs a paid WakaTime plan (402)")
        if exc.code == 429:
            raise WakaTimeError("WakaTime rate-limited this request (429)")
        raise WakaTimeError(f"WakaTime returned HTTP {exc.code}")
    except urllib.error.URLError as exc:
        raise WakaTimeError(f"cannot reach WakaTime ({exc.reason})")
    except ValueError:
        raise WakaTimeError("WakaTime returned something that was not JSON")


# ---------------------------------------------------------------------
# READS
# ---------------------------------------------------------------------
def statusbar_today():
    """Today's running total - the cheapest live figure WakaTime has."""
    return _get("/users/current/statusbar/today").get("data", {})


def summaries(start_day, end_day):
    """One object per day: grand_total plus the project / language /
    editor breakdowns. This is the endpoint the day cells come from."""
    return _get("/users/current/summaries",
                {"start": start_day, "end": end_day}).get("data", [])


def stats(range_key="last_7_days"):
    """Aggregate for a range: languages, editors, projects, best_day,
    daily_average. Ranges past 7 days need a paid plan; a 402 comes back
    as a plain sentence rather than an empty chart."""
    return _get(f"/users/current/stats/{range_key}").get("data", {})


def all_time():
    return _get("/users/current/all_time_since_today").get("data", {})


# ---------------------------------------------------------------------
# THE SNAPSHOT - the one thing that must not wait for a paid plan
# ---------------------------------------------------------------------
def _top(entries):
    if not entries:
        return None
    best = max(entries, key=lambda e: e.get("total_seconds") or 0)
    return best.get("name")


def snapshot_recent(store, days=7):
    """Pull the last `days` of summaries and write each into the local
    store. Called on the sync loop, so the 7-day free window is captured
    before it rolls off. Returns how many days were written."""
    end = date.today()
    start = end - timedelta(days=max(days - 1, 0))
    rows = summaries(start.isoformat(), end.isoformat())
    written = 0
    for row in rows:
        day = (row.get("range") or {}).get("date")
        if not day:
            continue
        total = (row.get("grand_total") or {}).get("total_seconds")
        store.save_waka_day(
            day,
            int(total) if total is not None else None,
            _top(row.get("projects")),
            _top(row.get("languages")),
            {"projects": row.get("projects", [])[:5],
             "languages": row.get("languages", [])[:5],
             "editors": row.get("editors", [])[:5]},
        )
        written += 1
    return written
