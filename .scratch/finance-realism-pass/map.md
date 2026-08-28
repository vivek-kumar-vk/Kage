# Map: Finance realism pass

Label: wayfinder:map · Tracker: local markdown (`.scratch/finance-realism-pass/`)

## Destination

A built realism pass on the Finance screen that **feels like an F1 broadcast /
team tool** — two liveries, one interaction language:

- **(A) Overview tab — Ferrari livery.** Ferrari red `#DC0000` anchor on a warm
  evening charcoal-navy base, yellow `#F7D117` badge accents sparing, drifting
  sakura (warm-tinted), evening tone. One visualization per block (line/area,
  radial arc, bar/segmented meter, donut) on **seed data**. `ActivityRail` +
  chrome removed. A `224041.png`-style **goals list** (4 placeholder rows,
  user-placed icon slots) replacing `GoalsGauges`.
- **(B) Investments tab — Red Bull livery.** RB blue `#1E5BC6` dominant on an RB
  midnight-navy base, RB red `#DC052D` on trim/negative only, RB yellow `#F7C300`
  on the single best row, sakura (cool-tinted). Rebuilt as the **`090804.png`
  holdings-table replica** (data `app/lib/replicaHoldings.ts`), **replacing** the
  current Investments tab entirely.
- **(C) Shared "paddock" shell** — nav, header, footer, background — carries a
  thin **team-accent indicator that changes per tab** (Ferrari-red on Overview,
  RB-blue on Investments); layout/type/motion constant across tabs. All tabs
  inherit it (Debt + Portfolio internals are a follow-up).

Shared F1 interaction language (broadcast-derived): timing-tower list rows,
sector-colour delta semantics (purple = best, green = ahead, yellow = flat, alert
red stays "act now" only), tabular numerals, wipe-in panel entrances, ▲▼ trend
glyphs, one diagonal livery edge per panel. Detail in
[research/f1-feel.md](research/f1-feel.md).

## Notes

- **This effort overrides wayfinder's plan-only default** (user, 2026-08-29:
  "plan all ur self and just give me the final result"). All decision tickets are
  resolved by the orchestrator from the research + existing code; the map now
  carries the **phased build** through to done.
- The local model authors every code file ([[local-model-build-loop]]); the
  orchestrator writes prompts, runs `tsc`/`lint`/`build`, does the browser pass,
  and **owns cross-cutting edits** (globals.css tokens, page.tsx grid/layout,
  mechanical removals). **One `git commit` per finished task.**
- Target: `Screens/Finance/Page/next_app/` — patched Next (read its `AGENTS.md`),
  React 19, Tailwind v4 (`@theme`), framer-motion.
- **No chart lib, no Three.js** (repo D3). Visualizations = hand-rolled SVG +
  framer-motion.
- Amber-only rule **D1 is overridden** → record as **D1.1** in `AGENTS.md` at
  Phase 5, together with the **D-a revision** (two liveries, not one palette).
- Build harness: `.scratch/finance-telemetry/run_task.py` + `bump.py`; 90 s
  cooldown, pre-task RAM/GPU gate, every resource < 90%, VRAM ≤ 5 GB.
- Gap profiling: `ui-gap-scout` (runs on the local model) reviews **each finished
  task once**, reconciles delivered-vs-ask (deferred vs. dropped), emits a
  `carry-forward` line, maintains `.scratch/lm-ui-gaps/{ledger,prompt-contract,
  improvement-progress}.md`. See [[verify-builds-in-browser]].

## Decisions so far

- **D-a (REVISED 2026-08-29)** — not one palette. **Ferrari livery = Overview,
  Red Bull livery = Investments, shared F1 interaction language throughout.**
  Exact hexes + semantics in `research/f1-feel.md`. Still no Scuderia wordmark /
  shield / helmet-car icons / speedo-as-nav / AI-art; realism bar `224041.png`.
- **D-b Visualizations** — rich per-block viz, vocabulary varies per block
  (line/area + sparkline, radial arc, bar / segmented meter, donut). Hand-rolled
  SVG + framer-motion. Delta values use sector-colour semantics.
- **D-c Data** — seed only (`app/lib/blueprintSeed.ts` / `replicaHoldings.ts`).
  Live wiring is follow-up (`PLANNED_WORK.md` P8).
- **D-d Remove `ActivityRail`** + all plumbing (`useLiveEvents`, `LiveBadge`,
  `/api/finance/live` consumer, the right-rail column in `app/page.tsx`).
- **D-e Remove chrome text** — header subtitle line; footer disclaimer line;
  "could not reach /api/finance/command" error string.
- **D-f Shell scope** — nav + header + footer + background. `SpeedoNav` → plain
  vertical `PaddockNav`, tab-switch behaviour unchanged. Debt + Portfolio inherit
  the shell; internals are a follow-up effort.
