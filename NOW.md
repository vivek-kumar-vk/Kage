# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## Task — the agent roster bottom-up + the harness fleet (owner goal) — SHIPPED 2026-09-06

The owner's goal — "work and verify and create the agents from bottom to top, giving
them their task and files, then configure the main model with OpenClaw, Hermes and
the Deepseek harness" — is complete:

- **Roster (D60):** all 38 agents carry functional briefs + `data_sources`; the ask
  path injects their data (honest unreachable states); each verified with one real
  gateway ask.
- **Harnesses (D61–D61.2):** OpenClaw, dsh and Hermes Agent are all installed
  repo-locally (one self-contained folder for the future phone host) and verified —
  OpenClaw ring exchange (P3), dsh one-shot probe ("DSH GATEWAY CHECK OK"), Hermes
  v0.21.0 with the omniroute provider declared and the screen reporting
  `hermes: ok` / `dashboard: ok`.

Decision lines D60–D61.3 in `AGENTS.md`; PLAN items 11/16/20 updated.

**Next task is the owner's pick.** Natural candidates from `PLAN.md`: item 1
(finance data migration, active) and item 12 (Learning content, next module), with
item 3 (owner's own agent orchestration) now unblocked by the roster pass.

**Owner owes (tracked in PLAN/AGENTS):**
- Paste the real Jina key into the OmniRoute dashboard → Providers → Jina
  (embeddings 401 until then).
- Education-loan statement → real outstanding (D57.1).
- OpenClaw: add one real chat channel (item 19); Hermes: create the first profile
  and run the first real ask (D61.2 — deliberately not done for him).

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
