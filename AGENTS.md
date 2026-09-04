# AGENTS.md — Kage

> **Rules live in [`CLAUDE.md`](CLAUDE.md), not here.** This repo is built by Claude
> alone since 2026-09-03; the rules that used to sit in this file were collapsed to
> one line each and moved there so there is exactly one copy of them. This file is
> kept for the last in-flight GLM tasks and for the record below.
>
> - Standing rules -> [`CLAUDE.md`](CLAUDE.md)
> - What is not done yet -> [`PLAN.md`](PLAN.md)
> - Why a thing is the way it is -> the numbered decisions below

## Design decisions (CLAUDE.md Rule 11)

Numbered, append-only. A change to `D<n>` is filed as `D<n>.1`, `D<n>.2`, …; the
highest sub-number is the one in force and the parent stays as history.

> **D1, D1.1, D3, D3.1, D4, D5 are HISTORIC.** They governed the pre-finance-os
> Finance frontend at `Screens/Finance/Page/next_app/`, which the V1 rebuild
> replaced (`657774d`). Kept as history per CLAUDE.md Rule 11 — **not to be actioned**. See D7.

- **D1 — Finance telemetry skin: amber, not crimson.** The F1/"evening race"
  pass on the Finance screen (2026-08-28) uses warm amber/gold on carbon-black.
  Red / `--vermilion` / `--p5-red` stays reserved for "act now" state only
  (`colours_and_fonts.css` states this 3×) — never decoration.
- **D1.1 — Finance realism pass: two F1 liveries (2026-08-29, supersedes D1 for
  the realism pass).** Owner asked for a real "F1 broadcast/team-tool feel", not
  the amber skin. Two livery token sets in `globals.css`: `.liv-ferrari` (red
  `#DC0000` anchor, evening charcoal-navy, yellow sparing) on the Overview tab,
  `.liv-rb` (Red Bull blue `#1E5BC6` dominant, midnight navy, red/yellow trim) on
  Investments; a shared `--f1-*` set carries the broadcast sector-colour delta
  semantics (purple = best, green = ahead, grey = flat). **CLAUDE.md Rule 9 still holds** —
  `--f1-alert` (red) is the only "act now" colour and is never decoration; a
  monetary loss uses `--f1-flat` / `--liv-neg`, not alert-red. No Scuderia
  wordmark / shield / helmet-car icons / speedo-as-nav / AI-art. Detail:
  `.scratch/finance-realism-pass/research/f1-feel.md`. Authored by the local
  model; Claude orchestrated + validated.
