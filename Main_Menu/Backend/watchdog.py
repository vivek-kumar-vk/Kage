"""Watchdog on the Main Menu tick (K-19): verdicts only, never fixes.

Runs at most once per 30 minutes (a marker file in the spine dir, so the
budget survives restarts), writes one watchdog_verdict per check to the
spine, and rewrites kage-data/watchdog_audit.md as derived output. A check
whose data source did not answer is cannot_tell — never up (Rule 22).
"""

import json
import random
import re
import shutil
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Shared_By_All_Screens import read_screen_settings  # noqa: E402
from Shared_By_All_Screens import spine  # noqa: E402

import trace_every_action  # noqa: E402
from find_every_screen import discover  # noqa: E402

INTERVAL_MINUTES = 30
STORAGE_TIMEOUT_S = 4.0
CHECKS = ("source:*", "screen:*", "llm_spend", "projector_lag", "backup",
          "disk", "complexity", "spine_writable")
_IST = timezone(timedelta(hours=5, minutes=30))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _storage_port() -> int | None:
    path = _repo_root() / "Screens" / "Storage" / "Backend" / "settings_for_storage.py"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^PORT\s*=\s*(\d+)", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _get_json(url: str, timeout: float) -> tuple[int, object | None]:
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
        try:
            return status, json.loads(body)
        except ValueError:
            return status, None
    except Exception:
        return 0, None


def _marker_path() -> Path:
    return spine.spine_dir() / "_watchdog_last_run"


def run_if_due(now: datetime) -> list[dict] | None:
    """Run at most once per 30 minutes across restarts; never raises."""
    try:
        last = _marker_path().read_text(encoding="utf-8").strip()
        last_dt = datetime.fromisoformat(last)
        if (now - last_dt).total_seconds() < INTERVAL_MINUTES * 60:
            return None
    except (OSError, ValueError):
        pass
    try:
        results = run(now)
        _marker_path().write_text(now.isoformat(timespec="seconds"),
                                  encoding="utf-8")
        write_audit_md(results, now)
        return results
    except Exception as problem:  # noqa: BLE001 - the tick must survive
        try:
            trace_every_action.trace(
                "main_menu", "error", "watchdog_run_failed", outcome="fail",
                detail={"problem": str(problem)})
        except Exception:  # noqa: BLE001
            pass
        return None


def run(now: datetime) -> list[dict]:
    results: list[dict] = []
    results.extend(_check_sources())
    results.extend(_check_screens())
    results.append(_check_llm_spend())
    results.append(_check_projector_lag())
    results.append(_check_backup(now))
    results.append(_check_disk())
    results.append(_check_complexity())
    results.append(_check_spine_writable())
    results.extend(_check_random_tab(now))

    for verdict in results:
        check = verdict["check"]
        if check == "spine_writable":
            if verdict["verdict"] == "down":
                # the spine cannot record its own failure
                try:
                    trace_every_action.trace(
                        "main_menu", "error", "spine_write_failed",
                        outcome="fail", detail={"problem": verdict["detail"]})
                except Exception:  # noqa: BLE001
                    pass
            continue
        try:
            spine.emit("main_menu", "watchdog_verdict", check,
                       {"verdict": verdict["verdict"], "detail": verdict["detail"],
                        "value": verdict.get("value")})
        except spine.SpineWriteError as exc:
            try:
                trace_every_action.trace(
                    "main_menu", "error", "spine_write_failed", outcome="fail",
                    detail={"problem": str(exc)})
            except Exception:  # noqa: BLE001
                pass
    return results


def _storage_url(path: str) -> tuple[int, object | None]:
    port = _storage_port()
    if not port:
        return 0, None
    return _get_json(f"http://127.0.0.1:{port}{path}", STORAGE_TIMEOUT_S)


def _check_sources() -> list[dict]:
    status, body = _storage_url("/api/storage/spine/freshness")
    rows = body.get("sources") if isinstance(body, dict) else None
    if status == 0 or not isinstance(body, dict) or body.get("state") != "ok" \
            or rows is None:
        return [{"check": "source:*", "verdict": "cannot_tell",
                 "detail": "unreachable: storage freshness endpoint did not answer",
                 "value": None}]
    out: list[dict] = []
    for row in sorted(rows, key=lambda r: r.get("source") or ""):
        name = row.get("source") or "unknown"
        stale = row.get("stale")
        if stale is None:
            out.append({"check": f"source:{name}", "verdict": "cannot_tell",
                        "detail": "unreachable: freshness row carries no stale flag",
                        "value": None})
        elif stale == 1 or stale is True:
            out.append({"check": f"source:{name}", "verdict": "stale",
                        "detail": f"stale_source: {name} last ok at {row.get('last_ok_at')}",
                        "value": row.get("age_hours")})
        else:
            out.append({"check": f"source:{name}", "verdict": "up",
                        "detail": "ok", "value": row.get("age_hours")})
    return out


