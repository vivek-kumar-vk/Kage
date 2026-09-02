# PLAN

The single source of truth for everything **not yet done**. One ordered backlog, one
item at a time. Design rules live in [`AGENTS.md`](AGENTS.md); this file replaced
`WAYFINDER.md`, `PLANNED_WORK.md`, `immediate_plan.md` and `details` (2026-09-02).

Rule (`AGENTS.md` Rule 6): anything named as "later" lands here **and** as a card in
the AGENT DECK board. When an item ships, delete it from this file — shipped work is
recorded in git history and `AGENTS.md` decisions, not here.

Status: `queued` | `in progress` | `parked`.

---

## Active order

| # | Item | Status |
|---|------|--------|
| 1 | Finance data migration / backfill | **in progress** (user-led) |
| 2 | Google Drive private storage layer | **in progress** (Qwen-led, parallel) |
| 3 | Wire finance-os agents through OmniRoute | queued |
| 4 | AGENT DECK chambers (pixel V1.5) + V2 | queued |
| 5 | Replace the example Learning seeds | queued |
| 6 | finance-os Overview follow-ups | queued |
| 7 | Observability on every tab | queued |
| 8 | Remove `Shared_By_All_*` | queued |
| 9 | Python/FastAPI → Node + Express | queued |
| 10 | Anime-removal cleanup in framework UIs | queued |
| 11 | dsh local-model observability | parked |

Items 1 and 2 run in parallel (different hands). Everything else is sequential.

---

## 1 — Finance data migration / backfill  *(user-led, ACTIVE)*

Port the already-solved CAS parsing (`casparser`), market data (mfapi.in / AMFI /
yfinance), tax + planning rules and ISIN↔AMFI mapping from the old `Screens/Finance`
UI, and backfill transactions into `finance-os/backend`'s `finance.db`.

**Inputs / briefs**
- `finance-os/finance-datamigration.md` — detail (gitignored; PII, local only).
- `.scratch/finance-os-port/QWEN_PORT_PROMPT.md` — the port brief.
- `.scratch/finance-os-port/APPLY_PLAN.md`, `COLLECTED_ANSWERS.md` — decisions Q1–Q12,
  locked 2026-08-31.
- `qwen_agent_port/1_PORT_PROMPT.md` + `2_`–`5_` old-code extracts (gitignored).

**Still needed from you**
- Figures: `Screens/Finance/Reference_Data/Human_Checklists/What_To_Fill_In.txt`
  (term life, EPF, Slice balance, salaried-vs-self-employed, dependants, debt ledger,
  expenses, brokers, tax year).
- Decisions owed: **Q10** (finance AI agent + cloud LLM routing), **Q11** (port vs
  rebuild), **Q12** (OmniRoute before or after the migration).

**Why it blocks other things:** `lots` is empty, so finance-os XIRR is `null` and the
portfolio-value history is flat; `goals` is empty, so the Monte-Carlo path is
unexercised. Both fill in from this migration, not from UI work.

---

## 2 — Google Drive private storage layer  *(Qwen 3-Max writes the code, ACTIVE)*

Goal: **nothing personal on local disk.** Reads and writes both go through to Google
Drive, into the right folder.

**Brief written 2026-08-31:** `.scratch/drive-storage/QWEN_BUILD_PROMPT.md`
(+ `.scratch/drive-storage/map.md`, turn plan). Decisions **D11–D11.4** in `AGENTS.md`.
**Next:** paste the brief into Qwen 3-Max, turn by turn; Claude validates and wires in
(gateway runner, `Start_Everything.bat`, ports snapshot, menu glyph). The needs-Drive
half of the verify gate waits on your Google setup (README_SETUP).

**Spec (was `immediate_plan.md` Phase 5)**

- **One storage seam** — a single module every screen's persistence funnels through
  (`read_doc` / `write_doc` / `list_docs` / `delete_doc` / `search`), logical-path
  addressed. Replaces the scattered inline `json`/`csv` helpers in each screen's
  `Calculations/` modules.