- **D2 — Seed data for the telemetry panels v1.** New Finance panels read
  `app/lib/blueprintSeed.ts` (blueprint numbers real, rest `SEED`-tagged), not
  live endpoints. Live wiring was dropped — finance-os owns it (`PLAN.md` ## Dropped).
- **D3 — CSS/SVG + framer-motion for the telemetry motion.** ~~No Three.js added
  to the Finance app~~ *(superseded by D3.1)*.
- **D3.1 — Three.js welcomed on Finance (2026-08-29, supersedes D3).** Use
  Three.js (via `@react-three/fiber` + `@react-three/drei`) wherever it delivers
  better animation and interaction than CSS/SVG alone. `framer-motion` stays for
  page transitions and lightweight motion; Three.js handles 3D scenes, particle
  effects, and rich interactive visualizations. `output: "export"` is unaffected
  — Three.js is fully client-side. Install the same trio already in Main Menu's
  `package.json` (`three`, `@react-three/fiber`, `@react-three/drei`).
- **D4 — Additive placement.** Enrich the existing Overview tab (blueprint
  headline blocks) + a new TELEMETRY tab + a new left `SpeedoNav` that replaces
  the header tab-strip. Existing tabs/panels/endpoints untouched.
- **D5 — Finance "Neon Command Deck" (2026-08-28).** Vivid multi-hue accent set
  (`--gold/--cyan-e/--violet-e/--mint` + `--grad-wealth`/`--grad-flow`), glass
  panels (`.glass` + `backdrop-filter`), an `AuroraBackground` (drifting blobs +
  grain), `TiltCard` pointer-tilt wrappers, gradient+glow hero numbers, a
  `PulseCore` radar hero, and a spring page-transition. CLAUDE.md Rule 9 still holds — red
  is not in the decorative set. All motion freezes under reduced-motion.
  Authored entirely by the local model; Claude orchestrated + validated.
- **D6 — OmniRoute is the model gateway (2026-08-30).** The gateway slot on
  `127.0.0.1:8003` (vacated by the removed LiteLLM tooling) is OmniRoute
  (npm `omniroute`), bound to 127.0.0.1 only, `REQUIRE_API_KEY=true`. The
  Model screen reads it live: health `/api/monitoring/health` + `/v1/models`
  with `GATEWAY_API_KEY` from `.env` (env var wins). Gateway secrets are
  generated into `.env` by the launcher and never committed. Detail:
  `Screens/Model/GATEWAY_CONFIG.md` (gateway config shipped 2026-08-30).
  - **D6.1 — Gateway process ownership.** `Start_Inky/run_omniroute.py` owns
    starting/stopping the gateway (idempotent: an already-running one is left
    alone); `Start_Everything.bat` starts it in its own window before the
    screens. Self-contained — no shared-module imports (CLAUDE.md Rule 5).
  - **D6.2 — Health path.** OmniRoute's health route is
    `/api/monitoring/health`. The LiteLLM-era `/health/liveliness` 404s, and
    since a 404 counts as unreachable on the Model screen, the probe was
    switched (`Screens/Model/Backend/server_for_model.py`).
- **D7 — finance-os V1 is the Finance screen of record (2026-08-30).** The
  greenfield `finance-os/` app (React 19 + FastAPI + SQLite, built via the
  autonomous phase-gate loop, cut over in `657774d`) replaces
  `Screens/Finance/Page/next_app/` wholesale. finance-os carries its own
  "carbon/racing" theme (`racing.red #e10600`); **this supersedes D1.1's
  two-livery scheme**. All earlier Finance-UI decisions (D1–D5) are historic.
  finance-os keeps its decisions in `Screens/Finance/DECISIONS.md` and its
  data-backfill plan in
  `Screens/Finance/finance-datamigration.md` (gitignored — contains PII).
- **D8 — Two Learning surfaces, deliberately (2026-08-30).** The standalone
  **`Screens/Learning/`** screen (terminal/CLI theme; tabs Today/Plan/Recall;
  SQLite + seed file; `/ask` stubbed) is the canonical personal-learning surface
  — spec `Screens/Learning/QWEN_BUILD_PROMPT.md`, shipped `ed833dd`. The
  **finance-os "Learning tab"** (`Screens/Finance/Page/next_app/.../learning/`) is
  finance-scoped RAG over public finance primers only; it does not duplicate the
  standalone screen and neither absorbs the other. The old
  `learning-tab-plan.md` (Model-screen theme, full Drive+FAISS) is dropped.
- **D9 — The AGENTS screen is the agent workspace (2026-08-30).**
  `Screens/Enhancement/` → `Screens/Agents/` (`MENU_LABEL="AGENT DECK"`, port 8004).
  A local 3-pane agent workspace ("Deck" theme — Main-Menu DNA, not Slack). The
  kanban "ideas" board is **one room** inside it, owned by `Agent_Head`;
  board card keys stay `ENH-n`. Agent profiles live in
  `Screens/Agents/AI_Agents/` (the screen owns its own agents — CLAUDE.md Rule 5; V1 seeds
  21 role-stub profiles, `Agent_Head` first). V1 ships the shell + working board +
  profiles + honest stubs, **no LLM**. Agent
  execution (OmniRoute wiring, per-agent model sets, routing) is **V2**. Repo-root
  `Agents/` (20 stubs) and `Shared_By_All_Agents/` are a **V2 reuse pool — left
  untouched by V1**, not moved or imported. Plan: `.scratch/agents-workspace/`.
  Supersedes P3's old "rebuild the kanban" scope.
- **D10 — Model screen embeds OmniRoute's own dashboard (2026-08-30).** The
  Model screen at `:8005` **iframes OmniRoute's built-in dashboard** at
  `127.0.0.1:8003` instead of building custom data-proxy panels. The page
  keeps its RUBRIC header (title + status dot + "open in new tab" link) and
  the back-to-menu link; the iframe fills the remaining viewport. The
  existing `/api/model/overview` health probe gates whether the iframe is
  shown or a "gateway unreachable" fallback panel is displayed — honest
  states, no fake data. Auto-retry every 30 s when down. This supersedes
  the T7 "custom data blocks" plan from `screen_definition_for_model.py`'s
  original docstring; OmniRoute's dashboard already has models, usage, cost,
  logs, and latency views built in — duplicating them is waste.
  - **D10.1 — Model screen direct redirect to OmniRoute (2026-08-30, supersedes D10 iframe wrap).**
    `GET http://127.0.0.1:8005/` redirects directly (`307`) to OmniRoute's
    dashboard at `http://127.0.0.1:8003/`. Dashboard login requirement is
    auto-disabled on gateway startup by `Start_Inky/run_omniroute.py`.
- **D11 — The Drive-backed private storage layer (P7; 2026-08-31).** `Screens/Storage/`
  is the repo's **one storage seam** (`read_doc`/`write_doc`/`list_docs`/`delete_doc`/
  `search`, logical-path addressed under one Drive root folder): FastAPI, port **8009**,
  `MENU_ORDER 8`, one Status tab, hand-rolled HTML status page (no Next app). Built by
  Qwen 3-Max from the house brief `.scratch/drive-storage/QWEN_BUILD_PROMPT.md`
  (map: `.scratch/drive-storage/map.md`); Node migration rides P4 (user chose FastAPI
  for this service over the old Node-only stack rule — the seam is HTTP, consumers don't care).
  Nothing personal lives **only** on local disk.
  - **D11.1 — Adopted gateway.** The Drive transport is npm
    `@piotr-agier/google-drive-mcp` (MIT; service-account auth via
    `GOOGLE_APPLICATION_CREDENTIALS`, scope `drive`), run as a **standalone Streamable
    HTTP server** at `127.0.0.1:3100/mcp` by `Start_Inky/run_drive_mcp.py`
    (`run_omniroute.py` pattern, idempotent; auto-discovered by
    `start_every_screen.py`'s `run_*.py` glob — no `Start_Everything.bat` edit).
    The app is an MCP client (official Python SDK) and **never spawns it** —
    gateway-down is an honest first-class state. The app carries zero Google client
    libraries and never opens the SA key.
    - **D11.1a — Gateway pinned + tool surface verified (2026-09-04, v2.8.0).**
      Package still MIT, actively released. Standalone HTTP is
      `... start --transport http --host 127.0.0.1 --port 3100`; endpoint `POST/GET
      /mcp` with an `mcp-session-id` header after `initialize` (the Python SDK's
      `streamablehttp_client` handles it). Service-account mode is auto-selected when
      `GOOGLE_APPLICATION_CREDENTIALS` is set; scopes via `GOOGLE_DRIVE_MCP_SCOPES=drive`.
      The eight seam tools exist as named in the brief — `search` (`rawQuery:true`),
      `listFolder`, `readTextFile`, `createTextFile`, `updateTextFile`, `uploadFile`
      (`contentBase64`), `deleteItem` (→ trash), `createFolder` — **one correction:
      `createFolder`'s parent arg is `parent`, not `parentFolderId`.** Account/identity
      for the status panel comes from `authGetStatus` (reports active auth mode +
      effective Google identity). Open risk: a service account has no Drive storage
      quota of its own, so writes into a **consumer-Gmail**-owned shared folder can be
      rejected — a Workspace account with domain-wide delegation
      (`GOOGLE_DRIVE_MCP_SUBJECT`), a Shared Drive, or local-OAuth/external-token mode
      is the fallback if the gate hits it.
  - **D11.2 — Stateless path resolution.** Logical paths resolve by name via Drive
    `listFolder`/`search` with an in-memory cache only — **no local path→id map**
    (that map would be personal data on disk). All seam docs are stored as UTF-8
    `text/plain`; the extension (`.md`/`.txt`/`.json`) carries the format.
  - **D11.3 — RAG on the seam.** `services/rag.py` ports
    `add_and_search_the_knowledge_base.py`'s pattern (Ollama `nomic-embed-text`, plain
    cosine, sourced notes at `knowledge/notes/*.md` in Drive) + chunk overlap
    (180 words / 20 overlap). The chunk index (`Backend/index/chunks.sqlite`) is a
    **git-ignored rebuildable cache**, never a copy of record; `reindex` rebuilds it
    from Drive.
  - **D11.4 — Trader seam stub.** The future AI-trader lives in its own screen/agent
    (Finance's no-buy/sell-recommendation rule stays). This build ships only its
    append-only decisions ledger (`trader/ledger/<IST date>/<HHMMSS>-<seq>.json` via
    the seam — no update/delete routes); the agent itself is unbuilt.
  - **D11.5 — Storage goes local-disk; Google Drive is dropped (2026-09-04).**
    Supersedes the transport half of D11 / D11.1 / D11.1a / D11.2. The seam, the
    screen (`Screens/Storage/`, FastAPI, **8009**, `MENU_ORDER 8`, one Status tab,
    hand HTML) and the RAG / trader layers stay; the **backend becomes plain files
    under `KAGE_DATA_DIR`** (default `~/kage-data`, outside the repo — Rule 7), not
    MCP-to-Google-Drive. Why: the intended host is Termux on Android (no Node, no
    Ollama, 24/7), and the Drive-MCP path needed a Node gateway + a service account
    + OAuth and hit "service accounts have no Drive storage quota" for a consumer
    Gmail. `Start_Inky/run_drive_mcp.py` is removed; no `mcp` SDK, no Google
    libraries, no `path_map` (a logical path is now a validated real subpath).
    `write_doc` is atomic (`os.replace`); `delete_doc` moves to
    `KAGE_DATA_DIR/.trash/<date>/`. Near-term the laptop hosts and the phone
    browses over LAN; a phone deploy repoints `KAGE_DATA_DIR` to `/sdcard/kage-data`.
    Build brief lives in `PLAN.md` item 2 (the `.scratch/drive-storage/` brief is
    history). Open: a backup path — local disk is the only copy today.
    - **D11.5.1 — Embeddings via OmniRoute, not Ollama.** Supersedes D11.3's Ollama
      `nomic-embed-text`. `rag.py` calls the gateway's OpenAI-compatible
      `/v1/embeddings` (a **free** model, id in `.env` as `STORAGE_EMBED_MODEL`,
      reuse `GATEWAY_API_KEY`). Unreachable or not-an-embedder → keyword-only
      `partial`, honest.
    - **D11.5.2 — Hybrid retrieval.** Keyword (SQLite **FTS5**, stdlib) + dense
      fused; fusion method (RRF / weighted / + reranker) is an owner decision from
      research 2026-09-04. Index `Backend/index/rag.sqlite` — git-ignored,
      rebuildable from the notes.
    - **D11.5.3 — Sanitizer hook.** `services/sanitize.py` `sanitize(text)` (rules
      at `knowledge/_sanitize_rules.json` via the seam) runs on every chunk before
      it is sent to OmniRoute to embed. v1 = hook + empty ruleset; real rules and a
      possible LLM scrub pass follow the owner's data review.
- **D12 — AGENT DECK Pixel Office (Screens/Agents/; 2026-08-31).** The Agents screen
  landing view is a Three.js/react-three-fiber pixel "office stage" driven by an
  append-only `events` table + one SSE endpoint (`Backend/services/events.py`);
  characters animate strictly from real events, roster is registry-driven from
  `AI_Agents/*/office.json` (`{department, tier, parent}`). Old 3-pane workspace
  moved to `/workspace`.
  - **D12.1 — LLM still last.** `omni.py` (OmniRoute client, the one LLM seam) is in
    the tree but `POST /agents/{name}/ask` stays the V1 `{"state":"pending"}` stub.
    Live agent asks are `PLAN.md` item 3, after all data wiring.
  - **D12.2 — Demo events opt-in.** Ambient simulated activity is `AGENTS_DEMO_EVENTS`
    off by default (public repo); every generated event carries `sim=1` and is
    labeled simulated client-side. Never presented as real work.
- **D13 — Aurum is the Overview skin (finance-os/; 2026-09-02).** The finance-os
  Overview wears the "Aurum" private-wealth theme — near-black ground, gold
  `#E4C07C` accent, Fraunces serif hero numbers, 12-col panel grid, hand-rolled
  SVG charts (no chart library) — ported from
  `.scratch/finance-redesign/mockups/overview.html`. The racing palette and
  `.card` stay for the tabs that have not been re-skinned; the two coexist.
  - **D13.1 — Red is still act-now only.** Aurum's coral `#FF7A6B` marks a
    monetary loss (an expense bar, a negative day change, an above-20% APR).
    Nothing decorative is red, and no card is red at rest.
  - **D13.2 — The 3D ridge degrades, it does not disappear.** The net-worth
    ridge is react-three-fiber, dynamically imported, `ssr:false`. It falls back
    to a static gold SVG drawn from *the same real series* on no-WebGL, on
    `prefers-reduced-motion`, and when a mounted WebGL context has not painted
    within 1.5 s. The panel's tag names whichever one actually drew.
  - **D13.3 — No manufactured market data.** A price row is written only for a
    date the feed actually published. Carrying the last NAV forward (or stamping
    a stale NAV as today) fills the series with duplicates and silently flattens
    every day change to 0.00 — both paths did this and both were fixed. A day
    with no published quote stays absent, and a card with nothing real to plot
    says so instead of drawing a curve.
- **D15 — Pixel Office is 2D, not 3D (Screens/Agents/; 2026-09-02).** The D12 stage
  was Three.js/r3f. It could not reach the reference art (`Agent-idea.png`, a 16-bit
  top-down game scene), so the whole 3D pass — including the abandoned
  `vivek/agent-chambers-wip` chambers branch — is replaced by a **2D pixel-art canvas
  renderer**. `three`, `@react-three/fiber`, `@react-three/drei` and `@types/three`
  are out of `package.json`; static export drops ~1.2 MB → ~770 KB.
  - **D15.1 — Still no binary assets.** Art is code: a palette + string-matrix
    sprites + painter functions (`components/office/pixelArt.ts`), composed into one
    468 x 206 plan buffer (`components/office/roomPlan.ts`) blitted at an integer
    scale with smoothing off. Nothing to license, nothing to ship.
  - **D15.2 — One attached building.** Six chambers in a 3x2 block with shared walls
    and doorways (Model server room / Finance trading floor / Learning library /
    Agent Deck war room / Anime lounge / Lobby reception), not six floating tiles.
    Desks are generated per occupied seat, so dropping a profile folder in furnishes
    a desk automatically — the roster stays registry-driven (D12).
  - **D15.3 — Device-pixel camera.** Pan/wheel-zoom/room-focus all work in *device*
    pixels so one art pixel is always an exact square of physical pixels on
    fractional-DPI displays. Text (name plates, room plates, speech bubbles) stays in
    a DOM overlay above the canvas so it never gets pixel-scaled.
  - **D15.4 — One bubble at a time.** With a busy event stream every desk would shout
    at once; the stage speaks for the selected agent, else the hovered one, else
    whoever was tasked most recently. Dormant subs show no name plate.
    *(superseded by D18.5 — up to 3 clouds now)*
- **D16 — Learning OS rebuild (Screens/Learning/; 2026-09-02).** The Learning screen
  is rebuilt into a personal, agent-driven learning platform that teaches
  TryHackMe-style (track → module → room → 4-beat steps: explain / real-world /
  lab / checkpoint → auto-minted recall cards) in an **Ember Studio** design system
  (warm near-black, bone text, single ember `#E8A851` accent, Fraunces display
  numerals; jade = success, violet = AI-authored, red stays act-now only). Five tabs:
  TODAY (focus cockpit + Focus Session) / PATH (fully dynamic tracks, modules, rooms —
  no A/B enum, archive-not-delete) / RECALL (SM-2 + Card Studio) / INSIGHTS
  (retention curve, mastery map, weak spots, confidence-vs-reality, rhythm, coverage,
  append-only ledger) / CREW (six agents on an OmniRoute seam copied from the Agents
  screen: Planner, Tutor, Quizmaster, Librarian, Guardian, Auditor — every output is
  an Approve-card; ~~no agent fetches internet content~~ *(superseded by D17.3)*).
  Plan + milestones: `.scratch/learning-redesign/PLAN.md`, `PLAN.md` item 12.
  Supersedes D8's terminal/CLI theme for this screen; D8's two-surface split still
  stands.
- **D17 — Learning OS v3 "real-life pass" (Screens/Learning/ + Screens/Office/;
  2026-09-02).** The owner's pasted corpus (14-week plan, Master Context, resume)
  enters the system and the OS starts tracking his real life: honest zero, two
  ground-up tracks, a daily TryHackMe lab habit, a job-hunt Office screen, and a
  live agent crew. Plan: `.scratch/learning-redesign/PLAN_V3.md` (`PLAN.md` item 12
  v3). Everything in D16 stands except its fetch ban (D17.3 below).
  - **D17.1 — Honest zero.** All demo history (sessions, attempts, reviews, cards,
    notes, ledger, proposals, agent_runs) is wiped; rooms re-seed as **empty
    skeletons** ("planned, not taught" is a visible state). Standing rule, his
    words: **nothing records work that has not happened.** His PII corpus stores
    verbatim under gitignored `Screens/Learning/Context/`, served only by a
    localhost allowlisted read router; never committed.
  - **D17.2 — Two tracks from ground 0; the detection track dissolves.** Track 1
    "Project → DevOps" (goal: forward-deployment engineer; KAGE is the lab):
    Git/GitHub + Linux + networking basics → AI agenting (incl. Hermes agent,
    DeepSeek harness) → multi-model routing (OmniRoute) → RAG (Storage D11.3, then
    a finance-data RAG) → containers/CI-CD → Arize. Track 2 "Observability
    (job-driven)": networking + Linux ground 0 → Splunk SPL/ES → Dynatrace
    migration story incl. **DQL/DPL** (his differentiator) → real observability →
    Prometheus/Grafana/OTel/Bindplane labs built ON KAGE. Old detection rooms
    redistribute into both tracks where they pay; leftovers park archived in a
    visible Track 2 module — nothing deleted, nothing hidden.
  - **D17.3 — Agents may fetch; everything starts UNVERIFIED (supersedes D16's fetch
    ban).** Services fetch whitelisted sources (GitHub AI, Anthropic/OpenAI news,
    Chinese-AI channels, TryHackMe catalog — editable `Context/SOURCES.md`); the
    LLM only digests what the service fetched; every fetched/authored item is
    UNVERIFIED (violet) until his one-click approve. Agents that touch PII
    (resume, employers, contact) route to **local models only**.
  - **D17.4 — Office is its own screen (:8008).** The menu's hard `MAX_TABS = 5`
    bars a sixth Learning tab (ADR-067 precedent: cross-domain = own screen). Tabs:
    Overview / Applications / Interview Prep / Work Log / Resume Readiness; own
    FastAPI + SQLite; reads Learning over HTTP. Job-hunt agents prep (tailoring,
    interview packs, funnel reports); the owner still clicks Apply — **no portal
    automation, ever**.
  - **D17.5 — Resume-defensible by machine.** A skill (room `skill_tag`) is
    resume-ready only at ≥2 Good/Easy recall ratings (his Week-14 rule); the Office
    RESUME READINESS tab enforces his no-skills-inflation rule mechanically.
  - **D17.6 — Activity-rebalanced timetable, no dated grid.** The 14-week dated grid
    is not restored. A settings day-template (his real windows: morning drip,
    evening core, THM slot, apply block) + weekly Planner rebalance from the ledger
    (what actually happened). Interview day preempts learning (2–3 h prep insert).
  - **D17.7 — SIGNAL lives in CREW.** Researcher+Curator digests + his verification
    queue are a Crew-tab section (agent output pending approve — Crew's existing
    pattern), not a new tab.
  - **D17.8 — TryHackMe is the standing lab.** Every track's LAB beat may link a THM
    room; sessions carry a `source` tag; Today shows a THM streak line + a daily
    Scout pick (plan-matched THM rooms, honest login-wall fallback with remembered
    manual mapping). The OS never submits or fakes anything on THM — his streak is
    his own real activity.
- **D18 — Pix-Agents: the warm rebuild (Screens/Agents/; 2026-09-02).** The D15 stage
  and the whole Agents chrome leave the dark theme for warm paper / honey / sand
  (`pixelArt.ts` palette remapped 1:1 — same char keys, so every sprite matrix
  survived; `globals.css` tokens re-valued). No near-black anywhere — even outlines
  are walnut ink `#4A3527`; coral `#D95F43` stays act-now only.
  - **D18.1 — One open floor, no walls.** Walls, doorways and the outer shell are
    deleted; six 140×128 zones (plan 476×296 — sized so an integer 3× blit covers a
    1440×900 viewport; fixed sizing superseded by D18.7) are separated by tinted rugs, floor tone and furniture, linked
    by one honey walkway loop (apron ring + two vertical corridors + one horizontal).
    The page backdrop is the same honey as the walkway, so fit-all reads full-bleed;
    fit-all rounds up to the next integer scale when within 15% (a small apron
    overflow is invisible). Room plates are clickable to focus the camera; Follow is
    opt-in, off by default.
  - **D18.2 — Six identities.** Model = warm server garden (racks, amber LEDs) ·
    Finance = trading floor (brass ticker) · Learning = library loft (shelves, lamp
    pools) · Agent Deck = war room (round table, ENH pinboard) · Anime = lounge (CRT,
    sofas) · Lobby = café reception (espresso, welcome mat). Desks stay
    registry-generated — D15.2 carries over.
  - **D18.3 — Spawn → work → leave.** Agents exist only while working: `started` →
    materialize with a sparkle at their own desk, or **walk in from the Lobby along
    the honey paths** when `deriveWalkIns()` sees a cross-department handover within
    30 s (owner chose "Both") → work loops → `done` → stretch-fade + puff with a 6 s
    linger, then the desk sits empty. Heads follow the same lifecycle — D15's
    always-awake heads are gone.
  - **D18.4 — Ambient life.** Coffee steam, dust motes in the lamp pools, amber LED
    flicker, CRT scanline, lamp-pool pulse, and a cat patrolling the bottom walkway.
    All of it freezes under prefers-reduced-motion.
  - **D18.5 — Up to 3 clouds (supersedes D15.4).** Most-recent tasked agents win the
    bubbles; SIM-tagged when sim=1.
  - **D18.6 — Livelier demo for review.** The demo generator runs up to three
    overlapping sim bursts (was one every 6–12 s, which left the stage empty most of
    the time). Still sim=1 and still `AGENTS_DEMO_EVENTS` opt-in — D12.2 holds.
  - **D18.7 — Responsive floor (2026-09-02; supersedes D18.1's fixed 476×296
    plan sizing, keeps its open-floor design).** `buildLayout(vw, vh)` rebuilds
    the plan per viewport: the six 140×128 zones stay fixed while the
    walkways/aprons flex to absorb the viewport aspect, so the plan buffer is
    exactly `ceil(viewport / scale)` and always fills the frame — nothing
    scrolls and the honey never shows beyond the floor (zoom is floored at the
    cover scale, pan clamped to the plan; a ResizeObserver re-layouts). Scale
    is round-to-nearest integer with a feasibility floor (buffer ≥ 434×264,
    aprons squeeze to 1 px before dropping a step, min 2×). Owner verified on
    1920×1080-class browser viewports and accepted the current rendering;
    further responsive polish is his to drive later (ENH-19, PLAN.md item 4).
- **D19 — Agent Deck tab: Slack workflow, pixel skin (Screens/Agents/ /workspace;
  2026-09-02).** The D9 three-pane workspace becomes the **AGENT DECK** tab next to
  **PIX-AGENTS** (`/` ↔ `/workspace` tabs in the header; the floor-tab strip and the
  floating DeskChat are deleted — chat lives in the deck now; RoomTabs / Navigator /
  AgentCard deleted, CLAUDE.md Rule 6). Same pixel language as the office — not a flat Slack
  clone — while chat bodies stay human-readable.
  - **D19.1 — Pixel UI kit.** `.px-panel/.px-btn/.px-input/.px-tab/.px-chip` +
    pixel-corner bubbles (edge-bar box-shadows, not borders) on D18's warm tokens;
    BoardRoom / IdeaDetail / RunsStub re-skin unchanged through the tokens.
  - **D19.2 — Fonts.** Pixelify Sans (next/font) carries the chrome — wordmark, tabs,
    rail, section labels, buttons, profile rows; chat bodies and card copy stay IBM
    Plex. Font stacks live in a plain `:root` block with the next/font variables on
    `<html>`: `@theme inline` does not emit custom properties, so plain CSS var()
    references need the real declarations.
  - **D19.3 — Layout.** Left rail: search + rooms (# board-room, # runs) + the roster
    grouped by department with SSE presence dots. Center: 1:1 chat per agent (day
    chips, terracotta user bubbles right, typing indicator while a run is live) or the
    board/runs room. Right: profile drawer opens on agent click; ✕ or Esc closes.
  - **D19.4 — Agent files, view + edit.** The profile drawer's FILES tab lists the
    agent's real files under `AI_Agents/<name>/`, opens any in a monospace editor, and
    Save writes back. Routes `GET/PUT /agents/{name}/files[/{file}]`; filenames must
    match `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}\.(md|txt|json)$` (no separators — the
    path can never leave the profile folder), 100 KB cap; missing canonical
    identity.md / context.md / memory.md are one-click creatable.
  - **D19.5 — Chat persistence.** `POST /agents/{name}/messages` finally writes the
    messages table (nothing wrote it before) and emits a `source=ui` note event, so a
    DM shows up as a cloud on the stage. Replies stay the honest pending stub
    (D12.1); live wiring is PLAN.md item 4 V2.


- **D20 — Investments end-to-end: Analyse drawer, Analysis tab, Trade Desk
  (finance-os/; 2026-09-02).** The Investments tab is rebuilt on Aurum (hero +
  value ridge fed by the smoothed portfolio series, holdings table with ONE
  Analyse action — archive/delete buttons are gone — SIP-rhythm strip from
  lots, day's leaders), the per-holding ANALYSE drawer (an independent in-tab
  window: published portfolio with weights/sectors, facts, returns, risk
  ratios vs NIFTY 50, peers, pros/cons, plain-English explainer + Varsity
  links), a dedicated Analysis tab (look-through X-ray + HHI, pair-overlap
  heatmap, behaviour vs the index, allocation vs targets + drift, cost & tax,
  fact-based observations), and a Trade Desk tab (WATCHLIST / JOURNAL / IPO /
  GLOBAL). Backend: routers `analysis.py` + `tradedesk.py`; services
  `fund_reference.py`, `ipo_calendar.py`, `calculations/ratios.py`,
  `calculations/analysis.py`. The finance-os Learning tab is removed (D8's
  two-surface split stands; the standalone D16 screen is untouched).
  - **D20.1 — Fund reference = Groww public pages.** The page's
    `__NEXT_DATA__` → `mfServerSideData` is fetched once per fund per month
    into `fund_facts`/`fund_portfolios` (through `ref_cache`). Slug
    resolution: manual overrides → name-slugified candidates → AMC-page
    enumeration → mfapi `fund_house`; a page whose `scheme_code` differs from
    the requested AMFI code is DISCARDED. Unresolved pages (100900, 120760)
    show honest `pending` — NAV maths still works. mfdata.in was down
    (2026-09-02) and stays out.
  - **D20.2 — Advisory-neutral analysis.** Observations are FACTS + the named
    threshold (pair overlap 40% watch, sector 30%, single fund 25%, top-10
    25/40, blended TER 1.0%, drift ±5pp — the house
    `build_the_portfolio_review.py` values); no buy/sell verb appears
    anywhere. Ratio maths is the ported pure-math `compute_the_ratios.py`.
    Targets and the risk-free rate carry the settings file's
    `verified_by_a_person: false` into the UI as [UNVERIFIED].
  - **D20.3 — The portfolio value series rides each fund's last-known NAV in
    memory between publications; nothing is written back** (FD6/D13.3
    intact). The old same-date-only sum made the whole portfolio dive on any
    day one fund's NAV lagged — fake drawdowns, portfolio volatility read
    32.4% instead of the real 10.5%.
  - **D20.4 — Trade Desk rules.** The journal is delivery-only capital
    gains: a trade closes once and is never rewritten; per-trade STCG/LTCG
    buckets come from the tax rulebook file. The IPO calendar source is
    groww.in/ipo's `__NEXT_DATA__` (Chittorgarh dropped), cached 24 h;
    applying is a user checkbox, never advice. GLOBAL is LRS/TCS math with
    sources named and an unverified tag; TCS is surfaced as creditable, not
    lost.
  - **D20.5 — Market-data MCP server.** `Start_Inky/run_market_mcp.py`
    (official `mcp` SDK pinned `<2`, Streamable HTTP `127.0.0.1:3101/mcp`,
    idempotent, chained into `Start_Everything.bat`) proxies the finance
    backend — the one tool seam for the Agent Deck research agents (V2 ask
    wiring rides item 3/4). Tool output is bounded structurally (lists
    capped with a marked `_truncated` row), never string-sliced into invalid
    JSON.
  - **D20.6 — `backfill_price_history` writes real points only.** The old
    straight-line synthetic fill is gone; when no source answers, nothing is
    written and the UI keeps its honest empty state.

- **D21 — Claude-only, one rules file, one port each (2026-09-03).** The multi-model
  era (local 7B, Qwen 3-Max, GLM 5.3) ends; Claude builds this repo alone. The rules
  that lived in this file are collapsed to one line each in
  [`CLAUDE.md`](CLAUDE.md), which is now the single source of truth for how the repo
  is worked on. This file keeps only the numbered decision log. `TOMORROW.md` is
  folded into `PLAN.md` — there is no fourth planning doc.
  - **D21.1 — Polyglot backend, runtime chosen per service (supersedes the old
    "Backend: Node.js + Express" letter; owner's call 2026-09-02).** The seam between
    screens is HTTP, so each screen or service picks the runtime whose libraries the
    work actually lives in, and never imports across the line — CLAUDE.md Rule 5
    already enforces the isolation that makes this safe. Python/FastAPI keeps
    finance-os (casparser, yfinance, AMFI, tax math), RAG (local embeddings), the
    Learning backend (SQLite + SM-2) and the Main Menu; Node/Express keeps the Agent
    Deck's SSE fan-out, Anime, and the MCP servers (the ecosystem is Node-first).
    No screen is rewritten for the sake of its language. This rescopes `PLAN.md`
    item 9 from a 30-50 h migration to a case-by-case choice — the single biggest
    hour saving in the backlog. Cost: two toolchains, which
    `Start_Inky/start_every_screen.py` already handles (the Anime Python launcher
    shim around a Node server is the proof).
  - **D21.2 — 8000 is the Main Menu and nothing else.** `finance-os/backend/main.py`
    hard-coded `port=8000`; running finance-os directly stood Finance up on the Main
    Menu's address, and the menu appeared to have vanished. It now reads the Finance
    screen's own `settings_for_finance.py` (8001), so a port is still written in
    exactly one place. The cutover note's pre-check commands were wrong the same way;
    that note described a migration finished months earlier and was deleted with the
    move in D21.5.
  - **D21.3 — The Model screen serves a page again (supersedes D10.1's redirect,
    restoring D10's iframe).** `GET :8005/` 307-redirecting straight to the gateway
    meant that whenever OmniRoute was down the browser left Kage entirely and landed
    on a connection error with no way back to the menu. The screen now serves
    `Page/page_for_model.html`: it asks its own `/api/model/overview`, embeds the
    gateway dashboard when that answers `ok`, and otherwise shows which command
    starts the gateway. It re-checks every 10 s, so the gateway coming up needs no
    reload. Honest states, CLAUDE.md Rule 8.
    - **D21.3.1 — The menu links straight to the gateway (2026-09-04).** D21.3's
      iframe embed never rendered: the OmniRoute dashboard sends
      `X-Frame-Options: DENY` and CSP `frame-ancestors 'none'`, so `:8005/` showed
      the status header over a blank pane and the owner had to type `:8003` by hand.
      Two changes: (1) the MODEL menu row now points **directly** at the gateway.
      A screen may declare `MENU_ADDRESS` in its settings; `read_screen_settings.
      web_address()` returns it for direct access (still the folder path behind the
      one-port proxy, still no screen named anywhere). The Model screen still runs
      on `PORT` 8005 — the launcher starts it there and it stays reachable for the
      `/api/model/overview` probe and the "gateway is down" page. (2) The `:8005`
      page, when visited directly, forwards to the dashboard with `location.replace`
      when the probe says `ok` and keeps D21.3's start-it panel when it says down;
      `GET :8005/` is served `Cache-Control: no-store` so a stale pre-forward copy
      can't linger. Same "can't be framed, so link out" move D24 made for DeepSeek.
  - **D21.4 — The old agent layer is deleted (2026-09-03).** Repo-root `Agents/`
    (20 folders holding one `description.txt` each, every one reporting "not built")
    and `Shared_By_All_Agents/` were kept as a reuse pool for a future agent version.
    They cannot run: `the_supervisor.py` imports `do_one_task`, which exists nowhere
    in the repo, so the three Main Menu endpoints that called it
    (`agents/home_blocks/refresh`, `calendar/events` GET and POST) returned
    "the agent layer could not be reached" on every request, and every other file in
    that folder existed only to serve the supervisor. Both folders are deleted, along
    with those endpoints, `agents/fleet`, `agents/{name}/files`, `/governor`, and the
    two plain-page scripts that read them (`home_data.js`, `home_agents_box.js`) plus
    the agents box markup. The Next export the Main Menu actually serves never called
    any of them. `Screens/Agents/` is the agent surface; the local-model chain the
    deleted files implemented ended with D21.
  - **D21.5 — Finance is one folder again (2026-09-03).** The Finance app was built
    at the repo root as `finance-os/` while a three-file shim under
    `Screens/Finance/` mounted it — the only screen split across two locations. It
    now sits under its screen in the shape the Anime screen already used for its Node
    server: `Backend/app/` (the FastAPI app + its requirements and data),
    `Page/next_app/` (the Next source, matching every other screen), `Shared/`, with
    `Backend/build.py` mirroring `Page/next_app/out` into `Backend/app/static`. The
    dead pre-rebuild trees (`Screens/Finance/{Page,Calculations,Setup}`, 409 MB) are
    deleted. `Start_Everything.bat` now installs the app's own `requirements.txt`,
    which no loop had ever picked up — a fresh clone got a Finance screen that could
    not import casparser, mftool or pdfplumber, and only said so at the first request.
  - **D21.6 — `Shared_By_All_Screens/` shrunk to what is actually shared
    (2026-09-03).** Eight of its twelve modules had exactly one caller, the Main
    Menu — a shared file with one caller is not shared, it is misplaced. Moved into
    `Main_Menu/Backend/` with their paths corrected: `format_indian_money`,
    `health_check`, `read_and_write_numbers`, `trace_every_action` (with its
    `Trace_Ledger/` and the rotate script), `tail_the_trace_ledger`, and
    `code_change_monitor` (with its toggle file). Deleted: `mark_unverified_numbers`,
    `show_not_built_yet` and `Column_Contracts/frozen_column_names.json`, all with no
    reader at all. `add_and_search_the_knowledge_base.py` — the RAG implementation the
    unbuilt Storage screen will be ported from — moved to `.scratch/drive-storage/`
    beside the brief that cites it, since it has no caller until that screen exists.
    What stays is what two or more trees genuinely use: `read_screen_settings` (the
    menu + four launcher scripts), `restart_signal` and `clear_every_data_cache` (the
    menu + the launcher), `Look_And_Feel/` (four screens), and the `Current_Numbers/`
    noticeboard (the menu + a Finance backfill script). The folder still trends to
    empty — `PLAN.md` item 8.
  - **D21.7 — `TREE.md` (2026-09-03).** A root-level map of every file in the repo
    with one line each, generated and annotated by hand. It is a snapshot, not a
    source of truth: ports live in each screen's settings file, rules in `CLAUDE.md`,
    the backlog in `PLAN.md`. Adding a screen means adding its lines here.

## D23 — The Calendar card (2026-09-03)

- **D23.1 — The card gained a switch and lost its decoration.** On the owner's
  instruction the `OPEN CAL` pill became a two-way switch (`CAL` / `WAKA`), so
  WakaTime opens *in this card* rather than another tab. The world-clock row
  (USA PT / USA ET / LONDON) and the Q1–Q4 quarter grid both came out; a real
  month grid replaced them. The quarter grid was gesturing at "a year's rhythm at
  a glance" with a decorative pattern — the month grid does that job on real
  WakaTime seconds (each cell tinted by how much was coded that day) *and* gives
  every day a real cell to hover. `WHAT'S NEXT` is unchanged in shape and now
  reads real events.
- **D23.2 — Hover opens to the right, never over the grid.** A day cell carries a
  marker only when that day actually has something: a filled amber dot for a real
  calendar event, a hollow amber ring for a pending agent proposal, a grey dot for
  an agent note. Hovering (or keyboard-focusing) such a cell opens a popover in
  the empty gutter between the left column and the centre core — so it never
  covers the grid being read, and there is room for a real list with buttons.
  Cells with nothing do not open anything, so hovering is never a guess.
- **D23.3 — Observations are written, intentions are not.** The nightly agent
  produces two kinds of output and they are stored in two different tables.
  *Notes* describe the past and their evidence is the day's real signals
  (WakaTime seconds, this repo's commits for that day, existing events, what the
  Email card flagged) — they are written straight to the store. *Proposals* are
  events it wants to add; they sit as `pending` and are **never** written to
  Google by a sync. Writing to a real calendar rings a real phone, so it takes a
  deliberate click on *Add to calendar* in the popover. `CALENDAR_AUTO_WRITE`
  ships off; it exists so the owner can turn it on after watching a week of
  proposals. *Dismiss* on an already-written proposal deletes the Google event
  again — every agent-written event carries
  `extendedProperties.private.kage_agent = "1"` so it stays findable and undoable.
- **D23.4 — WakaTime auth is the API key, not OAuth.** One local user reading his
  own stats has no third party to consent; OAuth would add a redirect URI, a
  consent tab and refresh tokens, and an app secret is one more thing to leak.
  The key is base64 over HTTP Basic, read from the gitignored
  `Calendar_Data/wakatime.json` or the env.
- **D23.5 — The free plan's 7-day window is snapshotted, not worked around.**
  WakaTime free exposes only the last week. Every sync writes those seven days
  into `calendar.sqlite`, so history accumulates from the day the key is added
  regardless of plan, and the week bars and the month tint read the local
  snapshot rather than the API. A range that needs a paid plan returns 402; that
  is reported as a sentence beside the view, and the rest keeps working.
- **D23.6 — Two brains, one prompt.** `CALENDAR_AGENT_BACKEND=claude_cli`
  (default) is the Email card's proven path — one `claude -p` per run, already
  logged in, no key in `.env`. `omniroute` POSTs the same prompt to the gateway on
  8003, which is where Hermes and DeepSeek arrive (`PLAN.md` item 3). A brain that
  is unreachable reports `offline` and the run is skipped — it never guesses
  something onto a real calendar.
- **D23.7 — Google not being set up is a sentence, not an empty month.** The grid
  still draws September because the dates are real; underneath it says "Google
  Calendar not set up" and "Dates are real; event data is not connected", so an
  empty row is never mistaken for a clear day (Rule 8). Setup for both
  connections: `Main_Menu/CALENDAR_SETUP.md`.

## D24 — The Deepseek screen: DeepSeek Harness, for traces (2026-09-03)

- **D24 — A nav for the harness, because the point is watching.** `dsh`
  (DeepSeek AI's agent harness, MIT) shows every prompt, tool call and file
  write an agent makes, step by step. That is the reason this screen exists:
  to see what the agents are actually doing rather than trust a summary. The
  screen embeds dsh's web profile the way the Model screen embeds the
  gateway dashboard (D10), with an "open in a tab" link beside it because a
  page that refuses to be framed must still be reachable.
- **D24.1 — The harness reaches models through the gateway, not DeepSeek's
  cloud.** The parked plan recorded a blocker: dsh ships only DeepSeek-cloud
  LLM adapters, so a local or third-party model needed a custom adapter
  (~half a day) or a baseURL gamble. Neither was necessary.
  `@deepseek-ai/dsh-llm-pi-ai` accepts hand-declared OpenAI-compatible
  providers (`api: openai-completions`), and OmniRoute is exactly that. So
  `llm-pi-ai.providers.omniroute` points at 8003 and the harness reaches
  `deepseek-v4-*` with no adapter written and no second API key held. A
  hand-declared route needs all three of `api`, `baseURL` and a non-empty
  `models` list or dsh rejects it on save.
- **D24.2 — Kage never starts the harness.** `dsh web` runs in its own
  window (Rule 20). "not running" is a first-class state that names the
  command, so a dead harness is never mistaken for an idle one (Rule 8).
- **D24.3 — The installer edits text, never a YAML round-trip.** The first
  version dumped the parsed settings back out and silently deleted the
  comment block documenting the other provider. `install_dsh_provider.py`
  now inserts its block as text inside the existing `providers:` mapping,
  backs the file up first, and leaves every other byte alone. Configs are
  read by people; a writer that eats their documentation is a broken writer.

## D25 — The Hermes screen: the profile fleet (2026-09-03)

- **D25 — The profile is the unit, and its history is the training.** Hermes
  Agent (Nous Research) keeps a fleet under `%LOCALAPPDATA%\hermes\profiles`,
  each with a `SOUL.md` persona, a model choice and its own chat history.
  That history *is* the bot's memory — "training an agent" here means a
  profile accumulating what it learned across sessions, not fine-tuning
  weights. The screen reports the fleet: what each profile runs on, whether
  it has a soul, and the command to run it.
- **D25.1 — One gateway entry, declared for all, opted into by hand.**
  `custom_providers.omniroute` is added to the install-wide config so any
  profile can name it, but no profile's default model is changed. Declaring
  is additive and reversible; repointing fifteen agents is a separate
  decision and not one to make as a side effect of wiring.
- **D25.2 — The screen never runs an agent.** A run costs money and mutates
  that profile's memory. A page open in a tab must never cause one, so the
  screen shows `hermes -p <name> chat` to copy rather than a button.
- **D25.3 — Keys never leave the process.** Profile configs carry literal
  `api_key` values for custom providers. The overview endpoint redacts every
  secret-looking key recursively before serialising, so an open tab cannot
  show one even when the config on disk holds it.
- **D25.4 — Hermes' `custom_providers` takes a literal key, so one is
  written.** Unlike dsh's `apiKeyEnv`, Hermes wants the value. The installer
  copies `GATEWAY_API_KEY` out of the repo's `.env` into
  `%LOCALAPPDATA%\hermes\config.yaml` — outside the repo and outside git
  (Rule 7), but a real key at rest on disk, which is worth knowing rather
  than discovering.

## D26 — Tab navigation keeps browser history shallow (2026-09-04)

- **D26 — One Back press per level, not per tab.** Every screen's tab bar
  used `<Link>` (= `router.push`), so visiting Overview → Investments →
  Analysis → Trade Desk left four history entries and Back walked through
  every one before reaching the Main Menu. A screen's stack now never
  grows past `[Main Menu, Overview, current tab]`: a small `useShallowTabNav`
  in each screen's own nav component (`Finance/…/app/finance/layout.tsx`,
  `Learning/…/components/Rail.tsx` — copied, not shared, per Rule 5)
  intercepts the plain left-click and routes it — **to Overview:**
  `router.back()` (Overview is always the entry just below a tab);
  **Overview → tab:** `router.push` (the one entry above Overview);
  **tab → tab:** `router.replace` (swap that one entry). `<Link>` is kept
  for prefetch and a real href, so middle-/right-click still open a tab.
  Single-view screens (Model, Deepseek, Hermes) and the two-route Agents
  deck need nothing. Anime's SPA is out of the repo.
  - **D26.1 — HTML shells are served `Cache-Control: no-cache`.** The bug
    hid twice behind stale caches: the exported `*.html` shells point at
    hash-named `_next/*` chunks, and FastAPI's `FileResponse` sent no
    cache header, so a browser kept an old shell (and its old JS) for
    hours and the fix "didn't land." Finance (`app_factory.py`) and
    Learning (`server_for_learning.py`) now send `no-cache` on every HTML
    shell; the hashed assets stay cacheable because the hash busts them.
    Same class of staleness as D21.3.1's Model page.
