# AGENTS.md — Kage decision log

One numbered decision, one line. Append-only: a change to `D<n>` is filed as `D<n>.1`;
the highest sub-number is in force, the parent stays as history. Rationale beyond the
line lives in git history — this file is the *what*, not the essay.

Rules → [`CLAUDE.md`](CLAUDE.md) · Open work → [`PLAN.md`](PLAN.md) · Today's one task → [`NOW.md`](NOW.md)

**HISTORIC, do not action:** D1, D1.1, D2, D3, D4, D5 governed the pre-rebuild Finance
frontend that D7 replaced. D10/D10.1, D11.1–D11.3, D12.1, D15.4, D18.1, D21.7 are each
superseded by a later line below.

## Finance UI, pre-rebuild (all historic — see D7)

- **D1** — Finance telemetry skin was amber-on-carbon, red reserved for act-now. *(superseded by D1.1)*
- **D1.1** — Two F1 liveries (Ferrari red Overview / Red Bull blue Investments) plus `--f1-*` sector-delta tokens. *(historic, D7)*
- **D2** — Telemetry panels read `blueprintSeed.ts`, not live endpoints. *(historic)*
- **D3** — CSS/SVG + framer-motion only, no Three.js. *(superseded by D3.1)*
- **D3.1** — Three.js welcomed via `@react-three/fiber` + `drei`; framer-motion keeps page transitions; static export is unaffected because Three.js is client-side.
- **D4** — Enrich the Overview tab additively, add a TELEMETRY tab and a left SpeedoNav. *(historic)*
- **D5** — "Neon Command Deck": glass panels, aurora background, tilt cards, pulse-core hero. *(historic)*

## Gateway and models

- **D6** — OmniRoute (npm `omniroute`) is the model gateway on `127.0.0.1:8003`, bound to localhost, `REQUIRE_API_KEY=true`; secrets are generated into `.env` and never committed. Config: `Screens/Model/GATEWAY_CONFIG.md`.
- **D6.1** — `Start_Inky/run_omniroute.py` owns start/stop, is idempotent, and imports nothing shared; `Start_Everything.bat` starts it before the screens.
- **D6.2** — Health path is `/api/monitoring/health`; the LiteLLM-era `/health/liveliness` 404s, and a 404 counts as unreachable.

## Screens of record

- **D7** — `Screens/Finance/Backend/app` (React 19 + FastAPI + SQLite, cut over in `657774d`) is the Finance screen of record; its own decisions live in `Screens/Finance/DECISIONS.md`. Supersedes D1–D5.
- **D8** — Two Learning surfaces on purpose: standalone `Screens/Learning/` is canonical personal learning; finance-os's Learning tab was finance-scoped RAG only, and was removed in D20. Theme half superseded by D16.
- **D9** — `Screens/Agents/` (`AGENT DECK`, 8004) is the agent workspace; profiles live in `Screens/Agents/AI_Agents/` because the screen owns its own agents (Rule 5); the kanban is one room inside it, card keys `ENH-n`.
- **D10** — Model screen iframes OmniRoute's own dashboard rather than rebuilding its panels. *(superseded by D10.1, then restored by D21.3)*
- **D10.1** — `:8005/` 307-redirects straight to the gateway. *(superseded by D21.3 — the redirect stranded the browser outside Kage whenever the gateway was down)*

## Storage seam

- **D11** — `Screens/Storage/` is the repo's one storage seam (`read_doc`/`write_doc`/`list_docs`/`delete_doc`/`search`, logical-path addressed): FastAPI, **8009**, `MENU_ORDER 8`, one Status tab, hand-rolled HTML, no Next app.
- **D11.1 / D11.1a / D11.2 / D11.3** — Google-Drive-MCP transport, stateless name resolution, Ollama `nomic-embed-text` RAG. *(all superseded by D11.5 / D11.5.1)*
- **D11.4** — The trader seam ships only its append-only ledger (`trader/ledger/<IST date>/<HHMMSS>-<seq>.json`, no update or delete route); the trader agent itself is unbuilt and gets its own screen later.
- **D11.5** — Storage is **local disk**, not Drive: plain files under `KAGE_DATA_DIR` (default `~/kage-data`, outside the repo). Why: the target host is Termux on Android — no Node, no Ollama — and service accounts have no Drive quota on a consumer Gmail. `write_doc` is atomic via `os.replace`; `delete_doc` moves to `.trash/<date>/`.
- **D11.5.1** — Embeddings go through OmniRoute's OpenAI-compatible `/v1/embeddings` (free model id in `.env` as `STORAGE_EMBED_MODEL`), never Ollama. Unreachable means keyword-only `partial`, stated honestly.
- **D11.5.2** — Retrieval is hybrid: SQLite **FTS5** keyword plus dense, fused. The index `Backend/index/rag.sqlite` is git-ignored and rebuildable from the notes.
- **D11.5.3** — `services/sanitize.py` runs on every chunk before it is sent out to embed; rules live at `knowledge/_sanitize_rules.json`. v1 is the hook plus an empty ruleset.

