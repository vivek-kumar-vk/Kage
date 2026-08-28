# Planned Work

The living list of work to do later. Rule 6 in [`AGENTS.md`](AGENTS.md): anything
named as "later" lands here and as a card in the Enhancement tab. Newest at the
bottom. Status: `queued` | `in progress` | `done`.

---

## P1 — Integrate observability across every tab
- **Status:** queued
- On each tab (Finance, Learning, Enhancement, Model, Main Menu), pick one
  existing block and replace it with an observability feature (live health,
  request/latency, error feed, or trace view for that screen).
- Each observability block is self-contained per Rule 4 — it reads its own
  screen's data directly, no shared module.

## P2 — Remove `Shared_By_All_Agents/` and `Shared_By_All_Screens/` entirely
- **Status:** queued
- End state: both directories gone. Every currently-shared function moves into
  the single screen/agent that uses it; genuinely multi-consumer logic is
  duplicated per consumer, not shared.
- Sequence: inventory each shared file's callers → for single-caller files, inline
  and delete → for multi-caller files, copy into each caller, then delete → keep
  the app booting after each file.
- Known heavy shared pieces: `read_and_write_numbers.py` (the noticeboard),
  `add_and_search_the_knowledge_base.py`, `trace_every_action.py`,
  `the_lease_board.py`, `read_screen_settings.py`.

## P3 — Design the Enhancement tab
- **Status:** queued
- Build the Enhancement tab UI + structure (React 19 / Tailwind / Next.js per
  Rule 3) to show: this file's tracked plans as cards, and any data items flagged
  for follow-up. Card = title, area, status, priority, detail.
- Existing Enhancement screen is a Python/FastAPI ideas board
  (`Screens/Enhancement/`, SQLite `enhancement_board.db`); this replaces its
  frontend and, per Rule 3, its backend.

## P4 — Stack migration: Python/FastAPI → Node.js + Express
- **Status:** queued
- Per Rule 3. Migrate one screen at a time (Main Menu, Finance, Learning,
  Enhancement), keeping ports and the plain-page fallback behaviour.

## P5 — Finish the Anime removal in the optional framework UIs
- **Status:** queued
- The plain HTML/JS Main Menu is clean. Give the Next.js and Svelte Main Menu
  variants a full pass for any layout gaps left by removing the Anime card.

## P6 — Replace the example Learning seeds
- **Status:** queued
- `manage_study_topics.py`, `seed_the_week_plans.py`, and `manage_recall_cards.py`
  ship generic example content. Swap in a real plan, or make the seeds load from
  the private (Google Drive) layer once P-drive lands.

## P7 — Google Drive private storage layer
- **Status:** queued
- See [`immediate_plan.md`](immediate_plan.md) Phase 5: one storage seam → adopted
  Node.js Google Drive MCP server (app is the MCP client) → RAG/smart-retrieval
  extending `add_and_search_the_knowledge_base.py`. Goal: nothing personal on
  local disk.
