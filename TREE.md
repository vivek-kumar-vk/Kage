# TREE — every file in Kage, and what it does

Generated 2026-09-03, after the Claude-only cleanup. One line per file.

Rules for reading it: folders that are generated, vendored, or private are
**collapsed to a file count** — `node_modules/`, `.next/`, `out/`, `static/`,
`__pycache__/`, `.git/`, `.venv/`, and the data folders holding your real records.
Nothing inside them is hand-written, and none of it belongs in a map.

Rules for keeping it: this file is a snapshot, not a source of truth. The ports it
mentions live in each screen's own settings file; the rules live in `CLAUDE.md`; the
backlog lives in `PLAN.md`. When you add a screen, add its four lines here.

---

## Root

```
.env                          your real secrets — gitignored, never committed
.env.example                  the same keys with the values blanked, as the template to copy
.gitignore                    what never reaches the public repo: secrets, personal data, builds, databases
AGENTS.md                     the numbered design-decision log; points at CLAUDE.md for rules
CLAUDE.md                     THE rules file — 20 one-line rules, the port table, how to run it
LICENSE                       MIT
PLAN.md                       THE backlog — everything not yet done, one ordered list
README.md                     the public front page: what Kage is, the stack, how to run it
TREE.md                       this file
Agent-idea.png                the 16-bit reference art the Agent Deck pixel office is built against
LEARNING_SEED_MAINTAINER.md   the project instructions for the Claude chat that maintains your study seed file
```

## `.claude/` — Claude Code's own settings

```
settings.local.json           tool permissions for this machine
```

## `.obsidian/` — Obsidian's vault settings (gitignored)

```
app.json                      editor preferences
appearance.json               theme
core-plugins.json             which built-in plugins are on
graph.json                    graph-view settings
workspace.json                which panes were open last
```

## `.scratch/` — working notes, briefs and mockups (gitignored)

Outcomes land in `PLAN.md`; this folder is the scaffolding they were built from.

```
agents-warm-v2/
  mockups.html                the warm paper/honey mockup the Agent Deck was re-skinned against
  mockup-agent-deck.png       rendered mockup, deck tab
  mockup-pix-agents.png       rendered mockup, pixel office
  shots/                      browser screenshots taken during that build, plus the tab id used
agents-workspace/
  QWEN_BUILD_PROMPT.md        the Agent Deck V1 brief — shipped; kept as the house-style template
  map.md                      the turn-by-turn map that brief was executed from
drive-storage/
  QWEN_BUILD_PROMPT.md        the build brief for the unbuilt Storage screen (PLAN item 2)
  map.md                      its turn map
  reference_add_and_search_the_knowledge_base.py
                              the working RAG implementation the Storage screen will be ported from —
                              parked here because it has no caller until that screen exists
dsh-local-model/
  PLAN.md                     the parked local-model observability plan (PLAN item 11)
finance-investments-shots/    browser screenshots proving the Investments/Analysis/Trade Desk build
finance-os-build/
  BUILD_BRIEF.md              the brief the whole Finance app was built from
  run_build.py                the phase-gated build runner that executed it
  run_build_all.bat           one-click wrapper for the above
  serve_dev.py                dev server used during that build
  gates/                      one executable pass/fail gate per phase, plus shared helpers
  manifests/                  the task list for each phase
  progress/                   what each phase actually produced, and the final run report
  spec/                       the written spec for each phase
finance-os-port/
  QWEN_PORT_PROMPT.md         the brief for porting the old Finance engine (PLAN item 1, active)
  APPLY_PLAN.md               how that port gets applied
  COLLECTED_ANSWERS.md        your locked answers to the port's open questions
  _build_bundle.py            assembles the brief's context bundle
finance-redesign/
  mockups/                    the Aurum HTML mockups the Finance Overview was built against
  *.png                       rendered versions of those mockups
finance-telemetry/
  HARNESS.md                  the shared run harness for the old local-model build loop
  run_phase.py                phase runner from that era
  run_task.py                 single-task runner from that era
  bump.py                     progress bumper
  lm_chores.py                offloaded chores (commit messages, summaries)
glm-briefs/
  README.md                   what these four parallel briefs were
  1_AGENT_DECK_v2_groundwork.md        + __CONTEXT.md — the Agent Deck V2 brief
  2_FINANCE_backend_lots_history.md    + __CONTEXT.md — the Finance lots/history brief (PLAN item 1)
  3_FINANCE_frontend_overview.md       + __CONTEXT.md — the Finance Overview brief
  4_STORAGE_drive_layer.md             + __CONTEXT.md — the Storage screen brief
learning-redesign/
  PLAN_V3.md                  the Learning OS v3 plan and its milestones (PLAN item 12)
  mockups/                    the Ember Studio mockups for all five tabs plus a room view
  live_*.png                  screenshots of what actually shipped, tab by tab
lm-ui-gaps/
  README.md                   what the UI-gap ledger was for
  ledger.md                   the gaps the scout found, build by build
  prompt-contract.md          the contract prepended to every local-model prompt
  improvement-progress.md     whether that loop was actually improving
  SOUL.md                     the scout bot's persona
model-page-gateway/
  map.md                      the Model screen + gateway wayfinder
  issues/                     the four numbered issues that build was cut into
```

