# AGENTS.md — Kage

Read this first, every session. Standing rules for this repo; the plan list is
[`PLANNED_WORK.md`](PLANNED_WORK.md).

## Rules

1. **Use the installed custom skills.** Check the skill list at session start and
   invoke the matching skill before falling back to a default approach.
2. **Optimize cloud cost** — for any cloud service, take the cheapest option that
   still meets the requirement exactly.
   - **2.1 (supersedes 2)** — **Optimize Claude Code (Sonnet) usage while
     building this project.** Fewest tokens and tool calls for the outcome: batch
     independent calls, reuse earlier findings instead of re-exploring, keep
     context lean.
3. **Stack.** Frontend: React 19, Tailwind CSS, Next.js, Three.js. Backend:
   Node.js + Express. New and rewritten code uses only these; the current
   Python/FastAPI backends migrate screen by screen (`PLANNED_WORK.md` P4).
4. **Modular to the block.** Every page, tab, and block within a page runs
   independently and calls its dependencies directly, never through a shared
   directory.
5. **Shrink the shared folders.** When you work near `Shared_By_All_Agents/` or
   `Shared_By_All_Screens/`, move logic into its one caller and delete the shared
   file. These folders trend to empty.
6. **Track future work.** Anything named as "later" goes to `PLANNED_WORK.md` and
   a card in the Enhancement tab.
7. **Log every instruction as a numbered item** — a Rule, a Plan
   (`PLANNED_WORK.md`), or a Task. New topic gets a new number. A change to item
   _N_ is filed as _N.1_, _N.2_, …; the highest sub-number is the one in force
   and the parent stays as history. Before adding, diff against what is already
   here and keep only what is new.
8. **Number every logical and design decision** the same way (`D1`, `D1.1`, …),
   wherever it is recorded — not only rules and plans.

## Plans

[`WAYFINDER.md`](WAYFINDER.md) is the ordered map — one workstream at a time.
[`PLANNED_WORK.md`](PLANNED_WORK.md) holds the numbered list with status and detail
(and a `## Active order` + `## Dropped` section). Active now: Finance data migration
(user-led) ∥ Google Drive storage layer (P7, Qwen-led).

## Design decisions (Rule 8)

> **D1, D1.1, D3, D3.1, D4, D5 are HISTORIC.** They governed the pre-finance-os
> Finance frontend at `Screens/Finance/Page/next_app/`, which `finance-os/` V1
> replaced (`657774d`). Kept as history per Rule 7 — **not to be actioned**. See D7.

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
  semantics (purple = best, green = ahead, grey = flat). **Rule 8 still holds** —
  `--f1-alert` (red) is the only "act now" colour and is never decoration; a
  monetary loss uses `--f1-flat` / `--liv-neg`, not alert-red. No Scuderia
  wordmark / shield / helmet-car icons / speedo-as-nav / AI-art. Detail:
  `.scratch/finance-realism-pass/research/f1-feel.md`. Authored by the local
  model; Claude orchestrated + validated.
- **D2 — Seed data for the telemetry panels v1.** New Finance panels read
  `app/lib/blueprintSeed.ts` (blueprint numbers real, rest `SEED`-tagged), not
  live endpoints. Live wiring is `PLANNED_WORK.md` P8.
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
  `PulseCore` radar hero, and a spring page-transition. Rule 8 still holds — red
  is not in the decorative set. All motion freezes under reduced-motion.
  Authored entirely by the local model; Claude orchestrated + validated.
- **D6 — OmniRoute is the model gateway (2026-08-30).** The gateway slot on
  `127.0.0.1:8003` (vacated by the removed LiteLLM tooling) is OmniRoute
  (npm `omniroute`), bound to 127.0.0.1 only, `REQUIRE_API_KEY=true`. The
  Model screen reads it live: health `/api/monitoring/health` + `/v1/models`
  with `GATEWAY_API_KEY` from `.env` (env var wins). Gateway secrets are
  generated into `.env` by the launcher and never committed. Detail:
  PLANNED_WORK P10.
  - **D6.1 — Gateway process ownership.** `Start_Inky/run_omniroute.py` owns
    starting/stopping the gateway (idempotent: an already-running one is left
    alone); `Start_Everything.bat` starts it in its own window before the
    screens. Self-contained — no shared-module imports (Rule 4).
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
  finance-os keeps its decisions in `finance-os/DECISIONS.md`, its cutover note
  in `finance-os/CUTOVER.md`, and its data-backfill plan in
  `finance-os/finance-datamigration.md` (gitignored — contains PII).
- **D8 — Two Learning surfaces, deliberately (2026-08-30).** The standalone
  **`Screens/Learning/`** screen (terminal/CLI theme; tabs Today/Plan/Recall;
  SQLite + seed file; `/ask` stubbed) is the canonical personal-learning surface
  — spec `Screens/Learning/QWEN_BUILD_PROMPT.md`, shipped `ed833dd`. The
  **finance-os "Learning tab"** (`finance-os/frontend/.../learning/`) is
  finance-scoped RAG over public finance primers only; it does not duplicate the
  standalone screen and neither absorbs the other. The old
  `learning-tab-plan.md` (Model-screen theme, full Drive+FAISS) is dropped.
- **D9 — The AGENTS screen is the agent workspace (2026-08-30).**
  `Screens/Enhancement/` → `Screens/Agents/` (`MENU_LABEL="AGENT DECK"`, port 8004).
  A local 3-pane agent workspace ("Deck" theme — Main-Menu DNA, not Slack). The
  kanban "ideas" board is **one room** inside it, owned by `Agent_Head`;
  board card keys stay `ENH-n`. Agent profiles live in
  `Screens/Agents/AI_Agents/` (the screen owns its own agents — Rule 4; V1 seeds
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
  `search`, logical-path addressed under one Drive root folder): FastAPI, port **8007**,
  `MENU_ORDER 6`, one Status tab, hand-rolled HTML status page (no Next app). Built by
  Qwen 3-Max from the house brief `.scratch/drive-storage/QWEN_BUILD_PROMPT.md`
  (map: `.scratch/drive-storage/map.md`); Node migration rides P4 (user chose FastAPI
  for this service over Rule 3's Node letter — the seam is HTTP, consumers don't care).
  Nothing personal lives **only** on local disk.
  - **D11.1 — Adopted gateway.** The Drive transport is npm
    `@piotr-agier/google-drive-mcp` (MIT; service-account auth via
    `GOOGLE_APPLICATION_CREDENTIALS`, scope `drive`), run as a **standalone Streamable
    HTTP server** at `127.0.0.1:3100/mcp` by `Start_Inky/run_drive_mcp.py`
    (`run_omniroute.py` pattern, idempotent, chained into `Start_Everything.bat`).
    The app is an MCP client (official Python SDK) and **never spawns it** —
    gateway-down is an honest first-class state. The app carries zero Google client
    libraries and never opens the SA key.
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
- **D12 — AGENT DECK Pixel Office (Screens/Agents/; 2026-08-31).** The Agents screen
  landing view is a Three.js/react-three-fiber pixel "office stage" driven by an
  append-only `events` table + one SSE endpoint (`Backend/services/events.py`);
  characters animate strictly from real events, roster is registry-driven from
  `AI_Agents/*/office.json` (`{department, tier, parent}`). Old 3-pane workspace
  moved to `/workspace`.
  - **D12.1 — LLM still last.** `omni.py` (OmniRoute client, the one LLM seam) is in
    the tree but `POST /agents/{name}/ask` stays the V1 `{"state":"pending"}` stub.
    Live agent asks are WAYFINDER item 3, after all data wiring.
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

