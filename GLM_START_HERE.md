# GLM 5.3 Flash — start here

You are implementing in `B:\inky_code`. Read this file first, then follow it exactly.

## Standing rules for every ticket you take

1. **One ticket per session.** Clear your context between tickets. Every ticket is written to
   be executable without reading any other ticket, so nothing carries over.
2. **Open only the files a ticket names.** Do not explore the repository. If a ticket does not
   name a file, you do not need it.
3. **Change only what the ticket's anchor names.** No other line in a named file changes.
4. **Run the regression command after every ticket.** It is always:

       .venv\Scripts\python Start_Inky\run_checks.py

   **Your baseline today is five of six.** The Agents suite fails on purpose: three async tests
   used to be skipped silently and one of them fails for a real reason. Ticket Z0 fixes that.
   Until Z0 is done, "no worse than five of six, and Agents is the only failure" is your
   baseline. After Z0 it is six of six, and any failure at all stops the run.
5. **Never invent a value.** If a fetch, a price or a timestamp is unavailable, render it absent
   and dated. Never carry the last known value forward.
6. **Do not touch** port settings files, the launcher, or anything that discovers screens by
   walking folders. A test enforces that no screen is named in those places.

## Right now: the audit is not finished

The main build plan (`BUILD_ORDER.md`) is still being written by Fable and will arrive in
`C:\Users\vkjha\Project-Audit-OUT\`. Until it does, do not start feature work.

There are four tickets you can do immediately. They are independent of the audit, they are
mechanical, and everything else is blocked until they are done. Do Z0 first.

---

## Ticket Z0 — make the three skipped async tests actually run

**Model:** GLM

**Why it is first:** `Screens/Agents/Backend/tests/test_context_injection.py` holds three
`async def` tests. Without an async plugin configured, pytest skips them with a warning and the
suite still prints PASS. Every regression command you run depends on this suite telling the
truth, so it has to run its own tests before anything else is built on top of it.

**Files created (1):** `Screens/Agents/Backend/pytest.ini`

**Anchor:** a new file. No existing file changes.

**Algorithm:**
1. Create `Screens/Agents/Backend/pytest.ini` containing exactly these three lines:

       [pytest]
       asyncio_mode = auto
       testpaths = tests

2. Do not add a `conftest.py`. Do not add markers to the test functions.
3. Do not change any test file.

**Red test:**

    .venv\Scripts\python -m pytest Screens\Agents\Backend\tests -q

Today this reports `24 passed, 3 skipped`. After this ticket it must report 27 collected with
**zero skipped**. It will then show one genuine failure, which is expected and is Z0b's job.

**Regression command:**

    .venv\Scripts\python Start_Inky\run_checks.py

**Done when:** the Agents suite runs 27 tests with none skipped.

**Do not:**
- Do not make the failing test pass by editing the test. The failure is real.
- Do not delete or mark `xfail` the test that fails. Leave it failing and stop.
- Do not pin pytest back to 7.4.0. That version is what hid the tests.

**Blocks:** Z0b. **Blocked by:** nothing.

---

## Ticket Z0b — decide where the source-size budget is enforced

**Model:** SONNET. Do not take this ticket yourself. Hand it to Sonnet 5.

**Why Sonnet:** `test_current_data_block_truncates_oversized` asserts that the assembled data
block carries a `truncated at 4000 chars` notice. It does not. `_current_data_block` in
`Screens/Agents/Backend/services/agents.py` does no bounding of its own; the `MAX_SOURCE_CHARS`
cap lives only inside `_fetch_source` at lines 405-417. So the point that builds the prompt
trusts its producer and enforces no budget. Whether the bound belongs at the fetch, at the
assembly, or both is a design decision about a silent failure mode, and worker prompts are
capped at 4,000 tokens. That is Sonnet's call, not a mechanical edit.

**Blocked by:** Z0.

---

## Ticket Z1 — make the Finance requirements installable

**Model:** GLM

**Why it blocks everything:** `Start_Inky\Start_Everything.bat` installs this file explicitly
at line 85. It has never been installable, so a fresh install of Kage has always failed here.

**Files modified (1):** `Screens/Finance/Backend/app/requirements.txt`

**Anchor:** the whole file is a dependency list. Replace its contents. No other file changes.

**Algorithm:**
1. Delete the line `mftool==0.1.0`. That version does not exist on PyPI, the earliest real
   release is 1.0.6, and the package is not imported anywhere in the codebase.
2. Delete the line `ruff==2.0.0`. That version does not exist, ruff is still on 0.x, and
   nothing in the project ever invokes ruff.
3. Change `pdfplumber==0.11.3` to `pdfplumber==0.11.10`.
4. Change `casparser==0.7.4` to `casparser==1.4.1`. The old pair could not resolve together.
   `casparser` is genuinely used, at `Screens/Finance/Backend/app/services/imports/cas.py:32`.
5. Change `pytest==7.4.0` to `pytest==8.4.2`. The old pin is what silently skipped the async
   tests in the Agents screen.
6. Add the line `pytest-asyncio==1.4.0` directly below it.
7. Leave every other line exactly as it is.

**Resulting file, verbatim:**

    fastapi==0.100.0
    uvicorn[standard]==0.20.0
    pydantic==2.4.2
    python-multipart==0.0.6
    python-dateutil==2.8.2
    yfinance==0.2.66
    tenacity==8.2.2
    pdfplumber==0.11.10
    casparser==1.4.1
    pytest==8.4.2
    pytest-asyncio==1.4.0
    mcp>=1.2.0,<2

**Red test:**

    .venv\Scripts\python -m pip install --dry-run -r Screens\Finance\Backend\app\requirements.txt

Fails today with `ResolutionImpossible`. Must succeed after.

**Regression command:**

    .venv\Scripts\python Start_Inky\run_checks.py

**Done when:** a dry-run install of the Finance requirements resolves without error.

**Do not:**
- Do not keep `pytest==7.4.0`. That pin is what hid three async tests behind a silent skip.
- Do not "fix" `ruff==2.0.0` by picking a real ruff version. Remove it. Nothing runs ruff.
- Do not add `mftool` back at any version. Nothing imports it.

**Blocks:** Z2. **Blocked by:** Z0.

---

## Ticket Z2 — declare the test dependencies each screen actually needs

**Model:** GLM

**Why:** four screens have test suites that `run_checks.py` runs, and not one of them declares
`pytest` in its requirements. The suites only ever passed because packages had accumulated in a
global Python by hand. A clean machine cannot run them.

**Files modified (4):**

- `Screens/Agents/Setup/requirements_for_agents.txt`
- `Screens/Learning/Setup/requirements_for_learning.txt`
- `Screens/Model/Setup/requirements_for_model.txt`
- `Screens/Office/Setup/requirements_for_office.txt`

This exceeds the normal three-file limit. It is permitted here because it is one concern
repeated mechanically, not four concerns.

**Anchor:** append to the end of each file. No existing line changes in any of them.

**Algorithm:**
1. For each of the four files, append a blank line, then the comment line
   `# Running this screen's test suite.`, then `pytest==8.4.2`, then `pytest-asyncio==1.4.0`.
