"""Backend for the Learning UI - rebuilt 2026-08-23 against the new page.

WHAT THIS FILE DOES
    Turns what this screen's Calculations folder already knows into JSON
    the Learning page can fetch. Same rule as every other screen's
    server: no arithmetic happens here, only fetching, shaping and
    handing over. Every number comes from a calculation module call -
    this file computes nothing itself.

THE REBUILD
    The old four-tab server answered /today /plan /study /recall from
    four modules. The rebuilt screen keeps all four tabs' behaviour and
    adds the modules two teammates wrote behind it:

    Today      streaks.compute on real sessions + build_daily_checklist
               (three boxes) + both recall queues' due counts + the
               today row out of manage_week_plans.current_week().
    Plan       manage_study_topics (the two-track topic board, seeded
               from a generic example plan) + manage_week_plans
               (seven-day plans per track), alongside the original
               loose-items /plan endpoints kept untouched in behaviour.
    Study      track_study_sessions as before, its stop now carrying the
               work-capture line (`capture`, frozen column contract v14),
               plus build_study_heatmap for the activity grid.
    Recall     TWO queues side by side: the kept Leitner schedule over
               Knowledge_Base notes (/recall), and the new 5-part
               SM-2 recall cards (/recall-cards) seeded with one example
               card.

    Jobs/interviews tracking was deliberately left out - it belongs to
    the future Job_Hunt screen, not here.

HOW TO RUN IT ON ITS OWN
    python Screens\\Learning\\Backend\\server_for_learning.py
    then open http://127.0.0.1:8002
"""

# =====================================================================
# SETUP
# =====================================================================
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent      # the Backend folder
SCREEN = HERE.parent                        # the Learning folder
PROJECT_ROOT = HERE.parents[2]              # the inky folder

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCREEN / "Calculations"))   # for this screen's maths
for _group in (SCREEN / "Calculations").iterdir():   # tab-mirrored groups
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":
        sys.path.insert(0, str(_group))

from fastapi import Body, FastAPI                                       # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles                             # noqa: E402

import settings_for_learning as cfg                                     # noqa: E402

import track_study_sessions as study                                    # noqa: E402
import calculate_streak_and_budget as streak_calc                       # noqa: E402
import manage_recall_schedule as recall                                 # noqa: E402
import manage_the_study_plan as plan                                    # noqa: E402
import manage_study_topics as topics                                    # noqa: E402
import manage_week_plans as week_plans                                  # noqa: E402
import manage_daily_targets as daily_targets                            # noqa: E402
import manage_note_annotations as note_annotations                      # noqa: E402
import match_notes_to_topics as note_match                              # noqa: E402
import read_study_modules as modules_reader                             # noqa: E402
import track_module_progress as module_progress                         # noqa: E402
import check_module_answers as answers                                  # noqa: E402

import build_daily_checklist as checklist                               # noqa: E402
import manage_recall_cards as recall_cards                              # noqa: E402
import build_study_heatmap as heatmap_mod                               # noqa: E402

from Shared_By_All_Screens.show_not_built_yet import page_html          # noqa: E402
from Shared_By_All_Screens.trace_every_action import (                  # noqa: E402
    new_correlation_id, trace,
)

# Example seed data, written to Saved_Records once, on the first start -
# the two-track topic board and one recall card. A re-run never
# overwrites: both functions return False when real data already exists.
topics.seed_topics_if_empty()
recall_cards.seed_cards_if_empty()

app = FastAPI(title=cfg.SCREEN_LABEL)

# Liveness + dependency probe (Phase-1 W1.3) - see health_check.py.
from Shared_By_All_Screens import health_check                          # noqa: E402
health_check.register(app, "learning", saved_records=lambda: cfg.SAVED_RECORDS)


