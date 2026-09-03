"""The live end of the trace ledger: one screen's events, as they land.

WHAT THIS IS
    An async generator that tails the current day's
    Main_Menu/Backend/Trace_Ledger/traces_<date>.jsonl and yields
    Server-Sent-Event frames for every row whose actor is one screen.
    Each FastAPI screen serves it at GET /api/<screen>/live (Phase 12.2,
    additive only - no existing endpoint changed shape).

WHY TAIL THE FILE RATHER THAN SUBSCRIBE
    Verified against the real file before building (see the note at the
    top of Phase 12.1 in OX_ALPHA_EXECUTION_PLAN.md): trace_every_action
    has no in-process callback or subscribe API - trace() appends and
    plain readers read. So the honest mechanism is a byte-offset tail of
    today's file, polled faster than a person can notice.

HONESTY DETAILS
    - Only COMPLETE lines are parsed; a torn final line waits to be
      finished by its writer, never guessed at.
    - Rows are de-duplicated by their per-day `seq`, so a mid-day
      rotation (which resets our byte offset) cannot resend old events.
    - A day rollover restarts the tail at tomorrow's file, empty.
    - A silent stream emits an SSE comment (`: keep-alive`) rather than
      nothing, so proxies do not declare it dead.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime

try:
    import trace_every_action as tea   # noqa: F401
except ImportError:                                   # pragma: no cover
    import trace_every_action as tea                  # noqa: F401

# Live defaults. Module attributes rather than baked-in parameter
# defaults so Tests can tighten them without touching production code.
POLL_SECONDS = 0.5
HEARTBEAT_SECONDS = 15.0


async def stream_screen_events(screen_actor: str, *,
                               poll_seconds: float | None = None,
                               heartbeat_seconds: float | None = None):
    """Yield SSE frames: this screen's trace rows, oldest-first, live."""
    poll = POLL_SECONDS if poll_seconds is None else poll_seconds
    heartbeat = HEARTBEAT_SECONDS if heartbeat_seconds is None \
        else heartbeat_seconds
    yield ": stream open\n\n"

    offset = 0                 # bytes of today's active file already read
    partial = ""               # a line whose newline has not landed yet
    last_seq = None            # newest row seq already sent (dedupe)
    day_being_tailed = None
    last_frame_at = time.monotonic()

    while True:
        frames: list[dict] = []
        try:
            now = datetime.now(tea.IST)
            if now.date() != day_being_tailed:
                day_being_tailed = now.date()
                offset, partial = 0, ""
            path = tea.TRACE_DIR / f"traces_{day_being_tailed.isoformat()}.jsonl"
            if path.exists():
                size = path.stat().st_size
                if size < offset:          # rotated/replaced mid-day
                    offset, partial = 0, ""
                if size > offset:
                    with path.open("rb") as f:
                        f.seek(offset)
                        raw = f.read()
                    offset += len(raw)
                    text = partial + raw.decode("utf-8", errors="replace")
                    *complete, partial = text.split("\n")
                    for line in complete:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            row = json.loads(line)
                        except ValueError:
                            continue       # torn line - wait, never guess
                        seq = row.get("seq")
                        if isinstance(seq, int) and last_seq is not None \
                                and seq <= last_seq:
                            continue       # replayed by a rotation, not news
                        if str(row.get("actor", "")).lower() \
                                != screen_actor.lower():
                            continue       # another screen's event
                        if isinstance(seq, int):
                            last_seq = seq if last_seq is None \
                                else max(last_seq, seq)
                        frames.append(row)
        except OSError:
            pass                           # mid-write/mid-rotate - retry

        for row in frames:
            last_frame_at = time.monotonic()
            yield f"data: {json.dumps(row, ensure_ascii=False)}\n\n"

        if time.monotonic() - last_frame_at >= heartbeat:
            last_frame_at = time.monotonic()
            yield ": keep-alive\n\n"

        await asyncio.sleep(poll)