def _check_screens() -> list[dict]:
    try:
        built, _not_built = discover()
    except Exception as exc:  # noqa: BLE001
        return [{"check": "screen:*", "verdict": "cannot_tell",
                 "detail": f"unreachable: screen discovery failed: {exc}",
                 "value": None}]
    out: list[dict] = []
    for module in built:
        folder = getattr(module, "SCREEN_FOLDER", None)
        if not folder:
            continue
        settings_file = read_screen_settings.settings_file(Path(folder))
        settings = (read_screen_settings.read_settings(settings_file)
                    if settings_file else {})
        port = settings.get("port")
        name = Path(folder).name
        if port is None:
            out.append({"check": f"screen:{name}", "verdict": "cannot_tell",
                        "detail": "unreachable: settings name no port", "value": None})
            continue
        status, _ = _get_json(f"http://127.0.0.1:{port}/", STORAGE_TIMEOUT_S)
        if 200 <= status < 400:
            out.append({"check": f"screen:{name}", "verdict": "up",
                        "detail": "ok", "value": port})
        elif status == 0:
            out.append({"check": f"screen:{name}", "verdict": "down",
                        "detail": "screen_down: connection refused", "value": port})
        else:
            out.append({"check": f"screen:{name}", "verdict": "down",
                        "detail": f"screen_down: HTTP {status}", "value": port})
    return out


def _check_llm_spend() -> dict:
    status, body = _storage_url("/api/storage/spine/spend")
    spend = body.get("cost_usd") if isinstance(body, dict) else None
    if status == 0 or not isinstance(body, dict) or body.get("state") != "ok" \
            or spend is None:
        return {"check": "llm_spend", "verdict": "cannot_tell",
                "detail": "unreachable: spend endpoint did not answer", "value": None}
    if spend >= 0.30:
        return {"check": "llm_spend", "verdict": "down",
                "detail": f"spend_over_cap: ${spend:.2f} today (cap $0.30)",
                "value": spend}
    return {"check": "llm_spend", "verdict": "up", "detail": "ok", "value": spend}


def _check_projector_lag() -> dict:
    status, body = _storage_url("/api/storage/spine/events?limit=1")
    lag = body.get("projector_lag_bytes") if isinstance(body, dict) else None
    if status == 0 or not isinstance(body, dict) or lag is None:
        return {"check": "projector_lag", "verdict": "cannot_tell",
                "detail": "unreachable: events endpoint did not answer", "value": None}
    if lag >= 1_048_576:
        return {"check": "projector_lag", "verdict": "stale",
                "detail": f"projector_lag: {lag} bytes unprojected (threshold 1048576)",
                "value": lag}
    return {"check": "projector_lag", "verdict": "up", "detail": "ok", "value": lag}


