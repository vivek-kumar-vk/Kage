# PLAN

The single source of truth for everything **not yet done**. One ordered backlog, one
item at a time. Rules live in [`CLAUDE.md`](CLAUDE.md), numbered decisions in
[`AGENTS.md`](AGENTS.md). This file replaced `WAYFINDER.md`, `PLANNED_WORK.md`,
`immediate_plan.md` and `details` (2026-09-02) and absorbed `TOMORROW.md` (2026-09-03).

Rule (`CLAUDE.md` Rule 10): anything named as "later" lands here **and** as a card in
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
| 6 | finance-os Overview follow-ups | queued |
| 7 | Observability on every tab | queued |
| 8 | Remove `Shared_By_All_Screens/` — mostly done 2026-09-03 | queued |
| 9 | Python/FastAPI → Node + Express | queued |
| 10 | Anime-removal cleanup in framework UIs | queued |
| 11 | dsh local-model observability | parked |
| 12 | Learning OS rebuild (D16): Ember Studio UI + agent crew | **in progress** |
| 13 | Investments end-to-end (Analyse / Analysis / Trade Desk / market MCP) | **shipped 2026-09-02** — residue tracked below |
| 14 | Calendar card (D23): Google Calendar + agent + WakaTime | **in progress** |

Items 1, 2 and 12 run in parallel . Everything else is sequential.

### Next up (folded in from `TOMORROW.md`, 2026-09-03)

In order. Hours are focused build hours; **you** marks a step only the owner can do.

**A — Storage seam + RAG (item 2), 9-13 h.** Nothing personal on local disk.
**you** Google setup (project, Drive API, service account key into the gitignored
path, folder shared) ~30 min -> adopt the Node Drive MCP as its own process
(`mcp_servers.json`; Kage never spawns one) -> the seam
(`read_doc`/`write_doc`/`list_docs`/`delete_doc`/`search`, logical paths) -> RAG on
top (chunk+overlap, `nomic-embed-text`, cosine, sourced Markdown) -> honest
"Drive unreachable" everywhere -> wire into the launcher, port snapshot, menu glyph.
Brief: `.scratch/drive-storage/QWEN_BUILD_PROMPT.md` + `map.md`; decisions D11-D11.4.

**B — Finance data into Drive, pulled back live (items 1 + 13 residue), 9-13 h.**
Depends on A; starting early writes the data twice. **you** re-import the CAS PDF
(Investments -> IMPORT CAS PDF) -> rebuild `lots` from `my_investments.csv` units
(root cause: `backfill_from_old_records.py` §3 calls `upsert_holding(mode="set_snapshot")`;
only `mode="add_lot"` writes a lot — this one fix unblocks null XIRR *and* the flat
net-worth ridge) -> move the finance corpus to Drive -> finance-os reads through the
seam, not the filesystem -> index the corpus into RAG -> verify in a browser.
Still owed by you: `Screens/Finance/Reference_Data/Human_Checklists/What_To_Fill_In.txt`
(term life, EPF, Slice balance, dependants, debt ledger, expenses, brokers, tax year)
and decisions Q10 / Q11 / Q12.

**C — Repo hygiene. Done 2026-09-03.** Rules rewritten for Claude-only into
`CLAUDE.md`, project memory written, ports fixed, ~430 MB of dead trees deleted,
the unrunnable root agent layer removed, and the Finance app moved under its own
screen. Decisions D21 through D21.5.
Remaining from this block: seed the four "two runtimes, one launcher" Learning rooms
from D21.1 (~1 h, part of item 12).

### Rough hours on the rest

| # | Item | Hours |
|---|------|-------|
| 3 | Wire finance-os agents through OmniRoute (blocked on Q10/Q12) | 2-3 |
| 4 | AGENT DECK V2 — real agents, runs table, DM rooms, TaskBrief | 8-12 |
| 6 | finance-os Overview follow-ups (month selector, benchmark line, SMS import) | 4-6 |
| 7 | Observability on every tab (5 screens) | 8-12 |
| 8 | Delete `Shared_By_All_*` entirely | 6-10 |
| 9 | Runtime choice per service — rescoped by D21.1 | ~0 |
| 10 | Anime-removal cleanup in the Next/Svelte menu variants | 1-2 |
| 11 | dsh local-model observability (parked) | 4-6 |
| 12 | Learning M6 — THM lab, day template, Planner rebalance | 6-8 |
| 12 | Learning M7 — OFFICE screen (:8008), job hunt | 8-12 |
| 12 | Learning M8 — crew live on OmniRoute (gated on real data) | 10-14 |
| 12 | Room content: 101 rooms have 0 steps, 0 cards | 2-3 + your reading |

