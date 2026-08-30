# The ask — what the finished Finance screen must feel like

Walking the tabs should feel like an **F1 broadcast / team tool**. Two liveries,
one interaction language. Realism bar = a clean real dashboard, NOT AI-art.

## Liveries (set by a `.liv-*` class on an ancestor — never hard-code these)

- **Overview = Ferrari livery** (`--liv-ferrari`): red `#DC0000` is the anchor
  (headings, active nav, primary strokes); warm evening charcoal-navy base;
  yellow used sparingly for "best" badges only.
- **Investments = Red Bull livery** (`--liv-rb`): blue `#1E5BC6` is the dominant
  chrome/fills; midnight-navy base; red `#DC052D` only on trim / negative
  numbers; yellow `#F7C300` only on the single best row.

A component reads colour ONLY through `var(--liv-bg | --liv-bg-2 | --liv-surface
| --liv-line | --liv-text | --liv-text-dim | --liv-accent | --liv-accent-2 |
--liv-neg | --liv-glow | --liv-petal)` and `var(--f1-best | --f1-ahead |
--f1-flat | --f1-alert)`. **No raw hex anywhere in a component.**

## Shared F1 interaction language

- **Sector-colour deltas:** purple `--f1-best` = session/all-time best, green
  `--f1-ahead` = ahead of plan, grey `--f1-flat` = no change. `--f1-alert`
  (red) is reserved for "act now" — NEVER used to mean "a number went down".
- **Tabular numerals everywhere** a figure appears (`fontVariantNumeric:
  "tabular-nums"` + a monospace family).
- **Big glanceable primary number** at the top of every card; supporting detail
  smaller / secondary.
- **Wipe-in** entrances are allowed but every animation must be frozen under
  `prefers-reduced-motion` / `useReducedMotion()`.
- **One diagonal livery edge per panel** (`className="livery-edge"`), not more.
- Hand-rolled SVG + framer-motion only — **no chart library, no 3D**.

## Data

Seed only — `app/lib/blueprintSeed.ts` (Overview) and
`app/lib/replicaHoldings.ts` (Investments). Never invent a figure. Live wiring
is a later effort.

## Per-file check

- Does every colour come from a `var(--liv-*)` / `var(--f1-*)` token? (no `#hex`,
  no Tailwind colour utilities that aren't backed by these tokens)
- Are all numbers tabular + monospace?
- Is "down / loss" shown with `--f1-flat` or `--liv-neg`, never `--f1-alert`?
- If it animates, is there a reduced-motion path?
- Does it read its numbers from the named seed module, unchanged?
- Does it match its SPEC's prop names / exports exactly (so orchestrator glue
  that imports it still type-checks)?
