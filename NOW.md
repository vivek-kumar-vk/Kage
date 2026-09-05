# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## No task open

**Finance data fill done 2026-09-06 (PLAN item 1, D48–D50).** Owner
figures wired into `finance.db` (uncle 96000, salary 70000/70000, term
life 0, Slice 0, 4 goals seeded, 2 folio numbers from the CAS) and the
noticeboard (`all_current_numbers.md`, skip-worktree — EPF VERIFY
dropped, edu-loan marker, portfolio_total 149513 Jul as-of, LAMF
Oct-flight plan). Q11 answered: port the old finance code, don't rebuild
(D48). CDSL CAS parsed via pdfminer (casparser can't read CDSL — D49);
it only confirmed the portfolio, finance.db was already fresher.
DB backup: `data/backups/finance.pre-owner-figures-20260906.db`.

**Owner still owes** (tracked in `finance-datamigration.md` §9):
- Education-loan statement screenshot → real outstanding (left at
  654750 with a marker; `data_health.missing_info=edu_loan_statement`).
- The pasted Gemini answer on the embedder (referenced but NOT in the
  message — item 2, not item 1).
- Whether to flip `verified_by_a_person` in the tax JSON (needs the
  incometax.gov.in check).
- Goa figure is a ₹35k midpoint of ₹30–40k; laptop target is NULL.

Sequence the owner set: OmniRoute → OpenClaw → finance AI agent (Q10/Q12).

Carried: M6 browser check — Claude-in-Chrome offline, `Preempt Test Co`
interview in `office.db`. Clean `start_every_screen.py` run owed.

Pick the next item off `PLAN.md`'s Order table, state its "done when"
here, then start.

If you catch yourself opening another screen's folder — stop, come back here.

---

## Rules for this file

- Only one task block at a time.
- Every task states its "done when" before work starts.
- Blocked > 20 min? Write the blocker under the task and stop for the day.
  Don't start something else.
