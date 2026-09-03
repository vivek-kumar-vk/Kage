"""Rotation and retention for the raw trace ledger.

WHAT THIS OWNS
    Two jobs on Shared_By_All_Screens/Trace_Ledger/, both called from
    trace_every_action.trace() so no other writer has to remember them:

    ROTATION - one day's file is capped at ROTATE_AT_BYTES. When the
    active traces_<date>.jsonl reaches the cap it is renamed to
    traces_<date>_part1.jsonl (then part2, part3...) and writing
    continues in a fresh active file. Nothing is lost: the readers in
    trace_every_action know that a day = its active file PLUS its parts,
    oldest first.

    PRUNING - raw daily files older than KEEP_DAYS are deleted, once per
    process per day. Raw traces are breadcrumbs; 90 days of them is a
    memory, more is clutter. This touches ONLY Trace_Ledger files - a
    promoted, permanent ledger (a CSV under some Saved_Records) is never
    touched by this module and never expires.

THE CONFIG LIVES HERE
    The two constants below are the single place these limits exist.
    They are deliberately not a settings file: a number that governs
    disk growth is read once by whoever changes it, not by every screen.

REVERSIBILITY
    Deleting this module and its call sites leaves valid daily files
    behind; an old reader simply ignores _part-suffixed names ("not a
    day", as list_available_days already put it) and loses nothing but
    the rotated tail.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

# Rotate when today's file passes this size. 50 MB keeps a day readable
# in one pass by both audiences the ledger serves (a person grepping,
# the nightly local-model reflection reading whole days).
ROTATE_AT_BYTES = 50 * 1024 * 1024

# Raw daily traces older than this are pruned. Phase-1 rule 5.2:
# raw 30-90 days; the generous end is chosen because nothing else
# consumes old traces yet.
KEEP_DAYS = 90

_PART_RE = re.compile(r"^traces_(\d{4}-\d{2}-\d{2})(?:_part(\d+))?\.jsonl$")


def day_and_part(stem_or_name: str) -> tuple[date, int] | None:
    """Parse a ledger filename into (day, part). Part 0 = the active file.

    Returns None for anything that does not name a real day - the same
    "not a day" verdict list_available_days has always given.
    """
    m = _PART_RE.match(Path(stem_or_name).name)
    if not m:
        return None
    try:
        day = date.fromisoformat(m.group(1))
    except ValueError:
        return None
    return day, int(m.group(2) or 0)


def files_for_day(trace_dir: Path, day: date) -> list[Path]:
    """One day's files in write order: part1, part2... then the active."""
    prefix = f"traces_{day.isoformat()}"
    found = []
    if trace_dir.exists():
        for path in trace_dir.glob(f"{prefix}*.jsonl"):
            parsed = day_and_part(path.name)
            if parsed and parsed[0] == day:
                found.append((parsed[1], path))
    return [path for _, path in sorted(found)]


def rotate_active_file_if_large(day: date, trace_dir: Path,
                                limit: int | None = None) -> Path:
    """Keep writing to a fresh active file once today's hits `limit`.

    Returns the path the next line should be appended to - usually the
    unchanged active file. Raises nothing a caller doesn't already
    survive: rename errors bubble, and trace() catches everything.
    """
    if limit is None:
        limit = ROTATE_AT_BYTES      # read at call time, so it stays patchable
    active = trace_dir / f"traces_{day.isoformat()}.jsonl"
    if not active.exists() or active.stat().st_size < limit:
        return active
    part_no = 1
    while (trace_dir / f"traces_{day.isoformat()}_part{part_no}.jsonl").exists():
        part_no += 1
    active.rename(trace_dir / f"traces_{day.isoformat()}_part{part_no}.jsonl")
    return active


def prune_old_raw_traces(trace_dir: Path, keep_days: int | None = None,
                         today: date | None = None) -> list[str]:
    """Delete raw daily/part files older than keep_days. Returns names removed.

    Today's files are never candidates even if keep_days were 0 - the
    ledger being written right now must never be pruned mid-write.
    """
    if keep_days is None:
        keep_days = KEEP_DAYS        # read at call time, so it stays patchable
    cutoff_day = (today or date.today()) - timedelta(days=keep_days)
    removed: list[str] = []
    if not trace_dir.exists():
        return removed
    for path in trace_dir.glob("traces_*.jsonl"):
        parsed = day_and_part(path.name)
        if parsed and parsed[0] < cutoff_day:
            try:
                path.unlink()
                removed.append(path.name)
            except OSError:
                continue   # a locked file survives until the next sweep
    return removed