Whole backlog: roughly **80-120 focused hours** (was 110-170 before D21.1 rescoped
item 9). Estimates assume Claude writes and verifies, the owner reviews and answers
the blocking questions; they exclude the CAS import, the owner's figures, the Google
setup, and the hours spent actually studying the Learning rooms.

---

## 1 — Finance data migration / backfill  *(user-led, ACTIVE)*

**Brief written 2026-09-02** for the part that needs no input from you:
`.scratch/glm-briefs/2_FINANCE_backend_lots_history.md`. Measured state — `transactions`
112, `holdings` 10, `price_history` 27 095 (full daily NAV, all 10 symbols, back to
2006); `lots` 0, `goals` 0, `benchmarks` 0. `lots` is empty because
`backfill_from_old_records.py` §3 calls `upsert_holding(mode="set_snapshot")`, and only
`mode="add_lot"` writes a lot — that is the single root cause of the null XIRR *and* the
flat ridge (`backfill_snapshots.py` values history from `lots`). Units are already
recorded per-transaction in `my_investments.csv`, so lots are rebuildable without you.
Goals still need your figures.

Port the already-solved CAS parsing (`casparser`), market data (mfapi.in / AMFI /
yfinance), tax + planning rules and ISIN↔AMFI mapping from the old `Screens/Finance`
UI, and backfill transactions into `Screens/Finance/Backend/app`'s `finance.db`.

**Inputs / briefs**
- `Screens/Finance/finance-datamigration.md` — detail (gitignored; PII, local only).
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

- **Warm Pix-Agents + Agent Deck UI — SHIPPED 2026-09-02** (`AGENTS.md` D18/D19):
  warm retheme of the whole screen (no dark surfaces), open-wall floor with the
  spawn/walk/work/leave lifecycle, up-to-3 clouds and ambient life, and the
  pixel-skinned Agent Deck (rail / 1:1 chat / profile drawer with the FILES editor +
  DM persistence). The V2 brief below is unchanged and still next.
- **Chambers — SHIPPED in 2D, not as briefed.** The D15 commit `c2cad1a` built the six
  furnished chambers on one connected pan/zoom/click-focus plan in a 2D canvas
  (`PixelOffice.tsx` + `roomPlan.ts`), superseding the three.js `Chamber.tsx` /
  `furniture.tsx` design in `.scratch/agents-chambers/QWEN_BUILD_PROMPT.md` — that brief
  is **obsolete**. The only piece of it never built is the bottom-left `TaskBrief`
  panel, now folded into the V2 brief below.
- **V2 — real AI agents.** Brief written 2026-09-02:
  `.scratch/glm-briefs/1_AGENT_DECK_v2_groundwork.md` (+ `__CONTEXT.md`). Turns the
  `ask_agent` stub into a real OmniRoute call (`services/omni.py` is already complete),
  adds a `runs` table + RUNS panel, DM rooms, per-agent model pinning via new optional
  `office.json` keys, and the leftover `TaskBrief` panel. 26 agent profiles today.
  Does **not** need Q10/Q12 — those govern the *finance-os* agents (item 3), not this
  screen's gateway, which is already live. Ties to items 3 and 8. (The repo-root
  `Agents/` + `Shared_By_All_Agents/` reuse pool this used to point at was deleted
  2026-09-03 — it could not run; see the decision log.)
- **V3 (optional)** — board × agents: pick an `ENH-n`, ask an agent.
- **Responsive polish (owner-led, later; ENH-19).** D18.7 made the floor
  re-layout per viewport (fixed 140×128 zones, flex walkways, camera clamped to
  the plan — no scroll, no backdrop). Owner accepted the current rendering on
  his 1920×1080 laptop and took the remaining polish himself: on short
  viewports (canvas under ~790 px tall) the integer scale drops to 2× and rooms
  read small in wide corridors; very small windows crop the plan edge.
- **Build method:** Claude, as with everything else since 2026-09-03.

---

## 6 — finance-os Overview follow-ups

The Aurum rebuild shipped 2026-09-02 (`AGENTS.md` D13/D13.1-3,
`Screens/Finance/DECISIONS.md` FD5+FD6). Left open:

- Interactive month selector in the header — the pill is display-only today.
  **Brief written 2026-09-02:** `.scratch/glm-briefs/3_FINANCE_frontend_overview.md`.
- Benchmark comparison on the net-worth ridge (index line behind the actual).
  Same brief; the `GET /api/finance/market/benchmark` contract is frozen there and built
  by the item-1 backend brief.
- SMS import pipeline, so `sms_last_import` stops going stale by hand. **Not briefed** —
  needs your SMS export format first.
- **One manual check owed:** the three.js net-worth ridge was never watched running.
  Automated Chrome reports `visibilityState: hidden` (freezes `requestAnimationFrame`)
  and `prefers-reduced-motion: reduce`, so only the SVG fallback was verified. The
  WebGL path, its draw-in and drag-to-tilt need one look in a normal window.