## Pixel Office (Agents screen)

- **D12** — The landing view is a pixel office stage driven by an append-only `events` table and one SSE endpoint; the roster is registry-driven from `AI_Agents/*/office.json`.
- **D12.1** — `omni.py` existed but `POST /agents/{name}/ask` stayed a stub in V1. *(closed by D27)*
- **D12.2** — Ambient simulated activity is `AGENTS_DEMO_EVENTS`, off by default; every generated event carries `sim=1` and is labelled simulated. Never presented as real work.
- **D15** — The stage is a **2D canvas pixel renderer**, not Three.js — the 3D pass could not reach the reference art. `three`/`fiber`/`drei` removed; static export dropped ~1.2 MB to ~770 KB.
- **D15.1** — Art is code: a palette plus string-matrix sprites plus painter functions (`pixelArt.ts`). No binary assets, nothing to license.
- **D15.2** — One attached building; desks are generated per occupied seat, so dropping in a profile folder furnishes a desk automatically.
- **D15.3** — Pan, zoom and focus work in *device* pixels so one art pixel is an exact square of physical pixels; text lives in a DOM overlay so it is never pixel-scaled.
- **D15.4** — One speech bubble at a time. *(superseded by D18.5)*
- **D18** — Warm rebuild: paper, honey and sand, walnut-ink outlines, no near-black anywhere; coral `#D95F43` stays act-now only. The palette was remapped 1:1 on the same char keys, so every sprite matrix survived.
- **D18.1** — Walls deleted: six zones on one open floor separated by rugs and furniture, linked by a honey walkway loop. Its fixed sizing is superseded by D18.7; the open-floor design stands.
- **D18.2** — Six identities: Model server garden, Finance trading floor, Learning library loft, Agent Deck war room, Anime lounge, Lobby café.
- **D18.3** — Agents exist only while working: `started` materialises them at their desk, or walks them in from the Lobby on a cross-department handover; `done` fades them after a 6 s linger. Heads follow the same lifecycle.
- **D18.4** — Ambient life — steam, dust motes, LED flicker, CRT scanline, a patrolling cat — all of which freezes under `prefers-reduced-motion`.
- **D18.5** — Up to 3 speech clouds; most-recently-tasked agents win, SIM-tagged when `sim=1`.
- **D18.6** — The demo generator runs up to three overlapping bursts; still opt-in, still `sim=1`.
- **D18.7** — `buildLayout(vw, vh)` re-plans per viewport: fixed 140×128 zones, flexing walkways, camera clamped to the plan, so nothing scrolls and no backdrop shows. Remaining polish is owner-led (ENH-19).
- **D19** — The D9 three-pane workspace becomes the **AGENT DECK** tab at `/workspace` in the same pixel language; the floor-tab strip, floating DeskChat, RoomTabs, Navigator and AgentCard are deleted (Rule 6).
- **D19.1** — A pixel UI kit (`.px-panel`, `.px-btn`, `.px-input`, `.px-tab`, `.px-chip`) with pixel-corner bubbles built from edge-bar box-shadows, not borders.
- **D19.2** — Pixelify Sans carries the chrome, IBM Plex carries chat bodies. Font stacks are declared in a plain `:root` block, because `@theme inline` does not emit custom properties and `var()` needs real declarations.
- **D19.3** — Three panes: rail (search, rooms, roster with SSE presence dots), centre (1:1 chat or the board/runs room), right profile drawer that Esc closes.
- **D19.4** — The profile drawer's FILES tab reads and writes the agent's real files; filenames must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}\.(md|txt|json)$` — no separators, so the path can never leave the profile folder — with a 100 KB cap.
- **D19.5** — `POST /agents/{name}/messages` writes the messages table and emits a `source=ui` event, so a DM shows up as a cloud on the stage.

## Finance rebuild

- **D13** — "Aurum" is the Overview skin: near-black ground, gold `#E4C07C`, Fraunces serif hero numerals, a 12-column grid, hand-rolled SVG charts and no chart library. The racing palette stays on tabs not yet re-skinned; the two coexist.
- **D13.1** — Aurum's coral `#FF7A6B` marks a monetary loss only. Nothing decorative is red and no card is red at rest.
- **D13.2** — The 3D net-worth ridge degrades, it does not disappear: it falls back to a static SVG drawn from *the same real series* on no-WebGL, on reduced-motion, and when a mounted context has not painted within 1.5 s. The panel's tag names whichever one drew.
- **D13.3** — **No manufactured market data.** A price row exists only for a date the feed actually published; carrying the last NAV forward fills the series with duplicates and flattens every day change to 0.00. A day with no quote stays absent.
- **D20** — Investments rebuilt end-to-end on Aurum: hero plus value ridge, one ANALYSE action per holding, the per-holding drawer, an Analysis tab (look-through X-ray, HHI, overlap heatmap, drift, cost and tax) and a Trade Desk tab (WATCHLIST / JOURNAL / IPO / GLOBAL).
- **D20.1** — Fund reference comes from Groww public pages (`__NEXT_DATA__` → `mfServerSideData`), cached once per fund per month. A page whose `scheme_code` differs from the requested AMFI code is DISCARDED; unresolved pages show honest `pending`.
- **D20.2** — Analysis is advisory-neutral: an observation is a fact plus the named threshold, and no buy or sell verb appears anywhere. Unverified settings carry `[UNVERIFIED]` into the UI.
- **D20.3** — The portfolio series rides each fund's last-known NAV **in memory** between publications and writes nothing back; the old same-date-only sum invented drawdowns and read volatility at 32.4% instead of the real 10.5%.
- **D20.4** — Trade Desk rules: the journal is delivery-only capital gains and a trade closes once, never rewritten; the IPO source is groww.in/ipo cached 24 h; applying is a checkbox, never advice.
- **D20.5** — `Start_Inky/run_market_mcp.py` (`mcp` SDK pinned `<2`, Streamable HTTP on `127.0.0.1:3101/mcp`) is the one tool seam for research agents. Output is bounded structurally with a marked `_truncated` row, never string-sliced into invalid JSON.
- **D20.6** — `backfill_price_history` writes real points only; when no source answers, nothing is written and the UI keeps its honest empty state.
- **D28** — Two series on one ridge share ONE min/max, never two.
- **D28.1** — Month scope lives in the URL as `?month=YYYY-MM-DD`, and the month list is read off `net-worth`'s own `trend`, never an arithmetic range.
- **D28.2** — The month pill is interactive on the Overview tab only.
- **D28.3** — The backend has no `?through=` yet, so only `NetWorthCard` truly scopes; every other card shows an honest "AS OF \<month\> — not yet historical" marker.
- **D28.4** — The benchmark symbol is hardcoded `^NSEI` (Nifty 50); a 404 on `GET /api/finance/market/benchmark` renders `NO BENCHMARK LOADED`, not a broken card.