2. Match each file's existing comment style. These files use `#` comments and explain why a
   dependency is there.
3. Do not add these to any screen without a `Backend/tests/` directory.

**Red test:**

    .venv\Scripts\python -c "import pathlib,sys; f=[pathlib.Path(p) for p in ['Screens/Agents/Setup/requirements_for_agents.txt','Screens/Learning/Setup/requirements_for_learning.txt','Screens/Model/Setup/requirements_for_model.txt','Screens/Office/Setup/requirements_for_office.txt']]; missing=[str(p) for p in f if 'pytest' not in p.read_text()]; print('MISSING:',missing); sys.exit(1 if missing else 0)"

Fails today listing all four files. Must pass after.

**Regression command:**

    .venv\Scripts\python Start_Inky\run_checks.py

**Done when:** all four screen requirements files declare pytest and pytest-asyncio, and the
aggregator is no worse than before.

**Do not:**
- Do not create a shared requirements file. Every screen keeps its own list so it can be
  installed alone. That is deliberate.
- Do not add test dependencies to Main_Menu or Finance. Neither has a tests directory yet.

**Blocks:** nothing. **Blocked by:** Z1.

---

## Ticket Z3 — stop the Anime setup notes from breaking the installer

**Model:** GLM

**Why:** `Start_Everything.bat` line 64 installs every file matching `Setup\requirements_*.txt`.
The Anime one is prose, not a dependency list, so pip fails on its first line, `Anime screen`.
The Anime screen is Node and has no Python dependencies at all.

**Files modified (1):** `Screens/Anime/Setup/requirements_for_anime.txt` becomes
`Screens/Anime/Setup/SETUP_NOTES_for_anime.md`

**Anchor:** rename the file, then correct one line inside it. No other file changes.

**Algorithm:**
1. Rename the file to `SETUP_NOTES_for_anime.md` so it no longer matches the installer's glob.
2. Inside it, find the sentence saying the Anime screen appears on port 8006. Change 8006 to
   8005. Port 8006 now belongs to the OpenClaw screen; Anime moved to 8005 when the ports were
   renumbered.
3. Change nothing else in the text.

**Red test:**

    .venv\Scripts\python -c "import glob,sys; bad=[p for p in glob.glob('Screens/*/Setup/requirements_*.txt') if not open(p,encoding='utf-8').readline().strip().startswith(('#','')) or 'Anime screen' in open(p,encoding='utf-8').read()]; print('BAD:',bad); sys.exit(1 if bad else 0)"

Fails today naming the Anime file. Must pass after.

**Regression command:**

    .venv\Scripts\python Start_Inky\run_checks.py

**Done when:** no file matching `Screens/*/Setup/requirements_*.txt` contains prose, and the
Anime setup notes cite port 8005.

**Do not:**
- Do not delete the file. Its content is the real setup guide for the Anime screen.
- Do not turn it into an empty requirements file. The screen has no Python dependencies.
- Do not change any port anywhere else. Only this document's stale reference is wrong.

**Blocks:** nothing. **Blocked by:** nothing.

---

## After these three

Stop and wait. The audit output lands in `C:\Users\vkjha\Project-Audit-OUT\BUILD_ORDER.md`.
Take its tickets in dependency order, one per session, under the standing rules above.