---

## 7 — Observability on every tab

On each tab (Finance, Learning, AGENT DECK, Model, Main Menu), pick one existing block
and replace it with an observability feature: live health, request/latency, error feed,
or a trace view for that screen. Each block is self-contained per `CLAUDE.md` Rule 5 — it reads its
own screen's data directly, no shared module.

---

## 8 — Remove `Shared_By_All_Screens/` entirely

End state: both directories gone (`CLAUDE.md` Rule 6). Every currently-shared function
moves into the single screen/agent that uses it; genuinely multi-consumer logic is
duplicated per consumer, not shared.

Sequence: inventory each shared file's callers → inline and delete the single-caller
files → copy the multi-caller ones into each caller, then delete → keep the app booting
after each file.

Known heavy pieces: `read_and_write_numbers.py` (the noticeboard),
`add_and_search_the_knowledge_base.py`, `trace_every_action.py`, `the_lease_board.py`,
`read_screen_settings.py`.

---

## 9 — Runtime choice per service  *(rescoped by D21.1 — no longer a migration)*

**Not a migration any more.** Per `CLAUDE.md` Rule 4 / D21.1 each service keeps the
runtime whose libraries its work lives in: Python/FastAPI for finance-os, RAG, the
Learning backend and the Main Menu; Node/Express for the Agent Deck's SSE fan-out,
Anime and the MCP servers. Nothing is rewritten for the sake of its language. What is
left of this item is only the discipline — every cross-language call stays on HTTP,
and no service imports across the line.

---

## 10 — Finish the Anime removal in the optional framework UIs

The plain HTML/JS Main Menu is clean. Give the Next.js and Svelte Main Menu variants a
full pass for layout gaps left by removing the Anime *card*.

Note: the Anime *screen* (`Screens/Anime/`, Node/Express + Vite React, port 8006) was
restored locally 2026-08-30 and is **gitignored** — never on GitHub. It reappears in the
Main Menu via normal screen discovery. This item is only about the removed dashboard
card, not the screen.

---

## 11 — Repoint the Hermes fleet off the dead local endpoint

*(Supersedes "dsh local-model observability", parked 2026-08-29. Unparked and
mostly shipped 2026-09-03 — decisions D24, D25. The blocker it was parked on,
"no local adapter", was never real: `dsh-llm-pi-ai` takes hand-declared
OpenAI-compatible providers, so the harness reaches the gateway with no adapter
written. `.scratch/dsh-local-model/PLAN.md` is now history, not a plan.)*

What shipped: the Deepseek screen (8007) over `dsh`, the Hermes screen (8008)
over the profile fleet, and an `omniroute` provider declared in both tools'
configs pointing at the gateway on 8003.

What is left: **all 15 Hermes profiles still name `local-model-a` @
`localhost:8080`** — a llama-server that is not running and, per the user, not
coming back. Each profile's `model:` block needs repointing to
`provider: omniroute`. Deliberately not done in bulk: repointing fifteen agents
changes what every one of them costs and how it behaves, so it is a decision per
profile, not a side effect of wiring (D25.1).

Also open: only three DeepSeek routes on the gateway actually answer
(`cfp/deepseek-ai/…`); the `-free` route reports "Model is unavailable" upstream
and the `opencode/` ones return 402. If that changes, the model lists in both
`install_*_provider.py` scripts want revisiting.

---

## 12 — Learning OS rebuild  *(D16 + D17, ACTIVE)*

**D16 (shipped 2026-09-02):** M0–M3 — Ember Studio shell, schema v2, dynamic Path,
Today/Focus Session, Room player (4-beat steps, checkpoints), Recall/Card Studio
(SM-2), INSIGHTS tab, crew shell (roster/SSE feed/proposals on sample data).

**D17 v3 — "real-life pass", now ACTIVE.** The owner's corpus (14-week plan, Master
Context, resume) enters the system; all demo history wipes to an honest zero; two
ground-0 tracks (Project → DevOps ∥ Observability job-driven, detection track
dissolved into both); TryHackMe becomes the daily standing lab; a new OFFICE screen
tracks the job hunt; the crew goes live on OmniRoute. Plan + milestones:
`.scratch/learning-redesign/PLAN_V3.md`; decisions **D17–D17.8** in `AGENTS.md`.
Absorbs old item 5 (the example seeds are replaced by the D17 re-seed).