# =====================================================================
# THE TRACE LEDGER - every served request and every page click lands in
# Shared_By_All_Screens/Trace_Ledger/, the same way Finance does it.
# =====================================================================
@app.middleware("http")
async def _trace_api_requests(request, call_next):
    """One row per API call served. Static mounts (/shared, /page, /fonts)
    and the 30-second /dev poll are excluded on purpose - that is noise,
    not signal.

    Phase-1 CS-1: one correlation id per request - honoured from an
    inbound X-Correlation-Id header when present, minted when not,
    echoed back so the caller can chain the next hop."""
    started = time.time()
    cid = request.headers.get("x-correlation-id") or new_correlation_id()
    response = await call_next(request)
    response.headers["X-Correlation-Id"] = cid
    path = request.url.path
    if not path.startswith(("/shared", "/page", "/fonts", "/docs",
                            "/redoc", "/openapi.json", "/dev")):
        trace("learning", "api", f"{request.method} {path}",
              target=path.split("/")[-1] or "/",
              detail={"status": response.status_code},
              outcome="ok" if response.status_code < 400 else "fail",
              duration_ms=int((time.time() - started) * 1000),
              correlation_id=cid)
    return response


@app.post(cfg.API_PREFIX + "/trace")
def receive_page_trace(event: dict = Body(...)):
    """One row per click the page reports. Fire-and-forget from the
    page's side; a failed trace must never break the page."""
    written = trace(
        actor=event.get("actor") or "you",
        kind=event.get("kind") or "click",
        action=event.get("action") or "unknown",
        target=event.get("target") or "",
        detail=event.get("detail"),
        outcome=event.get("outcome") or "ok",
        duration_ms=event.get("duration_ms"),
        correlation_id=event.get("correlation_id"),
    )
    return {"written": written}


@app.get("/dev/changed-since")
def dev_changed_since(token: str = ""):
    """Has any code file behind this page moved since it was loaded?
    An empty token only establishes the baseline and can never say
    'changed' - otherwise every fresh page would reload in a loop."""
    from Shared_By_All_Screens.code_change_monitor import has_changed, is_enabled
    result = has_changed(token, cfg.WATCHED_FOLDERS)
    if not is_enabled():
        return {"changed": False, "fingerprint": result["fingerprint"],
                "latest_file": "", "latest_at": ""}
    if result["changed"] and token:
        trace("learning", "ledger", "file_changed",
              target=result["latest_file"],
              detail={"latest_at": result["latest_at"]})
    return result


# =====================================================================
# HELPERS
# =====================================================================
def _running_session():
    running = study.current_session()
    if running is None:
        return None
    return {"topic": running.topic, "started_at": running.started_at.isoformat(),
           "elapsed_minutes": running.elapsed_minutes}


def _recall_row(r) -> dict:
    return {"note_file": r.note_file, "title": r.title, "box": r.box,
           "last_reviewed": r.last_reviewed, "next_due": r.next_due,
           "is_due": r.is_due}

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def _today_iso() -> str:
    """This screen's own clock - IST, like every calculation module here."""
    return datetime.now(IST).date().isoformat()


def _week_brief(week) -> dict | None:
    """The four fields of a week the page shows; None when nothing is
    planned - an honest empty state, not an error."""
    if week is None:
        return None
    return {"id": week["id"], "num": week["num"], "start": week["start"],
            "focusA": week["focusA"], "focusB": week["focusB"]}


# =====================================================================
# THE PAGE
# =====================================================================
@app.get("/")
def page():
    # The Next.js rebuild (Phase 12.4): first throne, same rule as
    # Main_Menu's (12.3), Enhancement's and Models' (12.4) guards - only
    # when the flag is on AND the build actually exists does it take
    # over the root route. A flag on with no export falls through to the
    # ordinary page instead of a blank screen - honest beats broken.
    if getattr(cfg, "USE_NEXT_UI", False):
        index = getattr(cfg, "NEXT_DIST", None)
        if index is not None and (index / "index.html").exists():
            return FileResponse(index / "index.html")
    if cfg.PAGE.exists():
        return FileResponse(cfg.PAGE)

    return HTMLResponse(page_html(
        cfg.SCREEN_LABEL,
        cfg.PAGE,
        [f"{cfg.API_PREFIX}/today",
         f"{cfg.API_PREFIX}/topics",
         f"{cfg.API_PREFIX}/weeks",
         f"{cfg.API_PREFIX}/study",
         f"{cfg.API_PREFIX}/recall-cards",
         f"{cfg.API_PREFIX}/recall"],
    ))


# =====================================================================
# TAB 1 — TODAY
# =====================================================================
def _next_week_brief(today_iso: str) -> dict:
    """The soonest planned week that starts after today, or empty when
    there is none. Empty is the honest answer at the end of a plan."""
    later = sorted((w for w in week_plans.read_weeks() if w["start"] > today_iso),
                   key=lambda w: w["start"])
    if not later:
        return {}
    return {"next_week_start": later[0]["start"], "next_week_num": later[0]["num"]}


