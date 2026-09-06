# GLM 5.3 Flash — start here

You are implementing in `B:\inky_code`. Read this file first, then follow it exactly.

## Standing rules for every ticket you take

1. **One ticket per session.** Clear your context between tickets. Every ticket is written to
   be executable without reading any other ticket, so nothing carries over.
2. **Open only the files a ticket names.** Do not explore the repository. If a ticket does not
   name a file, you do not need it.
3. **Change only what the ticket's anchor names.** No other line in a named file changes.
4. **Run the regression command after every ticket** and stop the run if it fails. Do not build
   the next ticket on top of a red baseline. The regression command is always:

       .venv\Scripts\python Start_Inky\run_checks.py

   All six checks pass right now. That is your baseline. If it is red before you start, stop.
5. **Never invent a value.** If a fetch, a price or a timestamp is unavailable, render it absent
   and dated. Never carry the last known value forward.
6. **Do not touch** port settings files, the launcher, or anything that discovers screens by
   walking folders. A test enforces that no screen is named in those places.

## Right now: the audit is not finished

The main build plan (`BUILD_ORDER.md`) is still being written by Fable and will arrive in
`C:\Users\vkjha\Project-Audit-OUT\`. Until it does, do not start feature work.

There are three tickets you can do immediately. They are independent of the audit, they are
mechanical, and everything else is blocked until they are done.

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
5. Add the line `anyio==4.15.1` below `pytest==7.4.0`.
6. Leave every other line exactly as it is, including `pytest==7.4.0`.

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
    pytest==7.4.0
    anyio==4.15.1
    mcp>=1.2.0,<2

**Red test:**

    .venv\Scripts\python -m pip install --dry-run -r Screens\Finance\Backend\app\requirements.txt

Fails today with `ResolutionImpossible`. Must succeed after.

**Regression command:**

    .venv\Scripts\python Start_Inky\run_checks.py

**Done when:** a dry-run install of the Finance requirements resolves without error.

**Do not:**
- Do not upgrade `pytest` past 7.4.0. The async tests in the Agents screen fail under pytest 9.
- Do not add `pytest-asyncio`. Version 1.4.0 requires pytest 8.4 or newer and breaks the pin
  above. The async tests pass under the anyio plugin instead.
- Do not "fix" `ruff==2.0.0` by picking a real ruff version. Remove it. Nothing runs ruff.

**Blocks:** Z2. **Blocked by:** nothing.

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
   `# Running this screen's test suite.`, then `pytest==7.4.0`, then `anyio==4.15.1`.
2. Match each file's existing comment style. These files use `#` comments and explain why a
   dependency is there.
3. Do not add these to any screen without a `Backend/tests/` directory.

**Red test:**

    .venv\Scripts\python -c "import pathlib,sys; f=[pathlib.Path(p) for p in ['Screens/Agents/Setup/requirements_for_agents.txt','Screens/Learning/Setup/requirements_for_learning.txt','Screens/Model/Setup/requirements_for_model.txt','Screens/Office/Setup/requirements_for_office.txt']]; missing=[str(p) for p in f if 'pytest' not in p.read_text()]; print('MISSING:',missing); sys.exit(1 if missing else 0)"

Fails today listing all four files. Must pass after.

**Regression command:**

    .venv\Scripts\python Start_Inky\run_checks.py

**Done when:** all four screen requirements files declare pytest and anyio, and the six checks
still pass.

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
