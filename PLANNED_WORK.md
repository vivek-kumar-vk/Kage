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

## P8 — Wire the Finance telemetry panels to live endpoints
- **Status:** queued
- The TELEMETRY tab and the two blueprint blocks on Overview
  (`TotalBalanceReadout`, `FundTiers`) currently read
  `Screens/Finance/Page/next_app/app/lib/blueprintSeed.ts`. Real numbers there
  (total balance, the three emergency-fund tiers, the target) come from the
  blueprint; everything tagged `SEED` is a demo placeholder.
- Swap each `SEED` field for its source and delete it from the seed file:
  - `totalBalance` ← `/api/finance/liabilities` `total_assets`
  - `cashFlow` ← `/api/finance/money` (income / fixed-bills lines)
  - `totalDebt` ← `/api/finance/debt`
  - `investments` / `portfolioValue` ← `/api/finance/portfolio-analysis`
  - `goals` ← no endpoint yet; add one or drop the RPM gauges
  - `buckets` fill % ← derive from buffer tiers + surplus allocation, or keep illustrative
- The 3-tier emergency-fund view (`FundTiers`) is richer than the backend's
  2-tier `g2_buffer` gate (`buffer_tier_1` / `buffer_tier_2` in
  `check_investment_gates.py`) — reconcile when wiring.
- Built 2026-08-28 as an F1/telemetry skin, additive, local-model-authored;
  orchestration notes in `.scratch/finance-telemetry/`.

## P9 — Finance realism pass (F1-feel Overview + Investments)
- **Status:** in progress — building (Phase 1 of 6)
- Replace the AI-generated F1 costume with a **researched F1 broadcast/team-tool
  feel**: **Ferrari livery on Overview** (red `#DC0000` anchor, evening
  charcoal-navy, yellow sparing), **Red Bull livery on Investments** (blue
  `#1E5BC6` dominant, midnight navy, red/yellow trim), a **shared F1 interaction
  language** (timing-tower rows, sector-colour deltas, tabular nums, wipe-in
  entrances, ▲▼ trend glyphs, one livery edge per panel), drifting sakura +
  evening tone. Overview: per-block viz on seed data, remove `ActivityRail` +
  chrome, `224041.png`-style goals timing-row list (4 placeholder rows).
  Investments: `090804.png` holdings-table replica, RB livery, replacing the
  panel. Shared "paddock" shell with a per-tab team-accent indicator; Debt +
  Portfolio inherit it, internals a follow-up.
- **Overrides D1** (amber-only) → log **D1.1** + the D-a two-livery revision in
  `AGENTS.md` at Phase 5.
- Map: `.scratch/finance-realism-pass/map.md` → "Phased build" (Phases 0–5,
  replaces decision tickets 01–07). F1-UX research:
  `.scratch/finance-realism-pass/research/f1-feel.md`.
- Local-model-authored via the caged loop; **one commit per finished task**;
  `ui-gap-scout` (runs on the local model) reviews each finished task + does an
  end-of-effort reconcile vs. the ask (`.scratch/lm-ui-gaps/`).
- **Out of scope here:** live endpoint wiring (P8), Portfolio Analysis tab
  rebuild (needs its own research-first plan), real goal/holding values.
- Session plan: `~/.claude/plans/yes-please-procced-and-zazzy-dawn.md`.