@app.get(cfg.API_PREFIX + "/today")
def today():
    result = streak_calc.compute()
    week = week_plans.current_week()
    today_iso = _today_iso()

    # Today's row: the day inside the current week whose date is today.
    today_row = None
    if week is not None:
        for day in week.get("days", []):
            if day.get("date") == today_iso:
                today_row = day
                break

    # Recent learning activity - the last finished blocks, newest first.
    # This is what the streak card's activity list shows, and what makes
    # the streak feel alive: every stopped session appears here.
    sessions_desc = list(reversed(study.read_sessions()))
    recent_activity = [
        {"date": s["date"], "minutes": s["minutes"], "topic": s["topic"],
         "notes": s.get("notes", ""), "capture": s.get("capture", "")}
        for s in sessions_desc[:5]
    ]

    target_minutes = daily_targets.target_for(today_iso)

    return {
        "streak": {
            "days": result.current_streak_days,
            "last_studied": result.last_studied,
        },
        # The weekly-budget gauge was replaced (2026-08-23) by the
        # reader's own honest schedule view; the budget maths stay in
        # calculate_streak_and_budget.py for anything that wants them.
        "schedule": {
            "date": today_iso,
            "day_name": (today_row or {}).get("d", ""),
            "track_a": (today_row or {}).get("a", ""),
            "track_b": (today_row or {}).get("b", ""),
            # What the day is for, and the timed blocks it was planned
            # as. Empty list means the day was planned as a title only -
            # honestly different from a day with no plan at all.
            "kind": (today_row or {}).get("kind", ""),
            "chunks": (today_row or {}).get("chunks", []),
            "evening": (today_row or {}).get("evening"),
            "note": (today_row or {}).get("note", ""),
            "day_done": bool((today_row or {}).get("done", False)),
            "week_found": week is not None,
            "week_num": week["num"] if week else None,
            "focus_a": week["focusA"] if week else "",
            "focus_b": week["focusB"] if week else "",
            "target_minutes": target_minutes,
            # When no week covers today, say when the next one starts
            # rather than only that nothing is planned. A plan that has
            # not begun yet is a different fact from no plan at all.
            **_next_week_brief(today_iso),
        },
        "recent_activity": recent_activity,
        "checklist": checklist.read_day(today_iso),
        "running_session": _running_session(),
        "due_cards": len(recall_cards.due_cards()),
        "due_notes": len(recall.notes_due()),
        "today_row": today_row,
        "week": _week_brief(week),
    }



@app.post(cfg.API_PREFIX + "/checklist")
def set_checklist_key(body: dict = Body(...)):
    """Set one of the three boxes for today. The module only knows how
    to toggle, so a set that would change nothing simply does not write -
    and an unknown key is refused loudly by the module itself."""
    key = body.get("key")
    value = bool(body.get("value"))
    try:
        current = checklist.read_day(_today_iso())
        if bool(current.get(key)) != value:
            value = checklist.toggle(_today_iso(), key)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "key": key, "value": value}


# =====================================================================
# TAB 2 — PLAN (topic board, week plans, loose items)
# =====================================================================
@app.get(cfg.API_PREFIX + "/topics")
def get_topics():
    book = topics.read_topics()
    return {
        "trackA": {"groups": book.get("trackA", []),
                   "progress": topics.progress("trackA")},
        "trackB": {"groups": book.get("trackB", []),
                   "progress": topics.progress("trackB")},
    }


@app.post(cfg.API_PREFIX + "/topics/status")
def set_topic_status(body: dict = Body(...)):
    try:
        topic = topics.set_status(body.get("id"), body.get("status"))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    except topics.NoSuchTopic as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True, "topic": topic}


@app.get(cfg.API_PREFIX + "/weeks")
def get_weeks():
    weeks = week_plans.read_weeks()
    current = week_plans.current_week()
    return {"weeks": weeks,
            "current_id": current["id"] if current else None,
            "current_focus_a": current["focusA"] if current else "",
            "current_focus_b": current["focusB"] if current else ""}


