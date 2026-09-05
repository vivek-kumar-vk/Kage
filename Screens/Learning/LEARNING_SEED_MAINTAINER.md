# Learning seed maintainer — Claude project instructions

Paste this as the project instructions for a Claude chat project named "Learning".
Paste the current `Screens/Learning/Backend/seed_local.json` as the starting state,
then just say "add X, Y, Z" whenever you pick up new things to learn.

The Learning screen build (`Screens/Learning/QWEN_BUILD_PROMPT.md`) is a one-time
job — it builds the screen. This file is only about keeping the **data** current.

---

Maintain one file: `Screens/Learning/Backend/seed_local.json` (git-ignored, my real
study board). Output the **full updated JSON** each time, nothing else.

Shape — four top-level arrays:

- `topics[]`: `{name, stack_area: core|drip|capture, track: A|B, status: todo|learning|done, position, progress: 0.0, target_date: null, source_doc: null, group}`
- `week_plans[]`: `{week_start, focus_a, focus_b, note}` — `"@today"` allowed for dates
- `cards[]`: `{topic_index, front, part1..part5, tag: core|drip|capture, tether}` — `topic_index` = 1-based row in `topics`
- `reviews[]`: `{card_index, due_date, ease: 2.5, status: new|active}` — `card_index` = 1-based row in `cards`

When I give you new things to learn:

1. Append to `topics[]` — set `track`, `stack_area` (`core` if essential else `drip`), `group`, next `position` in that track.
2. For each new topic also add one `cards[]` row (`front` + 5 progressive `part` answers you write from the topic) and one matching `reviews[]` row (`due_date: "@today"`, `status: "new"`).
3. Keep existing rows untouched. Return valid JSON only. Never touch screen code.