## `Main_Menu/` — the frame you land on, port 8000

It discovers every screen by walking `Screens/`. No screen is named anywhere in it,
and a test fails if one ever is.

```
Backend/
  server_for_main_menu.py     the server: navigation, the noticeboard blocks, live traces, static mounts
  settings_for_main_menu.py   its port (8000), page path, shared look-and-feel paths, watched folders
  find_every_screen.py        walks Screens/, validates each screen_definition file, returns built + not-built
  read_and_write_numbers.py   reads the shared noticeboard file that carries the current figures
  format_indian_money.py      formats rupee amounts the Indian way (lakh/crore grouping)
  health_check.py             one honest health answer for this screen
  trace_every_action.py       writes this screen's own trace ledger, one JSONL line per action
  tail_the_trace_ledger.py    streams those trace lines back out for the live SSE endpoint
  code_change_monitor.py      fingerprints the repo so the dev auto-refresh knows when code changed
  dev_auto_refresh_toggle.json  whether that auto-refresh is on (local only, gitignored)
  Trace_Ledger/               this screen's own trace files, plus the script that rotates and prunes them
Page/
  page_for_main_menu.html     the plain HTML menu — the fallback served when the Next export is absent
  js/home_windows.js          the floating windows (notes, calendar) on that plain page
  next_app/                   the Next.js menu that is actually served when built
    app/page.tsx              the page itself
    app/layout.tsx            the shell around it
    app/globals.css           its styles
    app/components/AgentRing.tsx         the ring of agent nodes
    app/components/RingNode.tsx          one node on that ring
    app/components/CenterCore.tsx        the core at the centre of the ring
    app/components/ParticleCore3D.tsx    the Three.js particle core behind it
    app/components/TopBar.tsx            the header
    app/components/CalendarPanel.tsx     the calendar panel
    app/components/EmailPanel.tsx        the mail panel
    app/components/RoutinesPanel.tsx     the routines panel
    app/components/SkillsDeckPanel.tsx   the skills panel
    app/components/YouTubeStudioPanel.tsx  the video panel
    package.json, package-lock.json      its dependencies
    next.config.ts            static export config
    tsconfig.json             TypeScript config
    postcss.config.mjs        Tailwind/PostCSS pipeline
    eslint.config.mjs         lint rules
    next-env.d.ts             generated type shim
Setup/
  requirements_for_main_menu.txt   what this screen needs installed
```

## `Screens/` — one folder per screen

### `Screens/Agents/` — AGENT DECK, port 8004