@app.post(cfg.API_PREFIX + "/weeks")
def add_a_week(body: dict = Body(...)):
    try:
        week = week_plans.add_week(body.get("start", ""),
                                   body.get("focusA", ""),
                                   body.get("focusB", ""))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "week": week}


@app.post(cfg.API_PREFIX + "/weeks/save")
def save_a_week(body: dict = Body(...)):
    """Overwrite a week's editable parts. Only fields actually present
    in the body change anything - the module guards against a caller
    wiping the days by saving just the focus lines."""
    kwargs = {}
    if "days" in body:
        kwargs["days"] = body.get("days")
    if "focusA" in body:
        kwargs["focus_a"] = body.get("focusA")
    if "focusB" in body:
        kwargs["focus_b"] = body.get("focusB")
    try:
        week = week_plans.save_week(body.get("id"), **kwargs)
    except week_plans.NoSuchWeek as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "week": week}


@app.post(cfg.API_PREFIX + "/weeks/toggle")
def toggle_a_week_day(body: dict = Body(...)):
    try:
        day = week_plans.toggle_day(body.get("id"), body.get("date", ""))
    except week_plans.NoSuchWeek as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "day": day}


@app.post(cfg.API_PREFIX + "/weeks/delete")
def delete_a_week(body: dict = Body(...)):
    try:
        week_plans.delete_week(body.get("id"))
    except week_plans.NoSuchWeek as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True}


# --- loose items: the original plan endpoints, untouched in behaviour ---
@app.get(cfg.API_PREFIX + "/plan")
def get_plan():
    return {"built": True, "items": plan.read_plan()}


@app.post(cfg.API_PREFIX + "/plan")
@app.post(cfg.API_PREFIX + "/plan/add")
def add_plan_item(body: dict = Body(...)):
    try:
        item = plan.add_item(body.get("title"), body.get("target_date", ""),
                             body.get("notes", ""))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "item": item}


@app.post(cfg.API_PREFIX + "/plan/mark-done")
@app.post(cfg.API_PREFIX + "/plan/done")
def mark_plan_item_done(body: dict = Body(...)):
    try:
        item = plan.mark_done(body.get("id"), bool(body.get("done", True)))
    except plan.NoSuchPlanItem as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True, "item": item}


@app.delete(cfg.API_PREFIX + "/plan")
def remove_plan_item(item_id: str):
    try:
        plan.remove_item(item_id)
    except plan.NoSuchPlanItem as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True}


@app.post(cfg.API_PREFIX + "/plan/remove")
def remove_plan_item_from_page(body: dict = Body(...)):
    try:
        plan.remove_item(body.get("item_id"))
    except plan.NoSuchPlanItem as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True}
    try:
        plan.remove_item(item_id)
    except plan.NoSuchPlanItem as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True}


# =====================================================================
# TAB 3 — STUDY
# =====================================================================
@app.get(cfg.API_PREFIX + "/study")
def get_study():
    sessions = study.read_sessions()
    return {
        "running_session": _running_session(),
        "recent_sessions": list(reversed(sessions[-20:])),
        "total_sessions": len(sessions),
        "heatmap": heatmap_mod.heatmap(sessions),
    }


@app.post(cfg.API_PREFIX + "/study/start")
def start_study(body: dict = Body(...)):
    try:
        running = study.start_a_session(body.get("topic"))
    except (ValueError, study.ASessionIsAlreadyRunning) as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "running_session": {
        "topic": running.topic, "started_at": running.started_at.isoformat(),
        "elapsed_minutes": running.elapsed_minutes,
    }}


@app.post(cfg.API_PREFIX + "/study/stop")
def stop_study(body: dict = Body(default={})):
    try:
        row = study.stop_the_session(body.get("notes", ""),
                                     capture=body.get("capture", ""))
    except study.NoSessionIsRunning as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "session": row}


@app.post(cfg.API_PREFIX + "/schedule/target")
def set_schedule_target(body: dict = Body(...)):
    """The allocated minutes for today - typed by the person, never
    invented. Sending minutes: null clears it back to a dash."""
    try:
        value = daily_targets.set_target(body.get("date") or _today_iso(),
                                         body.get("minutes"))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "target_minutes": value}


# =====================================================================
# STUDY MODULES - Knowledge_Base notes written as numbered tasks
# =====================================================================
# Tier 0 end to end: regex parsing, a JSON lookup for the answer check,
# JSON counters for progress. No model call anywhere, and no stored
# answer ever crosses back over this boundary - check_one_answer()
# returns verdicts only, never the key it compared against.


