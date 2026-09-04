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
| 4 | AGENT DECK chambers (pixel V1.5) + V2 | **mostly shipped 2026-09-05** — TaskBrief panel + live-gateway run left |
| 6 | finance-os Overview follow-ups | **mostly shipped 2026-09-05** — SMS import + one manual browser check left |
| 7 | Observability on every tab | **mostly shipped 2026-09-05** — Main Menu panel left (frontend mid-redesign) |
| 9 | Python/FastAPI → Node + Express | queued |
| 11 | dsh local-model observability | parked |
| 12 | Learning OS rebuild (D16): Ember Studio UI + agent crew | **in progress** |
| 13 | Investments end-to-end (Analyse / Analysis / Trade Desk / market MCP) | **shipped 2026-09-02** — residue tracked below |
| 14 | Calendar card (D23): Google Calendar + agent + WakaTime | **in progress** |
| 15 | Day Plan card -> agent-owned: each area's agent (Finance/Learning/Anime/Agents) fetches its real state, plans today, writes rows. Card shipped 2026-09-04 as a hand-kept localStorage checklist (`Main_Menu/.../DayPlanPanel.tsx`); this item is the wiring. | queued |
| 16 | Agent roster expansion: awareness + autonomous-code + job-hunt agents on Muse Spark contributor — 12 profiles added 2026-09-05, none wired | queued (blocked on item 4 V2) |

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
| 9 | Runtime choice per service — rescoped by D21.1 | ~0 |
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

## 2 — Local private storage seam + hybrid RAG  *(ACTIVE — build end-to-end)*

**Pivot 2026-09-04 (D11.5): Google Drive is dropped.** Store on local disk, in a
folder **outside the repo** (`KAGE_DATA_DIR`). Why: the intended host is Termux on
Android — no Node, no Ollama, must run 24/7 — and the Drive-MCP path needed a Node
gateway + a Google service account + OAuth and hit the "service accounts have no
Drive storage quota" wall for a consumer Gmail account. Near-term the **laptop is
the host** and the phone reaches it over LAN (`http://<laptop-ip>:8000`); a
phone-only deploy later just repoints `KAGE_DATA_DIR` to `/sdcard/kage-data`.

Goal is unchanged: **one seam every screen's persistence funnels through**, with a
retrieval layer on top. Only the backend changes — plain files in a folder instead
of MCP-to-Drive. This makes the build markedly smaller (no Node, no `mcp` SDK, no
Google libraries, no `path_map` id-resolution, no gateway process).

Old Drive brief (`.scratch/drive-storage/*`) and decisions **D11–D11.4 / D11.1a**
are **history**; the in-force decision is **D11.5** (+ D11.5.1–.3) in `AGENTS.md`.

### Shape

`Screens/Storage/` — FastAPI on **8009**, `MENU_ORDER 8`, one Status tab,
hand-rolled HTML status page (no Next app).

- **The seam** — `Backend/services/seam.py`: module functions + thin routes,
  `read_doc` / `write_doc` / `list_docs` / `delete_doc` / `search`, logical-path
  addressed (`finance/blueprint.json`, `knowledge/notes/docker.md`,
  `trader/ledger/2026-09-04/143005-001.json`). A logical path **is** a real subpath
  under `KAGE_DATA_DIR`: validate (`^[a-z0-9][a-z0-9._-]*(/…)*$`, ext ∈
  {.md,.txt,.json}, depth ≤ 6, no `..`), then `open()`. `write_doc` = atomic
  (tmp + `os.replace`), `mkdir -p` the parent. `delete_doc` moves to
  `KAGE_DATA_DIR/.trash/<date>/` — recoverable, never annihilation (Rule 8).
  Routes: `GET /api/storage/docs?prefix=`, `GET /api/storage/doc?path=`,
  `PUT /api/storage/doc {path,content}`, `DELETE /api/storage/doc?path=`,
  `GET /api/storage/search?q=` (keyword). RAG + trader call the functions
  in-process, never over HTTP.