- **Transport** — the app is an MCP *client* to an adopted open-source (Node.js) Google
  Drive MCP server. The server runs as its own process the app connects to — **Inky
  never spawns an MCP server** (house rule). Config in a repo-tracked
  `mcp_servers.json`; the Google service-account credential stays in a gitignored file.
  Portable: laptop now, a phone host later.
- **RAG / smart retrieval** — extend the existing
  `Shared_By_All_Screens/add_and_search_the_knowledge_base.py` pattern (local
  embeddings + cosine + sourced Markdown notes) so retrieval returns exactly the source
  docs a query needs. Add chunk overlap and a real index when the corpus outgrows a few
  thousand rows.
- **AI-trader hook (seam only)** — a future trader reads portfolio state via
  `build_the_portfolio_review.read_review()` and market data via the
  `Screens/Finance/Calculations/Shared_Market_Data/fetch_*` modules, pulls context
  through the retrieval layer, and writes decisions to a new append-only ledger. It must
  live in its own screen/agent — the Finance screen's rule against recommending buy/sell
  stays.

---

## 3 — Wire the finance-os agents through OmniRoute

Small adapters over `/v1/chat/completions` on `127.0.0.1:8003` with `GATEWAY_API_KEY`.
Supervisor needs `complete(question, context) -> str`; specialists need
`summarize(payload) -> str`. Model choice stays a gateway routing decision, not code.

**Blocked on** Q10 and Q12 from item 1. Gateway itself is already configured and live
(`AGENTS.md` D6/D6.1/D6.2, `Screens/Model/GATEWAY_CONFIG.md`).

---

## 4 — AGENT DECK: chambers pass, then V2

`Screens/Agents/` (port 8004, `MENU_LABEL="AGENT DECK"`). V1 shipped 2026-08-30; the
D15 2D pixel-art office replaced the 3D stage 2026-09-02.

- **Chambers (pixel V1.5, frontend-only) — brief written 2026-09-01, not built.**
  Turn the flat zones into 6 distinct furnished rooms on one connected pan/zoom/
  click-focus plan — one room *type* per main agent (server room / trading floor /
  library / war room / lounge) + a lobby reception for `Agent_Head`. Adds a bottom-left
  `TaskBrief` panel. Spawn/brief stay SSE-only, no backend change (keeps D12.1).
  Brief: `.scratch/agents-chambers/QWEN_BUILD_PROMPT.md` (+ `map.md`, decisions C1–C6,
  7 turns + gate). Reference art: `Agent-idea.png`.
- **V2 — real AI agents.** Live agents in `Screens/Agents/AI_Agents/` (21 role stubs
  today), DM rooms, OmniRoute wiring (`complete` / `summarize`), per-agent model sets,
  routing, live RUNS. Ties to items 3 and 8. Mines repo-root `Agents/` +
  `Shared_By_All_Agents/` (untouched by V1) for reuse.
- **V3 (optional)** — board × agents: pick an `ENH-n`, ask an agent.
- **Build method:** Qwen 3-Max, one unit per turn, backend/frontend alternating, each
  gated. Apply harness: `Stage_agents/apply_new.ps1` + `watch.ps1`.

---

## 5 — Replace the example Learning seeds

`manage_study_topics.py`, `seed_the_week_plans.py` and `manage_recall_cards.py` ship
generic example content. Swap in a real plan, or make the seeds load from the Drive
layer once item 2 lands. Canonical Learning surface is `Screens/Learning/`
(`AGENTS.md` D8); ongoing topic upkeep is
[`LEARNING_SEED_MAINTAINER.md`](LEARNING_SEED_MAINTAINER.md) → `seed_local.json`.

*Deferred idea:* a time-agent that learns your time-spending pattern, finds gaps and
coaches time management — likely a 4th Learning tab.

---

## 6 — finance-os Overview follow-ups

The Aurum rebuild shipped 2026-09-02 (`AGENTS.md` D13/D13.1-3,
`finance-os/DECISIONS.md` FD5+FD6). Left open:

- Interactive month selector in the header — the pill is display-only today.
- SMS import pipeline, so `sms_last_import` stops going stale by hand.
- Benchmark comparison on the net-worth ridge (index line behind the actual).
- **One manual check owed:** the three.js net-worth ridge was never watched running.
  Automated Chrome reports `visibilityState: hidden` (freezes `requestAnimationFrame`)
  and `prefers-reduced-motion: reduce`, so only the SVG fallback was verified. The
  WebGL path, its draw-in and drag-to-tilt need one look in a normal window.