def _module_title(note_file: str) -> str:
    """A display title from the file name, the same way /notes/file
    builds one when the front matter carries no explicit title."""
    return note_file[:-3].replace("_", " ") if note_file.endswith(".md") \
        else note_file


def _board_row_for(topic: dict) -> dict:
    """One topic row: who it is, and whether a module serves it -
    ready (with live task counts), missing, or malformed. The state is
    exactly one of those three; there is no fourth maybe."""
    row = {"id": topic["id"], "topic": topic["topic"],
           "tier": topic.get("tier", ""), "status": topic.get("status", "")}
    module = modules_reader.find_module_for_topic(topic)
    if module is None:
        row["module_state"] = "missing"
        return row
    if module.get("malformed"):
        row["module_state"] = "malformed"
        row["note_file"] = module["note_file"]
        return row
    counts = module_progress.counts_for(module["note_file"],
                                        len(module["tasks"]))
    row.update({"module_state": "ready",
                "note_file": module["note_file"],
                "title": _module_title(module["note_file"]),
                "tasks_done": counts["done"],
                "tasks_total": counts["total"]})
    return row


@app.get(cfg.API_PREFIX + "/modules")
def get_modules_board():
    """The whole board: every study topic in the file's own groups and
    order, each with its module state, led by an honest count of how
    many topics have a module at all. Today that count is 0 out of 32
    and the page says so plainly - the gap is the to-do list."""
    book = topics.read_topics()
    groups = []
    with_modules = 0
    total = 0
    for track in topics.TRACKS:
        for group in book.get(track, []):
            rows = []
            for topic in group.get("topics", []):
                total += 1
                row = _board_row_for(topic)
                if row["module_state"] == "ready":
                    with_modules += 1
                rows.append(row)
            groups.append({"group": group["group"], "track": track,
                           "topics": rows})
    return {"built": True,
            "topics_total": total,
            "topics_with_modules": with_modules,
            "groups": groups}


@app.get(cfg.API_PREFIX + "/modules/one")
def get_one_module(name: str = ""):
    """Tasks, questions and stored progress for one module. Never any
    answer or key data - the key file is not even opened on this path."""
    try:
        note_match.read_note_markdown(name)   # name safety + existence first
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    try:
        module = modules_reader.parse_module(name)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)

    stored = module_progress.progress_for(name)
    tasks_out = []
    done_count = 0
    for task in module["tasks"]:
        done = bool(stored["tasks"].get(task["id"], {}).get("done"))
        if done:
            done_count += 1
        questions = []
        for q in task["questions"]:
            record = stored["answers"].get(q["id"], {})
            questions.append({"id": q["id"], "text": q["text"],
                              "attempts": record.get("attempts"),
                              "solved": bool(record.get("correct", False))})
        tasks_out.append({"id": task["id"], "number": task["number"],
                          "title": task["title"], "done": done,
                          "questions": questions})
    return {"ok": True, "note_file": name,
            "title": _module_title(name),
            "malformed": module["malformed"],
            "topic_id": module["topic_id"],
            "tasks": tasks_out,
            "counts": {"done": done_count, "total": len(tasks_out)}}


@app.post(cfg.API_PREFIX + "/modules/task")
def toggle_a_module_task(body: dict = Body(...)):
    """Tick or un-tick one task. Replies with the new state plus counts
    recomputed against the note parsed right now - a stored percentage
    would go stale the day the note gains a task."""
    name = body.get("name", "")
    try:
        module = modules_reader.parse_module(name)
    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    try:
        toggle = module_progress.toggle_task(name, body.get("task_id"))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    counts = module_progress.counts_for(name, len(module["tasks"]))
    return {"ok": True, "toggle": toggle, "counts": counts}


@app.post(cfg.API_PREFIX + "/modules/answer")
def check_a_module_answer(body: dict = Body(...)):
    """Right, wrong, or no-key - the verdict only. An attempt is logged
    only when a key exists to check against; an unchecked guess is not
    an attempt. A wrong answer gets nothing but the cross."""
    name = body.get("name", "")
    question_id = body.get("question_id")
    try:
        result = answers.check_one_answer(name, question_id,
                                          body.get("typed"))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    if result.get("has_key"):
        module_progress.record_attempt(name, question_id,
                                       bool(result["correct"]))
    reply = {"ok": True, "has_key": result["has_key"],
             "correct": result["correct"]}
    if result.get("why"):
        reply["why"] = result["why"]
    return reply


