"""The Calendar card's pipeline (D23): Google Calendar -> local SQLite ->
the card, plus the WakaTime half of the same card's switch.

Every endpoint in server_for_main_menu.py answers from the local store.
Nothing in here blocks a page load on a network call, and nothing in here
invents a value: when Google is not connected the month comes back with
`state` saying exactly that, and the card draws the honest message rather
than an empty grid pretending to be an empty month (Rule 8).

The one write path to the outside world - approving a proposal, which
creates a real event and rings a real phone - is deliberately narrow: it
takes one proposal id, it refuses anything not `pending`, and it records
the Google event id so the write can be undone.
"""

import json
import threading
from datetime import date, datetime, timedelta, timezone

import calendar_agent
import calendar_google as google
import calendar_store as store
import settings_for_main_menu as cfg
import trace_every_action
import wakatime_client as waka

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Shared_By_All_Screens import spine  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))


def _emit(kind, subject, **payload):
    """One spine event for a fetch. A failed spine write is traced and
    dropped, never raised: the sync continues and the source shows stale
    (Rule 22's consequence), which is the honest state."""
    try:
        spine.emit("main_menu", kind, subject, payload)
    except spine.SpineWriteError as exc:
        trace_every_action.trace("main_menu", "error", "spine_write_failed",
                                 target=subject, outcome="fail",
                                 detail={"problem": str(exc)})

_sync_lock = threading.Lock()
_syncing = False
# True only while a consent tab is open and Google has not called back yet.
# The card polls faster in this state so it flips the moment consent lands.
_connecting = False

MONTH_LABELS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def is_syncing():
    return _syncing


def start_once():
    global _syncing
    _syncing = True


# ---------------------------------------------------------------------
# CONNECTION STATE - one place that decides what the card is allowed
# to claim
# ---------------------------------------------------------------------
def connection_state():
    missing = google.libs_missing()
    if missing:
        return "libs_missing", missing
    if not google.has_credentials_file():
        return "needs_credentials", (
            f"no OAuth client at {google.credentials_file().name} "
            f"- see CALENDAR_SETUP.md")
    if not google.has_token():
        return "not_connected", "Google Calendar has not been authorised yet"
    return "ok", ""


def connect_start():
    """Open the one-time consent tab. Answers immediately; the browser
    tab finishes on its own and writes the token."""
    state, detail = connection_state()
    if state == "ok":
        return {"state": "already_connected"}
    if state in ("libs_missing", "needs_credentials"):
        return {"state": state, "detail": detail}
    global _connecting
    _connecting = True
    threading.Thread(target=_consent_worker, daemon=True).start()
    return {"state": "consent_started",
            "detail": f"a Google tab is opening on port {cfg.CALENDAR_OAUTH_PORT}"}


def _consent_worker():
    """Blocks until Google calls back, so it only ever runs in a thread.
    Either way `_connecting` is cleared, so a card that says "connecting"
    is always telling the truth about a flow that is really still open."""
    global _connecting
    try:
        google.run_consent()
        sync_cycle()
    except Exception as problem:  # noqa: BLE001 - recorded, not raised into a thread
        store.set_meta("last_error", f"consent: {problem}")
    finally:
        _connecting = False


def is_connecting():
    return _connecting


# ---------------------------------------------------------------------
# SYNC - Google events + the WakaTime snapshot
# ---------------------------------------------------------------------
def _day_of(event: dict) -> tuple[str | None, str | None, bool]:
    """day = IST date of the start instant; start_iso re-serialised +05:30."""
    start = event.get("start") or {}
    if "date" in start:
        return start["date"], None, True
    stamp = start.get("dateTime")
    if not stamp:
        return None, None, False
    try:
        instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None, None, False
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=IST)
    local = instant.astimezone(IST)
    return local.date().isoformat(), local.isoformat(), False


def _window(today: date) -> tuple[str, str]:
    """(start, end) UTC instants covering [today - DAYS_BACK, today + DAYS_AHEAD]
    as IST calendar days, so Google's window matches the wall calendar here."""
    first = today - timedelta(days=cfg.CALENDAR_DAYS_BACK)
    last = today + timedelta(days=cfg.CALENDAR_DAYS_AHEAD)
    start_utc = datetime(first.year, first.month, first.day, tzinfo=IST).astimezone(timezone.utc)
    end_utc = datetime(last.year, last.month, last.day, 23, 59, 59, tzinfo=IST).astimezone(timezone.utc)
    return start_utc.isoformat(), end_utc.isoformat()


