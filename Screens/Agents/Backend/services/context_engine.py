"""The Context Engine (PLAN item 16 A) - the awareness collector.

WHAT IT DOES
    One run polls four sources and writes one honest snapshot per source
    into the Storage library (D40 convention):
    `library/context_engine/<source>/today/` - so `Time_Analyst_Agent`'s
    evening gap report and every other agent read what is true right now,
    not what was true last run.

        wakatime         what the editor/project says the owner is doing
                         (via the Main Menu's own summary endpoint - item 14;
                         no key wired yet means a `missing` state, not silence)
        google_calendar  today's events (via the Main Menu's calendar endpoint, D23)
        git              commits since local midnight (`git log --since`)
        screens          which screen answers on its port, discovered by
                         looking at each Backend/settings_for_*.py - the same
                         promise the launcher makes, never a hardcoded list

WHY IT LOOKS LIKE THIS
    Rule 8 applies hard here: a source that is unreachable is written as
    unreachable. Nothing is carried over from the last poll, nothing is
    invented. The run itself is triggered by hand or by the owner's
    orchestration - it never runs on a timer inside this process.

SEAMS
    - Main Menu and Storage are reached over HTTP only (Rule 5), never by
      import. Their ports are read from their own settings files, so a port
      stays written in exactly one place (D21.2).
    - Each snapshot is a Storage library write - never a second store.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter

import settings_for_agents as cfg

router = APIRouter()

IST = timezone(timedelta(hours=5, minutes=30))
HTTP_TIMEOUT_S = 4.0
GIT_TIMEOUT_S = 10.0
MAX_COMMIT_LINES = 30

# The sources, in the order the report reads them. Each entry is
# (source name, collector) - the collector returns (state, markdown body).
SOURCE_ORDER = ["wakatime", "google_calendar", "git", "screens"]


# =====================================================================
# SCREEN DISCOVERY - by looking, never by name
# =====================================================================
def _settings_files(roots: list[Path]) -> list[Path]:
    """Every settings_for_*.py under the given roots, at any depth - a
    screen's settings file lives in its own Backend folder, which may sit
    directly under the root (Main_Menu/Backend) or two levels in
    (Screens/<name>/Backend)."""
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        found += sorted(root.glob("settings_for_*.py"))
        found += sorted(root.glob("*/Backend/settings_for_*.py"))
    return found


def discover_screens(roots: list[Path]) -> list[dict]:
    """Every screen's name/host/port, read from its own settings file.

    Same shape as the launcher's discovery: a Backend folder with a
    settings_for_*.py is a screen. A file without a PORT line is reported
    as broken rather than silently skipped.
    """
    found: list[dict] = []
    seen: set[Path] = set()
    for settings_path in _settings_files(roots):
        if settings_path in seen:
            continue
        seen.add(settings_path)
        try:
            text = settings_path.read_text(encoding="utf-8")
        except OSError:
            continue
        name_m = re.search(r'^SCREEN_NAME\s*=\s*"([^"]+)"', text, re.M)
        port_m = re.search(r"^PORT\s*=\s*(\d+)", text, re.M)
        host_m = re.search(r'^HOST\s*=\s*"([^"]+)"', text, re.M)
        if not port_m:
            continue          # a settings file with no PORT is not startable
        found.append({
            "name": name_m.group(1) if name_m else settings_path.stem,
            "host": host_m.group(1) if host_m else "127.0.0.1",
            "port": int(port_m.group(1)),
        })
    return found


def _screen_roots() -> list[Path]:
    return [cfg.PROJECT_ROOT / "Main_Menu" / "Backend",
            cfg.PROJECT_ROOT / "Screens"]


def _settings_dir_for(screen_name: str, roots: list[Path]) -> Path | None:
    """The Backend folder whose settings file declares this SCREEN_NAME."""
    for settings_path in _settings_files(roots):
        try:
            text = settings_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if re.search(rf'^SCREEN_NAME\s*=\s*"{re.escape(screen_name)}"', text, re.M):
            return settings_path.parent
    return None


def _port_of(screen_name: str, roots: list[Path]) -> int | None:
    folder = _settings_dir_for(screen_name, roots)
    if folder is None:
        return None
    text = (next(folder.glob("settings_for_*.py"))).read_text(encoding="utf-8")
    m = re.search(r"^PORT\s*=\s*(\d+)", text, re.M)
    return int(m.group(1)) if m else None


# =====================================================================
# HTTP - stdlib only, one small helper (Rule 5: no shared module)
# =====================================================================
def _get_json(url: str, timeout: float = HTTP_TIMEOUT_S) -> tuple[int, object | None]:
    """(status, parsed json) or (0, None) when the transport itself failed."""
    try:
        req = urllib.request.Request(url, headers={"accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, None
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, None


def _post_json(url: str, payload: dict, timeout: float = HTTP_TIMEOUT_S) -> tuple[int, object | None]:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method="POST",
            headers={"Content-Type": "application/json", "accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, None
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, None


# =====================================================================
# THE FOUR COLLECTORS - each returns (state, markdown_lines)
#   state: ok | partial | not_wired | unreachable | error
# =====================================================================
def collect_wakatime(now: datetime) -> tuple[str, list[str]]:
    port = _port_of("main_menu", _screen_roots())
    if port is None:
        return "error", ["the Main Menu settings file could not be found or read"]
    status, payload = _get_json(f"http://127.0.0.1:{port}/api/main_menu/wakatime/summary")
    if status == 0:
        return "unreachable", [f"Main Menu not answering on :{port} - editor time unknown"]
    if status != 200 or not isinstance(payload, dict):
        return "error", [f"Main Menu returned HTTP {status} for the WakaTime summary"]
    # Main Menu's shape: {"state": "ok"|"not_connected"|"error", "detail",
    #                     "today": "...", "week": [...], "snapshot_days"}
    state = payload.get("state")
    if state == "not_connected":
        return "not_wired", [
            "WakaTime is not wired yet (PLAN item 14): no API key on file.",
            *(f"detail: {payload['detail']}" if payload.get("detail") else []),
            "Logged editor time is UNKNOWN - plan from standing blocks, not from this.",
        ]
    if state == "error":
        return "error", [f"WakaTime errored upstream: {payload.get('detail', '')}"]
    lines = ["```json", json.dumps(payload, indent=2, ensure_ascii=False), "```"]
    return "ok", lines


def collect_google_calendar(now: datetime) -> tuple[str, list[str]]:
    port = _port_of("main_menu", _screen_roots())
    if port is None:
        return "error", ["the Main Menu settings file could not be found or read"]
    day = now.strftime("%Y-%m-%d")
    status, payload = _get_json(
        f"http://127.0.0.1:{port}/api/main_menu/calendar/day?day={day}")
    if status == 0:
        return "unreachable", [f"Main Menu not answering on :{port} - today's calendar unknown"]
    if status != 200:
        return "error", [f"Main Menu returned HTTP {status} for calendar day {day}"]
    lines = [f"day: {day}",
             "```json", json.dumps(payload, indent=2, ensure_ascii=False), "```"]
    text = json.dumps(payload)
    if '"connected": false' in text or '"state": "unconnected"' in text:
        return "not_wired", [
            "Google Calendar is not connected (D23.7) - that is a sentence, not an empty day.",
        ] + lines
    return "ok", lines


def collect_git(now: datetime) -> tuple[str, list[str]]:
    since = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
    try:
        result = subprocess.run(
            ["git", "-C", str(cfg.PROJECT_ROOT), "log",
             f"--since={since}", "--pretty=%h %ad %s",
             "--date=format:%H:%M"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "error", [f"git could not be asked: {exc}"]
    if result.returncode != 0:
        return "error", [f"git failed: {(result.stderr or '').strip()[:300]}"]
    commits = [line for line in result.stdout.splitlines() if line.strip()]
    if not commits:
        return "ok", [f"0 commits since local midnight ({since}) - nothing logged today."]
    lines = [f"{len(commits)} commit(s) since local midnight:", ""]
    lines += [f"- {c}" for c in commits[:MAX_COMMIT_LINES]]
    if len(commits) > MAX_COMMIT_LINES:
        lines.append(f"- ... and {len(commits) - MAX_COMMIT_LINES} more")
    return "ok", lines


def collect_screens(now: datetime) -> tuple[str, list[str]]:
    screens = discover_screens(_screen_roots())
    if not screens:
        return "error", ["no screen settings files found - discovery failed, not a fleet of zero"]
    lines = [f"{len(screens)} screen(s) discovered by walking the settings files:", ""]
    downs = 0
    for s in screens:
        url = f"http://{s['host']}:{s['port']}/"
        status, _ = _get_json(url)
        if status == 0:
            downs += 1
            lines.append(f"- {s['name']} :{s['port']} — DOWN (no answer)")
        elif 200 <= status < 400:
            lines.append(f"- {s['name']} :{s['port']} — up (HTTP {status})")
        else:
            downs += 1
            lines.append(f"- {s['name']} :{s['port']} — HTTP {status}")
    if downs:
        return "partial", lines + ["", f"{downs} screen(s) did not answer."]
    return "ok", lines


COLLECTORS = {
    "wakatime": collect_wakatime,
    "google_calendar": collect_google_calendar,
    "git": collect_git,
    "screens": collect_screens,
}


# =====================================================================
# THE RUN
# =====================================================================
def _storage_port(roots: list[Path]) -> int | None:
    return _port_of("storage", roots)


def run_collection() -> dict:
    """One run: collect every source, write each snapshot to the library.

    Returns a summary with one row per source. A source that cannot be
    collected still gets its honest row - it is never dropped from the
    report just because it had nothing to say (Rule 8).
    """
    now = datetime.now(IST)
    roots = _screen_roots()
    storage_port = _storage_port(roots)
    results: list[dict] = []

    for source in SOURCE_ORDER:
        state, body_lines = COLLECTORS[source](now)
        stamp = now.strftime("%Y-%m-%d %H:%M IST")
        content = (f"# context_engine / {source}\n\n"
                   f"- collected: {stamp}\n"
                   f"- state: {state}\n\n"
                   + "\n".join(body_lines) + "\n")
        row = {"source": source, "state": state, "collected_at": stamp}
        if storage_port is None:
            row["written"] = False
            row["problem"] = "the Storage screen's port could not be discovered"
        else:
            status, payload = _post_json(
                f"http://127.0.0.1:{storage_port}"
                f"/api/storage/library/context_engine/{source}/today",
                {"content": content})
            if status == 200 and isinstance(payload, dict) and payload.get("state") == "ok":
                row["written"] = True
                row["path"] = payload.get("path")
            else:
                row["written"] = False
                row["problem"] = (f"library write returned HTTP {status}"
                                  if status else "Storage not answering")
        results.append(row)

    written = sum(1 for r in results if r.get("written"))
    overall = "ok" if written == len(results) else (
        "partial" if written else "error")
    return {"state": overall, "run_at": now.strftime("%Y-%m-%d %H:%M IST"),
            "written": f"{written}/{len(results)}", "sources": results}


def read_latest() -> dict:
    """The newest snapshot per source - what Time_Analyst_Agent reads.

    A source with no snapshot yet is reported as `no_snapshot`, never
    filled with an older file or a fabricated empty state (Rule 8).
    """
    now = datetime.now(IST)
    roots = _screen_roots()
    storage_port = _storage_port(roots)
    out: list[dict] = []
    for source in SOURCE_ORDER:
        row: dict = {"source": source}
        if storage_port is None:
            row.update({"state": "error",
                        "problem": "the Storage screen's port could not be discovered"})
        else:
            status, payload = _get_json(
                f"http://127.0.0.1:{storage_port}"
                f"/api/storage/library/context_engine/{source}/today/latest")
            if status == 200 and isinstance(payload, dict):
                row.update({"state": "ok", "path": payload.get("path"),
                            "content": payload.get("content")})
            elif status == 404:
                row.update({"state": "no_snapshot",
                            "problem": "the collector has not run for this source yet"})
            else:
                row.update({"state": "unreachable",
                            "problem": f"library read returned HTTP {status or 'no answer'}"})
        out.append(row)
    return {"read_at": now.strftime("%Y-%m-%d %H:%M IST"), "sources": out}


# =====================================================================
# ROUTES
# =====================================================================
@router.post(cfg.API_PREFIX + "/context-engine/run")
def context_engine_run():
    # Sync on purpose: the collectors block on HTTP and git, and FastAPI
    # runs sync handlers in its threadpool - an async handler here would
    # freeze the event loop and the self-probe to :8004 would time out.
    return run_collection()


@router.get(cfg.API_PREFIX + "/context-engine/latest")
def context_engine_latest():
    return read_latest()
