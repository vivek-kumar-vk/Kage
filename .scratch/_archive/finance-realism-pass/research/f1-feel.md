# F1 feel — research → design language (wayfinder ticket 02b, AFK research)

Goal: walking Overview → Investments → (Debt/Portfolio later) should *feel* like an
F1 broadcast / team tool. Two liveries, one interaction language.

## 1. Exact team palettes (source: infysia F1 team color codes, 2026 grid)

### Ferrari livery — **Overview tab**
| token | hex | role |
|---|---|---|
| ferrari red | `#DC0000` | anchor: headings, dividers, active nav bar, primary viz stroke |
| near-black | `#111111` | base surface family (with an evening-navy tint, see below) |
| ferrari yellow | `#F7D117` | badge-style emphasis ONLY, sparing (best/target-hit) |

Evening tone: shift the base from flat `#111` toward warm charcoal-navy
(`#0E0B12` bg, `#141019` surface). Petals tinted warm rose `#F3C4C9`.

### Red Bull livery — **Investments tab**
| token | hex | role |
|---|---|---|
| rb blue | `#1E5BC6` | dominant chrome + area-fills (largest color area) |
| rb midnight | `#0A1633` | base bg family |
| rb red | `#DC052D` | trim + negative deltas ONLY |
| rb yellow | `#F7C300` | the single fastest/best row, position leader |

Petals tinted cool `#CBD8F2`.

Guidance from source, obeyed: "red as anchor, yellow sparingly" (Ferrari);
"blue covers the largest area, red+yellow strongest in icons/trim" (Red Bull);
"calmer base, team color for headings/dividers/labels/small cues"; "leave room
for color to breathe".

## 2. Broadcast timing conventions → reusable semantics

**Sector colours** (racingnews365 / f1chronicle):
- **purple** = session best / all-time best  → our `--f1-best` `#B44BFF`
- **green**  = personal best / ahead of plan  → our `--f1-ahead` `#37D67A`
- **yellow** = no improvement / flat           → our `--f1-flat` (livery yellow)
- **red**    = reserved for "act now" only (AGENTS D1 intent kept) — NOT "loss".
  A monetary loss uses livery red on Investments trim, but the *alert* red stays
  its own thing.
- little **purple clock** by a name = "fastest lap" → a badge motif for "best
  performing goal / holding".

## 3. Interaction language (shared primitives — the local model builds these)

| primitive | what | notes |
|---|---|---|
| `TimingRow` | ranked list row: rank chip · icon slot · label · value · delta col · thin leading accent bar | goals list + holdings table both use it |
| `DeltaBadge` | signed value, coloured by the sector semantics above (best/ahead/flat), ▲▼ glyph | never bare red for "down" |
| `TrendArrow` | ▲ ▼ ▬ triangle, coloured, for series direction | |
| `WipeIn` | entrance: `clip-path` inset reveal L→R, 380ms; `useReducedMotion()` → plain fade | broadcast graphics "wipe" |
| `LiveryEdge` | one diagonal speed-line cut on a panel corner, `--livery-accent` at 8–12% | ONE per panel, not everywhere |
| `TelemetryCard` | panel shell: label (dim, tracked caps), big tabular number, viz slot, `LiveryEdge` | |
| `Sparkline` | hand-rolled `<svg>` line + area from a series (compute path, min/max) | no chart lib |
| `StatDial` | radial arc gauge, hand-rolled `<svg>` | for rates / ratios |
| `SegmentMeter` | segmented bar (tyre-compound pip vibe), 3–5 cells | 3-bucket / fund tiers |

Shared rules:
- **Tabular numerals everywhere** (`font-variant-numeric: tabular-nums` + mono
  stack) — the broadcast-timing feel.
- Big glanceable primary number top of every card; detail is progressive
  disclosure, never crammed onto the main view.
- Motion is purposeful + short; everything behind `useReducedMotion()`.
- Strong hue only on trim / chips / strokes; body text on calm base.

## 4. The shell ties it together

Neutral "paddock" shell (nav + header + footer + background). A **thin team-accent
indicator** on the active nav item + a 2px top hairline changes colour per tab:
Ferrari red on Overview, RB blue on Investments. Layout/type/motion are constant
across tabs → the *feel* is one tool; the *livery* changes like a garage.

## 5. What this locks (feeds the spec)

- D-a **revised**: not one palette — **Ferrari livery (Overview) + Red Bull livery
  (Investments) + shared F1 interaction language**. Still: no Scuderia wordmark,
  no shield, no helmet/car icons, no speedo-as-nav, no AI-art. Realism bar stays
  `224041.png`.
- New shared token groups: `--f1-*` (structural/semantic), `--liv-*` (per-tab
  livery, set on the tab wrapper).
- Primitive component set in §3 is Phase 1; tabs consume it in Phases 2–3.

Sources:
- https://www.infysia.com/design/f1-team-color-codes/
- https://racingnews365.com/what-sectors-are-f1-and-what-do-the-different-colours-mean
- https://f1chronicle.com/what-does-purple-sector-mean-in-f1/
- https://medium.com/@myroslavtsyupka/evolution-of-f1-telemetry-graphics-58d2e2e1e270
- https://medium.com/@jadhavvaishnavi.0306/revving-up-ui-ux-design-lessons-from-formula-1-7b0cec5ac1f4
