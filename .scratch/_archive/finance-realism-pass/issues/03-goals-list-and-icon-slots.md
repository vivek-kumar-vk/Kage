Type: grilling
Status: open
Blocked by: —

## Question

Spec the goals block that replaces `GoalsGauges` on Overview, modelled on
`Screenshot 2026-08-28 224041.png`.

Row layout: icon image · goal name · ₹current / ₹target · progress bar (+ % label).

Locked: **4 placeholder rows**; real names / values / icon images come later.

Decide:

- Where the user drops icon files (proposed:
  `Screens/Finance/Page/next_app/public/goals/<slug>.png`) and the reference
  path the component expects.
- Icon dimensions + shape (square? rounded-rect thumbnail like the screenshot?
  target px).
- Fallback when an icon file is absent (crimson monogram tile? neutral shape?).
- Placeholder seed: add a `goals` shape to `blueprintSeed.ts` with
  `{ slug, name, current, target }` for 4 rows (or extend the existing
  `goals: [{label, pct}]`).
- Progress-bar style — inherits ticket 01 accent; confirm fill colour + track.
- Does Overview also keep a themed summary arc above the list, or is the list
  the whole goals block? (fog item on the map — settle here.)