- **D-g Goals block** — `224041.png`-style timing-row list (icon slot + name +
  ₹current/₹target + progress bar + delta badge), replacing `GoalsGauges`, end of
  Overview. 4 placeholder rows; icons at `public/goals/<slug>.png` with a
  fallback glyph; user supplies real names / values / icons later.
- **D-h TELEMETRY tab** — keep the tab, slimmed. After Overview absorbs the
  summary panels, remove only the overlapping panels from `TelemetryPanel`; strip
  the seed/endpoint disclaimer strings there too.
- **D-i Investments tab = replica, replacing everything** — RB livery (not the
  screenshot's light theme). NAV ledger / per-holding XIRR / `AskStrip` removed.
  Editable fields + analysis/save/delete buttons = non-functional visual
  placeholders.
- **D-j Portfolio Analysis tab = out of scope** — separate research-first plan.
- **D-k Two token groups** — `--f1-*` (shared structural + semantic:
  best/ahead/flat, timing-row, wipe, edge) always on; `--liv-*` (per-tab livery
  bg/surface/line/text/accent/accent-2/glow/petal) set on each tab's wrapper.
- **Research: F1 feel** — resolved AFK, `research/f1-feel.md`. Exact Ferrari / Red
  Bull palettes, broadcast sector-colour semantics, the shared primitive set.

## Not yet specified

- Debt + Portfolio tab internals — graduate after Phase 3 locks the vocabulary.
- Sakura-petal motion budget on the RTX 3050 — tune during Phase 1 (petal
  component already built, `app/theme-lab/petals.tsx`).
- Whether goals needs a themed summary stat above the list — decide in Phase 2.

## Out of scope

- Wiring Overview blocks to live endpoints — stays on seed (`PLANNED_WORK.md` P8).
- Portfolio Analysis tab rebuild — separate research-first plan.
- Swapping in real goal / holding values — user edits seed data by hand.
- Debt + Portfolio tab internal reskins — follow-up effort.

## Supersedes

- `.scratch/finance-telemetry/` X1–X9 (light-theme replica sketch) — replaced by
  Phase 3.
- Tickets 01–07 (decision tickets) — replaced by Phases 0–5 below; the user asked
  the orchestrator to resolve all decisions and carry the map to a built result.

## Phased build

Each phase = a batch of one-file local-model tasks. Per task: prompt (with
`prompt-contract.md` prepended) → generate → `tsc`/`lint`/`build` gate → fix loop
→ orchestrator reads the diff → scout review + reconcile → **commit** → 90 s
cooldown. Browser-verify at each phase boundary. Phases are sequential; a phase
ships (all green + committed + verified) before the next starts.

- **Phase 0 — Tokens + preview.** Orchestrator writes `--f1-*` + both `--liv-*`
  sets into `globals.css` `@theme`. Local model builds nothing new; `/theme-lab`
  is repointed to show both liveries on the existing stage for one glance-check.
  Ship: tokens committed, user has seen both liveries.
- **Phase 1 — Shell + primitives.** Local model authors the shared primitive
  components (`TimingRow`, `DeltaBadge`, `TrendArrow`, `WipeIn`, `LiveryEdge`,
  `TelemetryCard`, `Sparkline`, `StatDial`, `SegmentMeter` — see f1-feel.md §3),
  one file per task. Orchestrator: `PaddockNav` (from `SpeedoNav`, same
  `items`/`tab`/`onSelect` contract), header/footer edits, background layer,
  remove `ActivityRail` + plumbing + right-rail grid column. Ship: shell reskinned
  on all tabs, primitives compile + render in isolation.
- **Phase 2 — Overview (Ferrari livery).** Wrap Overview in `--liv-ferrari`.
  Local model rebuilds each block as its own viz using Phase 1 primitives; the
  goals timing-row list (4 rows + icon slots) replaces `GoalsGauges`. Orchestrator
  removes the command-error string, owns the grid. ~8–12 tasks. Ship: Overview
  matches the Ferrari-livery + F1-language intent against `224041.png` realism.
- **Phase 3 — Investments (Red Bull livery).** Delete `InvestmentsPanel`
  internals; local model builds the `090804.png` replica table (data
  `replicaHoldings.ts`) with `TimingRow` treatment, RB livery, placeholder
  editable fields + buttons. ~6–8 tasks. Ship: replica renders, RB livery, tab
  switch intact.
- **Phase 4 — TELEMETRY de-dup + cleanup.** Remove the panels Overview now owns
  from `TelemetryPanel`; strip disclaimer strings; slim the tab. Ship: no
  duplicate panels, no disclaimer text anywhere.
- **Phase 5 — Capture + close.** Delete `/theme-lab` (prototype captured to a
  throwaway branch); log **D1.1** + the **D-a revision** in `AGENTS.md`; update
  `PLANNED_WORK.md` P9; gap-scout end-of-effort pass (whole effort vs. the ask);
  fold the ledger into [[local-model-build-loop]]. Final commit.