## Learning OS

- **D16** — Learning is rebuilt as an agent-driven platform teaching TryHackMe-style (track → module → room → explain / real-world / lab / checkpoint → auto-minted recall cards) in the **Ember Studio** system: warm near-black, bone text, ember `#E8A851`, Fraunces numerals, jade for success, violet for AI-authored, red act-now only. Five tabs: TODAY, PATH, RECALL, INSIGHTS, CREW.
- **D17** — v3 "real-life pass": the owner's real corpus enters the system and the OS starts tracking his actual life.
- **D17.1** — **Honest zero.** All demo history is wiped and rooms re-seed as empty skeletons, so "planned, not taught" is a visible state. Nothing records work that has not happened. The PII corpus stays in gitignored `Screens/Learning/Context/`, served only by a localhost-allowlisted read router.
- **D17.2** — Two tracks from ground zero: "Project → DevOps" (Git/Linux/networking → AI agenting → multi-model routing → RAG → containers and CI/CD → Arize) and "Observability, job-driven" (networking/Linux → Splunk → Dynatrace including DQL/DPL → Prometheus/Grafana/OTel labs built on Kage). Old detection rooms redistribute; leftovers park archived and visible, never deleted.
- **D17.3** — Agents may fetch whitelisted sources (list editable at `Context/SOURCES.md`); the LLM only digests what the service fetched; everything arrives UNVERIFIED in violet until one-click approve. Supersedes D16's fetch ban.
- **D17.4** — OFFICE is its own screen, because the menu's hard `MAX_TABS = 5` bars a sixth Learning tab: Overview / Applications / Interview Prep / Work Log / Resume Readiness, its own FastAPI and SQLite, reading Learning over HTTP. **No portal automation, ever.**
- **D17.5** — A skill is resume-ready only at ≥2 Good/Easy recall ratings, and the OFFICE screen enforces the no-inflation rule mechanically. OFFICE's port is **8010**; 8008 is Hermes.
- **D17.6** — No dated grid. A settings day-template plus a weekly Planner rebalance driven by what actually happened; interview day preempts learning.
- **D17.7** — SIGNAL is a section inside CREW (agent output pending approve), not a sixth tab.
- **D17.8** — TryHackMe is the standing lab: LAB beats may link a room, sessions carry a `source` tag, and Today shows a real streak. The OS never submits or fakes anything on THM.