- **Hybrid RAG** — `Backend/services/rag.py`. Retrieval = **keyword (SQLite FTS5,
  stdlib) + dense (embeddings) fused** (fusion method — RRF / weighted / rerank —
  from the owner's research today). Sourced Markdown notes at
  `knowledge/notes/<slug>.md` via the seam (frontmatter + inline `**Source:**`
  lines, ported from `add_and_search_the_knowledge_base.py`); sourceless note → 422.
  Chunks 180 words / 20 overlap. Index `Backend/index/rag.sqlite` (FTS5 table +
  chunks table with a JSON vector column) — git-ignored, rebuilt from the notes by
  `reindex` (BackgroundTask).
  - **Embeddings via OmniRoute** (`127.0.0.1:8003`, OpenAI-compatible
    `/v1/embeddings`, reuse `GATEWAY_API_KEY`) — a **free** embedding model, id in
    `.env` as `STORAGE_EMBED_MODEL`. **Not Ollama** (won't exist on the phone).
    Endpoint unreachable / model isn't an embedder → note still saves, search
    returns keyword-only, state `partial`, honest "dense search offline" note.
  - **Sanitizer hook** — `Backend/services/sanitize.py`: `sanitize(text) ->
    (clean, hits)`, rules the owner maintains at `knowledge/_sanitize_rules.json`
    via the seam, run on every chunk **before** it is sent to OmniRoute to embed.
    v1 ships the hook + an empty ruleset; real rules and whether an LLM scrub pass
    is added come after the owner reviews his actual data. Nothing leaves the
    device except embedding inputs, and those are scrubbed.
- **Trader ledger stub** — `Backend/services/trader.py`, unchanged from D11.4:
  append-only, `POST /api/storage/trader/decisions` writes one
  `trader/ledger/<IST date>/<HHMMSS>-<seq>.json` via the seam; `GET` newest-first;
  no update/delete. The trader agent stays unbuilt, in its own screen later.
- **Status page** — STORE panel (data dir, doc count, free space), KNOWLEDGE
  (notes / chunks / topics + a working hybrid-search box), EMBEDDINGS (OmniRoute
  reachable? model? — honest down state), TRADER LEDGER (count + newest, stub
  copy). Distinct loading / empty / error / degraded branches. Utility/terminal
  look, one amber accent, red only for delete.
- **Menu glyph** — add a `storage:` case to `Main_Menu/…/components/TopBar.tsx`
  `GLYPHS` (a drive/box mark), then rebuild `Main_Menu/Page/next_app`.

### Config (repo-root `.env`; `.env.example` updated)

`KAGE_DATA_DIR` (default `~/kage-data`; phone/Termux → `/sdcard/kage-data`),
`STORAGE_EMBED_MODEL` (free embedder routed on OmniRoute), reuse `GATEWAY_API_KEY`.
No Google keys.

### Build phases (all this pass)

1. Contract files — `screen_definition_for_storage.py`, `settings_for_storage.py`
   (`_env` loader + `KAGE_DATA_DIR`), `Setup/requirements_for_storage.txt`
   (`fastapi`, `uvicorn[standard]`, `pydantic` — nothing else), `.gitignore`
   (`Backend/index/`), README.
2. `seam.py` — path validation, atomic write, `.trash`, the 5 routes; `server_for_
   storage.py` boots on 8009 with no data dir yet (creates it).
3. `db.py` + `rag.sqlite` schema (FTS5 + chunks) + honest-zero seed (2 generic
   sourced notes, guarded/idempotent).
4. `rag.py` — note CRUD via seam, chunk+overlap, FTS5 keyword, embeddings client
   (OmniRoute), hybrid fusion, `reindex`, sanitizer hook.
5. `trader.py` — append-only ledger.
6. Status page — every panel, real states.
7. Glyph in `TopBar.tsx` + Main-Menu rebuild; regenerate `ports_for_inky.json`.
8. Verify: boots on 8009 with OmniRoute down (keyword-only, honest, no traceback);
   PUT/GET/LIST/DELETE round-trip on disk + `.trash`; note+source → hybrid search
   returns it; `reindex` rebuilds to the same counts; trader POST lands on disk;
   STORAGE row at menu position 8; `grep -R "Shared_By_All\|googleapi\|mcp\b"
   Screens/Storage/` empty.

### Consumers (own follow-ups, not this item)

finance-os and Learning stop writing their own scattered local files and persist
through the seam — one place, one backup point. **Finance is the first real user:**
salary transactions from 2026-09-04 on should land via the seam from day one.

### Open — owner researching today

- Hybrid fusion method (RRF vs weighted vs add a reranker) and **which free
  OmniRoute model is an actual embedder**.
- Sanitizer rules + whether an LLM scrub pass earns its cost — after the data review.
- **Backup:** local disk is the only copy today. A periodic export (zip → Drive /
  SD card / another box) is a later PLAN item.

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
- **V2 — real AI agents. Mostly shipped 2026-09-05 (D27–D27.5).** `ask_agent` is a
  real OmniRoute call through one shared ask path (`/ask`, the DM composer, and
  agent-kind rooms all use it); a `runs` table backs a live RUNS panel in
  `/workspace`; per-agent model pinning is two optional `office.json` keys
  (`model`/`models`) plus `GET /api/agents/models`; `AgentChat.tsx` renders real
  replies and honest gateway-down errors inline. Verified live: gateway down →
  the exact "OmniRoute unreachable…" sentence in the chat and in `runs`, no
  fabricated reply; `npm run build` clean; `package.json`/lock untouched;
  `Shared_By_All`/`httpx`/SDK greps clean; changes confined to `Screens/Agents/`.
  **Left from the original brief** (`.scratch/glm-briefs/1_AGENT_DECK_v2_groundwork.md`,
  now superseded by D27.4's scope note): the bottom-left **TaskBrief** panel — the
  one D15-chambers piece never built — since the brief assumed a root-page chat
  panel that doesn't exist; and a real-gateway-up end-to-end run (only the
  gateway-down path was exercised this pass — OmniRoute wasn't started to avoid
  generating fresh gateway secrets mid-autonomous-run). 26 agent profiles today
  (34 once item 16's twelve are counted, still inert). Ties to items 3 and 8.
- **V3 (optional)** — board × agents: pick an `ENH-n`, ask an agent.
- **Twelve new agent profiles landed 2026-09-05** — awareness (Context Engine,
  Time Analyst, Pattern Learner, Focus Guard), autonomous code (UI Builder, Code
  Explainer, Bug Fix, Regression Watcher) and job hunt (Job Research, Resume,
  Interview Prep, Application Tracker — these four belong to item 12's OFFICE
  screen). Folders + `office.json` only; none run until V2 above turns
  `ask_agent` into a real call, and the per-agent model key they'll need is V2's
  to introduce. Scope, data sources, the Muse Spark contributor decision and what
  each one is *not* allowed to do: **item 16**.
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
`Screens/Finance/DECISIONS.md` FD5+FD6).

- **Interactive month selector + benchmark ridge overlay — shipped 2026-09-05
  (D28-D28.4).** Brief: `.scratch/glm-briefs/3_FINANCE_frontend_overview.md`.
  The header pill is a real accessible dropdown scoped to Overview only,
  reading its month list off `net-worth`'s own `trend` (never an arithmetic
  range); the scope lives in `?month=` in the URL. `NetWorthCard` genuinely
  scopes to a past month (hero, deltas, truncated ridge, projection hidden);
  every other Overview card appends `?through=` and shows an honest
  "AS OF \<month\> — not yet historical" marker, since the backend doesn't
  support it yet. The ridge's benchmark line (Nifty 50, hardcoded symbol) is
  rebased onto net worth's own scale through one shared normalize call — no
  double-scaling — and renders `NO BENCHMARK LOADED` honestly since
  `GET /api/finance/market/benchmark` (item 1's backend brief) doesn't exist
  on this branch yet; verified live that a 404 there doesn't break the card.
  `npm run build` clean, zero TS errors, `package.json`/lock untouched,
  chart/animation-lib and `Shared_By_All` greps clean, changes confined to
  `Screens/Finance/Page/next_app/`.
  **Not verified this pass** (no browser extension connected during this
  autonomous run): the benchmark line actually drawing once the backend
  endpoint exists, and the three.js WebGL render/draw-in/drag-to-tilt in a
  real window — folds into the manual check below.
- SMS import pipeline, so `sms_last_import` stops going stale by hand. **Not briefed** —
  needs your SMS export format first.
- **One manual check owed:** the three.js net-worth ridge (now with the
  benchmark line) was never watched running. Automated Chrome reports
  `visibilityState: hidden` (freezes `requestAnimationFrame`) and
  `prefers-reduced-motion: reduce`, so only the SVG fallback was verified.
  The WebGL path, its draw-in, drag-to-tilt, and the benchmark overlay (once
  item 1 lands the backend endpoint) need one look in a normal window.

---

## 7 — Observability on every tab

**Mostly shipped 2026-09-05 (D30–D30.5).** Finance (`DataHealthCard` footnote) and
Learning (Insights "Ledger" panel header) each got their own request/error-rate
observability, self-contained per Rule 5 — no shared module, verified live (honest
zero with no traffic, real counts once requests land). AGENT DECK's `RunsPanel`
(item 4) got a stats strip (runs/error-rate/avg-latency) — no backend change needed,
item 4 already built the `runs` table. Model is exempted — it already *is* the
gateway's observability surface. **Left:** Main Menu already has the backend half
(full request trace middleware into the trace ledger, `health_check` dependency
probe, `GET /api/main_menu/live` SSE) — none of it surfaced as a UI panel yet. Not
done this pass because `Main_Menu/Page/next_app/` was mid-redesign (uncommitted
home-page rework) when this item was reached; wire `/api/main_menu/live` into a
small panel once that settles.

---

## 8 — Shrink `Shared_By_All_Screens/` to its irreducible core — closed 2026-09-05 (D31-D31.3)

**Closed as this state, not as an empty folder.** The "known heavy pieces" this item
originally named were already gone: `read_and_write_numbers.py` and `trace_every_action.py`
are single-owner in `Main_Menu/Backend/`; `add_and_search_the_knowledge_base.py` and
`the_lease_board.py` don't exist in the repo. This pass moved `Look_And_Feel/` into
`Main_Menu/Look_And_Feel/` (its one real tracked caller — Finance's reference was dead)
and deleted the dead `LOOK_AND_FEEL`/`FONTS_DIR`/`WATCHED_FOLDERS` lines from
`settings_for_finance.py`; also repointed the gitignored `Screens/Anime/` screen's own
reference (uncommitted, untracked, but a real local dependency a plain grep misses).

**What's left, on purpose:** `read_screen_settings.py`, `restart_signal.py`,
`clear_every_data_cache.py` — imported only by `Main_Menu/Backend/server_for_main_menu.py`
and `Start_Inky/*.py`. Neither caller is a screen; `Start_Inky/` is the launcher, which
Rule 17 already carves out as allowed to know about every screen. Duplicating
`read_screen_settings.py` would reintroduce the exact "two copies of how-do-I-find-the-port"
bug its own docstring exists to prevent. `Current_Numbers/` (the noticeboard) is data, not
logic — the deliberate one channel between screens (ADR-010), not a Rule 6 violation.

---

## 9 — Runtime choice per service  *(rescoped by D21.1 — no longer a migration)*

**Not a migration any more.** Per `CLAUDE.md` Rule 4 / D21.1 each service keeps the
runtime whose libraries its work lives in: Python/FastAPI for finance-os, RAG, the
Learning backend and the Main Menu; Node/Express for the Agent Deck's SSE fan-out,
Anime and the MCP servers. Nothing is rewritten for the sake of its language. What is
left of this item is only the discipline — every cross-language call stays on HTTP,
and no service imports across the line.

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

## 16 — Agent roster expansion: awareness layer + autonomous code agents

Raised 2026-09-05 from two sources: the owner's own agent asks this session, and an
outside "Kage Agent System" draft (Qwen3.8-Max, 2026-09-04) pasted in for sifting.
**Only the parts that fit this repo are below** — what was dropped, and why, is at the
end so it isn't re-proposed. Twelve profile folders exist now
(`Screens/Agents/AI_Agents/*/description.txt` + `office.json`) — eight `deck`/`sub`
under `Deck_Main_Agent`, four `learning`/`sub` under `Learning_Main_Agent`. **None of
them run**: `ask_agent` is still the honest `pending` stub, so this whole item is
blocked on **item 4 V2**. The model they route to is section **D**.

### A — Awareness layer

The load-bearing idea from the draft, and the one thing genuinely missing today: no
agent knows what the owner is *currently doing*, so every planner guesses.

- **`Context_Engine_Agent`** — the collector everything else reads. Polls WakaTime
  (item 14 already brings it in), Google Calendar (D23), `git log --since` today, and
  each screen's own health/activity endpoint; writes one current-state file into the
  Storage seam (item 2 — it owns `KAGE_DATA_DIR`, don't invent a second store).
  **Rule 8 applies hard:** an unreachable source is written as unreachable, never
  silently carried over from the last poll. Build this first; A and B below are
  worthless without it.
- **`Time_Analyst_Agent`** — evening pass: planned blocks vs logged time, writes the
  gap report. Consumes the Context Engine; hands the report to `Day_Planner_Agent`
  (which already writes tomorrow's plan — item 15) rather than planning itself.
- **`Pattern_Learner_Agent`** — weekly: rolling per-time-of-day focus score from
  accumulated gap reports. Needs ~6 weeks of real history before it says anything;
  until then it reports "not enough data", not a guess.
- **`Focus_Guard_Agent`** — one short nudge when current activity has drifted from the
  planned block. Cheap, no LLM needed for the *detection* (a comparison, not a
  judgment); only the wording of the nudge is worth a model call, if that.

**Data source for non-office hours: a custom Pomodoro tracker.** Owner starts/stops a
session by hand (no auto-detection); each session logs start, end, and — v2 — a task
label. Its own small Home card + local table, feeding the four agents above the same
way WakaTime feeds them for office hours. What the agents get out of it: idle gaps
between sessions, sessions that don't line up with the plan, session-length and break
pattern vs a baseline, which hours produce *finished* vs abandoned sessions,
streak/consistency, and an honest weekly "where the time actually went". **All of it
waits on real logged data** — none of it is specified yet.

Supersedes the narrower "time-pattern coach" deferred under item 12 (Learning study
sessions only). Same idea, whole-day scope: build it once, here.

### B — Autonomous code agents

Today `UI_Steward_Agent` finds drift and writes proposals but edits nothing. These
four close that loop.

- **`UI_Builder_Agent`** — plain-English UI request → edits that screen's own `Page/`
  files → runs its build + lint → reports the diff. One screen per request; never
  reaches across the HTTP seam (Rule 5).
- **`Code_Explainer_Agent`** — reads the live source, not the docs, and answers "what
  does this do / why". Distinct from `Inky_Knowledge_Agent` (stored knowledge;
  `context.md` still empty and unscoped).
- **`Bug_Fix_Agent`** — stack trace or breakage report → patch → *runs it* → reports.
  A fix it could not verify is reported unverified (Rule 8).
- **`Regression_Watcher_Agent`** — fires after any agent edits a screen, re-runs that
  screen's tests/build, files a board card on a break. The net under autonomous
  editing, where no human has reviewed the diff.

### C — Job hunt (4 agents) — belongs to the OFFICE screen, item 12 M7

**Correction, same session:** these were first ruled out of scope on the grounds that
no Job screen was planned. That was wrong. **Item 12 M7 is the OFFICE screen** —
applications pipeline, interview prep, work log, machine-enforced resume-defensible
flag (≥2 Good/Easy ratings) — and M8 already lists "Office agents" as crew work.
D17.5 moved that screen to **port 8010** (CLAUDE.md port table); item 12's own line
still says `:8008`, which is Hermes. **Fix that line when M7 starts.**

Four profiles added, `learning`/`sub` under `Learning_Main_Agent`:

- **`Job_Research_Agent`** — reads saved JDs, extracts the real skill/stack asks,
  aims the Planner at live openings. This *is* the "JD-skill radar" already deferred
  on the board under item 12 — one agent, not two.
- **`Resume_Agent`** — claims only what the Learning OS has marked
  resume-defensible; flags lines that no longer earn their place.
- **`Interview_Prep_Agent`** — per-interview prep pack; feeds the
  "interview-question radar → Quizmaster" deferred card and triggers M6's
  interview-day preemption.
- **`Application_Tracker_Agent`** — staleness over the pipeline rows. Plain SQL, no
  model call for the detection.

**Standing constraint, unchanged:** *never* auto-apply to job portals (item 12's own
"Never"). These four surface and draft; the owner sends.

**Department:** parked under `learning` because the Pixel Office floor has six
departments hard-coded (`Backend/services/office.py` + `roomPlan.ts`) and OFFICE is
not one of them. A real `office` department is a later change to both files, not part
of this item.

### D — Model: Muse Spark contributor

Owner's call, 2026-09-05: route this roster at the **Muse Spark contributor tier**
rather than burning the Claude subscription on it — an API key plus a large token
budget for a $20 top-up, against a subscription that gives no key at all.

Three things to settle before it's real:

1. **The exact model id.** `Screens/Model/GATEWAY_CONFIG.md` records
   `muse-spark-1.2-contributor-free` in the persisted OmniRoute config — **not 1.3**.
   Check the gateway dashboard, pin the id, update that file. The same file already
   carries a CONFIRM that no "GLM Flash 5.3" exists there either.
2. **Its real per-token price and rate limits.** Everything in D depends on these and
   the repo has verified neither. A 15-minute Context Engine poll is ~96 calls/day;
   confirm RPM first, fall back to a 30-minute cadence if it doesn't fit.
3. **The data-sharing tradeoff.** Contributor tier means prompts and outputs may be
   used to improve the provider's products. That collides directly with item 12 M8's
   standing rule, **"PII → local models only"** — and there is no local model here
   today. So: either those agents stay off this tier, or a sanitizer earns its place
   first (item 2 already asks whether an LLM sanitizer pass is worth its cost).
   **Unresolved. It gates C and every Finance agent; it does not gate A or B**, which
   read code, build state and timestamps — no personal data in either.

Per-agent model pinning is an `office.json` key that **item 4 V2 introduces**; the
twelve new profiles ship without it rather than carrying a key nothing reads.

### Blocked on

1. **Item 4 V2** — until `ask_agent` is a real OmniRoute call, all twelve are folders.
2. **Item 2 (Storage seam)** — the Context Engine needs somewhere to write.
3. **Item 14 (WakaTime)** — the Context Engine's main office-hours signal.
4. **D above** — model id, price, rate limits, and the contributor-tier data question.
5. **Item 12 M7** for section C specifically — the OFFICE screen has to exist before
   its four agents have anything to read.

### Sifted out of the pasted draft — do not re-propose

- **The ₹35/month cost table.** Arithmetic on a price the repo has not verified.
  Keep the *shape* of the estimate (see D below), throw away the numbers until the
  model id and its real price are confirmed.
- **Morning Brief + Schedule Optimizer as new agents.** `Day_Planner_Agent` already is
  both (reads the trace ledger nightly, writes tomorrow's plan). Item 15 is its wiring.
- **Watch_Dog / Quota Warden / Evolution Analyst as new agents.** All three already
  exist as profiles.
- **Architecture / Documentation / Project-Manager agents.** Overlap
  `Doctrine_Planner_Agent`, `Integration_Expert_Agent`, `Mission_Planner_Agent` and
  `UI_Steward_Agent`. Revisit only if a real gap shows up in use.
- **A separate `KAGE_DATA_DIR/planning/` store and a "trigger dispatcher" runtime.**
  Item 2 owns storage; item 4 V2 owns the runtime. Two owners for one job is how the
  deleted repo-root `Agents/` pool died.

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
