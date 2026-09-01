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

## P3 — The AGENT DECK screen (agent workspace; rebuild + rename of Enhancement)
- **Status:** V1 DONE 2026-08-30 (all 12 Qwen turns applied + verify gate passed).
  Full plan: `.scratch/agents-workspace/map.md`
  + `.scratch/agents-workspace/QWEN_BUILD_PROMPT.md`. V2 remains queued.
- Upgrade + reframe of the old "rebuild the kanban" P3. `Screens/Enhancement/` →
  `Screens/Agents/` (`MENU_LABEL="AGENT DECK"`, port 8004 kept). The screen is a
  local **agent workspace** (3-pane, "Deck" theme — Main-Menu DNA, not Slack's
  look). The kanban is one room inside it, owned by `Agent_Head`.
- **V1 (done):** rename + greenfield rebuild on the Learning template (Next 16 /
  React 19 / Tailwind v4 static export; FastAPI + stdlib sqlite3; self-contained).
  Board room fully working; `Screens/Agents/AI_Agents/` seeds 21 role-stub
  profiles (`Agent_Head` first); RUNS = honest stub; `rooms`/`messages` schema in
  place; `POST /agents/{name}/ask` ships as `{"state":"pending"}`. Main Menu label
  + nav glyph updated. No LLM.
- **V2:** real AI agents in `AI_Agents/`, DM rooms, OmniRoute wiring (`complete` /
  `summarize` over `127.0.0.1:8003`), per-agent model sets, routing, live RUNS.
  Ties to P11 / P2. Mines repo-root `Agents/` + `Shared_By_All_Agents/` (left
  untouched by V1) for reuse.
- **V3:** board × agents ("pick an ENH-n → ask an agent"). Optional.
- **Chambers (pixel V1.5, frontend-only):** turn the flat D12 `ZoneFrame`
  zones into 6 distinct furnished 3D rooms on one connected pan/zoom/click-focus
  plan — one room *type* per main agent (server room / trading floor / library /
  war room / lounge) + a lobby reception for `Agent_Head`. Adds a bottom-left
  `TaskBrief` panel. Spawn/brief stay SSE-only (no backend change, keeps D12.1).
  Brief: `.scratch/agents-chambers/QWEN_BUILD_PROMPT.md` (+ `map.md`, 7 turns +
  gate). Decisions C1–C6 in that map. Status: brief written 2026-09-01, not yet
  built.
- Build: Qwen 3-Max, one unit per turn, backend/frontend alternating, each gated.

## P4 — Stack migration: Python/FastAPI → Node.js + Express
- **Status:** queued
- Per Rule 3. Migrate one screen at a time (Main Menu, Finance, Learning,
  Enhancement), keeping ports and the plain-page fallback behaviour.

## P5 — Finish the Anime removal in the optional framework UIs
- **Status:** queued
- The plain HTML/JS Main Menu is clean. Give the Next.js and Svelte Main Menu
  variants a full pass for any layout gaps left by removing the Anime *card*.
- Note (2026-08-30): the Anime *screen* (`Screens/Anime/`, Node/Express + Vite
  React client, port 8006) was **restored locally** from the old checkout at the
  user's request — it is **gitignored** (`Screens/Anime/` in `.gitignore`), never
  on GitHub. It reappears in the Main Menu via normal screen discovery. This P5
  is only about the removed dashboard *card*, not the screen.

## P6 — Replace the example Learning seeds
- **Status:** queued
- `manage_study_topics.py`, `seed_the_week_plans.py`, and `manage_recall_cards.py`
  ship generic example content. Swap in a real plan, or make the seeds load from
  the private (Google Drive) layer once P-drive lands.

## P7 — Google Drive private storage layer
- **Status:** in progress (2026-08-31) — full spec is
  [`immediate_plan.md`](immediate_plan.md) Phase 5 (storage seam API, MCP
  transport, RAG, AI-trader seam). House brief written:
  [`.scratch/drive-storage/QWEN_BUILD_PROMPT.md`](.scratch/drive-storage/QWEN_BUILD_PROMPT.md)
  (map + turn plan: `.scratch/drive-storage/map.md`); decisions **D11–D11.4** in
  `AGENTS.md`. Next: paste the brief into Qwen 3-Max, turn by turn; the
  needs-Drive half of the gate waits on the user's Google setup (README_SETUP).
- In short: one storage seam (`read_doc`/`write_doc`/`list_docs`/`delete_doc`/
  `search`) → adopted Node.js **Google Drive MCP server** (app is the MCP client)
  → RAG extending `add_and_search_the_knowledge_base.py` → AI-trader seam stub.
  Goal: nothing personal on local disk.
- Build track: Qwen 3-Max writes the code from a house-style brief; Claude
  validates + wires in (gateway runner, `Start_Everything.bat`, ports snapshot,
  menu glyph rebuild).

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
