# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## Task — OpenClaw: configure real channels + a model provider (PLAN item 19)

Screen (`:8006`) + `run_openclaw.py` already shipped (D44). The local
install has **no `node_modules`** yet (`Screens/OpenClaw/Setup/
openclaw_install/` has only package.json + lock). So: `npm install` there
→ bring the gateway up on 18789 → run `openclaw onboard`/`configure` to
add a chat channel + a model provider. Open decision (PLAN item 19):
route model calls through OmniRoute (`http://127.0.0.1:8010/v1` +
`GATEWAY_API_KEY`, same as Hermes/DeepSeek — D6/D24.1/D25.1) or use
OpenClaw's own provider connections. Recommend OmniRoute.

**Done when:** local install built; gateway `GET :18789/healthz` →
`{"ok": true}`; at least one real chat channel + one model provider
configured (owner supplies channel choice + any tokens); OpenClaw screen
at `:8006` shows the Control UI live, not "gateway down"; D-line logged;
PLAN item 19 updated. **Owner input needed:** which chat channel(s), and
the OmniRoute-vs-own-providers call.

Carried: finance item 1 — owner sending the education-loan screenshot
later. M6 browser check still owed (Claude-in-Chrome offline).

---

## Done earlier this session

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
