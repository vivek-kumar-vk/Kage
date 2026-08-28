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

[`PLANNED_WORK.md`](PLANNED_WORK.md) holds the list with status and detail. Top
items: observability on every tab; remove `Shared_By_All_Agents/` and
`Shared_By_All_Screens/` entirely; build the Enhancement tab UI.

## Design decisions (Rule 8)

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
- **D3 — CSS/SVG + framer-motion for the telemetry motion.** No Three.js added
  to the Finance app (keeps the `output: "export"` bundle; framer-motion was
  already a dep).
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
