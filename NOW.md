# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## No task open

M6 interview-day preemption shipped 2026-09-05 (D38.1). `GET /api/learning/
today` carries an `office` block (state / `interview_today` / today's
pending interviews + packs), fetched from Office over HTTP with an honest
`office offline` state. Today page shows a pinned prep card and drops the
study plan to 0.5 opacity when there's an interview today. 14 Learning +
10 Office pytest green; Next export rebuilt.

**Browser check owed** — Claude-in-Chrome extension went offline. A
`Preempt Test Co` interview (today, with a prep pack) is left in
`office.db` so the owner can see the preemption at :8003; delete it from
Office → Interview Prep after.

Also owed: a clean `start_every_screen.py` run — Learning/Office are
hand-started processes right now.

Pick the next item off `PLAN.md`'s Order table, state its "done when"
here, then start.

If you catch yourself opening another screen's folder — stop, come back here.

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
