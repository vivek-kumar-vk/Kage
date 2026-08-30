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
- **Status:** queued — this is the status entry; **full spec is
  [`immediate_plan.md`](immediate_plan.md) Phase 5** (storage seam API, MCP
  transport, RAG, AI-trader seam).
- In short: one storage seam (`read_doc`/`write_doc`/`list_docs`/`delete_doc`/
  `search`) → adopted Node.js **Google Drive MCP server** (app is the MCP client)
  → RAG extending `add_and_search_the_knowledge_base.py` → AI-trader seam stub.
  Goal: nothing personal on local disk.
- Build track: Qwen 3-Max writes the code from a house-style brief (see
  [`WAYFINDER.md`](WAYFINDER.md) item 2 / Track A); Claude validates + wires in.

## P10 — Configure the OmniRoute gateway
- **Status:** done (2026-08-30)
- OmniRoute (npm `omniroute`) runs at `http://127.0.0.1:8003` — the port the
  Model screen always expected (the slot vacated by the removed LiteLLM).
  Started by `Start_Inky/run_omniroute.py`, chained into
  `Start_Everything.bat`; the launcher generates the gateway's secrets into
  `.env` on first run and leaves an already-running gateway alone.
- `GATEWAY_API_KEY` (dashboard key `kage-model-screen`) lives in `.env`;
  the Model screen sends it as a Bearer key. Health probe fixed to
  OmniRoute's real route `/api/monitoring/health` (the old
  `/health/liveliness` was LiteLLM's and 404'd → false "unreachable").
  Decisions: **D6 / D6.1 / D6.2** in `AGENTS.md`.
- Free provider `opencode` (OpenCode Free, no auth) connected: 63 models
  via `/v1/models` (Claude, Gemini, GPT, Grok, `glm-5.x`, DeepSeek, Qwen,
  Kimi …), chat smoke test routed through `auto/best-fast`. Real provider
  keys get added in the dashboard at `http://127.0.0.1:8003` → Providers.
- Secret-free config record: `Screens/Model/GATEWAY_CONFIG.md`.
- Wayfinder: `.scratch/model-page-gateway/map.md` (renamed from
  `model-page-litellm/`; LiteLLM tickets archived).

## P11 — Route the finance-os agents' LLM clients through OmniRoute
- **Status:** queued (was P10's follow-up)
- Supervisor needs `complete(question, context) -> str`; specialists need
  `summarize(payload) -> str`. Both are small adapters over
  `/v1/chat/completions` on `127.0.0.1:8003` with `GATEWAY_API_KEY`.
- Model choice stays a gateway routing decision, not code.
- Open questions to settle first: `finance-os/finance-datamigration.md`
  Q10 (finance AI agent + cloud LLM routing), Q12 (OmniRoute before/after
  the data migration).

---

## Active order

One item at a time. Full map with links: [`WAYFINDER.md`](WAYFINDER.md).

1. Finance data migration / backfill — *(user-led, ACTIVE)*
2. Google Drive private storage layer (P7) — *(Qwen-led, ACTIVE — parallel)*
3. Wire finance-os agents through OmniRoute (P11)
4. Enhancement tab UI (P3)
5. Replace Learning seeds (P6)
6. Observability on every tab (P1)
7. Remove `Shared_By_All_*` (P2)
8. Python → Node stack migration (P4)
9. Anime-removal cleanup (P5)
10. dsh local-model observability (`.scratch/dsh-local-model/PLAN.md`, parked)

---

## Dropped

- **P8 — Wire Finance telemetry panels to live endpoints.** Retired: targeted
  `Screens/Finance/Page/next_app/`, which `finance-os/` V1 replaced. finance-os
  owns Finance data wiring now.
- **P9 — Finance realism pass (F1 two-livery).** Built (`5b72750`) then superseded
  by the finance-os V1 cutover (`657774d`). Archived at
  `.scratch/_archive/finance-realism-pass/`. See `AGENTS.md` D7.
