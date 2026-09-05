# NOW

One task. Nothing else. When it's done, delete the block and write the next one.
Backlog lives in `PLAN.md` — do not open it while a task is open here.

---

## Task — OpenClaw: add one real chat channel (PLAN item 19, second half)

Model provider is **done** (2026-09-06, D44.2): owner picked his Claude
Pro subscription directly — `openclaw onboard --auth-choice anthropic-cli`,
`claude-cli` runtime, verified with a real reply. Gateway moved to token
auth (`run_openclaw.py --auth token`, token in `openclaw.json
gateway.auth`, still loopback). PLAN item 19's OmniRoute-vs-own question:
settled — own providers, Anthropic direct.

Left: **one real chat channel**. Owner picks (Telegram botToken easiest,
WhatsApp QR pairing), adds it via Control UI Settings → Channels or
`openclaw channels add`. Then send one real message from that channel and
get the Claude reply back.

**Done when:** a message sent from the chosen channel gets a real Claude
reply; D-line for the channel logged; PLAN item 19 closed.

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
