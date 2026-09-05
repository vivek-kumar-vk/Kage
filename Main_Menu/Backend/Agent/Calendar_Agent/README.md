# Calendar card agent

The Calendar card's nightly learning agent (`AGENTS.md` D23). Everything about
this agent lives in this one folder, no copy anywhere else. The card's
non-agent code (`calendar_store.py`, `calendar_google.py`,
`calendar_pipeline.py`, `wakatime_client.py`) stays two levels up in
`Main_Menu/Backend/`, since the sync loop and the endpoints use it whether
or not the agent ever runs.

Stands alone until the Main Menu page itself is finished (PLAN item 15,
"Day Plan card -> agent-owned") — that will be a separate, page-wide agent
built the same deliberate way once this one has proven the pattern.

## The agent's own profile (token optimization)

Split into 4 markdown files instead of one long `description.txt`, so
Agent Deck's roster API only ever ships the short one, not the whole
operating manual on every load:

- `identity.md` — who it is; this is what Agent Deck (port 8004) shows as
  the card's role/description.
- `context.md` — what it knows about the system it runs in (signals,
  notes vs proposals, the two brains). Loaded into the LLM prompt only.
- `goal.md` — the long-term direction, in plain terms. Loaded into the
  prompt so proposals lean that way without inventing anything.
- `memory.md` — append-only; one line per run. The last ~10 lines are fed
  back into the next prompt for continuity.

`office.json` still carries the Agent Deck department/tier/parent, same
as every other agent under `Screens/Agents/AI_Agents/`.

## What it does

Once a night (`CALENDAR_AGENT_HOUR`, default 22:00 — see
`calendar_pipeline.py`'s sync loop) it gathers real signals for the last
few days — WakaTime seconds, this repo's git commits, existing calendar
events, the Email card's signal — and asks an LLM for two things:

- **notes** — past tense, evidence-backed, one line each. Written straight
  to `calendar.sqlite`.
- **proposals** — future events worth adding. Stored `pending`; never
  written to Google until a deliberate "Add to calendar" click.

A day with no real signal gets no run at all (`has_any_signal`).

## Run it by hand

From `Main_Menu/Backend/`, with the venv active:

```
python Agent/Calendar_Agent/run_now.py                  # last 3 days
python Agent/Calendar_Agent/run_now.py --days 7          # last 7 days
python Agent/Calendar_Agent/run_now.py --day 2026-09-05  # one specific day
```

Or hit the endpoint the card itself uses (server must already be running):

```
curl -X POST "http://127.0.0.1:8000/api/main_menu/calendar/agent/run?days=3"
```

## Two brains, one prompt (D23.6)

`CALENDAR_AGENT_BACKEND` in `settings_for_main_menu.py`:

- `claude_cli` (default) — one `claude -p --model sonnet` per run.
- `omniroute` — POSTs the same prompt to the gateway on :8010. This is
  where a Hermes profile would arrive later, once the page-wide agent
  work starts — not wired up for this card yet.

Either brain being unreachable reports `offline` and the run is skipped;
it never guesses.