```
screen_definition_for_agents.py   its menu label, order, and tab list
.gitignore                        its database, seeds and builds stay out of git
AI_Agents/<Name>/
  description.txt                 what that agent is for
  office.json                     where it sits on the pixel floor: department, tier, parent
Backend/
  server_for_agents.py            the server: roster, board, events stream, chat, profile files
  settings_for_agents.py          its port (8004) and page path
  db.py                           opens the SQLite database
  schema.sql                      the tables
  seed.py                         fills a fresh database
  seed_local.example.json         the shape your private seed file should take
  README_seed.md                  how seeding works
  agents.db                       the database itself (gitignored)
  services/agents.py              the roster and per-agent reads and writes
  services/board.py               the kanban board of ideas
  services/events.py              the append-only event log plus its SSE stream
  services/office.py              builds the floor registry from every office.json
  services/omni.py                the one LLM seam — an OmniRoute client, not yet wired to a live ask
Page/
  page_for_agents.html            the plain fallback page
  next_app/
    app/page.tsx                  the pixel office
    app/workspace/page.tsx        the Slack-shaped deck
    app/layout.tsx, globals.css   shell and theme tokens
    components/office/PixelOffice.tsx   the canvas renderer and camera
    components/office/pixelArt.ts       the palette, sprite matrices and painters — art as code, no image files
    components/office/roomPlan.ts       composes those sprites into one floor buffer per viewport
    components/deck/DeckRail.tsx        left rail: search, rooms, roster with presence dots
    components/deck/AgentChat.tsx       the per-agent chat pane
    components/deck/ProfilePanel.tsx    the right-hand profile drawer and its file editor
    components/deck/PixelAvatar.tsx     an agent's pixel portrait
    components/BoardRoom.tsx            the ideas board
    components/IdeaCard.tsx             one card on it
    components/IdeaDetail.tsx           that card opened
    components/RunsStub.tsx             the runs room, still an honest stub
    lib/api.ts                    every fetch this screen makes
    lib/office.ts                 client-side floor helpers
Setup/requirements_for_agents.txt  what this screen needs installed
```

### `Screens/Anime/` — port 8006, Node behind a Python launcher, local-only

The whole folder is gitignored — it never reaches the public repo.

```
screen_definition_for_anime.py    its menu label, order, and tabs
Guide_To_Anime_Screen.md          how to run and use it
Backend/
  server_for_anime.py             the Python launcher: finds node, installs once, hands over to server.js
  settings_for_anime.py           its port (8006) and page path
  app/server.js                   the Express server
  app/store.js                    on-disk state
  app/routes/anime.js             one title's details
  app/routes/browse.js            the browse grids
  app/routes/discover.js          discovery feeds
  app/routes/search.js            search
  app/routes/watch.js             the watch page's data
  app/routes/watchlist.js         your list
  app/routes/progress.js          how far through an episode you are
  app/routes/stream.js            stream resolution
  app/routes/hls_proxy.js         proxies the HLS playlist so the player can reach it
  app/routes/subtitles.js         subtitle fetch and conversion
  app/services/anilistService.js  AniList metadata
  app/services/malCache.js        MyAnimeList cache
  app/services/malDiscoveryService.js  MAL-driven discovery
  app/services/malGrid.js         builds the grids from that
  app/services/cache.js           the generic cache
  app/services/nyaaFetcher.js     torrent index queries
  app/services/rssMatchService.js matches RSS entries to episodes
  app/services/torrentManager.js  manages active torrents
  app/sources/anikage_source.js   the direct source, with the torrent path as fallback
  app/models/Torrent.js           the torrent record shape
  app/models/WatchlistEntry.js    the watchlist record shape
  app/middleware/errorHandler.js  one place errors are turned into responses
  app/middleware/rateLimit.js     request throttling
  app/client/                     the Vite + React player UI (src/, built into dist/)
Page/
  page_for_anime.html             the plain page
  anime_responsive.css            its responsive rules
Saved_Records/                    your watch history and list (gitignored)
Setup/requirements_for_anime.txt  what the Python launcher needs
```

### `Screens/Finance/` — port 8001

The app used to live at the repo root as `finance-os/`. It was moved here on
2026-09-03 so Finance is one folder like every other screen.

