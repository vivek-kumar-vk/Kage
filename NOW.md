# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## No task open

**Item 18 shipped 2026-09-05** — `Start_Inky/run_checks.py`, wired into
`.git/hooks/pre-commit` (blocks) and the launcher (reports).

**Item 2's data-dir move + agent library shipped 2026-09-05 (D40, owner's
call, mid-session — mobile/Termux hosting).** `KAGE_DATA_DIR` is now
`<repo>/kage-data/` (gitignored, Rule 7.1 supersedes Rule 7). New
`services/library.py`: `library/<screen>/<tab>/<card>/<card>_<timestamp>.md`,
one dated file per write, `GET .../latest` + full history. Verified live via
curl (write, latest, history, honest 404 on an unwritten card), test data
cleaned up, `run_checks.py` still green. Scope stopped at skeleton + write
API on purpose — no screen writes into it yet; that's per-screen follow-up
work as each agent gets built (item 16 A's `Context_Engine_Agent` is the
natural first real writer).

Pick the next item off `PLAN.md`'s Order table, state its "done when" here,
then start.

If you catch yourself opening another screen's folder — stop, come back here.

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
