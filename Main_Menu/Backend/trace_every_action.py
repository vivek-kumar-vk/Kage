"""The trace ledger: everything INKY does, written down as it happens.

WHAT THIS IS
    An append-only, one-file-per-day event log — INKY's version of the
    "traceable" idea from recent agent harnesses. Every click on a page,
    every API call a screen serves, every agent step and every skill
    invocation can land here as one small JSON line:

        Main_Menu/Backend/Trace_Ledger/traces_YYYY-MM-DD.jsonl

    One file per day, because the two readers of this ledger are a
    person (grep today's file) and the local model (read today's file,
    all of it, in one prompt). A year in one file would serve neither.

THE SCHEMA (stable - treat like a column contract)
    ts          ISO timestamp with offset
    actor       who acted: a screen ("finance"), an agent name, "you"
    kind        click | view | api | skill | agent | model | ledger | error
    action      the verb, lowercase with underscores ("open_tab")
    target      what it acted on ("investments", "fund_nav_ledger")
    detail      small dict, optional - capped, never a payload dump
    outcome     ok | fail | escalated
    duration_ms int, optional
    seq         int, optional but always written since ADR-085: one
                monotonic number per day, so a reader can tell order
                without trusting clock precision, and can spot gaps.
    correlation_id  short string, optional since Phase-1 CS-1 (2026-08-25):
                ties the rows of one user-visible action together - a
                click, the api call it caused, the agent run and the
                model call behind it all carry the same id. Absent means
                "written before this existed or with nothing to tie to",
                never a guess. Every reader must tolerate its absence.

V2 ADDITIVE FIELDS (ADR-118, 2026-08-25 - implemented Track L)
    ts_utc      ISO UTC timestamp, written on every NEW row. Storage
                timestamps are UTC per ADR-118; the legacy `ts` above
                stays IST-offset so every existing reader and display
                keeps working untouched. Old rows simply lack this key.
    token_counts  dict, optional - e.g. {"prompt": 123, "completion": 45}.
                Validated small and integer-valued; anything else is
                dropped rather than guessed into shape.
    cost_usd    float, optional. 0.0 is a real fact (a local model call
                costs nothing) and IS stored; absent means unknown.
    model_name  string, optional, capped at 80 chars - what answered,
                when this row came from a model call.
    quant       string, optional, capped at 40 chars - quantization tag
                (e.g. "Q5_K_M") alongside model_name.
    error_fix_id  string, optional, capped at 80 chars - ties a fix back
                to the error row(s) it fixed.
    source      string, optional, capped at 120 chars - where the row's
                numbers trace to (a ledger path, a provider response id).

    All of these are ADDITIVE ONLY: no existing field was renamed, and
    every key above is written ONLY when somebody actually supplied it,
    so new rows stay byte-compatible with readers written before v2 -
    they just ignore keys they do not know. Old lines still parse.

ROTATION & RETENTION (Phase-1 W1.1)
    A day's file rotates to traces_<date>_part<n>.jsonl at 50 MB and
    raw days older than 90 are pruned - see Trace_Ledger/
    rotate_and_prune_traces.py. The readers here treat a day as its
    active file plus its parts; promoted CSV ledgers are permanent and
    untouched by any of it.

WHY IT EXISTS
    The local model (qwen3:8b through Ollama) can only learn from what
    it can see. Until now its picture of a day was scattered across
    model_call_log.csv, what_happened.csv per agent, and whatever a
    person remembered. This file is the single, complete record the
    nightly reflection reads to write the next day's plan.

THE ONE RULE
    Tracing must never break the thing it observes. Every write here is
    wrapped: if tracing fails, the failure is noted on stderr and the
    caller carries on. A lost click is cheaper than a crashed screen.
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Rotation/retention (Phase-1 W1.1): the writer keeps the raw ledger
# bounded so no reader ever has to. Dual import form because some
# callers put this folder itself on sys.path and others reach the
# package through the project root.
try:
    from Trace_Ledger.rotate_and_prune_traces import (
        day_and_part, files_for_day, prune_old_raw_traces,
        rotate_active_file_if_large,
    )
except ImportError:                                   # pragma: no cover
    from Trace_Ledger.rotate_and_prune_traces import (
        day_and_part, files_for_day, prune_old_raw_traces,
        rotate_active_file_if_large,
    )

HERE = Path(__file__).resolve().parent          # Main_Menu/Backend
PROJECT_ROOT = HERE.parents[2]                  # the inky folder
TRACE_DIR = HERE / "Trace_Ledger"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# India has no daylight saving; fixed offset, same clock as everywhere.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

# A detail dict larger than this is truncated. A trace is a breadcrumb,
# not a payload copy - the data lives in its own file and the trace
# should point at it, not duplicate it. Raised from 400 when the ledger
# became the Models screen's Log tab source (ADR-085): a model learning
# from clicks needs the shape of an interaction, which 400 chars kept
# cutting off.
MOST_DETAIL_CHARS = 1500

KINDS = ("click", "view", "api", "skill", "agent", "model", "ledger", "error")

# The per-day sequence counter. One process writes most of a day, but it
# may be restarted - so the first write after a restart counts the lines
# already in the file and continues from there, under a lock, because
# FastAPI serves requests concurrently.
_seq_lock = threading.Lock()
_seq_seen: dict[str, int] = {}

# Pruning runs at most once per process per day - a directory sweep is
# not work every traced click should pay for.
_last_prune_day: date | None = None


def _next_seq(day: date) -> int:
    """The next monotonic number for this day's file.

    Counts across the day's ACTIVE file AND its rotated parts, so a
    rotation mid-day never resets the sequence and two rows can never
    share one number within a day.
    """
    key = day.isoformat()
    with _seq_lock:
        if key not in _seq_seen:
            last = 0
            for path in files_for_day(TRACE_DIR, day):
                with path.open(encoding="utf-8") as f:
                    for _line in f:
                        if _line.strip():
                            last += 1
            _seq_seen[key] = last
        _seq_seen[key] += 1
        return _seq_seen[key]


def _housekeep_once() -> None:
    """Rotate a too-large active file; prune stale days once per day.

    Housekeeping failing must never cost the trace that triggered it -
    the caller's append still runs, worst case into an unrotated file.
    """
    global _last_prune_day
    try:
        today = _now().date()
        rotate_active_file_if_large(today, TRACE_DIR)
        if _last_prune_day != today:
            prune_old_raw_traces(TRACE_DIR)
            _last_prune_day = today
    except Exception as trouble:                      # noqa: BLE001
        print(f"[trace] housekeeping skipped ({trouble})", file=sys.stderr)


def _now() -> datetime:
    return datetime.now(IST)


def _day_file(day: date) -> Path:
    return TRACE_DIR / f"traces_{day.isoformat()}.jsonl"


def _clean_detail(detail) -> dict:
    """Detail must be small, JSON-safe and bounded."""
    if not detail:
        return {}
    try:
        text = json.dumps(detail, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return {"note": "unserialisable detail dropped"}
    if len(text) > MOST_DETAIL_CHARS:
        return {"note": "detail truncated", "head": text[:MOST_DETAIL_CHARS]}
    return json.loads(text)


def new_correlation_id() -> str:
    """A fresh short id for one user-visible action.

    Twelve hex chars: small enough to eyeball in a grep, wide enough
    that two actions colliding inside one day's file is not a realistic
    worry. Callers who already have their own per-run id (the
    supervisor's ticket, an inbound X-Correlation-Id header) should use
    that instead - the point is one id per action, not this function.
    """
    return uuid.uuid4().hex[:12]


def _clean_token_counts(value) -> dict | None:
    """Token counts must be a small flat dict of integers, else nothing.

    A blank is None, never 0: an absent measurement is written as no key
    at all. Garbage ("many", nested blobs, floats) is dropped whole - a
    wrong number here poisons the usage maths downstream, so partial
    guesses are refused on purpose.
    """
    if not isinstance(value, dict):
        return None
    cleaned: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not key or len(key) > 40:
            continue
        if isinstance(count, bool) or not isinstance(count, int):
            continue
        if count < 0:
            continue          # a negative token count is garbage, not data
        cleaned[key] = count
    return cleaned or None


def trace(actor: str, kind: str, action: str, target: str = "",
          detail: dict | None = None, outcome: str = "ok",
          duration_ms: int | None = None,
          correlation_id: str | None = None,
          token_counts: dict | None = None, cost_usd: float | None = None,
          model_name: str | None = None, quant: str | None = None,
          error_fix_id: str | None = None, source: str | None = None) -> bool:
    """Write one line. Returns True when written, False when dropped.

    Never raises. A trace that cannot be written must not take the
    screen, the agent or the click down with it - that is the one rule
    at the top of this file.

    The v2 keyword arguments (ADR-118) are all optional and all additive:
    leave them out and the row looks exactly like a pre-v2 row except for
    the always-written `ts_utc` stamp.
    """
    try:
        if kind not in KINDS:
            kind = "view"
        entry = {
            "ts": _now().isoformat(timespec="milliseconds"),
            "actor": str(actor)[:60],
            "kind": kind,
            "action": str(action)[:80],
            "target": str(target)[:120],
            "detail": _clean_detail(detail),
            "outcome": outcome if outcome in ("ok", "fail", "escalated") else "ok",
            "seq": _next_seq(_now().date()),
            # ADR-118: storage timestamps are UTC. The legacy IST `ts`
            # above stays because renaming it would break every reader;
            # this is the standardized form, added next to it.
            "ts_utc": datetime.now(timezone.utc)
                              .isoformat(timespec="milliseconds"),
        }
        if duration_ms is not None:
            entry["duration_ms"] = int(duration_ms)
        # Additive since CS-1: only present when somebody had something
        # to correlate. An empty/absent id writes nothing, so rows stay
        # byte-compatible with every reader written before it existed.
        if correlation_id:
            entry["correlation_id"] = str(correlation_id)[:80]
        # Additive since ADR-118: same discipline - supply it or the key
        # does not exist. Blank is absence, never a fabricated 0.
        counts = _clean_token_counts(token_counts)
        if counts:
            entry["token_counts"] = counts
        if isinstance(cost_usd, (int, float)) and not isinstance(cost_usd, bool):
            entry["cost_usd"] = round(float(cost_usd), 6)
        if model_name:
            entry["model_name"] = str(model_name)[:80]
        if quant:
            entry["quant"] = str(quant)[:40]
        if error_fix_id:
            entry["error_fix_id"] = str(error_fix_id)[:80]
        if source:
            entry["source"] = str(source)[:120]

        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        _housekeep_once()
        with _day_file(_now().date()).open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except Exception as trouble:                                      # noqa: BLE001
        print(f"[trace] dropped ({trouble})", file=sys.stderr)
        return False


def read_day(day: date) -> list[dict]:
    """Every trace for one day, oldest first. Empty when nothing happened.

    A day is its active file PLUS any rotated parts of it (part1 holds
    the oldest lines), so rotation never hides history from a reader.
    """
    out = []
    for path in files_for_day(TRACE_DIR, day):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue   # a torn line is skipped, never guessed at
    return out


def list_available_days() -> list[str]:
    """Every day that has a ledger file, newest first (ISO strings).

    Part-suffixed files count too: a day known only through its rotated
    parts still happened.
    """
    if not TRACE_DIR.exists():
        return []
    found = set()
    for path in TRACE_DIR.glob("traces_*.jsonl"):
        parsed = day_and_part(path.name)
        if parsed:
            found.add(parsed[0].isoformat())
    return sorted(found, reverse=True)


def read_day_filtered(day, actor: str = "", kind: str = "",
                      outcome: str = "", search: str = "",
                      limit: int = 200) -> dict:
    """One day's traces through the Log tab's filters.

    `day` is a date or an ISO string. `search` matches inside the
    action, the target and the detail JSON, case-insensitively.
    has_data says whether the DAY has anything at all - so an empty
    filtered result on a busy day reads as "nothing matched", not as
    "nothing happened" (those are different facts).
    """
    if isinstance(day, str):
        day = date.fromisoformat(day)
    rows = read_day(day)
    kept = []
    needle = (search or "").lower()
    for row in rows:
        if actor and row.get("actor") != actor:
            continue
        if kind and row.get("kind") != kind:
            continue
        if outcome and row.get("outcome") != outcome:
            continue
        if needle:
            haystack = " ".join((
                row.get("action", ""),
                row.get("target", ""),
                json.dumps(row.get("detail", {}), ensure_ascii=False),
            )).lower()
            if needle not in haystack:
                continue
        kept.append(row)
        if len(kept) >= limit:
            break
    return {"has_data": bool(rows), "total": len(rows),
            "showing": len(kept), "rows": kept}


def summarise_day(day: date) -> dict:
    """Counts a person (or a model) can act on, without reading every line."""
    rows = read_day(day)
    by_kind = Counter(r["kind"] for r in rows)
    by_actor = Counter(r["actor"] for r in rows)
    actions = Counter(r["action"] for r in rows)
    targets = Counter(r["target"] for r in rows if r["target"])
    errors = [r for r in rows if r["outcome"] != "ok"]
    durations = [r["duration_ms"] for r in rows
                 if isinstance(r.get("duration_ms"), int)]
    return {
        "has_data": bool(rows),
        "day": day.isoformat(),
        "total": len(rows),
        "by_kind": dict(by_kind),
        "by_actor": dict(by_actor),
        "top_actions": actions.most_common(10),
        "top_targets": targets.most_common(10),
        "not_ok": len(errors),
        "errors": [{"action": r["action"], "target": r["target"],
                    "outcome": r["outcome"]} for r in errors[:10]],
        "first_activity": rows[0]["ts"] if rows else None,
        "last_activity": rows[-1]["ts"] if rows else None,
        "median_duration_ms": (sorted(durations)[len(durations) // 2]
                               if durations else None),
    }


def brief_for_the_model(day: date) -> str:
    """The day as compact prose a local model can ingest in one prompt.

    Built from the summary plus a sampled tail of raw lines - enough to
    reason about, small enough for an 8B model's context window.
    """
    s = summarise_day(day)
    if not s["has_data"]:
        return f"No traces recorded on {day.isoformat()}."

    lines = [f"Traces for {s['day']} — {s['total']} events "
             f"({s['not_ok']} not ok), {s['first_activity']} → {s['last_activity']}."]
    if s["by_actor"]:
        lines.append("Actors: " + ", ".join(
            f"{k}={v}" for k, v in sorted(s["by_actor"].items())))
    if s["top_actions"]:
        lines.append("Most common actions: " + ", ".join(
            f"{a}×{n}" for a, n in s["top_actions"]))
    if s["top_targets"]:
        lines.append("Most touched targets: " + ", ".join(
            f"{t}×{n}" for t, n in s["top_targets"]))
    for e in s["errors"][:5]:
        lines.append(f"- not ok: {e['action']} on {e['target'] or '—'} ({e['outcome']})")

    lines.append("Last events, oldest first:")
    for r in read_day(day)[-40:]:
        extra = f" :: {json.dumps(r['detail'], ensure_ascii=False)}" if r["detail"] else ""
        lines.append(f"- {r['ts'][11:19]} {r['actor']} {r['kind']} "
                     f"{r['action']} → {r['target'] or '—'} [{r['outcome']}]{extra}")
    return "\n".join(lines)


def plan_items_from_note(text: str) -> list[dict]:
    """Parse the checklist a reflection wrote under a 'plan' heading.

    Reflections keep their plan as markdown checkboxes so tomorrow's
    reflection can score follow-through instead of planning into a void.
    """
    items, in_plan = [], False
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            in_plan = "plan" in stripped.lower()
            continue
        if in_plan and stripped.startswith("- ["):
            done = stripped.startswith("- [x]") or stripped.startswith("- [X]")
            label = stripped[stripped.index("]") + 1:].strip()
            words = {w for w in "".join(
                ch if ch.isalnum() else " " for ch in label.lower()).split()
                if len(w) > 3}
            items.append({"label": label, "done": done, "words": words})
    return items


def estimated_follow_through(plan_items: list[dict],
                             evidence_text: str) -> dict:
    """How much of yesterday's plan shows up in today's traces.

    A keyword-overlap ESTIMATE, labelled as one. Traces use machine-word
    actions while plans are human sentences, so this can never be more
    than an estimate - the field names say so rather than presenting a
    guess as a measurement.
    """
    if not plan_items:
        return {"planned": 0, "evidenced": 0,
                "estimated_follow_through_pct": None,
                "note": "no plan was written the previous day"}
    evidence = set(evidence_text.lower().split())
    hit = sum(1 for item in plan_items if item["words"] & evidence)
    pct = round(hit / len(plan_items) * 100, 1)
    return {"planned": len(plan_items), "evidenced": hit,
            "estimated_follow_through_pct": pct}


def main() -> None:
    today = _now().date()
    print("TRACE LEDGER")
    print("=" * 50)
    s = summarise_day(today)
    if not s["has_data"]:
        print(f"  Nothing traced yet today ({today.isoformat()}).")
        print(f"  Ledger folder: {TRACE_DIR.relative_to(PROJECT_ROOT)}")
        return
    print(f"  {s['total']} events today ({s['not_ok']} not ok)")
    for k, v in sorted(s["by_kind"].items()):
        print(f"    {k:<8}{v}")
    print()
    print(brief_for_the_model(today)[:800])


if __name__ == "__main__":
    main()