```
screen_definition_for_finance.py  its menu label, order, and five tabs
DECISIONS.md                      the Finance app's own numbered decisions
finance-datamigration.md          your data-backfill plan (gitignored — contains personal figures)
Backend/
  server_for_finance.py           the thin shim: stands the app up on port 8001, lands you on Overview
  settings_for_finance.py         its port (8001), page path, shared look-and-feel paths
  build.py                        runs `next build` and mirrors the export into app/static
  night_worker.py                 the scheduled job: fetches prices, writes snapshots, takes backups
  app/main.py                     runs the app alone on 8001 (reads the port from the settings file above)
  app/app_factory.py              builds the FastAPI app: routers, static mount, deep-link fallback
  app/startup.py                  startup checks, including the encrypted-volume check
  app/requirements.txt            what the Finance app needs installed
  app/routers/overview.py         the Overview tab's endpoints
  app/routers/investments.py      holdings, lots, the Analyse drawer
  app/routers/analysis.py         the look-through X-ray, overlap, drift, cost and tax
  app/routers/tradedesk.py        watchlist, journal, IPO calendar, global/LRS
  app/routers/debt.py             loans and payoff maths
  app/routers/tracker.py          transactions
  app/routers/accounts.py         accounts
  app/routers/entities.py         the shared entity CRUD behind several tabs (goals, insurance, salary ride on this)
  app/routers/imports.py          CAS PDF and broker-statement import
  app/routers/market.py           market quotes and index data
  app/routers/settings.py         the app's own settings
  app/routers/health.py           its honest health answer
  app/services/db.py              the SQLite connection and schema bootstrap
  app/services/market_data.py     price and NAV fetching — writes only dates a feed actually published
  app/services/fund_reference.py  fund facts and portfolios pulled from public fund pages, cached monthly
  app/services/ipo_calendar.py    the IPO calendar, cached daily
  app/services/calculations/core.py            the shared arithmetic
  app/services/calculations/portfolio.py       portfolio value and the smoothed series
  app/services/calculations/xirr.py            XIRR
  app/services/calculations/ratios.py          risk ratios against the index
  app/services/calculations/analysis.py        overlap, concentration, drift, the fact-based observations
  app/services/calculations/holdings_upsert.py how a holding or a lot is written
  app/services/calculations/backfill.py        rebuilding history from records
  app/services/calculations/debt.py            loan maths
  app/services/calculations/scenario.py        what-if projections
  app/services/calculations/monte_carlo.py     the probabilistic projection
  app/services/calculations/data_health.py     what is missing or stale, said honestly
  app/services/imports/cas.py            reads a CAS statement PDF
  app/services/imports/groww.py          reads a Groww export
  app/services/imports/transactions.py   the shared import path for transactions
  app/services/reference/reference.py    loads the reference JSON below
  app/services/reference/india_income_tax_rules.json     the tax rulebook
  app/services/reference/india_planning_assumptions.json planning assumptions
  app/services/reference/fund_analysis_settings.json     thresholds and targets, with their verified flag
  app/services/reference/sector_for_stocks.json          stock-to-sector map
  app/services/agents/supervisor.py            routes a finance question to a specialist (LLM not yet wired)
  app/services/agents/specialists.py           the shared specialist base
  app/services/agents/investment_specialist.py investments
  app/services/agents/debt_specialist.py       debt
  app/services/agents/tracker_specialist.py    spending
  app/scripts/backfill_from_old_records.py     one-off: load the old records into this database
  app/scripts/backfill_snapshots.py            one-off: rebuild the snapshot history
  app/scripts/check_view_perf.py               checks the database views are fast enough
  app/scripts/set_perms.py                     tightens file permissions on the data folder
  app/scripts/schema.sql                       the tables
  app/data/                                    your database, backups and vector store (gitignored)
  app/static/                                  the built UI the server actually serves (generated)
Page/next_app/                    the Next.js source the export is built from
  app/page.tsx                    root, redirects into /finance
  app/finance/page.tsx            Overview
  app/finance/investments/page.tsx  Investments
  app/finance/analysis/page.tsx     Analysis
  app/finance/tradedesk/page.tsx    Trade Desk
  app/finance/debt/page.tsx         Debt
  app/finance/tracker/page.tsx      Tracker
  app/finance/scenario/page.tsx     Scenario
  app/finance/settings/page.tsx     Settings
  app/finance/layout.tsx            the tab shell around them
  app/globals.css                   the Aurum theme tokens
  components/finance/cards/NetWorthCard.tsx          net worth plus the ridge
  components/finance/cards/PortfolioPulseCard.tsx    portfolio movement
  components/finance/cards/CashflowCard.tsx          money in and out
  components/finance/cards/DebtStatusCard.tsx        what is owed
  components/finance/cards/EmergencyFundCard.tsx     the buffer
  components/finance/cards/GoalsCard.tsx             goal progress
  components/finance/cards/SurplusAllocationCard.tsx where the surplus goes
  components/finance/cards/TopActionsCard.tsx        what needs attention
  components/finance/cards/DataHealthCard.tsx        what data is missing, said plainly
  components/finance/analyse/AnalyseDrawer.tsx       the per-holding drawer
  components/finance/analyse/Explainer.tsx           its plain-English explanation
  components/finance/charts/InvestmentCharts.tsx     the hand-rolled SVG charts
  components/finance/three/NetWorthRidge.tsx         the 3D ridge, with an SVG fallback from the same data
  components/finance/forms/TransactionForm.tsx       adding a transaction
  components/finance/forms/EntityForms.tsx           adding everything else
  components/finance/Card.tsx        the panel shell
  components/finance/FormModal.tsx   the modal wrapper
  components/finance/Skeleton.tsx    loading placeholders
  lib/api.ts                        every fetch this screen makes
  lib/format.ts                     number and date formatting
  lib/types.ts                      the shared types
  next.config.js, tailwind.config.ts, postcss.config.js, tsconfig.json, package.json
                                    build and dependency config
Reference_Data/
  Human_Checklists/What_To_Fill_In.txt   the figures still owed by you (term life, EPF, debt ledger, ...)
  india_income_tax_rules.json            reference copies kept outside the app
  india_planning_assumptions.json        "
  fund_analysis_settings.json            "
  sector_for_stocks.json                 "
  nse_equity_universe.json               the NSE symbol list
Saved_Records/                    your older saved records (gitignored)
Shared/constants/categories.py    the spending categories, for the backend
Shared/constants/categories.ts    the same list, for the frontend
```