# =====================================================================
# THE READER - notes explorer + interactive markdown reading
# =====================================================================
# Everything here is Tier 0: listing files the research agent really
# wrote, matching a topic to a note by counting shared words, storing
# what the reader highlighted. No model call anywhere.
@app.get(cfg.API_PREFIX + "/notes")
def list_notes():
    """Every Knowledge_Base note, title + filename. This is what the
    Notes Explorer drawer lists."""
    notes = recall.all_notes()
    return {"built": True, "total": len(notes), "notes": notes}


@app.get(cfg.API_PREFIX + "/notes/file")
def read_a_note(name: str = ""):
    """The markdown of one note, front matter split off so the reader
    can show clean content plus its sources."""
    try:
        text = note_match.read_note_markdown(name)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)

    meta = {"title": name[:-3].replace("_", " ") if name.endswith(".md")
            else name,
            "added_at": "", "sources": [], "type": ""}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if line.startswith("title:"):
                    meta["title"] = line.split(":", 1)[1].strip()
                elif line.startswith("added_at:"):
                    meta["added_at"] = line.split(":", 1)[1].strip()
                elif line.startswith("type:"):
                    meta["type"] = line.split(":", 1)[1].strip()
                elif line.strip().startswith("- http"):
                    meta["sources"].append(line.strip().lstrip("- ").strip())
            body = parts[2]
    annotations = note_annotations.annotations_for(name)
    return {"ok": True, "note_file": name, **meta,
            "markdown": body.strip(), "annotations": annotations}


@app.get(cfg.API_PREFIX + "/study/reading")
def reading_for_topic(topic: str = ""):
    """Which note to open when a session starts on a planned topic -
    decided by shared-word scoring, or an honest 'no note yet'."""
    match = note_match.best_note_for(topic)
    if match is None:
        return {"ok": True, "match": None,
                "reason": "no Knowledge_Base note matches this topic closely"}
    return {"ok": True, "match": match}


@app.get(cfg.API_PREFIX + "/annotations")
def get_annotations(note_file: str = ""):
    return {"ok": True, "note_file": note_file,
            "annotations": note_annotations.annotations_for(note_file)}


@app.post(cfg.API_PREFIX + "/annotations")
def add_annotation_from_reader(body: dict = Body(...)):
    try:
        entry = note_annotations.add_annotation(
            body.get("note_file", ""), body.get("quote", ""),
            body.get("note", ""), body.get("occurrence", 0))
    except note_annotations.DuplicateAnnotation as d:
        # Phase-1 CS-2 retry-safety: the same highlight saved twice is
        # answered with the entry already on file, never a second copy.
        return {"ok": True, "annotation": d.existing, "duplicate": True}
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "annotation": entry}


@app.post(cfg.API_PREFIX + "/annotations/delete")
def delete_annotation_from_reader(body: dict = Body(...)):
    try:
        note_annotations.delete_annotation(body.get("id"))
    except note_annotations.NoSuchAnnotation as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True}


# =====================================================================
# TAB 4 — RECALL (my SM-2 cards | Knowledge_Base notes)
# =====================================================================
@app.get(cfg.API_PREFIX + "/recall-cards")
def get_recall_cards():
    cards = recall_cards.read_cards()
    due = recall_cards.due_cards()
    return {
        "cards": cards,
        "due": due,
        "resume_ready_count":
            sum(1 for c in cards if recall_cards.resume_ready(c)),
    }


@app.post(cfg.API_PREFIX + "/recall-cards/review")
def review_a_card(body: dict = Body(...)):
    try:
        card = recall_cards.review_card(body.get("card_id"),
                                        body.get("quality"))
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    except recall_cards.NoSuchCard as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True, "card": card}


