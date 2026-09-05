# CLAUDE.md — Kage

**The single source of truth for how this repo is worked on.** Read it first, every
session. Built by Claude alone since 2026-09-03.

Four docs, nothing said twice: **rules here** · today's one task in [`NOW.md`](NOW.md) ·
the queue in [`PLAN.md`](PLAN.md) · numbered decisions in [`AGENTS.md`](AGENTS.md).
`README.md` is the public face. There is no fifth (D34).

## Rules

Each rule is one line. A new standing instruction is added as one more line here —
never as a paragraph, and never into a second file.

1. **Skills first** — check the skill list at session start and invoke the matching skill before any default approach.
2. **Cheapest cloud option** that still meets the requirement exactly.
3. **Spend Claude sparingly** — batch independent tool calls, reuse earlier findings instead of re-exploring, keep context lean.
4. **Stack** — frontend is React 19 + Tailwind + Next.js (+ Three.js where it earns it); the backend runtime is chosen per service (the seam between screens is HTTP, so pick the runtime whose libraries the work lives in and never import across the line — see D21.1).
5. **Modular to the block** — every page, tab and block runs independently and calls its dependencies directly, never through a shared directory.
6. **Shrink the shared folders** — when you work near `Shared_By_All_*`, move the logic into its one caller and delete the shared file.
7. **Nothing personal in git** — Kage is public; real data lives under `KAGE_DATA_DIR`, reached through the Storage seam (D11.5), kept out of git by `.gitignore` alone since D40 (7.1) — not by living outside the repo folder.
7.1. **`KAGE_DATA_DIR` is repo-relative** (`<repo>/kage-data/`, gitignored) — one self-contained folder, code and data together, for phone/Termux hosting (D40). Superseded from "outside the repo" (original Rule 7).
8. **Honest states only** — a thing that is down says it is down; never fake data, never a silent fallback to stale data, never a record of work that did not happen.
9. **Red is act-now only** — never decorative, in any screen's palette.
10. **Track future work** — anything named "later" goes to `PLAN.md` and a card on the AGENT DECK board.
11. **Number every instruction and decision** — Rules here, backlog items in `PLAN.md`, decisions `D<n>` in `AGENTS.md`; a change to item _N_ is filed as _N.1_, _N.2_ and the parent stays as history.
12. **Delete shipped work from `PLAN.md`** — git history and the decision log are the record.
13. **Reference given (image / repo / link) = match it exactly** unless told to adapt.
14. **Ask ≤3 questions in one batch before exploring or designing** — match-exact vs adapt / scope / hard constraints — then proceed with no further gates.
15. **Verify UI work in a browser**, not only build and lint.
16. **One port per screen, written in one place** — `Screens/<Name>/Backend/settings_for_<name>.py`; regenerate the snapshot with `Start_Inky/write_ports_for_inky.py` after any change.
17. **Never name a screen** in the launcher, the menu discovery, or the one-port proxy — they find screens by walking folders, and a test enforces it.
18. **Branches are prefixed `vivek/`**; GitHub work goes through the `gh` CLI.
19. **Be concise** — in replies and commit messages, sacrifice grammar for concision.
20. **Kage never spawns an MCP server** — gateways run as their own processes; unreachable is a first-class state.
21. **Grep the disk, not git, when hunting callers** — gitignored screens (Anime, Learning `Context/`) are real runtime consumers that a tracked-files grep silently misses (D31.1).
22. **Never fill a gap** — a missing price, a lagging NAV, an unreachable poll: the point stays absent and says so. Carrying the last value forward reads as real data and hides the outage (D13.3, D20.3, D20.6).
23. **One task open at a time** — it goes in `NOW.md` with its "done when" before work starts; `PLAN.md` stays shut until that task closes.
24. **A brief dies with its build** — when work ships, delete its `.scratch/` folder and its screenshots the same day; what survives is listed in `PLAN.md`'s reference table (D34.1).

## Ports

One screen, one port. Nothing else may take these.

| Port | What | Where the port is written |
|------|------|---------------------------|
| 8000 | **Main Menu** — land here | `Main_Menu/Backend/settings_for_main_menu.py` |
| 8001 | **Finance** | `Screens/Finance/Backend/settings_for_finance.py` |
| 8002 | **Learning** | `Screens/Learning/Backend/settings_for_learning.py` |
| 8003 | OmniRoute gateway (a service, not a screen) | `Start_Inky/run_omniroute.py` |
| 8004 | **Agent Deck** | `Screens/Agents/Backend/settings_for_agents.py` |
| 8005 | **Model** — reports on the gateway | `Screens/Model/Backend/settings_for_model.py` |
| 8006 | **Anime** — Node, gitignored, local-only | `Screens/Anime/Backend/settings_for_anime.py` |
| 8007 | **Deepseek** — reports on the DeepSeek Harness | `Screens/Deepseek/Backend/settings_for_deepseek.py` |
| 8008 | **Hermes** — reports on the Hermes profile fleet | `Screens/Hermes/Backend/settings_for_hermes.py` |
| 3080 | DeepSeek Harness (`dsh web`) — a service, not a screen | `Start_Inky/run_dsh_web.py`; dsh's own default, `DSH_BASE_URL` overrides |
| 9119 | Hermes dashboard (`hermes dashboard`) — a service, not a screen | `Start_Inky/run_hermes_dashboard.py`; Hermes's own default, `HERMES_DASHBOARD_URL` overrides |
| 3100 | *free* — was the Drive MCP gateway; D11.5 moved Storage to local disk | — |
| 3101 | Market-data MCP server | `Start_Inky/run_market_mcp.py` |
| 8009 | **Storage** — local-disk seam + hybrid RAG (D11.5, D33) | `Screens/Storage/Backend/settings_for_storage.py` |
| 8010 | *reserved* — Office screen (D17.5), not built | — |
| 8080 / 8081 | *reserved* — local llama.cpp models | — |
| 9000 | one-port proxy, only for phone / ngrok | `Start_Inky/serve_everything_on_one_port.py` |

**8000 is the Main Menu and nothing else.** The Finance app used to hard-code 8000
in its own `main.py`; running it stood Finance up where the Main Menu lives and the
menu appeared to vanish. It now reads the Finance screen's own port (8001).

## Running it

```
.venv\Scripts\python Start_Inky\start_every_screen.py     # gateways + all screens, Ctrl+C stops all
Start_Inky\Start_Everything.bat                            # venv + install + gateways + screens
```

Then open <http://127.0.0.1:8000>. A screen alone:
`.venv\Scripts\python Screens\<Name>\Backend\server_for_<name>.py`.

The launcher refuses to start a screen whose port another process holds, and names
that process — a screen that dies quietly is much harder to notice than one that says why.

## Where things are

| Path | What |
|------|------|
| `Main_Menu/` | the frame you land on; discovers screens, never names one |
| `Screens/<Name>/` | one screen, one folder: `Backend/` (server + settings), `Page/`, `screen_definition_for_<name>.py` |
| `Screens/<Name>/Backend/app/` | a screen whose app is a whole tree of its own keeps it here — Finance (FastAPI) and Anime (Node) both do |
| `Screens/<Name>/Page/next_app/` | that screen's Next source; `out/` is the static export the backend serves |
| `Start_Inky/` | launchers, the port snapshot, gateway runners |
| `Shared_By_All_Screens/` | its irreducible core: three launcher/menu-discovery modules + the `Current_Numbers/` noticeboard (D31.2, D31.3) |
| `.scratch/` | gitignored briefs for **open** work only; outcomes land in `PLAN.md` (Rule 24) |