### `Screens/Learning/` — port 8002

```
screen_definition_for_learning.py  its menu label, order, and five tabs
.gitignore                         its database and your seed file stay out of git
Ratings_For_Learning_Topics.mmd    a mindmap of the topics and your self-rating on each
Context/                           your personal corpus — resume, master context, the 14-week plan (gitignored)
Backend/
  server_for_learning.py           the server for all five tabs, plus the localhost-only context reader
  settings_for_learning.py         its port (8002), the Next export path, the database path
  db.py                            opens the SQLite database
  schema.sql                       the tables
  seed.py                          fills a fresh database
  seed_local.example.json          the shape your private seed file should take
  seed_local.json                  your real study board (gitignored)
  README_seed.md                   how seeding works
  learning.db                      the database (gitignored)
  learning.db.bak-preD16           your backup from before the v2 rebuild (gitignored)
  learning.db.bak-preD17           your backup from before the v3 rebuild (gitignored)
  services/today.py                the Today cockpit and the focus session
  services/path.py                 tracks, modules and rooms
  services/room.py                 one room's four beats: explain, real-world, lab, checkpoint
  services/recall.py               spaced repetition, SM-2, and the card studio
  services/insights.py             retention curve, mastery map, weak spots, rhythm, coverage
  services/crew.py                 the six learning agents and their approve-cards
  services/sessions.py             what you actually studied, when
  services/common.py               the helpers those services share
  tests/test_honest_zero.py        proves nothing records work that has not happened
Page/next_app/
  app/page.tsx                     Today
  app/path/page.tsx                Path
  app/recall/page.tsx              Recall
  app/insights/page.tsx            Insights
  app/crew/page.tsx                Crew
  app/room/page.tsx                one room, opened
  app/layout.tsx, globals.css      shell and the Ember Studio theme
  components/Rail.tsx              the left navigation rail
  lib/api.ts                       every fetch this screen makes
  next.config.ts, tailwind.config.js, postcss.config.mjs, tsconfig.json, package.json
                                   build and dependency config
Setup/requirements_for_learning.txt  what this screen needs installed
```

