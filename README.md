# Kage

A personal dashboard system. One folder per screen, each a self-contained
web app on its own port. The screen you land on (Main Menu, port 8000)
discovers the rest and links to them.

Kage is the public code for the **Inky** dashboard (the module names you'll
see throughout are `inky`). It ships **code only** — no personal data, no
private notes, no agent memory. Screens that normally show saved data start
empty; you supply your own. Real data lives outside this repo, in a folder
you point `KAGE_DATA_DIR` at — see [`PLAN.md`](PLAN.md) for the roadmap.

Stack (`CLAUDE.md` Rule 4): **frontend** React 19 + Tailwind + Next.js (+ Three.js
where it earns it); the **backend runtime is chosen per service** — the seam between
screens is HTTP, so each one uses the runtime whose libraries its work actually lives
in, and never imports across the line.

- **Frontend.** Finance, Learning and the Model screen are
  React 19 / Next.js (`output: "export"`, static). Main Menu and Enhancement
  still serve plain HTML / CSS / JS with an optional prebuilt Next.js UI
  (`Page/next_app/out`) picked up automatically if you build it. Charts:
  hand-rolled SVG / **Apache ECharts** (vendored).
- **Backend.** Mixed on purpose. **FastAPI + Uvicorn**: Main Menu `8000`,
  Model `8001`, Finance `8002`, Learning `8003`, Agent Deck `8004`.
  **Node + Express**: Anime `8005` (local-only) and the MCP servers. Each screen's port is written in exactly one place —
  `Screens/<Name>/Backend/settings_for_<name>.py`; `Start_Inky/ports_for_inky.json`
  is a regenerated snapshot of them.
- **Model gateway.** An **OmniRoute** instance on `127.0.0.1:8010` (started by
  `Start_Inky/run_omniroute.py`); the Model screen reports on it. Config note:
  `Screens/Model/GATEWAY_CONFIG.md`.
- **Launcher.** Plain Python scripts in `Start_Inky/`.
- **Storage.** One seam every screen persists through (Storage screen, `:8009`):
  plain files under `KAGE_DATA_DIR` outside the repo, with hybrid keyword +
  dense retrieval on top. Nothing personal is committed here.
- Agents live inside the Agent Deck screen (`Screens/Agents/AI_Agents/`). The
  older root-level agent layer was removed in 2026-09-03 — it could not run.

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

Then open <http://127.0.0.1:8000> — that address is the Main Menu and nothing else.
Ctrl+C in that window stops everything.

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
[`NOW.md`](NOW.md) for what's being worked on right now, and
[`PLAN.md`](PLAN.md) for the queue behind it.

## License

MIT — see [`LICENSE`](LICENSE).