- **M5** context in + honest zero + board re-seed — *SHIPPED 2026-09-02: three
  corpus docs stored verbatim in gitignored `Screens/Learning/Context/` with an
  allowlisted read router; demo history wiped (`learning.db.bak-preD17` kept);
  board re-seeded as two ground-0 tracks (68 rooms, empty steps — "planned, not
  taught"); card reveal parts relabeled to his 5-part format; 6 pytest tests on a
  temp DB (`Backend/tests/test_honest_zero.py`)*
- **M6** TryHackMe standing lab (`lab_url`, `source` tags, streak line on Today) +
  day-template settings + weekly ledger-driven Planner rebalance + interview-day
  preemption
- **M7** OFFICE screen v1 (:8008) — applications pipeline, interview prep, work
  log, machine-enforced resume-defensible flag (≥2 Good/Easy ratings)
- **M8** Crew live on OmniRoute (Planner/Quizmaster/Tutor/Auditor) + SIGNAL
  verification queue + THM Scout + Office agents (PII → local models only) +
  per-agent token/cost discipline — **GATED (owner 2026-09-02): plan only until
  the real data is wired; where testing is needed, test on dummy data (tests
  only, never the DB)**
- Deferred cards (ENH-n on the AGENT DECK board): agents drafting full lesson
  content (digests + card minting ship in M8); Storage-seam note sync; progress
  backup; release-radar for the project stack; JD-skill radar feeding the Planner;
  interview-question radar → Quizmaster; preference learning from verification
  choices; time-pattern coach (old item 5 idea); Warden/Quill live. **Never:**
  auto-applying to job portals.

---

## 13 — Investments end-to-end  *(SHIPPED 2026-09-02 — decisions D20, finance-os FD7)*

Built and verified live in one session, before the Sept-4 salary: the rebuilt
Investments tab (single Analyse action, value ridge, SIP rhythm, CAS-import
button), the per-holding Analyse drawer (Groww reference data: facts, published
portfolio with weights/sectors, returns, risk ratios vs NIFTY 50, peers,
pros/cons, plain-English explainer), the Analysis tab (look-through X-ray + HHI,
pair-overlap heatmap, behaviour, allocation vs targets, cost & tax, fact-based
observations), the Trade Desk tab (WATCHLIST / JOURNAL / IPO / GLOBAL), the
market-data MCP server (`Start_Inky/run_market_mcp.py`, :3101/mcp) for the Agent
Deck research agents, and Learning-tab removal from finance-os. Static export
re-built and served. Residue:
- **User step:** re-import the CAS PDF via Investments → IMPORT CAS PDF — fills
  `lots`, XIRR and the unrealised STCG/LTCG buckets (the UI is ready; the old
  CAS carried no transaction history). Pairs with item 1's lots rebuild.
- Two Groww pages unresolved (100900 HDFC Children's, 120760 UTI Multi Asset) —
  sheets show honest `pending`; add a slug override in
  `services/fund_reference.py` `MANUAL_OVERRIDES` when the page is found.
- Market-cap split not shown (needs per-stock facts; never guessed).
- AMFI NAVAll.txt retires 2026-09-30 (old format): mfapi stays primary — watch
  for a parser-only change if the fallback is ever needed.
- Agent Deck V2 (items 3/4): point the research agents' tool loop at
  `127.0.0.1:3101/mcp` (tools already live).

---

## Reference material kept on disk

| Path | What it is |
|------|-----------|
| `.scratch/drive-storage/` | Item 2 build brief + turn map (paste-ready for Qwen) |
| `.scratch/glm-briefs/` | The four parallel GLM 5.3 briefs + per-chat context packs (2026-09-02) |
| `.scratch/finance-os-port/` | Item 1 port brief, apply plan, locked answers |
| `.scratch/dsh-local-model/PLAN.md` | Item 11 plan |
| `.scratch/agents-workspace/` | AGENT DECK V1 brief — shipped; kept as the house-style template |
| `.scratch/finance-os-build/` | finance-os V1 phase specs + gate scripts — shipped; gates reusable |
| `.scratch/finance-redesign/` | Aurum mockups + PNGs the Overview was built against |
| `.scratch/finance-telemetry/HARNESS.md` | Shared local-model run harness |
| `.scratch/lm-ui-gaps/` | Local-model UI-gap ledger + prompt contract |
| `.scratch/model-page-gateway/` | OmniRoute gateway wayfinder + issues — shipped |
| `qwen_agent_port/` | Item 1 old-code extracts (gitignored) |

---

## Dropped

- **Wire Finance telemetry panels to live endpoints** (old P8). Targeted
  `Screens/Finance/Page/next_app/`, which the V1 rebuild replaced. That rebuild owns
  Finance data wiring now.
- **Finance realism pass, F1 two-livery** (old P9). Built (`5b72750`), then superseded
  by the finance-os V1 cutover (`657774d`). See `AGENTS.md` D7.
- `finance-os-master-plan-final.md`, `learning-tab-plan.md`, `wire-screens-plan.md` —
  deleted; the work shipped.
