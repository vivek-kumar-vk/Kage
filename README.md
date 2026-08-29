# Kage

A personal dashboard system. One folder per screen, each a self-contained
web app on its own port. The screen you land on (Main Menu, port 8000)
discovers the rest and links to them.

Kage is the public code for the **Inky** dashboard (the module names you'll
see throughout are `inky`). It ships **code only** — no personal data, no
private notes, no agent memory. Screens that normally show saved data start
empty; you supply your own. Real data is meant to live outside this repo
(Google Drive) — see [`immediate_plan.md`](immediate_plan.md) for the roadmap.

## Tech stack

- **Python 3.11+** — every screen's backend
- **FastAPI + Uvicorn** — one server process per screen (Main Menu 8000,
  Finance 8001, Learning 8002, Enhancement 8004)
- **Frontend: plain HTML / CSS / JS**, served directly by each backend —
  this is the default and needs no build step. Each of Main Menu, Finance,
  Learning and Enhancement also ships the *source* of an optional richer UI
  (**Next.js 15 / React 19**, and for some a **Svelte 5** pilot); the
  backend serves the prebuilt version automatically if you build it, and
  falls back to the plain pages if you don't. Charts: **Apache ECharts**
  (vendored, no install).
- **Launcher**: plain Python scripts in `Start_Inky/`.
- **Storage**: local flat files + **SQLite** today; moving to a Google
  Drive–backed layer (see roadmap). Nothing personal is committed here.
- Agents are described only (`Agents/<name>/description.txt`); their code,
  memory and the optional local-LLM path are not included.

## Run it

```
cd <repo root>
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install ^
  -r Main_Menu\Setup\requirements_for_main_menu.txt ^
  -r Screens\Finance\Setup\requirements_for_finance.txt ^
  -r Screens\Learning\Setup\requirements_for_learning.txt ^
  -r Screens\Enhancement\Setup\requirements_for_enhancement.txt
.venv\Scripts\python Start_Inky\start_every_screen.py
```

Then open <http://127.0.0.1:8000>. Ctrl+C in that window stops everything.

`Start_Inky\Start_Everything.bat` does the venv + install + launch in one
double-click.

### Optional: the richer per-screen UI

In any `Screens\<Name>\Page\next_app` (or `Main_Menu\Page\next_app`):

```
npm install && npm run build
```

The backend picks up `next_app\out` on its next start.

## Status

Active. This is v2 of a private project, rebuilt in the open. See
[`immediate_plan.md`](immediate_plan.md) for what's being worked on next —
principally moving all private data into Google Drive behind a smart
retrieval layer.

## License

MIT — see [`LICENSE`](LICENSE).
