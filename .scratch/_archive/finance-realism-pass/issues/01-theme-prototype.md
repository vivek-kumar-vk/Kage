Type: prototype
Status: claimed
Blocked by: —

## Question

Turn the user's vibe into a locked visual language: **Red Bull F1 palette
(deep navy + red + yellow), drifting sakura petals, evening-light tone**,
realistic and polished like `Screenshot 2026-08-28 224041.png` — explicitly
NOT the Ferrari/telemetry F1 costume (no shield, no "Scuderia", no helmet/car
icons, no speedo-as-nav, no AI-art gloss).

Run `prototype` (UI branch): Claude writes the throwaway multi-variant route
prompt; the **local model builds the variants** on one route, switchable by a
URL search param + a floating bottom bar; the user picks / mixes.

Each variant renders: one representative Overview block (e.g. Total Balance with
a line/area viz), a slice of the vertical nav, the page background, and one card.

### Output (the answer to record)

- Palette tokens: `--bg`, `--surface`, `--surface-2`, `--line`, `--text`,
  `--text-dim`, and an accent scale (navy / red / yellow steps) — mapped into
  the existing `@theme inline` block style in `globals.css`.
- Sakura-petal approach: SVG vs CSS, count, drift model, z-layer, and the
  `prefers-reduced-motion` behaviour (freeze).
- Panel / card treatment (radius, border, glow, grain) and the evening-tone
  background (gradient / vignette).
- Nav treatment: plain vertical list, active-item style.

Capture per `prototype` rule 6: fold the decision into real tokens, commit the
prototype to a throwaway branch, leave a pointer here.
