# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## Task — item 16 A tail: `Pattern_Learner_Agent` + `Focus_Guard_Agent`

The Context Engine collector is live (D58): a run at
`POST :8004/api/agents/context-engine/run` writes four honest snapshots to the
library and `GET .../latest` reads them. What remains of the awareness layer:

- **`Time_Analyst_Agent`** is already re-briefed to read `/latest` — verify the
  brief renders at :8004 and a real gateway ask answers from it.
- **`Pattern_Learner_Agent`** — re-brief it on the same `/latest` snapshots,
  saying "not enough data" honestly until ~6 weeks of real history exists.
- **`Focus_Guard_Agent`** — a comparison of the day plan against the collected
  context, not a judgment; no model call unless asked.

**Done when:** all three briefs are live at :8004, each verified with one real
gateway ask, and the AGENT DECK board carries the card.

**Owner owes (tracked in PLAN/AGENTS D57):**
- Paste the real Jina key into the OmniRoute dashboard → Providers → Jina
  (embeddings 401 until then).
- `openclaw onboard --auth-choice anthropic-cli` + Claude Code login.
- Education-loan statement → real outstanding (D57.1).

---

## Done earlier this session

See `active_imple.md` (the overnight build log, all boxes ticked) and
AGENTS.md D52–D58.

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
