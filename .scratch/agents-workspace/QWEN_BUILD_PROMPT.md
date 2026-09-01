# Build spec — Kage **AGENTS** screen (hand this whole file to Qwen 3-Max)

You are building one screen of **Kage** (public GitHub repo; internal module names stay
`inky`) — a private, self-hosted personal-dashboard system. Kage is a **public repo**:
**no personal data, keys, tokens, or file contents may ever be committed.**

You are **renaming and rebuilding** the current `Screens/Enhancement/` screen into
`Screens/Agents/` — a local **agent workspace**. It replaces that folder's contents
wholesale (frontend **and** backend). Keep nothing from the old plain-HTML page or the
old FastAPI server; the *only* thing carried over is the board's **data model and CRUD
logic** (see §7).

---

## 0. Decisions already made — do not deviate

| Topic | Decision |
|---|---|
| Folder | `Screens/Enhancement/` → **`Screens/Agents/`**. `SCREEN_NAME = "agents"` (must equal the folder name lowercased). |
| Menu | `MENU_LABEL = "AGENTS"`, `MENU_ORDER = 4`, port **8004** (all kept). |
| API prefix | `/api/agents` (was `/api/enhancement`). |
| What it is | A 3-pane **agent workspace**: navigator (left) / open-room (center) / context (right). Rooms switch **client-side** (no per-room route — static export can't do dynamic segments). |
| V1 rooms | **board** (the kanban, carried over) + **runs** (an honest stub). No agent DM rooms, no topic rooms, **no LLM** in V1. |
| Board | Same substance as today: `ideas` / `comments` / `meta` schema **verbatim**, 4 columns `ideas→todo→in_progress→done`, native HTML5 drag-drop, `ENH-n` keys, priority badges, per-card comment thread. |
| Agent profiles | Live in **`Screens/Agents/AI_Agents/<Name>/description.txt`**. V1 ships exactly one: `Announcement_Agent`. |
| Theme | **"Deck"** — see §8. Near-black + copper, Main-Menu DNA. **Not** Slack's look. |
| Backend | FastAPI + `uvicorn[standard]` + Pydantic + **standard-library `sqlite3` only**. `requirements_for_agents.txt` = exactly `fastapi`, `uvicorn[standard]`, `pydantic`. |
| Frontend | **Next.js 16.3.x, React 19.2.x, TypeScript 5, Tailwind CSS v4** (`@tailwindcss/postcss`, `@theme inline`), `output: "export"` (static). |
| Delivery | **One unit per turn**, backend and frontend alternating — see §Turns. |

---

## 1. Kage rules you MUST follow (from `AGENTS.md`)

1. **Modular to the block.** This screen is a complete independent component. It
   **imports nothing** from `Shared_By_All_Screens/` or `Shared_By_All_Agents/` and never
   reaches into another screen's code. It carries its own theme CSS, its own API client,
   its own everything. `grep -R "Shared_By_All" Screens/Agents/` must be empty. (The old
   Enhancement server imported a trace middleware, a health-check registrar and an SSE
   tail — **drop all of it.**)
2. **Stack is fixed.** React 19 + Tailwind + Next.js on the front; FastAPI + stdlib
   `sqlite3` on the back. **Banned deps:** `framer-motion`, `shadcn/ui`, `@radix-ui/*`,
   any chart library, any markdown library, `use-sync-external-store`, any ORM /
   SQLAlchemy. Every button/badge/panel is a `<div>`/`<button>` with Tailwind classes.
3. **No personal data in the repo.** `.gitignore` (§2.4) keeps out the DB, `.env`,
   `seed_local.json`, `node_modules`, `.next`, `out`. Commit code + `schema.sql` +
   `seed.py` + `seed_local.example.json` (generic data only) + the one
   `AI_Agents/Announcement_Agent/description.txt`.
4. **Honest states.** Every panel has visibly distinct **loading / error / empty** states;
   empty copy is literal ("No ideas captured yet"), never an endless spinner. List /
   history endpoints return `{"state": "ok" | "partial" | "pending", ...}` — never a bare
   `[]`. A feature that isn't wired ships its endpoint returning
   `{"state": "pending", ...}` with honest UI copy.
5. **Red is "act now" / destructive only — never decoration.**

---

## 2. Exact file tree to produce

```
Screens/Agents/
  screen_definition_for_agents.py        # 4 names + a list — see §3
  .gitignore                             # §2.4
  AI_Agents/
    Announcement_Agent/
      description.txt                     # one line — see §3
  Setup/
    requirements_for_agents.txt          # fastapi / uvicorn[standard] / pydantic
  Backend/
    settings_for_agents.py               # §3
    server_for_agents.py                 # §4 — the ONLY server: page + API + static assets
    db.py                                # §5 — one connect() + init_db()
    schema.sql                           # §6
    seed.py                              # §6 — two-tier idempotent seed
    seed_local.example.json              # shape doc (generic data)
    README_seed.md
    services/
      board.py                           # §7 — ideas/comments/status API
      agents.py                          # §7 — /agents, /rooms, /ask stub
  Page/
    next_app/
      package.json  package-lock.json (from npm i)
      next.config.ts  tsconfig.json  postcss.config.mjs
      next-env.d.ts
      app/
        layout.tsx  globals.css  page.tsx     # page.tsx == the whole workspace
      components/
        Navigator.tsx  BoardRoom.tsx  IdeaCard.tsx  IdeaDetail.tsx
        AgentCard.tsx  RunsStub.tsx
      lib/
        api.ts                                # useResource<T> + useSubmit<T>
```

Also do, as part of the effort (Turn 11): add an `agents` case to
`Main_Menu/Page/next_app/app/components/NavPanel.tsx`'s inline SVG glyph set and rebuild
`Main_Menu/Page/next_app`. **No other file under `Main_Menu/` or `Start_Inky/` changes.**

### 2.4 `.gitignore` (ship `Screens/Agents/.gitignore`)
```
agents.db
agents.db-*
*.db-wal
*.db-shm
.env
Backend/seed_local.json
seed_local.json
AI_Agents/*/Memory/
Page/next_app/node_modules/
Page/next_app/.next/
Page/next_app/out/
__pycache__/
*.pyc
```

---

## 3. The contract files

### `screen_definition_for_agents.py`
Exactly four names + a list. Nothing else (the menu rejects extras).
```python
SCREEN_NAME = "agents"          # must equal the folder name, lowercased
MENU_LABEL  = "AGENTS"
MENU_ORDER  = 4
TABS = [
    {"key": "workspace", "label": "Workspace", "endpoint": "/api/agents/workspace"},
]
```
Header docstring: what the screen is (the agent workspace), one tab, board is one room.

### `Backend/settings_for_agents.py` — plain module constants, no class
```python
from pathlib import Path
HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent
PROJECT_ROOT = HERE.parents[2]
SCREEN_NAME  = "agents"
SCREEN_LABEL = "Agents"
HOST = "127.0.0.1"
PORT = 8004
API_PREFIX = "/api/agents"
PAGE = SCREEN / "Page" / "page_for_agents.html"      # optional hand fallback; may not exist
NEXT_DIST = SCREEN / "Page" / "next_app" / "out"
USE_NEXT_UI = True
DB_PATH = HERE / "agents.db"
AI_AGENTS_DIR = SCREEN / "AI_Agents"
```
The launcher/menu only ever read `SCREEN_LABEL`, `HOST`, `PORT`, `PAGE` off this module.

### `AI_Agents/Announcement_Agent/description.txt`
One line, matching the house style of the repo-root `Agents/*/description.txt` stubs
(a role sentence, present tense, plain English). It owns the ideas board — e.g.
"Keeps the enhancement board: captures ideas, files them into columns, holds the comment
thread for each. Runs locally; wiring to a model comes later."

---

## 4. The serving contract (`server_for_agents.py`)

One uvicorn process on port 8004 serves the page at `/`, the JSON API under
`/api/agents/*`, and every Next static-export asset by path from `NEXT_DIST`.

- Flat imports: `sys.path.insert(0, <Backend dir>)`, then `import settings_for_agents as
  cfg`, `from db import init_db`, `import seed`, `from services import board, agents`.
- `app = FastAPI(title=cfg.SCREEN_LABEL)`.
- **At import time** (not in `@app.on_event` — banned): `init_db()` then `seed.run()`.
- `app.include_router(board.router)` and `app.include_router(agents.router)`.
- `GET /` — 3-way check: if `cfg.USE_NEXT_UI` and `(cfg.NEXT_DIST / "index.html").exists()`
  → `FileResponse(that)`; elif `cfg.PAGE.exists()` → serve it; else honest JSON
  `{"status": "not built yet", "api_routes": [...]}`.
- `GET /{full_path:path}` — **registered LAST**:
  - `if full_path.startswith("api/"): raise HTTPException(404)` (API 404s never fall
    through to HTML).
  - `exact = (cfg.NEXT_DIST / full_path).resolve()`; if `cfg.NEXT_DIST in exact.parents
    and exact.is_file()` → serve it (this serves `/_next/*`, fonts, `favicon.ico`).
  - else try `full_path + ".html"`, then `full_path + "/index.html"`, then `index.html`
    (SPA fallback).
  - else `raise HTTPException(404)`.
- `if __name__ == "__main__": uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)`.

**Router rule:** `APIRouter()` with **no prefix**; spell the full path on each route
(`@router.get(cfg.API_PREFIX + "/workspace")`). A sub-prefix on the router **and** a full
path on the route → every route 404s. Handlers never `pass`. POST bodies via Pydantic
models / `Body(...)`, never scalar query params (except `DELETE /ideas?id=` which the old
board already does — keep that one as a query param for parity).

### `GET /api/agents/workspace` — the bootstrap payload
```json
{
  "state": "ok",
  "rooms": [
    {"id": "board", "kind": "board", "name": "Board", "agent_name": "Announcement_Agent"},
    {"id": "runs",  "kind": "system", "name": "Runs", "agent_name": null}
  ],
  "agents": [{"name": "Announcement_Agent", "role": "<from description.txt>"}],
  "counts": {"ideas": {"ideas": 0, "todo": 0, "in_progress": 0, "done": 0}}
}
```
200 on a fresh/empty DB with zeros — never a 500. No `NaN` / `Infinity` anywhere.

---

## 5. `db.py`
```python
import sqlite3
import settings_for_agents as cfg

def connect():
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    try:
        has = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ideas'"
        ).fetchone()
        if not has:
            conn.executescript(open(cfg.SCREEN / "Backend" / "schema.sql", encoding="utf-8").read())
            conn.commit()
    finally:
        conn.close()
```
A bare `sqlite3.connect(` may appear **only** in this file.

---

## 6. `schema.sql` + seed

### Carried over **verbatim** from `Screens/Enhancement/Calculations/manage_enhancement_ideas.py` `_SCHEMA`:
```sql
CREATE TABLE IF NOT EXISTS ideas (
    id          TEXT PRIMARY KEY,
    enh_key     TEXT UNIQUE,
    title       TEXT NOT NULL,
    note        TEXT DEFAULT '',
    area        TEXT DEFAULT '',
    source      TEXT CHECK (source IN ('user','ai')) DEFAULT 'user',
    status      TEXT CHECK (status IN ('ideas','todo','in_progress','done')) DEFAULT 'ideas',
    priority    TEXT CHECK (priority IN ('low','medium','high','critical')) DEFAULT 'medium',
    order_index REAL,
    added_at    TEXT,
    updated_at  TEXT
);
CREATE TABLE IF NOT EXISTS comments (
    id         TEXT PRIMARY KEY,
    idea_id    TEXT REFERENCES ideas(id),
    text       TEXT NOT NULL,
    author     TEXT CHECK (author IN ('user','ai')) DEFAULT 'user',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
```

### New (workspace scaffolding — schema ready for V2, V1 only fills the board room):
```sql
CREATE TABLE IF NOT EXISTS rooms (
    id         TEXT PRIMARY KEY,             -- 'board', 'runs', later 'agent:<Name>'
    kind       TEXT CHECK (kind IN ('board','agent','system')) NOT NULL,
    name       TEXT NOT NULL,
    agent_name TEXT,
    position   REAL,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (       -- V1 leaves this empty
    id         TEXT PRIMARY KEY,
    room_id    TEXT NOT NULL REFERENCES rooms(id),
    author     TEXT CHECK (author IN ('user','agent','system')) NOT NULL DEFAULT 'user',
    agent_name TEXT,
    body       TEXT NOT NULL,
    idea_id    TEXT REFERENCES ideas(id),
    created_at TEXT
);
```
Field notes (keep these behaviours from the old module):
- `id` = `uuid.uuid4().hex[:12]`. `enh_key` = `ENH-<n>`, `n` = `MAX(existing)+1`, never recycled; the UI calls it `key`.
- Statuses are the column order left→right: `ideas → todo → in_progress → done`.
- `order_index` is a REAL; drop-between = midpoint of neighbours (no renumbering).
- `added_at` / `updated_at` = ISO-8601 with IST offset `+05:30`, seconds precision.
- `meta`: `seeded=yes` after the one-time seed; deleting all rows does not re-seed.

### `seed.py` — two-tier, idempotent, table order, **insert only when the table is empty**
1. If `Backend/seed_local.json` exists and parses to a dict → seed `ideas` from it.
2. Else insert the **generic** starter set: the P1–P7 cards from
   `Screens/Enhancement/enhancement_ideas_starter_seed.json` (copy that file's content in;
   they are generic project-plan items, no personal data), all `source='ai'`,
   `status='ideas'`.
Always (both tiers): seed `rooms` with the `board` row (`agent_name='Announcement_Agent'`)
and the `runs` row if absent. `run()` is a no-op on restart. Ship
`seed_local.example.json` (the `ideas` shape, `"@today"` date sentinel) + a one-paragraph
`README_seed.md`.

---

## 7. Backend services

### `services/board.py` — port the CRUD from `Screens/Enhancement/Calculations/manage_enhancement_ideas.py` + `find_similar_ideas.py`
Adapt to `from db import connect`. Uniform envelope: success `{"ok": true, "item": <idea>}`
(or `{"ok": true}` for delete); failure `{"ok": false, "problem": "<msg>"}` with HTTP 400
(`ValueError`) / 404 (unknown id). Idea shape:
`{id, key, title, note, area, source, status, priority, order_index, added_at, updated_at, comments:[{id,text,author,created_at}]}`.

| Route | Body / params | Notes |
|---|---|---|
| `GET  /api/agents/ideas` | — | `{"state":"ok","ideas":[…]}` — column order then `order_index` |
| `POST /api/agents/ideas` | `{title, note?, area?, source?="user", priority?="medium"}` | near-dup check (`find_similar_ideas`: ≥4 shared consecutive words OR `difflib` ratio ≥ 0.75, against **open** ideas only) → add `"duplicate_warning": {...}`, **non-blocking**. Exact `(title,note,area,source)` dup → return the existing item with `"duplicate": true`, don't insert. |
| `PUT  /api/agents/ideas/{id}` | `{title?, note?, area?, priority?}` | only supplied fields; touch `updated_at` |
| `PATCH /api/agents/ideas/{id}/status` | `{status, order_index?}` | no `order_index` → append to the bottom of the target column |
| `POST /api/agents/ideas/{id}/comments` | `{text, author?="user"}` | returns the idea with the new comment |
| `DELETE /api/agents/ideas?id=<id>` | query `id` | deletes the idea + its comments |

### `services/agents.py`
| Route | Returns |
|---|---|
| `GET /api/agents/workspace` | the §4 bootstrap payload (aggregates rooms + `GET /agents` + idea counts) |
| `GET /api/agents/agents` | `{"state":"ok","agents":[{"name","role"}]}` — one row per `AI_Agents/*/description.txt` (folder name = `name`, file's first non-empty line = `role`). Empty dir → `{"state":"ok","agents":[]}`. |
| `GET /api/agents/rooms` | `{"state":"ok","rooms":[…]}` from the `rooms` table |
| `GET /api/agents/rooms/{id}/messages` | `{"state":"ok","messages":[]}` in V1 (shape ready for V2) |
| `POST /api/agents/agents/{name}/ask` | **stub** — `{"state":"pending","reply":null,"note":"agent wiring lands in V2"}` |

---

## 8. Theme — "Deck" (`app/globals.css`, Tailwind v4)

`@import "tailwindcss";` then `@theme inline { ... }` mapping the tokens below to Tailwind
color names (`--color-deck-bg`, etc.). Define the raw values on `:root`. **No** `<link>` to
`/shared` — self-contained.

```
--deck-bg      #0E0E0E     ground
--deck-panel   #141212     panel surface
--deck-raised  #1A1818     raised surface (cards, compose)
--deck-line    #333333     1px borders
--deck-text    #F4F2EE     body text
--deck-dim     #8B9099     secondary / meta
--deck-copper  #FF7A00     primary accent (from Main Menu) — active, focus, "you"
--deck-slate   #6E8BA0     counter-accent — agent / system voice
--stat-idle    #8B9099     ) agent status dots — defined now,
--stat-run     #FF7A00     ) used in V2. running dot: slow opacity pulse.
--stat-block   #F2A93B     ) "blocked" is bright amber, NOT red.
--stat-done    #3FD9A4     ) jade, used sparingly.
--deck-alert   #E33B2E     the ONLY red — destructive / act-now, never decoration
```

- `.deck-panel` = `background: var(--deck-panel)`, `border: 1px solid var(--deck-line)`,
  `border-radius: 4px`, `box-shadow: inset 0 0 32px rgba(255,255,255,.015)` (Main Menu's
  inset glow).
- Section labels: 11px / 700 / `letter-spacing: .14em` / uppercase / `var(--deck-dim)`.
- `.num` (or a Tailwind util): `font-variant-numeric: tabular-nums` — on every figure,
  `ENH-` key, timestamp.
- Fonts via `next/font/google` (not `@import`): **IBM Plex Sans** body, **IBM Plex Mono**
  for keys/timestamps/meta, a display face (e.g. **Chakra Petch**) only for the
  `[AGENTS]` wordmark. Bind as CSS variables on `<body>`.
- Priority badge colours: `low → var(--deck-line)`, `medium → var(--deck-slate)`,
  `high → var(--deck-copper)`, `critical → var(--deck-alert)`.
- `source='ai'` ideas: a 2px `var(--deck-slate)` left border (the AI-content marker).
- Motion: a 1px `var(--deck-copper)` underline that slides between navigator sections;
  the running-status dot pulses. **Everything** wrapped in `motion-reduce:` (or a
  `@media (prefers-reduced-motion: reduce)` kill block).
- Layout: CSS grid, `[left 260px] [center 1fr] [right 320px]`. Responsive breakpoints at
  **1100 / 820 / 560 / 420** px — below 820 the right pane collapses to a toggle; below
  560 the navigator becomes a top drawer.
- Modals: plain `fixed inset-0` + an Escape-key handler. No modal library.

---

## 9. Mine the old code (reference, not copy-paste)

- `Screens/Enhancement/Calculations/manage_enhancement_ideas.py` — the schema, `ENH-n`
  key allocation, `order_index` midpoint logic, the CRUD, the envelope shape. **Port it**
  into `services/board.py` against `db.connect()`.
- `Screens/Enhancement/Calculations/find_similar_ideas.py` — the pure near-dup check.
  Port as-is (stdlib `difflib` only).
- `Screens/Enhancement/Page/js/script_for_enhancement.js` — the *interaction* reference
  for the kanban (native HTML5 drag-drop, midpoint `order_index` on drop, `dragend`
  suppresses the click, modal SAVE diffs fields). Rebuild it in React; do not import it.
- `Screens/Learning/` — the house build reference: `Backend/server_for_learning.py`
  (serving contract), `Backend/db.py`, `Backend/services/*.py` (router shape),
  `Page/next_app/lib/api.ts` (`useResource` / `useSubmit`, `API_BASE = ""`), the
  `"use client"` + explicit loading/error/empty branch pattern.
- `Main_Menu/Page/next_app/app/globals.css` — where the copper/inset-glow DNA comes from.

**Do NOT** carry over from the old Enhancement server: the trace middleware, `health_check`
registration, the `/live` SSE endpoint, `WATCHED_FOLDERS` / `/dev/changed-since`, any
`Shared_By_All_*` import.

---

## 10. Hard don'ts (working-memory list)

No personal data / keys / tokens; DB + `.env` + `seed_local.json` + build output
git-ignored. No ORM — stdlib `sqlite3` through the one `connect()`. No `framer-motion` /
`shadcn` / `@radix` / chart lib / markdown lib / `use-sync-external-store`. No imports
from `Shared_By_All_*` or another screen. No LLM call, no OmniRoute, no agent execution
(all V2). Don't touch repo-root `Agents/`, `Shared_By_All_Agents/`, or the Main-Menu
fleet endpoint. Don't rename `ENH-` keys. Router prefix = none, full path per route.
Handlers never `pass`. `"use client";` is the literal first line of every client file.
Don't touch `Start_Inky/`; the only `Main_Menu/` change is the one nav glyph (Turn 11).

---

## Turns — the delivery protocol

Deliver **one turn at a time**. For each turn output **only** that turn's file(s), each as
a full file under a path heading, in one code block, **no diffs, no ellipsis, no "unchanged"
placeholders**. Then stop and wait. The reviewer (Claude) checks it against this spec and
either asks for one correction or hands you the next turn. Do not run ahead.

| # | Side | Deliver | Self-check before you send |
|---|---|---|---|
| 1 | BE | `screen_definition_for_agents.py`, `Backend/settings_for_agents.py`, `Setup/requirements_for_agents.txt`, `Screens/Agents/.gitignore` | 4 constant names in the definition; `PORT=8004`; `MENU_LABEL="AGENTS"`; `TABS` has 1 entry whose `endpoint` starts `/api/`; requirements = the 3 lines only |
| 2 | BE | `Backend/db.py`, `Backend/schema.sql` | `init_db()` on an empty file creates ideas+comments+meta+rooms+messages; `PRAGMA foreign_keys=ON`; bare `sqlite3.connect(` only in `db.py` |
| 3 | BE | `Backend/seed.py`, `Backend/seed_local.example.json`, `Backend/README_seed.md`, `AI_Agents/Announcement_Agent/description.txt` | two-tier; inserts only when a table is empty; seeds the `board` + `runs` rooms + the P1–P7 ideas; second run is a no-op; `description.txt` is one plain sentence |
| 4 | BE | `Backend/server_for_agents.py` + `Backend/services/agents.py` (just `GET /workspace` + `GET /agents` for now; stub the rest of §7's `agents.py` routes) | boots on 8004; `GET /api/agents/workspace` → 200 with the §4 shape on a seeded DB; `/api/*` never returns HTML; catch-all is the last route |
| 5 | FE | `Page/next_app/{package.json,next.config.ts,tsconfig.json,postcss.config.mjs}`, `app/layout.tsx`, `app/globals.css`, `lib/api.ts`, `app/page.tsx` (shell only), `components/Navigator.tsx`, `components/RunsStub.tsx` | `npm i && npm run build` → `out/index.html`; page fetches `/api/agents/workspace`, renders the navigator (AGENTS → Announcement Agent; RUNS) with distinct loading/error/empty; `grep -R "framer-motion\|shadcn\|recharts" out/` empty; `API_BASE = ""` |
| 6 | BE | `Backend/services/board.py` (full §7 table) + wire its router into `server_for_agents.py` | every route 200 on an empty DB; `PATCH .../status` reorders via float `order_index`; near-dup warning is present and non-blocking; envelope shape matches |
| 7 | FE | `components/BoardRoom.tsx`, `components/IdeaCard.tsx`, `components/IdeaDetail.tsx`; wire the board room into `app/page.tsx` | 4 columns; native drag-drop moves a card and persists (midpoint `order_index`); clicking a card opens `IdeaDetail` in the right pane with its comment thread; posting a comment works; `dragend` suppresses the click; Deck styling |
| 8 | BE | finish `Backend/services/agents.py` — `GET /rooms`, `GET /rooms/{id}/messages`, `POST /agents/{name}/ask` stub | `/rooms` returns the 2 seeded rooms; `/messages` → `{"state":"ok","messages":[]}`; `/ask` → `{"state":"pending",...}` |
| 9 | FE | `components/AgentCard.tsx`; finish `RunsStub.tsx`; wire both into `app/page.tsx` | selecting Announcement Agent shows its card (name + role) in the right pane; RUNS shows the literal empty copy; no console errors |
| 10 | FE | polish pass across `app/globals.css` + components | Deck theme consistent; `motion-reduce:` on every animation; the 4 breakpoints behave; empty-state copy is literal; `[AGENTS]` wordmark; Esc closes `IdeaDetail`/modals |
| 11 | MENU | patched `Main_Menu/Page/next_app/app/components/NavPanel.tsx` (add an `agents` case to the inline SVG glyph map) — full file | the `agents` key renders a real glyph, not the `dot` fallback; nothing else in the file changes; note that `Main_Menu/Page/next_app` must be rebuilt |
| 12 | — | nothing new — confirm the §11 verification gate passes | — |

---

## 11. Verification gate (all must pass)

1. `pip install -r Screens/Agents/Setup/requirements_for_agents.txt` → only fastapi /
   uvicorn / pydantic (+ their deps).
2. `python Screens/Agents/Backend/server_for_agents.py` → starts on 8004;
   `GET /api/agents/workspace` → 200 on a fresh empty DB (zeros, nulls, no NaN/Infinity);
   schema auto-creates; a second start is seeded; `seed_local.json` present vs absent both
   idempotent across restarts.
3. `cd Screens/Agents/Page/next_app && npm i && npm run build` → `out/index.html` + every
   asset under `out/_next/`; `grep -R "framer-motion\|shadcn\|recharts\|chart.js" out/`
   empty.
4. Server running → `http://127.0.0.1:8004/` → the navigator lists AGENTS → Announcement
   Agent and RUNS; the Board room renders the seeded ideas in 4 columns; drag a card →
   it moves and survives a reload; open a card → right pane shows detail + comments;
   post a comment → it appears; `/_next/*` return 200 from the same origin.
5. `grep -R "Shared_By_All" Screens/Agents/` empty; `grep -Rn "sqlite3.connect(" Screens/Agents/Backend/` only inside `db.py`.
6. `python Start_Inky/start_every_screen.py` → a row **"AGENTS"** at menu position 4,
   linking to `:8004`, opening the workspace — with **no edits to `Start_Inky/`** and only
   the one glyph edit to `Main_Menu/`.
7. `git status` → only code + `schema.sql` + `seed.py` + `seed_local.example.json` +
   `README_seed.md` + `AI_Agents/Announcement_Agent/description.txt` + configs + the
   rebuilt Main-Menu `out/` staged; `agents.db`, `.env`, `seed_local.json`,
   `node_modules`, `.next`, `out` (under `Screens/Agents/`) all git-ignored.
