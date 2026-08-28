<!-- Prepended to every Model A build-task prompt. Maintained by ui-gap-scout.
     Keep it short. A line earns its place only after its tag recurs >=2x. -->

# Model A prompt contract (v1 — 1 real task in: P1)

- The literal first line of any client component is these 8 characters then a
  semicolon: `"use client";` — WITH the double quotes. `use client;` is a bug.
- Colours come only from the locked theme tokens (see the task's token list).
  Never a raw hex outside an explicitly-labelled data/tokens object. Red is
  reserved for "act now" state, never decoration.
- When asked for N distinct variants, each must differ in background hue AND
  contrast level AND one structural choice. Near-duplicate variants = failed task.
- If colour tokens are given as inline CSS vars (`var(--x)`), style with the
  `style={{}}` prop ONLY — never `className`/Tailwind. Spacing = literal numbers.
  Tailwind classes resolve only for tokens in the project's `@theme`; task-local
  vars are not there. Arbitrary Tailwind values need brackets: `max-w-[920px]`.
- Given a data series for a chart, COMPUTE the SVG path from it (index→x,
  value→y via min/max). Never hand-draw an approximation. A polyline is ONE
  `M` (first point) then `L` for every next point, space-joined — NOT `M..L..`
  per point (that draws disconnected zero-length dots).
- Read figures from the seed module named in the task
  (`app/lib/blueprintSeed.ts` or `app/lib/replicaHoldings.ts`). Never invent a
  number.
- No chart or 3D library. Visualizations are hand-rolled SVG + `framer-motion`
  (already a dependency).
- Every animation gets a `@media (prefers-reduced-motion: reduce)` /
  `useReducedMotion()` guard that freezes it.
- This repo runs a **patched Next.js** — follow the API shapes in the task, not
  your training data.
- Output **one file**, complete, no prose, no markdown fence around it beyond a
  single optional ```tsx wrapper.

## Retired
<!-- lines whose tag stopped recurring; kept for history -->