def _check_backup(now: datetime) -> dict:
    status, body = _storage_url(
        "/api/storage/spine/events?type=backup_completed&limit=1")
    events = body.get("events") if isinstance(body, dict) else None
    if status == 0 or not isinstance(body, dict) or events is None:
        return {"check": "backup", "verdict": "cannot_tell",
                "detail": "unreachable: events endpoint did not answer", "value": None}
    if not events:
        return {"check": "backup", "verdict": "stale",
                "detail": "backup_overdue: no backup_completed event on record",
                "value": None}
    event = events[0]
    if (event.get("payload") or {}).get("verified") is not True:
        return {"check": "backup", "verdict": "stale",
                "detail": "backup_overdue: last backup not verified", "value": None}
    try:
        ts = datetime.fromisoformat(event["ts"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_IST)
        age_days = (now - ts).days
    except (ValueError, KeyError, TypeError):
        return {"check": "backup", "verdict": "stale",
                "detail": "backup_overdue: unparsable backup timestamp", "value": None}
    if age_days > 7:
        return {"check": "backup", "verdict": "stale",
                "detail": f"backup_overdue: last verified backup {age_days} days ago "
                          f"(threshold 7)", "value": age_days}
    return {"check": "backup", "verdict": "up", "detail": "ok", "value": age_days}


def _check_disk() -> dict:
    try:
        free = shutil.disk_usage(_repo_root() / "kage-data").free
    except Exception as exc:  # noqa: BLE001
        return {"check": "disk", "verdict": "cannot_tell",
                "detail": f"unreachable: {exc}", "value": None}
    gib = free / (1024 ** 3)
    if free < 2 * 1024 ** 3:
        return {"check": "disk", "verdict": "down",
                "detail": f"disk_low: {gib:.1f} GiB free (threshold 2 GiB)",
                "value": round(gib, 2)}
    return {"check": "disk", "verdict": "up", "detail": "ok", "value": round(gib, 2)}


def _check_complexity() -> dict:
    status, body = _storage_url("/api/storage/spine/unfinished")
    count = body.get("count") if isinstance(body, dict) else None
    if status == 0 or not isinstance(body, dict) or body.get("state") != "ok" \
            or count is None:
        return {"check": "complexity", "verdict": "cannot_tell",
                "detail": "unreachable: unfinished endpoint did not answer",
                "value": None}
    if count > 12:
        return {"check": "complexity", "verdict": "stale",
                "detail": f"complexity_over_budget: {count} open ideas (budget 12)",
                "value": count}
    return {"check": "complexity", "verdict": "up", "detail": "ok", "value": count}


def _check_spine_writable() -> dict:
    """The check's own emit IS the probe: written means up."""
    try:
        spine.emit("main_menu", "watchdog_verdict", "spine_writable",
                   {"verdict": "up", "detail": "ok", "value": None})
    except spine.SpineWriteError as exc:
        return {"check": "spine_writable", "verdict": "down",
                "detail": f"spine_unwritable: {exc}", "value": None}
    return {"check": "spine_writable", "verdict": "up", "detail": "ok", "value": None}


def _check_random_tab(now: datetime) -> list[dict]:
    """One built screen's first tab endpoint, re-chosen per calendar day."""
    try:
        built, _not_built = discover()
        candidates = [m for m in built if getattr(m, "TABS", None)]
        if not candidates:
            return []
        module = random.Random(now.date().isoformat()).choice(candidates)
        folder = Path(getattr(module, "SCREEN_FOLDER"))
        endpoint = getattr(module, "TABS")[0]["endpoint"]
        settings_file = read_screen_settings.settings_file(folder)
        settings = (read_screen_settings.read_settings(settings_file)
                    if settings_file else {})
        port = settings.get("port")
        if port is None:
            return [{"check": f"screen:{folder.name}:tab", "verdict": "cannot_tell",
                     "detail": "unreachable: settings name no port", "value": None}]
        status, _ = _get_json(f"http://127.0.0.1:{port}{endpoint}", STORAGE_TIMEOUT_S)
        if 200 <= status < 400:
            return [{"check": f"screen:{folder.name}:tab", "verdict": "up",
                     "detail": "ok", "value": port}]
        return [{"check": f"screen:{folder.name}:tab", "verdict": "down",
                 "detail": f"screen_down: {endpoint} answered "
                           f"HTTP {status or 'nothing'}", "value": port}]
    except Exception as exc:  # noqa: BLE001
        return [{"check": "screen:*:tab", "verdict": "cannot_tell",
                 "detail": f"unreachable: {exc}", "value": None}]


def write_audit_md(results: list[dict], now: datetime) -> Path:
    """Rewrite the whole audit file; derived output, never read back."""
    path = _repo_root() / "kage-data" / "watchdog_audit.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    by_check = {r["check"]: r for r in results}
    order: list[str] = []
    for group in CHECKS:
        if group == "source:*":
            order.extend(sorted(k for k in by_check if k.startswith("source:")))
        elif group == "screen:*":
            order.extend(sorted(
                k for k in by_check
                if k.startswith("screen:") and not k.endswith(":tab")))
        elif group in by_check:
            order.append(group)
    order.extend(sorted(
        k for k in by_check
        if k.startswith("screen:") and k.endswith(":tab")))
    lines = [f"# watchdog {now.isoformat(timespec='seconds')}"]
    for check in order:
        result = by_check[check]
        lines.append(f"- {check}: {result['verdict']} — {result['detail']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
