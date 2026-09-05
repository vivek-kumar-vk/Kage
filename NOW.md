# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## Task — item 16 A: `Context_Engine_Agent`, the awareness collector

Overnight session 2026-09-06 shipped D52–D56 (see `active_imple.md`, all boxes
ticked): Ground Zero content + trained crew, SIP schedule + benchmark endpoint,
sanitizer rules, item 15 Day Plan card, job agents. The queue's next item is the
one everything else reads.

Build the collector: poll WakaTime (item 14 — not wired, write it as
unreachable, Rule 8), Google Calendar (D23 — same), `git log --since` today,
each screen's health endpoint; write each source's state into the Storage
library (`library/context_engine/<source>/today/`, D40 convention — never a
second store). An unreachable source is written as unreachable, never carried
over from the last poll. Then `Time_Analyst_Agent`'s evening gap report reads it.

**Done when:** a Context Engine run writes one honest snapshot per source into
the library (verified at :8009) and the AGENT DECK board has the card.

**Owner owes on waking** (tracked in PLAN):
- Education-loan statement screenshot → real outstanding (finance item 1).
- `kql` / `terraform` skill-tag mapping (Learning M7 tail).
- Finance agents (item 16 last) — then item 3 wiring is his own orchestration plan.

---

## Done earlier this session

See `active_imple.md` (the overnight build log, all boxes ticked) and
AGENTS.md D52–D56.

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
