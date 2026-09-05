# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## No task open

**Item 18 shipped 2026-09-05.** `Start_Inky/run_checks.py` (Qwen wrote the
aggregator from a self-contained brief, `.scratch/qwen/03_precommit_test_gate.md`)
runs Learning's pytest suite plus the two Finance hygiene gates (their
hardcoded paths were stale — `finance-os/backend` doesn't exist, fixed to
the real `Screens/Finance/Backend/app` / `Page/next_app` paths) and exits
non-zero on any failure. `.git/hooks/pre-commit` calls it and blocks the
commit on failure (verified: injected a stub route, watched it FAIL and
block, reverted, re-ran clean). `Start_Inky/start_every_screen.py` calls it
too at the top of `main()`, non-blocking (prints the result, starts screens
anyway — Rule 8 honesty without stopping the dev workflow).

Pick the next item off `PLAN.md`'s Order table, state its "done when" here,
then start.

If you catch yourself opening another screen's folder — stop, come back here.

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