## Platform

- **D21** — Claude builds this repo alone; rules collapse to one line each in `CLAUDE.md`, decisions live here, open work in `PLAN.md`. There is no fourth planning doc.
- **D21.1** — **Polyglot backend, runtime chosen per service.** The seam between screens is HTTP, so each service picks the runtime whose libraries the work lives in and never imports across the line. Python/FastAPI holds finance-os, Storage/RAG, Learning and the Main Menu; Node holds the Agent Deck's SSE fan-out, Anime and the MCP servers.
- **D21.2** — 8000 is the Main Menu and nothing else; the Finance app reads its own `settings_for_finance.py` (8001), so a port stays written in exactly one place.
- **D21.3** — The Model screen serves its own page again, restoring D10 and superseding D10.1: it probes `/api/model/overview`, embeds the dashboard when that answers `ok`, and otherwise names the command that starts the gateway. It re-checks every 10 s, so a gateway coming up needs no reload.
- **D21.3.1** — The menu links **directly** at the gateway, because OmniRoute sends `X-Frame-Options: DENY` and CSP `frame-ancestors 'none'` and the iframe never rendered. A screen may declare `MENU_ADDRESS`; `:8005` still runs for the probe and the gateway-down page, served `Cache-Control: no-store`.
- **D21.4** — The repo-root `Agents/` pool and `Shared_By_All_Agents/` are deleted: `the_supervisor.py` imported a `do_one_task` that exists nowhere in the repo, so every endpoint calling it failed on every request. `Screens/Agents/` is the agent surface.
- **D21.5** — Finance is one folder again (`Screens/Finance/{Backend/app, Page/next_app, Shared}`), matching the shape Anime already used; 409 MB of dead pre-rebuild trees deleted; `Start_Everything.bat` now installs the app's own `requirements.txt`, which no loop had ever picked up.
- **D21.6** — `Shared_By_All_Screens/` shrunk to what two or more trees genuinely use; eight single-caller modules moved into `Main_Menu/Backend/`. A shared file with one caller is not shared, it is misplaced.
- **D21.7** — `TREE.md`, a hand-annotated map of every file in the repo. *(reversed 2026-09-05 by D34 — it went stale on every commit, had no reader, and duplicated CLAUDE.md's "Where things are")*
- **D26** — One Back press per level, not per tab: a screen's tab bar replaces history rather than pushing it.

## Calendar card

- **D23.1** — The card gained a switch and lost its decoration.
- **D23.2** — Hover opens to the right, never over the grid.
- **D23.3** — Observations are written, intentions are not.
- **D23.4** — WakaTime auth is the API key, not OAuth: one local user reading his own data.
- **D23.5** — The free plan's 7-day window is snapshotted, not worked around.
- **D23.6** — Two brains, one prompt: `CALENDAR_AGENT_BACKEND` selects the backend and the prompt is shared.
- **D23.7** — Google not being set up is a sentence, not an empty month.

## Deepseek and Hermes screens

- **D24** — The Deepseek screen (8007) is a nav for the `dsh` harness, because the point is watching traces.
- **D24.1** — The harness reaches models through the gateway, not DeepSeek's API directly.
- **D24.2** — Kage never starts the harness; `dsh web` runs in its own process (Rule 20).
- **D24.3** — The installer edits config text, never a YAML round-trip.
- **D25** — Hermes (8008): the profile is the unit, and its history is the training.
- **D25.1** — One gateway entry declared for all profiles, opted into **by hand** — repointing fifteen agents changes what each one costs and how it behaves, so it is a decision per profile, not a side effect of wiring.
- **D25.2** — The screen never runs an agent; a run costs money and mutates state.
- **D25.3** — Keys never leave the process.
- **D25.4** — Hermes' `custom_providers` takes a literal key, so one is written there.

## Agent Deck V2

- **D27** — `ask_agent` calls OmniRoute for real, through one shared ask path used by `/ask`, the DM composer and agent-kind rooms alike. Closes D12.1.
- **D27.1** — `state: "error"` ships as HTTP 200, not a 5xx: a failed ask is a result, not a transport failure.
- **D27.2** — `runs` table, append-only; every ask opens a row.
- **D27.3** — Per-agent model pinning is two optional `office.json` keys, `model` and `models`, plus `GET /api/agents/models`.
- **D27.4** — Scope trimmed from the original brief: the TaskBrief panel is dropped from V2 because that brief assumed a root-page chat panel which does not exist.
- **D27.5** — `RunsStub.tsx` replaced by a live `RunsPanel.tsx`.

## Observability and hygiene

- **D30** — Finance and Learning each get **their own** `services/observability.py`; no shared module (Rule 5).
- **D30.1** — Folded into an existing block, not a tenth card.
- **D30.2** — AGENT DECK already had richer infrastructure from the `runs` table, so it got a stats strip and no backend change.
- **D30.3** — The Model screen is exempt: it already *is* the observability surface.
- **D30.4** — The Main Menu is exempt for now; its backend half (trace middleware, `health_check`, `/api/main_menu/live` SSE) already exists but is unsurfaced, and the frontend was mid-redesign.
- **D30.5** — `health_check.py`'s cross-screen-import pattern is not copied any further.
- **D31** — The four "known heavy pieces" `Shared_By_All_Screens/` was meant to lose were already gone.
- **D31.1** — `Look_And_Feel/` moved to `Main_Menu/Look_And_Feel/`, its one real caller. The lesson became Rule 21.
- **D31.2** — `read_screen_settings.py`, `restart_signal.py` and `clear_every_data_cache.py` stay shared **on purpose**: their importers are the Main Menu and `Start_Inky/`, and Rule 17 already carves out launcher and menu discovery. Duplicating "how do I find the port" is the exact bug that file exists to prevent.
- **D31.3** — `Current_Numbers/` is data, not logic: the one deliberate cross-screen channel, not a Rule 6 violation.

## Storage build

- **D32** — `Screens/Storage/` boots: the seam with validated logical paths (a segment opens with `[a-z0-9_]`, depth ≤ 6, extension in `{.md,.txt,.json}`, no `..`), atomic write, `.trash`, and an honest `GET /api/storage/status`.
- **D33** — **RRF is the fusion method**, because it needs no score normalisation between BM25 (unbounded) and cosine (−1..1); a fused score is just `Σ 1/(60 + rank)`. Cheap to swap if the owner's research says otherwise.
- **D33.1** — Dense search degrades to keyword-only with `state: "partial"` and an honest note, never to broken.
- **D33.2** — A *knowledge note* needs a `**Source:**` line or it is refused with 422; the generic seam door stays unrestricted, because a trader row or a blueprint is not a citation-bearing note.
- **D33.3** — System files get a leading underscore, so the path validator allows `[a-z0-9_]` to open a segment.
- **D33.4** — The honest-zero seed is guarded by a marker file, not by "does the file still exist" — existence-checking would silently recreate a note the owner deliberately deleted.
- **D33.5** — The Main Menu `storage:` glyph stays deferred while `TopBar.tsx` is mid-redesign, the same collision risk as D30.4.

## Repo hygiene

- **D34 — Four root docs, no fifth (2026-09-05).** `CLAUDE.md` (rules), `PLAN.md` (open work only), `AGENTS.md` (this log) and `NOW.md` (the one active task), plus the public `README.md`. Every one of them is one line per item, and nothing is stated in two of them. Deleted as duplication: `TREE.md` (reverses D21.7), and the `.scratch/` context packs that restated these files for other assistants. `LEARNING_SEED_MAINTAINER.md` moved to `Screens/Learning/`, beside the seed file it maintains. Shipped work is deleted from `PLAN.md` on sight (Rule 12) — the record is git history plus the decision line.
- **D34.1 — `.scratch/` holds only briefs for work that is still open.** A brief whose work shipped is deleted the day it ships; screenshots and mockups of shipped UI go with it. What survives a cleanup is named in `PLAN.md`'s reference table, and anything not in that table is fair game to delete.
- **D33.6 — the Storage `storage:` glyph shipped 2026-09-05, ahead of D33.5's wait.** `TopBar.tsx`'s home-page redesign hadn't landed yet, but the change was a single additive `GLYPHS` entry with zero surface overlap with the redesign — the collision D30.4/D33.5 guarded against needs a shared-region edit, which this wasn't. Verified live at `localhost:8000`.

## Learning OS M6

- **D35 — TryHackMe standing lab (slice 1, 2026-09-05).** `services/thm_lab.py`: `rooms.lab_url` + `rooms.source` columns (idempotent migration), `set_lab()` tagging with input validation, a THM-only streak mirroring the existing `streak_and_grace` logic. Room 55 ("Linux from ground 0") tagged with the owner's real TryHackMe room; no fabricated room was substituted (Rule 8/22) while waiting for a real one.
- **D36 — day-template settings (slice 2, 2026-09-05).** `services/day_template.py`: weekday/weekend minute-blocks (core/drip/thm/capture/apply) seeded verbatim from `Master_Context.md`'s stated daily defaults — no invented weekend-specific numbers (none are on record). Today's plan protects the THM slot: adds a plan entry only if today's slot-owning session hasn't happened yet.
- **D37 — Sunday-cadence Planner rebalance (slice 3, 2026-09-05).** `services/planner_rebalance.py`: fires once per ISO week on Sunday, files a `proposals` row (agent `planner`, kind `rebalance`) when a track falls under half an evenly-split weekly target, the THM slot gets skipped, or session completion drops below 70%. The even per-track split is a disclosed default, not a recorded target — no per-track minute target exists anywhere yet. Tested only against synthetic ledger fixtures (`tests/test_planner_rebalance.py`), never the real DB, per the M6.3 gate.
- **D38 — M6's interview-day preemption piece stays unbuilt.** It reads Office's interview data over HTTP; Office (M7) does not exist yet, so there is nothing to read and no real contract to integrate against. Not building against a guessed API shape (Rule 22) — picked up when M7 ships.

## Repo hygiene, item 18

- **D39 — one command for tests + hygiene gates (2026-09-05).** `Start_Inky/run_checks.py` runs Learning's pytest suite (the only real pytest suite in the repo today) plus the two Finance hygiene gates. Both gates had hardcoded paths into a `finance-os/` directory that doesn't exist — Finance actually lives at `Screens/Finance/Backend/app` / `Screens/Finance/Page/next_app`; fixed in place, left everything else in the gate logic untouched. `gate_phaseN.py` in the same folder are dead (tied to the deleted `run_build.py` finance-os-build harness) and were not wired in. `.git/hooks/pre-commit` calls it and blocks the commit on failure (verified: a deliberately injected stub route failed the gate and blocked the commit, then was reverted). `start_every_screen.py` calls it too, non-blocking — it reports honestly (Rule 8) without stopping the dev workflow.

## The agent library

- **D40 — `KAGE_DATA_DIR` moved repo-relative, and a library convention was added on top of the seam (2026-09-05, owner's call — phone/Termux hosting wants one self-contained folder).** `KAGE_DATA_DIR` defaults to `<repo>/kage-data/` (was `~/kage-data`, which never existed on this box — Storage shipped today, nothing had been written yet, so the cutover lost nothing). Gitignored (Rule 7.1 supersedes Rule 7's "outside the repo"). New service `Screens/Storage/Backend/services/library.py`: a naming convention over the existing seam, not a new store — `library/<screen>/<tab>/<card>/<card>_<IST timestamp>.md`, one new dated file per write, never an overwrite, so a card's folder is its own history. Three routes: `POST .../library/{screen}/{tab}/{card}` writes a snapshot, `GET .../latest` reads the newest (honest 404 if nothing's been written — Rule 8, no fabricated empty snapshot), `GET .../{screen}/{tab}/{card}` lists every version. Modeled directly on the existing `trader.py` ledger pattern (date-stamped filenames, `seam.write_doc`/`list_docs`/`read_doc`, no new database). **Scope deliberately stopped at the skeleton + write API** — no screen writes into it yet; each screen's own agent wires in as it's built (item 16 A's `Context_Engine_Agent` was already heading here for its one current-state file — this generalizes that idea to every screen/tab/card instead of one file). No retention cap — every version kept; revisit only if phone storage actually becomes tight.
