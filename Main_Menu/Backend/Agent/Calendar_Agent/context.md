# Context

Where you run: `Main_Menu/Backend/Agent/Calendar_Agent/calendar_agent.py`,
inside the Main Menu screen (port 8000). Triggered nightly at
`CALENDAR_AGENT_HOUR` (default 22:00) from `calendar_pipeline.py`'s sync
loop, or on demand via `POST /api/main_menu/calendar/agent/run`.

Your signals, gathered per day (`gather()`), all real, never simulated:

- **WakaTime** - coding seconds, top project, top language.
- **git** - this repo's commit subjects for that day.
- **existing calendar events** - what's already on the card.
- **Email card** - total/priority counts, if Gmail is connected; `None`
  if it isn't. A card being down is not an error here.

A day with none of the above (`has_any_signal`) gets no run at all - that
is what keeps every note evidence-backed (D23.3).

**Notes vs proposals**: notes are past tense and written straight to
`calendar.sqlite` - they're the record. Proposals are future and stay
`pending` - writing to Google Calendar rings the user's phone, so nothing
reaches Google without a deliberate "Add to calendar" click (or
`CALENDAR_AUTO_WRITE=1`, which is off).

**Two brains, one prompt** (D23.6): `CALENDAR_AGENT_BACKEND` picks
`claude_cli` (one `claude -p --model sonnet` per run) or `omniroute`
(POSTs to the gateway on :8003 - where a Hermes profile would eventually
arrive, not wired up yet). Either being unreachable reports `offline` and
the run is skipped, never guessed.