@app.post(cfg.API_PREFIX + "/recall-cards/add")
def add_a_recall_card(body: dict = Body(...)):
    try:
        card = recall_cards.add_card(
            body.get("topic", ""), track=body.get("track", "A"),
            elevator=body.get("elevator", ""),
            likely_q=body.get("likely_q", ""),
            trap_q=body.get("trap_q", ""),
            example=body.get("example", ""),
            resume_link=body.get("resume_link", ""))
    except recall_cards.DuplicateCard as d:
        # Phase-1 CS-2 retry-safety: a double-posted card is answered
        # with the card already stored, flagged, never a second one.
        return {"ok": True, "card": d.existing, "duplicate": True}
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    return {"ok": True, "card": card}


@app.post(cfg.API_PREFIX + "/recall-cards/update")
def update_a_recall_card(body: dict = Body(...)):
    card_id = body.pop("id", None)
    # Only the content fields the module allows - scheduling state is
    # review_card()'s alone and is refused here by the module itself.
    fields = {k: v for k, v in body.items()
              if k in recall_cards.CONTENT_FIELDS}
    try:
        card = recall_cards.update_card(card_id, **fields)
    except ValueError as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=400)
    except recall_cards.NoSuchCard as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True, "card": card}


@app.post(cfg.API_PREFIX + "/recall-cards/delete")
def delete_a_recall_card(body: dict = Body(...)):
    try:
        recall_cards.delete_card(body.get("id"))
    except recall_cards.NoSuchCard as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True}


# --- notes: the original Leitner queue over Knowledge_Base, kept as-is ---
@app.get(cfg.API_PREFIX + "/recall")
def get_recall():
    all_status = recall.schedule()
    due = [r for r in all_status if r.is_due]
    return {
        "built": True,
        "total_notes": len(all_status),
        "due_count": len(due),
        "due": [_recall_row(r) for r in due],
        "not_due": [_recall_row(r) for r in all_status if not r.is_due],
    }


@app.post(cfg.API_PREFIX + "/recall/review")
def review_a_note(body: dict = Body(...)):
    try:
        row = recall.mark_reviewed(body.get("note_file"), bool(body.get("remembered")))
    except recall.NoSuchNote as e:
        return JSONResponse({"ok": False, "problem": str(e)}, status_code=404)
    return {"ok": True, "review": row}


# =====================================================================
# STATIC FILES
# =====================================================================
# The look every screen shares.
if cfg.FONTS_DIR.exists():
    app.mount("/fonts", StaticFiles(directory=cfg.FONTS_DIR), name="fonts")

app.mount("/shared", StaticFiles(directory=cfg.LOOK_AND_FEEL), name="shared")

# This screen's own CSS/JS, split out of the HTML on 2026-08-20 so a UI
# change is a small file to open, not a scroll through one 800-line page.
# Mounted, not routed one file at a time - Page/ only ever holds this
# screen's own look, never anything that needs a check before serving.
app.mount("/page", StaticFiles(directory=cfg.PAGE.parent), name="page")


# =====================================================================
# LIVE SSE (Phase 12.2 - strictly additive)
#     GET /api/learning/live streams this screen's own trace-ledger
#     rows as they land. Tails Shared_By_All_Screens/Trace_Ledger/
#     traces_<date>.jsonl via tail_the_trace_ledger.py.
# =====================================================================
from fastapi.responses import StreamingResponse                          # noqa: E402
from Shared_By_All_Screens.tail_the_trace_ledger import (                # noqa: E402
    stream_screen_events,
)


@app.get(cfg.API_PREFIX + "/live")
async def stream_live_events():
    """Server-Sent Events: learning's own traces, as they happen."""
    return StreamingResponse(stream_screen_events("learning"),
                             media_type="text/event-stream")


# The Next.js rebuild's static export (Phase 12.4). Mounted LAST, after
# every /api route including /live above: Starlette matches routes in
# registration order, and a "/" mount is a catch-all - registering it
# any earlier would 404 every route below it once the flag goes on
# (the exact bug Enhancement's Phase 12.4 fork found and fixed). Flag
# off, or `npm run build` not run yet (no out/), means this block never
# runs and nothing changes.
if getattr(cfg, "USE_NEXT_UI", False):
    _next_dist = getattr(cfg, "NEXT_DIST", None)
    if _next_dist is not None and (_next_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=_next_dist, html=True),
                  name="next_ui")


# =====================================================================
# START IT
# =====================================================================
if __name__ == "__main__":
    import uvicorn

    print(f"{cfg.SCREEN_LABEL} -> http://{cfg.HOST}:{cfg.PORT}")
    uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)

