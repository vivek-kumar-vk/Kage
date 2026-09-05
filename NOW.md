# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## Item 6 — net-worth ridge: drop drag-to-tilt, add hover readout, stop the idle pulse

Root cause of "ridge · still" was the owner's own Windows "Animation
effects" setting (off) — confirmed live, three.js path does render. New
feedback from watching it run for real:
- drag-to-tilt reads as a broken zoom effect — remove it, no interactivity
  via drag.
- hovering the line shows nothing — add a tooltip with the date + value at
  the nearest point.
- after the draw-in sweep it should go fully static (no breathing scale
  pulse, no ring/tail opacity pulse) until reload or next visit.

**Done when:** dragging does nothing, hovering shows a real date+value
readout, and the ridge holds still after drawing in — verified live at
localhost:8001 (owner's own eyes, since automation can't see three.js mode).

If you catch yourself opening another screen's folder — stop, come back here.

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
