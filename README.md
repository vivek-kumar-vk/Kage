# Kage

A personal dashboard system. One folder per screen, each a self-contained
web app on its own port. The screen you land on (Main Menu, port 8000)
discovers the rest and links to them.

Kage is the public code for the **Inky** dashboard (the module names you'll
see throughout are `inky`). It ships **code only** — no personal data, no
private notes, no agent memory. Screens that normally show saved data start
empty; you supply your own. Real data is meant to live outside this repo
(Google Drive) — see [`PLAN.md`](PLAN.md) for the roadmap.

Target stack (`AGENTS.md` Rule 3): **frontend** React 19 + Tailwind + Next.js
(+ Three.js where it earns it); **backend** Node.js + Express. New and rewritten
code uses only these. The screens land there one at a time — see
[`PLAN.md`](PLAN.md) item 9.

- **Frontend.** Finance (`finance-os/`), Learning and the Model screen are
  React 19 / Next.js (`output: "export"`, static). Main Menu and Enhancement
  still serve plain HTML / CSS / JS with an optional prebuilt Next.js UI
  (`Page/next_app/out`) picked up automatically if you build it. Charts:
  hand-rolled SVG / **Apache ECharts** (vendored).
- **Backend.** Node.js + Express is the target. Today it's mixed: Finance
  (`finance-os/backend`) and the other screens run **FastAPI + Uvicorn** on
  their own ports (Main Menu 8000, Finance 8001, Learning 8002, Enhancement
  8004, Model 8005), pending the P4 migration.
- **Model gateway.** An **OmniRoute** instance on `127.0.0.1:8003` (started by
  `Start_Inky/run_omniroute.py`); the Model screen reports on it. Config note:
  `Screens/Model/GATEWAY_CONFIG.md`.
- **Launcher.** Plain Python scripts in `Start_Inky/`.
- **Storage.** Local flat files + **SQLite** today; moving to a Google
  Drive–backed layer ([`PLAN.md`](PLAN.md) item 2). Nothing personal
  is committed here.
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
[`PLAN.md`](PLAN.md) for what's being worked on next —
principally moving all private data into Google Drive behind a smart
retrieval layer.

## License

MIT — see [`LICENSE`](LICENSE).