### `Screens/Model/` — port 8005

```
screen_definition_for_model.py    its menu label, order, and one tab
GATEWAY_CONFIG.md                 how the OmniRoute gateway is configured
Backend/
  server_for_model.py             serves the page and one honest gateway-status endpoint
  settings_for_model.py           its port (8005), page path, gateway URL and key
Page/
  page_for_model.html             embeds the gateway dashboard when it answers, says what to start when it does not
Setup/requirements_for_model.txt  what this screen needs installed
```

## `Shared_By_All_Screens/` — what is genuinely shared

Everything with only one caller was moved into that caller on 2026-09-03. What is
left has two or more, across different trees. The folder is still meant to reach
empty (`PLAN.md` item 8).

```
read_screen_settings.py       reads a screen's port and page — used by the menu and four launcher scripts
restart_signal.py             the restart flag the menu drops and the launcher polls
clear_every_data_cache.py     clears every screen's cache on restart — used by the menu and the launcher
Current_Numbers/all_current_numbers.md   the noticeboard: current figures, read by the menu and a Finance script
Look_And_Feel/colours_and_fonts.css      the shared palette and type scale
Look_And_Feel/responsive_layout.css      the shared breakpoints
Look_And_Feel/page_not_built_yet.html    what a screen with no page serves, honestly
Look_And_Feel/auto_refresh_watch.js      the dev auto-refresh client
Look_And_Feel/page_tracer.js             sends page actions to the trace ledger
Look_And_Feel/block_guards.js            keeps a block that has no data from drawing a fake one
Look_And_Feel/p5_bg.jpg, p5_bg.webp      the shared background art
Look_And_Feel/Fonts/                     the shared typeface
```

## `Start_Inky/` — how it all starts

```
Start_Everything.bat              double-click: builds the venv, installs everything, starts gateways then screens
start_every_screen.py             starts every screen at once; refuses a port another process holds, and says who holds it
write_ports_for_inky.py           regenerates the port snapshot by reading each screen's own settings
ports_for_inky.json               that snapshot — generated, never hand-edited
run_omniroute.py                  starts the model gateway on 8003, idempotently
run_market_mcp.py                 starts the market-data MCP server on 3101, the tool seam for research agents
serve_everything_on_one_port.py   one address in front of every screen, for a phone or an ngrok tunnel
start_everything_behind_one_port.py  starts the screens behind that proxy and prints the ngrok command
```

## `Sync/` — laptop ⇄ phone over the LAN (gitignored)

```
to_phone.sh                   push the whole tree to Termux, dotfiles and gitignored extras included
from_phone.sh                 pull it back
exclude.txt                   what never crosses: the venv, node_modules, build output
README.md                     how to use the two scripts
```

## Collapsed on purpose

```
.git/                         version control internals
.venv/                        the Python environment — rebuilt by Start_Everything.bat
**/node_modules/              npm packages — rebuilt by `npm install`
**/.next/                     Next.js build cache
**/next_app/out/              the static export — rebuilt by `npm run build`
Backend/app/static/           Finance's served copy of that export — rebuilt by Backend/build.py
**/__pycache__/               compiled Python
**/data/, **/Saved_Records/   your real records — gitignored, never committed
Main_Menu/Backend/Trace_Ledger/  the menu's own trace files, rotated and pruned automatically
```
