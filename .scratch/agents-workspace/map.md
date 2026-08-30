# Wayfinder map — the AGENTS screen (agent workspace)

Label: wayfinder:map · Tracker: local markdown (`.scratch/agents-workspace/`)
Plan of record: `~/.claude/plans/i-finised-setting-up-sharded-diffie.md`
Build spec handed to Qwen 3-Max: `QWEN_BUILD_PROMPT.md` (this folder)

## Destination

`Screens/Enhancement/` is renamed to `Screens/Agents/` and rebuilt greenfield as a
local **agent workspace**: a 3-pane screen (navigator / open-room / context) on the
"Deck" theme (near-black + copper, Main-Menu DNA — not Slack's look). The existing
kanban "ideas" board becomes **one room** inside the workspace, owned by an
"Announcement Agent". `MENU_LABEL` becomes `AGENTS`; the Main Menu gets a matching
nav glyph.

Agent profiles live inside the screen at `Screens/Agents/AI_Agents/`. V1 ships **one**
real profile (`Announcement_Agent`). Real AI agents, their DM rooms, and LLM wiring
(OmniRoute, per-agent model sets, routing) are **V2**. The repo-root `Agents/` 20
stubs and `Shared_By_All_Agents/` are a **V2 reuse pool — untouched by V1**.

## Why

`PLANNED_WORK.md` P3 only asked to re-skin the kanban. The user upgraded it: the repo
already has a headless agent layer (20 role-stubs, a supervisor + lease board, a
Main-Menu fleet endpoint, "RUBRIC Agentic OS / Kage.GG" branding) with no front-end.
This builds the front-end. `AGENTS.md` D9 records the decision.

## Phased build

Qwen 3-Max codes it **one unit per turn, backend and frontend alternating**, each
gated by Claude before the next (stops plan drift). 12 turns — full table in
`QWEN_BUILD_PROMPT.md` §Turns.

| Turn | Side | Delivers |
|---|---|---|
| 1 | BE | `screen_definition` + `settings` + `requirements` + `.gitignore` |
| 2 | BE | `db.py` + `schema.sql` (ideas/comments/meta verbatim + rooms + messages) |
| 3 | BE | `seed.py` + examples + `AI_Agents/Announcement_Agent/description.txt` |
| 4 | BE | `server_for_agents.py` + `GET /api/agents/workspace` |
| 5 | FE | `next_app/` scaffold + `layout` + `globals.css` (Deck) + `lib/api.ts` + shell |
| 6 | BE | `services/board.py` (kanban API, ported) |
| 7 | FE | Board room (kanban + drag-drop + idea detail + comments) |
| 8 | BE | `services/agents.py` (`/agents`, `/rooms`, `/ask` stub) |
| 9 | FE | Right-pane agent card + RUNS stub |
| 10 | FE | Polish (Deck pass, motion-reduce, responsive, empty states) |
| 11 | MENU | `NavPanel.tsx` `agents` glyph + rebuild `Main_Menu/Page/next_app` |
| 12 | — | Build + verify gate |

## Decisions so far

- **Rename, don't fork.** `git mv Screens/Enhancement Screens/Agents`; all
  `*_for_enhancement.*` → `*_for_agents.*`; API prefix `/api/enhancement` →
  `/api/agents`. Port 8004 kept. `SCREEN_NAME` must equal the folder name lowercased.
- **Screen owns its agents.** Profiles in `Screens/Agents/AI_Agents/` (Rule 4/5). Not
  the repo-root `Agents/` dir — that stays as a reference pool for V2.
- **Board unchanged in substance.** `ideas` / `comments` / `meta` schema carried over
  verbatim from `Screens/Enhancement/Calculations/manage_enhancement_ideas.py`; `ENH-n`
  keys kept; renaming keys is a separate later task.
- **No topic/multi-agent rooms in V1** (the user found the concept unclear and they add
  nothing until agents can talk). `rooms.kind ∈ {board, agent, system}`.
- **Theme "Deck"** — own token set, sibling of Main Menu's RUBRIC look; agent-status
  hues defined now (idle/running/blocked/done) though only used in V2. Red stays
  act-now/destructive only.
- **Stack** matches the newer screens: Next 16 / React 19 / Tailwind v4 / static export;
  FastAPI + stdlib sqlite3. Banned: framer-motion, chart libs, component libs, markdown
  libs, `use-sync-external-store`, ORMs. `grep -R "Shared_By_All" Screens/Agents/` empty.
- **Main Menu in scope**: label comes free via `screen_definition`; add the `agents`
  SVG glyph to `NavPanel.tsx` and rebuild its `next_app`.

## Resolved (2026-08-30, after the prompt was already handed to Qwen — apply as turn-review corrections, do NOT re-edit QWEN_BUILD_PROMPT.md)

- **V1 roster = all 21.** `AI_Agents/` gets `Agent_Head/` (the lead, owns the board) +
  a **copy** of all 20 repo-root `Agents/*/description.txt` stubs. Repo-root `Agents/`
  stays untouched (still feeds `Shared_By_All_Agents/read_agent_cards.py`). Navigator
  lists 21; the 20 non-lead agents show only their card (right pane) in V1 — rooms /
  messaging are V2.
- **Lead profile name = "Agent Head"** (was "Announcement Agent"). `AI_Agents/Agent_Head/`.
  Board room seeds `agent_name='Agent_Head'`.
- **Wordmark / `MENU_LABEL` = "AGENT DECK"** (folder stays `Screens/Agents/`,
  `SCREEN_NAME="agents"` — locked by discovery; only the display string changes). On-screen
  header `[AGENT DECK]`.

Where these land in the turn flow: Turn 1 → `MENU_LABEL` + wordmark string. Turn 3 →
`Agent_Head/description.txt` + the 20 copied stubs; `rooms` seed `agent_name`. Turn 5/9 →
navigator renders 21 rows.

## Not in this effort

- Any LLM call, OmniRoute wiring, agent execution, routing, per-agent model sets (V2).
- Touching / moving / importing repo-root `Agents/` or `Shared_By_All_Agents/` (V2).
- The Main-Menu "agent fleet" endpoint (leave; the AGENTS screen supersedes it).
- Renaming board card keys (`ENH-n`).