---

## 7 — Observability on every tab

On each tab (Finance, Learning, AGENT DECK, Model, Main Menu), pick one existing block
and replace it with an observability feature: live health, request/latency, error feed,
or a trace view for that screen. Each block is self-contained per Rule 4 — it reads its
own screen's data directly, no shared module.

---

## 8 — Remove `Shared_By_All_Agents/` and `Shared_By_All_Screens/` entirely

End state: both directories gone (`AGENTS.md` Rule 5). Every currently-shared function
moves into the single screen/agent that uses it; genuinely multi-consumer logic is
duplicated per consumer, not shared.

Sequence: inventory each shared file's callers → inline and delete the single-caller
files → copy the multi-caller ones into each caller, then delete → keep the app booting
after each file.

Known heavy pieces: `read_and_write_numbers.py` (the noticeboard),
`add_and_search_the_knowledge_base.py`, `trace_every_action.py`, `the_lease_board.py`,
`read_screen_settings.py`.

---

## 9 — Stack migration: Python/FastAPI → Node.js + Express

Per `AGENTS.md` Rule 3. One screen at a time (Main Menu, Finance, Learning, Agents),
keeping ports and the plain-page fallback behaviour.

---

## 10 — Finish the Anime removal in the optional framework UIs

The plain HTML/JS Main Menu is clean. Give the Next.js and Svelte Main Menu variants a
full pass for layout gaps left by removing the Anime *card*.

Note: the Anime *screen* (`Screens/Anime/`, Node/Express + Vite React, port 8006) was
restored locally 2026-08-30 and is **gitignored** — never on GitHub. It reappears in the
Main Menu via normal screen discovery. This item is only about the removed dashboard
card, not the screen.

---

## 11 — dsh local-model observability  *(parked)*

Run the local coder model inside DeepSeek Harness for a step-by-step web UI.
Plan: `.scratch/dsh-local-model/PLAN.md`. Blocked on: no local adapter. The resume
trigger ("after the finance redesign") is now met — unpark when items 1–2 clear.

---

## Reference material kept on disk

| Path | What it is |
|------|-----------|
| `.scratch/drive-storage/` | Item 2 build brief + turn map (paste-ready for Qwen) |
| `.scratch/agents-chambers/` | Item 4 chambers brief, map, design HTML, current code snapshot |
| `.scratch/finance-os-port/` | Item 1 port brief, apply plan, locked answers |
| `.scratch/dsh-local-model/PLAN.md` | Item 11 plan |
| `.scratch/agents-workspace/` | AGENT DECK V1 brief — shipped; kept as the house-style template |
| `.scratch/finance-os-build/` | finance-os V1 phase specs + gate scripts — shipped; gates reusable |
| `.scratch/finance-redesign/` | Aurum mockups + PNGs the Overview was built against |
| `.scratch/finance-telemetry/HARNESS.md` | Shared local-model run harness |
| `.scratch/lm-ui-gaps/` | Local-model UI-gap ledger + prompt contract |
| `.scratch/model-page-gateway/` | OmniRoute gateway wayfinder + issues — shipped |
| `.scratch/_archive/` | Superseded passes (finance realism F1, telemetry skin, LiteLLM) |
| `qwen_agent_port/` | Item 1 old-code extracts (gitignored) |
| `Stage_agents/` | Qwen turn-apply harness for item 4 |

---

## Dropped

- **Wire Finance telemetry panels to live endpoints** (old P8). Targeted
  `Screens/Finance/Page/next_app/`, which `finance-os/` V1 replaced. finance-os owns
  Finance data wiring now.
- **Finance realism pass, F1 two-livery** (old P9). Built (`5b72750`), then superseded
  by the finance-os V1 cutover (`657774d`). See `AGENTS.md` D7.
- `finance-os-master-plan-final.md`, `learning-tab-plan.md`, `wire-screens-plan.md` —
  deleted; the work shipped.