def _calendar_freshness() -> dict:
    """Freshness of the google_calendar source, read from the spine (last
    two month files, newest line wins). Never invents a refresh."""
    out = {"state": "never", "last_ok_at": None, "stale_since": None,
           "last_error": None}
    directory = spine.spine_dir()
    newest_ok = None
    newest_fail = None
    newest_fail_error = None
    months = sorted({p.name for p in directory.glob("events_*.jsonl")}, reverse=True)[:2]
    for name in months:
        try:
            with open(directory / name, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("subject") != "google_calendar":
                        continue
                    if event.get("type") == "fetch_succeeded":
                        if newest_ok is None or event["ts"] > newest_ok:
                            newest_ok = event["ts"]
                    elif event.get("type") == "fetch_failed":
                        if newest_fail is None or event["ts"] > newest_fail:
                            newest_fail = event["ts"]
                            newest_fail_error = (event.get("payload") or {}).get("error")
        except OSError:
            continue
    if newest_ok:
        try:
            ok_at = datetime.fromisoformat(newest_ok)
        except ValueError:
            return out
        age_hours = (datetime.now(IST) - ok_at).total_seconds() / 3600.0
        out["last_ok_at"] = newest_ok
        out["state"] = "fresh" if age_hours < 6 else "stale"
        out["stale_since"] = (ok_at + timedelta(hours=6)).isoformat(timespec="seconds")
        if newest_fail and newest_fail > newest_ok:
            out["last_error"] = newest_fail_error
    return out


def sync_cycle():
    """Pull the window into the store. Safe to call from a thread; every
    failure is recorded rather than raised."""
    global _syncing
    _syncing = True
    _emit("fetch_attempted", "google_calendar")
    try:
        state, detail = connection_state()
        if state != "ok":
            store.set_meta("last_error", detail)
            _emit("fetch_failed", "google_calendar", error=detail)
            return {"state": state, "detail": detail}

        window_start, window_end = _window(datetime.now(IST).date())
        items = google.list_events(window_start, window_end)

        rows = []
        for item in items:
            if item.get("status") == "cancelled":
                continue
            day, start_iso, all_day = _day_of(item)
            if not day:
                continue
            end = item.get("end") or {}
            private = ((item.get("extendedProperties") or {}).get("private") or {})
            rows.append({
                "google_id": item.get("id"),
                "day": day,
                "start_iso": start_iso,
                "end_iso": end.get("dateTime") or end.get("date"),
                "all_day": all_day,
                "summary": item.get("summary") or "(no title)",
                "description": (item.get("description") or "")[:2000],
                "location": item.get("location"),
                "by_agent": 1 if private.get("kage_agent") == "1" else 0,
            })
        store.replace_events(window_start, window_end, rows)
        _emit("fetch_succeeded", "google_calendar",
              data_as_of=datetime.now(IST).isoformat(timespec="seconds"),
              items=len(rows))
        store.set_meta("last_sync", datetime.now(IST).isoformat(timespec="seconds"))
        store.set_meta("last_error", "")

        # How much is actually mirrored, for the card footer. The account
        # address is deliberately NOT shown here: reading it needs
        # calendarList, which the calendar.events scope cannot reach (403),
        # and a footer that guessed at the address would be exactly the kind
        # of confident-but-unverified claim Rule 8 forbids.
        store.set_meta("event_count", len(rows))

        # WakaTime rides the same loop: the free plan's 7-day window is
        # snapshotted before it rolls off, whatever the plan.
        if cfg.WAKATIME_SNAPSHOT_ENABLED and waka.api_key():
            _emit("fetch_attempted", "wakatime")
            try:
                waka.snapshot_recent(store, days=7)
                _emit("fetch_succeeded", "wakatime",
                      data_as_of=datetime.now(IST).isoformat(timespec="seconds"),
                      items=7)
                store.set_meta("last_waka_snapshot",
                               datetime.now().isoformat(timespec="seconds"))
            except waka.WakaTimeError as problem:
                _emit("fetch_failed", "wakatime", error=str(problem))
                store.set_meta("last_waka_error", str(problem))

        return {"state": "ok", "events": len(rows)}
    except Exception as problem:  # noqa: BLE001 - a sync that dies must say so
        store.set_meta("last_error", str(problem))
        _emit("fetch_failed", "google_calendar", error=str(problem))
        return {"state": "error", "detail": str(problem)}
    finally:
        _syncing = False


def background_loop():
    """One thread: sync on its cadence, and run the agent once a night."""
    import time

    while True:
        try:
            sync_cycle()
        except Exception:  # noqa: BLE001
            pass
        try:
            now = datetime.now(IST)
            today = now.date().isoformat()
            # The marker lives in the store, not in this process: otherwise
            # every restart after CALENDAR_AGENT_HOUR runs the agent again,
            # which costs a model call and re-proposes the same evenings.
            if (now.hour >= cfg.CALENDAR_AGENT_HOUR
                    and store.get_meta("last_agent_day") != today):
                store.set_meta("last_agent_day", today)
                calendar_agent.run_recent(days=3)
                if cfg.CALENDAR_AUTO_WRITE:
                    write_all_pending()
        except Exception:  # noqa: BLE001
            pass
        time.sleep(max(cfg.CALENDAR_SYNC_MINUTES, 1) * 60)


# ---------------------------------------------------------------------
# WHAT THE CARD READS
# ---------------------------------------------------------------------
def _hm(seconds):
    if not seconds:
        return None
    hours, minutes = divmod(int(seconds) // 60, 60)
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def _clock(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        instant = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=IST)
    return instant.astimezone(IST).strftime("%I:%M%p").lstrip("0").lower()


def month(year=None, month_number=None):
    """Everything one month grid needs, in one call: which days have
    something, and what kind, so a cell can carry its marker without the
    card fetching 30 days one at a time."""
    today = datetime.now(IST).date()
    year = year or today.year
    month_number = month_number or today.month
    first, last = store.month_bounds(year, month_number)

    state, detail = connection_state()

    events = store.events_between(first, last)
    notes = store.notes_between(first, last)
    waka_rows = store.waka_between(first, last)
    pending = store.proposals(status="pending")

    days = {}

    def slot(day):
        return days.setdefault(day, {"events": 0, "notes": 0, "proposals": 0,
                                     "coding_seconds": None})

    for event in events:
        slot(event["day"])["events"] += 1
    for note in notes:
        slot(note["day"])["notes"] += 1
    for proposal in pending:
        if first <= proposal["day"] <= last:
            slot(proposal["day"])["proposals"] += 1
    for row in waka_rows:
        slot(row["day"])["coding_seconds"] = row["total_seconds"]

    first_date = date(year, month_number, 1)
    last_date = date.fromisoformat(last)

    return {
        "state": state,
        "detail": detail,
        "year": year,
        "month": month_number,
        "label": f"{MONTH_LABELS[month_number - 1]} {year}",
        "today": today.isoformat() if (first <= today.isoformat() <= last) else None,
        "first_weekday": first_date.weekday(),      # 0 = Monday
        "days_in_month": last_date.day,
        "days": days,
        "synced_at": store.get_meta("last_sync"),
        "last_error": store.get_meta("last_error") or "",
        "event_count": int(store.get_meta("event_count") or 0),
        "connecting": _connecting,
        "syncing": _syncing,
        "freshness": _calendar_freshness(),
        "credentials_path": str(google.credentials_file()),
        "auto_write": cfg.CALENDAR_AUTO_WRITE,
        "pending_proposals": len(pending),
        "agent": {**calendar_agent.brain_state(),
                  "last_run": store.get_meta("last_agent_run")},
    }


def day(day_iso):
    """The hover popover's payload: what is on that day, what the agent
    observed, and what it is proposing."""
    events = [{
        "summary": e["summary"],
        "time": "all day" if e["all_day"] else _clock(e["start_iso"]),
        "all_day": bool(e["all_day"]),
        "location": e["location"],
        "by_agent": bool(e["by_agent"]),
    } for e in store.events_on(day_iso)]

    waka_row = store.waka_on(day_iso)
    parsed = date.fromisoformat(day_iso)

    return {
        "day": day_iso,
        "label": parsed.strftime("%a %d %b").upper(),
        "events": events,
        "notes": [{"kind": n["kind"], "text": n["text"]}
                  for n in store.notes_on(day_iso)],
        "proposals": [{"id": p["id"], "summary": p["summary"],
                       "time": _clock(p["start_iso"]), "reason": p["reason"],
                       "status": p["status"]}
                      for p in store.proposals_on(day_iso)],
        "coding": ({"seconds": waka_row["total_seconds"],
                    "display": _hm(waka_row["total_seconds"]),
                    "top_project": waka_row["top_project"],
                    "top_language": waka_row["top_language"]}
                   if waka_row else None),
    }


def whats_next(limit=3):
    """The WHAT'S NEXT list under the grid. Real events only - a pending
    proposal is not on the calendar yet and never appears here."""
    state, detail = connection_state()
    now = datetime.now(IST)
    rows = store.upcoming(now.isoformat(timespec="seconds"),
                          now.date().isoformat(), limit)
    return {
        "state": state,
        "detail": detail,
        "events": [{"summary": r["summary"],
                    "time": "all day" if r["all_day"] else _clock(r["start_iso"]),
                    "day": r["day"],
                    "today": r["day"] == now.date().isoformat(),
                    "by_agent": bool(r["by_agent"])}
                   for r in rows],
    }


# ---------------------------------------------------------------------
# THE WAKATIME HALF OF THE SWITCH
# ---------------------------------------------------------------------
def wakatime_summary():
    key = waka.key_state()
    if key["state"] != "ok":
        return {"state": "not_connected", "detail": key["detail"],
                "snapshot_days": store.waka_day_count()}

    payload = {"state": "ok", "detail": "",
               "snapshot_days": store.waka_day_count(),
               "snapshot_at": store.get_meta("last_waka_snapshot")}
    try:
        payload["today"] = waka.statusbar_today().get("grand_total", {}).get("text")
    except waka.WakaTimeError as problem:
        return {"state": "error", "detail": str(problem),
                "snapshot_days": store.waka_day_count()}

    # The last week always comes from the local snapshot, not the API:
    # it is the same data and it keeps working past the free window.
    end = date.today()
    start = end - timedelta(days=6)
    rows = {r["day"]: r for r in store.waka_between(start.isoformat(),
                                                    end.isoformat())}
    payload["week"] = []
    for offset in range(7):
        current = (start + timedelta(days=offset)).isoformat()
        row = rows.get(current)
        payload["week"].append({
            "day": current,
            "letter": date.fromisoformat(current).strftime("%a")[0],
            "seconds": row["total_seconds"] if row else None,
            "display": _hm(row["total_seconds"]) if row else None,
        })

    try:
        stats = waka.stats("last_7_days")
        payload["languages"] = [
            {"name": lang.get("name"), "percent": round(lang.get("percent") or 0, 1),
             "display": lang.get("text")}
            for lang in (stats.get("languages") or [])[:4]]
        payload["projects"] = [
            {"name": project.get("name"), "display": project.get("text")}
            for project in (stats.get("projects") or [])[:3]]
        payload["daily_average"] = stats.get("human_readable_daily_average")
        payload["range_total"] = stats.get("human_readable_total")
    except waka.WakaTimeError as problem:
        # A 402 here is the free plan, not a breakage: the week above is
        # still real, so say what is missing and keep the rest.
        payload["stats_detail"] = str(problem)
    return payload


# ---------------------------------------------------------------------
# THE ONE WRITE PATH OUT
# ---------------------------------------------------------------------
def approve(proposal_id):
    """Create the real Google event for one pending proposal.

    This is the only function in the card that changes anything outside
    this machine. It refuses anything that is not still `pending`, so a
    double click cannot create the event twice.
    """
    proposal = store.get_proposal(proposal_id)
    if not proposal:
        return {"state": "not_found"}
    if proposal["status"] != "pending":
        return {"state": "already_" + proposal["status"],
                "google_event_id": proposal["google_event_id"]}

    state, detail = connection_state()
    if state != "ok":
        return {"state": state, "detail": detail}

    start_iso = proposal["start_iso"]
    end_iso = proposal["end_iso"] or (
        (datetime.fromisoformat(start_iso) + timedelta(hours=1)).isoformat()
        if start_iso else None)
    if not start_iso or not end_iso:
        store.mark_proposal(proposal_id, "rejected", error="no usable time")
        return {"state": "rejected", "detail": "the proposal had no usable time"}

    try:
        event_id = google.create_event(
            proposal["summary"], start_iso, end_iso,
            description=(proposal["description"] or "")
            + ("\n\n-- proposed by Kage's calendar agent: "
               + (proposal["reason"] or "")),
        )
    except Exception as problem:  # noqa: BLE001 - the card prints the sentence
        store.mark_proposal(proposal_id, "pending", error=str(problem))
        return {"state": "error", "detail": str(problem)}

    store.mark_proposal(proposal_id, "written", google_event_id=event_id)
    threading.Thread(target=sync_cycle, daemon=True).start()
    return {"state": "written", "google_event_id": event_id}


def reject(proposal_id):
    proposal = store.get_proposal(proposal_id)
    if not proposal:
        return {"state": "not_found"}
    if proposal["status"] == "written":
        # Undo: the event is already on the real calendar, so take it off.
        try:
            google.delete_event(proposal["google_event_id"])
        except Exception as problem:  # noqa: BLE001
            return {"state": "error", "detail": str(problem)}
        threading.Thread(target=sync_cycle, daemon=True).start()
    store.mark_proposal(proposal_id, "rejected")
    return {"state": "rejected"}


def write_all_pending():
    """Only reached when CALENDAR_AUTO_WRITE is deliberately on."""
    results = []
    for proposal in store.proposals(status="pending"):
        results.append({"id": proposal["id"], **approve(proposal["id"])})
    return results


def pending_list():
    return {"proposals": [
        {"id": p["id"], "day": p["day"], "summary": p["summary"],
         "time": _clock(p["start_iso"]), "reason": p["reason"]}
        for p in store.proposals(status="pending")],
        "auto_write": cfg.CALENDAR_AUTO_WRITE}
