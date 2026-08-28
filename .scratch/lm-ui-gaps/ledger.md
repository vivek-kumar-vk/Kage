# Model A — UI gap ledger

Maintained by the `ui-gap-scout` Hermes Bot (`SOUL.md`). One entry per build
task. `prompt-contract.md` is the distilled, always-prepended version.

Model A: `Qwen2.5-Coder-7B-Instruct` (Q5_K_M → **Q4_K_M** from the realism pass
on). Harness: `.scratch/finance-telemetry/run_task.py` (`max_tokens` 2000,
`temperature` 0), 90 s cooldown, pre-task RAM/GPU gate.

---

## Backfill summary — `finance-telemetry` run (X1, R1–R18, T1–T15; 2026-08-25→28)

Scan of `.scratch/finance-telemetry/raw/*.json` (31 outputs). progress.md logged
"19/19 clean" *after* the orchestrator's cross-cutting edits + hardening, so
"clean" is post-fix, not first-try.

Signals:

- **`reduced-motion-ignored`** — recurring. Only ~6/31 outputs contained a
  `useReducedMotion` / `prefers-reduced-motion` guard; progress.md states the
  orchestrator did a separate "reduced-motion hardening" pass. → prompt-contract
  line active.
- **`palette-drift`** (raw hex) — R1, R6, R14 emitted literal `#rrggbb` instead
  of tokens. Low-moderate. → prompt-contract line active.
- **`good:reads-seed`** — strong. Most component tasks referenced
  `blueprintSeed` / `BLUEPRINT_SEED` / `REPLICA_*` rather than inventing figures.
  Keep asking explicitly.
- **`good:small-diff` / no truncation** — every output well under the 2000-token
  cap; one-file slices held coherence. Keep slices small.
- **`use-client`** — mostly present; a couple of non-component tasks (R7, T1)
  lacked it (likely data/CSS, not a real miss). Watch.
- Not yet observable from raw alone (need the gate + fix-diff inputs going
  forward): `patched-next-api-ignored`, `ts-type-break`, `hallucinated-import`,
  `prop-threading-error`, `invented-tailwind-class`.

---

## Entries
<!-- ui-gap-scout appends below, newest last -->

### 2026-08-29 00:1x · P1 · app/theme-lab/page.tsx
- verdict: fixed-by-human
- retries: 0
- tags: use-client-missing, palette-drift, good:structure, good:no-external-imports, good:hash-sync
- evidence:
  - line 1 emitted `use client;` (no quotes) — not a valid directive, would break the build.
  - 3 of 4 themes had identical `--tl-bg #1a1a2e` + identical surface/line/text; "distinct takes" ask ignored. Pure `#ff0000`/`#ffcc00` throughout.
- prompt-fix: (a) "The literal first line must be the 8 characters: \"use client\"; — with the double quotes and semicolon." (b) "When asked for N distinct variants, every variant must differ in base background hue AND contrast AND at least one structural choice; near-duplicates are a failed task."
- note: model's component structure, hash-sync effect, and 'no imports beyond react' were all correct. Palette *values* were hand-authored by the orchestrator (design judgement + weakest area for a 7B) — consistent with orchestrator-owns-tokens precedent from the finance-telemetry run.

### 2026-08-29 00:2x · P2 · app/theme-lab/stage.tsx
- verdict: fixed-by-human
- retries: 0 (hand-fixed; retry judged low-yield — see prompt-fix)
- tags: invented-tailwind-class, style-in-wrong-place, ignored-seed-module, good:svg-structure
- evidence:
  - emitted `max-w-920px`, `p-32`, `gap-20`, `rounded-14`, `w-68`, `z-1` — invalid/misscaled Tailwind; arbitrary values not bracketed (`max-w-[920px]`).
  - used `bg-tl-surface` / `text-tl-accent-2` etc. — these classes don't exist; the `--tl-*` vars are set INLINE by the ancestor, not registered in Tailwind `@theme`, so all theming was dead.
  - sparkline `<path d>` was a hand-typed zigzag, ignored the given SERIES [180,176,…240].
- prompt-fix: "When colour tokens are supplied as inline CSS variables (var(--x)), you MUST style with the `style={{}}` prop only — NEVER `className`/Tailwind. Spacing = literal numbers in `style`. Tailwind classes only resolve for tokens registered in the project's `@theme` block; prototype-local vars are not."
- prompt-fix: "Given a numeric data series for a chart, compute the SVG path from it (map index→x, value→y by min/max). Do not hand-draw an approximation."
- meta: `invented-tailwind-class` now 1x; `style-in-wrong-place` 1x; `ignored-seed-module` now the 2nd signal (backfill flagged the inverse as good:reads-seed). Watch all three on the first real build task — the inline-style rule is the highest-value new contract line.

### 2026-08-29 00:58 · Sparkline · app/components/f1/Sparkline.tsx
- verdict: clean
- retries: 0
- gate: clean

### 2026-08-29 00:58 · Sparkline (P9 Phase 1) · app/components/f1/Sparkline.tsx
- verdict: fixed-by-human
- retries: 0 (tsc+eslint both passed — semantic bug the gate can't see)
- tags: svg-path-logic, good:reads-props, good:no-extra-imports
- evidence: built the path as `series.map(p => "M x,y L x,y").join("")` — a run
  of disconnected zero-length segments, renders as nothing. Structure, prop
  destructure, min/max scaling, and the area/line split were all correct.
- carry-forward: primitives P1 remaining (DeltaBadge/StatDial/SegmentMeter/
  TimingRow/TelemetryCard/WipeIn) — no series math in those, low risk.
- prompt-fix: contract line sharpened — "polyline = ONE M then L per next point,
  space-joined; not M..L.. per point".
- note: new tag `svg-path-logic`. The gate (tsc + eslint) passes valid-but-wrong
  SVG math; overnight autonomous runs need a morning visual pass for this class.
