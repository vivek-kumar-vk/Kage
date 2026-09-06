# Final instruction for Fable 5.1 — paste this whole file, then say nothing else

This is the last input Fable gets before it runs the audit. It is self-contained: paste it
even if Fable's context was compacted. Everything below is verified fact or a binding rule.

---

## 0. Status — what is already done, do not redo

- Addendum 1 is applied to the plan at
  `C:\Users\vkjha\.claude\plans\go-throught-this-prompt-calm-newell.md`. The ticket contract
  has twelve fields, rules C1 to C5 and reference-shape rule D are in, the eval matrix
  precedes the agent specs and mints the case ids, and the verification checklist tests all
  of it mechanically.
- E1 to E5 below were sent and reported applied. They are restated here so the paste is
  self-contained after compaction. If they are already in the plan, confirm and move on.
- Pass 2 has NOT run. Pass 3 has NOT run. `C:\Users\vkjha\Project-Audit-OUT\` does not exist.
- The simplification targets Fable set are accepted: eight agents, sixteen tickets, three
  screens, one ingestion adapter, six mechanisms folded into the event spine.

---

## 1. Verified ground truth — use as fact, do not re-derive, do not spend reads on it

All of this was measured on the live repo at `B:\inky_code` on 2026-09-07. The audit export
at `C:\Project-Audit` is a copy of that repo and cannot show these.

### 1.1 Export drift

- Exactly **one** source file differs between the export and the live repo:
  `Start_Inky/run_checks.py`. The other **232** Python, SQL and TSX files are byte-identical.
  Every other `path:line` citation is therefore safe.
- In the live repo the two Finance hygiene gates were moved out of
  `.scratch/finance-os-build/gates/` to `Screens/Finance/Backend/checks/check_backend_hygiene.py`
  and `check_frontend_hygiene.py`. **`.scratch/` no longer exists.** No ticket may reference a
  `.scratch/` path. Treat the live paths as ground truth.
- `run_checks.py` names its four screens explicitly at lines 94-97: Learning, Office, Agents,
  Model. Fable's E2 handling of that is correct.

### 1.2 The baseline is green, and what it took to get there

`run_checks.py` now passes all six checks under the repo venv. It did not before today.
Three environment defects were found and fixed outside the repo:

| Defect | Detail |
|---|---|
| Broken venv | `.venv` pointed at a uv-managed CPython 3.11.16 that no longer exists on disk. Rebuilt on the only installed interpreter, Python 3.12.10. The old one is preserved as `.venv_broken_311`. |
| Finance requirements uninstallable | `Screens/Finance/Backend/app/requirements.txt` pins `mftool==0.1.0` (does not exist; earliest real release is 1.0.6) and `ruff==2.0.0` (does not exist; ruff is still 0.x, latest 0.16.6). It also pins `pdfplumber==0.11.3` against `casparser==0.7.4`, which pip resolves as **ResolutionImpossible**. This file has never been installable as written. `mftool` is not imported anywhere in the codebase; `casparser` is, at `Screens/Finance/Backend/app/services/imports/cas.py:32`. |
| Test dependencies unspecified | No screen requirements file lists `pytest`. Only Finance's does, and Finance's cannot install. The suites passed historically only because the global Python 3.12 had accumulated the packages. |

Working versions now in `.venv`, established by trial: `pytest==7.4.0`, `anyio==4.15.1`,
`pdfplumber 0.11.10`, `casparser 1.4.1`. Note that `pytest-asyncio` must **not** be installed:
version 1.4.0 requires pytest>=8.4 and breaks the pinned pytest 7.4.0. The async tests in
`Screens/Agents/Backend/tests/test_context_injection.py` pass under the anyio plugin with
pytest 7.4.0 and fail under pytest 9.

### 1.3 Toolchain present

Node v24.19.0, npm 11.17.0, git 2.55.0, Python 3.12.10. `node_modules` present in all four
Node applications. `kage-data/` and `.env` present. Git tree clean on branch
`vivek/main-menu-rubric-agentic-os`. Ports 8000 to 8011 free except 8007, held by Hermes.

**The `gh` CLI is not installed.** The repo rule requires GitHub work to go through it, so
the push phase is blocked until it is. That is a below-the-line ticket, not a build blocker.

### 1.4 A stale port reference

`Screens/Anime/Setup/requirements_for_anime.txt` is prose, not a requirements file, so any
installer looping over `requirements*.txt` fails on its first line. It also tells the reader
the Anime screen appears on **port 8006**, which is now OpenClaw; Anime is 8005 after the
renumbering. Both are audit findings, both are cheap tickets.

---

## 2. Corrections E1 to E5 — binding

**E1. UI tickets cannot satisfy field 4, and the Main Menu overhaul is mostly UI.**
There is no browser test harness anywhere: no Playwright, no Puppeteer, no Jest, no Vitest.
The only harness is pytest under `Screens/<Name>/Backend/tests/`. So "split until a red test
can be written" is unsatisfiable for a 3D animated landing page, and a weak model will either
invent a test that does not run or quietly avoid the visual work. Split every UI ticket in two:

- a **data-contract ticket**, `[GLM]` or `[SONNET]` as the logic demands, with a real pytest
  red test asserting the endpoint shape, the honest empty state and the staleness field;
- a **presentation ticket**, `[GLM]`, whose field 4 is replaced by a **Visual check** block:
  the exact URL, the exact viewport, numbered steps, and the observable end state, written so
  a human confirms it in under a minute. Motion bounds (1.5s, 60fps, reduced-motion) are
  stated as checkable observations, not as a test.

State in `BUILD_ORDER.md` that presentation tickets carry a Visual check instead of a red
test, and that this is the only permitted substitution. Do not put a browser harness above the
cut line; if you want one, it is a below-the-line ticket with its cost stated.

**E2. The conventions header (C5) is missing the test convention.**
Finance and Main_Menu have no tests directory at all; Agents, Learning, Model and Office do.
`run_checks.py` runs `python -m pytest tests/ -q` from each `Screens/<Name>/Backend/` directory
and names its four screens explicitly at lines 94-97, so creating a Finance tests folder does
not enlarge coverage on its own. The first Finance test ticket must add that line and leave the
whole run green. Put the test path convention, the command shape and this consequence in C5.

**E3. Verification step 1 contradicts C3.** Step 1 checks above-the-line tickets <=25 as a hard
failure; C3 orders splitting and reporting the true number instead of merging back. The count is
**reported against 25, not enforced**. If it exceeds 25, the document states the number and why.

**E4. Field 10 forbids an Algorithm on `[SONNET]` tickets**, leaving nowhere to put a hard
ordering requirement that is not a signature. Give Sonnet tickets an **Invariants** line: the
ordering, atomicity and idempotency rules that must hold, stated as constraints not steps.
The event spine write path needs this.

**E5. Verification step 3 will silently pass.** The pattern `def .*:\n\s+[^"]` spans lines, so
it needs multiline mode (`rg -U`) or it matches nothing and reports clean. Fix it or replace it
with a per-fence line-count heuristic.

---

## 3. Ticket zero — the environment tickets, above the cut line

The build cannot start until the repo can reproduce its own environment. These come first and
block every other ticket, because C1 requires every red test and regression command to run as
`.venv\Scripts\python`.

1. **Make the environment reproducible.** One pinned, installable dependency set that produces
   a green `run_checks.py` on a clean machine. It must resolve the three defects in section 1.2
   by name: the phantom `mftool==0.1.0` and `ruff==2.0.0` pins, the `pdfplumber`/`casparser`
   conflict, and the missing test dependencies. Record that `pytest` stays at 7.4.0 and that
   `pytest-asyncio` must not be added. Red test: a clean install followed by a green
   `run_checks.py`.
2. **Repair the malformed Anime requirements file** and correct its stale port reference.
3. **Below the line:** install `gh`, required before anything is pushed.

Rule 22 applies to none of these; they are local facts, not external sources.

---

## 4. Execution directive — binding for the rest of the session

1. Apply anything in section 2 not already in the plan. Do **not** print the revised plan for
   approval.
2. Run Pass 2 immediately. Announce the pass. Read the 40 units. Write notes to the scratchpad
   `notes.md` **after every single file**, never held in context only, so a compaction mid-pass
   is survivable. The no-re-read rule makes lost notes unrecoverable.
3. Run Pass 3 immediately after. Write all nine files into `C:\Users\vkjha\Project-Audit-OUT\`.
   Write nothing into `C:\Project-Audit` and nothing into `B:\inky_code`.
4. Run the verification checklist yourself and fix what it catches, silently.
5. Do not stop for approval, questions or status. Stop only if the $60 ceiling is genuinely at
   risk, or if a finding makes a deliverable impossible to write honestly. **Ambiguity is not a
   reason to stop**: state the assumption in the document, mark it `unverified`, keep going.
6. Report once, at the end, and only this: the nine file paths, the conditional opens actually
   used, every `unverified` claim, the final above-the-line ticket count against 25, and the spend.
