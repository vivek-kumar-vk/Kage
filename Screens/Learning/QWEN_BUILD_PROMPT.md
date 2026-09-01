# Build prompt — Kage **Learning** screen (hand this whole file to Qwen 3-Max)

You are building one screen of **Kage** (github repo name; internal module names stay
`inky`) — a private, self-hosted personal-dashboard system. Kage is a **public repo**:
**no personal data, keys, tokens, or file contents may ever be committed.**

Deliver a complete, working **Learning** screen that drops into `Screens/Learning/`.
It replaces the current contents of that folder **wholesale**, with ONE exception:
**keep `Screens/Learning/screen_definition_for_learning.py` exactly as it is** (it is
the menu's only knowledge of this screen — name `learning`, `MENU_ORDER = 2`, tabs
`today` / `plan` / `recall`).

There is a rough earlier build to mine for working code — see **§9**. It is not
conformant; do not copy it verbatim.

---

## 0. The decisions already made (do not deviate)

| Topic | Decision |
|---|---|
| Tabs | **Today · Plan · Recall** only. No Hunt / Resume / job-hunt / interviews — that is a future separate screen. |
| Theme | **Terminal / CLI**: green-on-black, `JetBrains Mono`. Keep the rough build's look (§8). |
| Data | **SQLite + a seed file only.** No Google Drive, no FAISS, no `sentence-transformers`, no `night_worker.py` in this build. |
| `/ask` (RAG) | Ship the endpoint but **stubbed**: returns `{"state": "pending", "answer": null, "sources": []}` with an honest UI message ("Ask is not wired yet"). |
| Backend | FastAPI + **standard-library `sqlite3` only**. `requirements_for_learning.txt` = exactly `fastapi`, `uvicorn[standard]`, `pydantic`. |
| Frontend | **Next.js 15.x, React 19, TypeScript 5, Tailwind CSS v3**, `output: "export"` (static). |
| Port | **8002** (already in the current `settings_for_learning.py`; keep it). |

---

## 1. Kage rules you MUST follow (from the repo's `AGENTS.md`)

1. **Modular to the block.** This screen is a complete independent component. It
   **imports nothing** from `Shared_By_All_Screens/` or `Shared_By_All_Agents/` and
   never reaches into another screen's code. It carries its own theme CSS, its own
   tiny API client, its own everything. `grep -R "Shared_By_All" Screens/Learning/`
   must be empty.
2. **Stack is fixed:** React 19 + Tailwind + Next.js + (optional) Three.js on the
   front; FastAPI + stdlib `sqlite3` on the back. No other UI libraries — **banned:**
   `framer-motion`, `shadcn/ui`, `@radix-ui/*`, any chart library, any markdown
   library, `use-sync-external-store`, any ORM / SQLAlchemy.
3. **No personal data in the repo.** `.gitignore` (add/extend
   `Screens/Learning/.gitignore`) keeps out `learning.db`, `learning.db-*`,
   `*.db-wal`, `*.db-shm`, `.env`, `Backend/seed_local.json`,
   `Page/next_app/node_modules/`, `Page/next_app/.next/`,
   `Page/next_app/out/`. Commit code + `schema.sql` + `seed.py` +
   `seed_local.example.json` (generic example data only — no real names,
   employers, PANs). The user's real study board lives only in the git-ignored
   `Backend/seed_local.json` (see §6).
4. **Honest states.** Every panel has visibly distinct **loading / error / empty**
   states; empty copy is literal ("No sessions logged yet"), never an endless
   spinner. Time-series / history endpoints return
   `{"state": "ok" | "partial" | "pending", ...}` — never a bare `[]`.

---

## 2. Exact file tree to produce

```
Screens/Learning/
  screen_definition_for_learning.py      # KEEP AS-IS — do not touch
  .gitignore                             # new — see §1.3
  Setup/
    requirements_for_learning.txt        # fastapi / uvicorn[standard] / pydantic
  Backend/
    settings_for_learning.py             # see §3
    server_for_learning.py               # see §4 — the ONLY server; serves page + API + assets
    schema.sql                           # see §6
    seed.py                              # two-tier idempotent seed — see §6
    seed_local.example.json              # shape doc; user copies → seed_local.json (git-ignored)
    README_seed.md                       # how to build seed_local.json
    db.py                                # one connect() helper — see §5
    services/                            # route logic, one file per concern
      today.py  plan.py  recall.py  ask.py
  Page/
    next_app/
      package.json  next.config.ts  tsconfig.json  postcss.config.mjs
      tailwind.config.js  next-env.d.ts
      app/
        layout.tsx  globals.css  page.tsx            # page.tsx = Today
        plan/page.tsx  recall/page.tsx
      components/  (TopNav.tsx, Heatmap.tsx, panels…)
      lib/api.ts                                     # useResource<T>, useSubmit
```

`Screens/Learning/Calculations/` (the old tree) is **deleted**. All logic lives in
`Backend/services/*.py`. (Kage's older screens used a `Calculations/` folder; this
screen keeps its maths in `services/` next to the server — same "no shared code"
intent, fewer folders.)

---

## 3. `Backend/settings_for_learning.py`

Plain module-level constants (no class). Required names, read by the launcher and
the Main Menu:

```python
from pathlib import Path
HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent
PROJECT_ROOT = HERE.parents[2]

SCREEN_NAME  = "learning"
SCREEN_LABEL = "Learning"
HOST = "127.0.0.1"
PORT = 8002
API_PREFIX = "/api/learning"

NEXT_DIST = SCREEN / "Page" / "next_app" / "out"   # where `npm run build` writes
USE_NEXT_UI = True                                  # serve the export when it exists
DB_PATH = HERE / "learning.db"
```

---

## 4. `Backend/server_for_learning.py` — the serving contract (get this right)

The Kage launcher (`Start_Inky/start_every_screen.py`) starts every
`Screens/<X>/Backend/server_for_*.py` that also has a `settings_for_*.py` with a
`PORT`. Each screen's server runs on its **own port** and must serve, all from
that one port / origin:

- `GET /`  → the page. If `USE_NEXT_UI` and `NEXT_DIST/index.html` exists, return
  it; else return a small honest "not built yet" JSON listing the working API
  routes. (No import from any shared folder for this — write the 5-line fallback
  inline.)
- `GET /api/learning/*` → the JSON API (see §7).
- **`GET /_next/*`, `/favicon.ico`, and every other exported asset** → served
  from `NEXT_DIST`. The Next export references assets as **absolute** `/_next/...`
  (no `basePath`), and in Kage's normal run mode the browser loads the page
  straight from `http://127.0.0.1:8002/`, so the asset requests come back to
  **this** server. You MUST serve them. Pattern that works (copy the shape):

  ```python
  from fastapi import FastAPI, HTTPException
  from fastapi.responses import FileResponse, JSONResponse
  app = FastAPI(title=cfg.SCREEN_LABEL)
  # ... all @app.get(cfg.API_PREFIX + "/...") routes first ...

  @app.get("/{full_path:path}")
  def _static_or_page(full_path: str):
      if full_path.startswith("api/"):
          raise HTTPException(404)
      root = cfg.NEXT_DIST
      exact = (root / full_path).resolve()
      if root in exact.parents and exact.is_file():
          return FileResponse(exact)
      for cand in (root / f"{full_path}.html", root / full_path / "index.html",
                   root / "index.html"):
          if cand.is_file():
              return FileResponse(cand)
      raise HTTPException(404)
  ```
  Register this catch-all **last**, after every real API route.
- DB: call `db.init_db()` once at import time (creates the schema if the file is
  missing) and `seed.run()` (idempotent — never overwrites existing rows).
- `if __name__ == "__main__": uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)`.
- Route handlers have **real bodies, never `pass`**. DB access via a
  `Depends(_db)` generator (`conn = db.connect(); try: yield conn; finally: conn.close()`).
  POST bodies via a Pydantic model or `Body(...)`, never scalar query params.
- The router's own `APIRouter(prefix=...)` — if you use one — takes the
  **sub-segment only** (`/topics`), never `/api/learning` (double prefix → every
  route 404s). Simplest: no sub-router, decorate with the full
  `cfg.API_PREFIX + "/..."`.

---

## 5. `Backend/db.py`

```python
import sqlite3, pathlib
import settings_for_learning as cfg          # same Backend dir on sys.path

def connect():
    conn = sqlite3.connect(cfg.DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        if not c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='topics'").fetchone():
            c.executescript((pathlib.Path(__file__).parent / "schema.sql").read_text("utf-8"))
```

Every DB open goes through `connect()`. Grep-ban a bare `sqlite3.connect(` anywhere
else in the screen.

---

## 6. `Backend/schema.sql`

```sql
CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  stack_area TEXT NOT NULL CHECK(stack_area IN ('core','drip','capture')),
  status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','learning','done')),
  track TEXT NOT NULL DEFAULT 'A' CHECK(track IN ('A','B')),
  position INTEGER DEFAULT 0,
  progress REAL DEFAULT 0.0,
  target_date TEXT,
  source_doc TEXT,
  "group" TEXT                          -- optional Plan-board section header
);
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER NOT NULL REFERENCES topics(id),
  session_date TEXT NOT NULL,          -- ISO yyyy-mm-dd
  minutes INTEGER NOT NULL DEFAULT 0,
  confidence INTEGER,                  -- 1..5, nullable
  notes TEXT
);
CREATE TABLE IF NOT EXISTS week_plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  week_start TEXT NOT NULL UNIQUE,     -- ISO date of the Monday
  focus_a TEXT, focus_b TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER REFERENCES topics(id),
  front TEXT NOT NULL,
  part1 TEXT NOT NULL, part2 TEXT NOT NULL, part3 TEXT NOT NULL,
  part4 TEXT NOT NULL, part5 TEXT NOT NULL,
  tag TEXT NOT NULL DEFAULT 'core' CHECK(tag IN ('core','drip','capture')),
  tether TEXT
);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id INTEGER NOT NULL REFERENCES cards(id),
  due_date TEXT NOT NULL,
  ease REAL NOT NULL DEFAULT 2.5,
  last_result TEXT,
  last_graded_date TEXT,
  status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','active'))
);
```

### Two-tier seed (get this right — it is how the real content lands)

`seed.py` must be idempotent and run in this order, only touching a table when
it is **empty**:

1. **If `Backend/seed_local.json` exists**, load topics / week_plans / cards
   (+ their `reviews`) from it. This file is **git-ignored** — it holds the
   user's actual study board and never enters the public repo.
2. **Else** insert a handful of **generic** rows so a fresh clone still demos:
   ~4 example topics ("Learn Docker networking", "Kubernetes probes", …), one
   `week_plans` row, ~3 recall cards each with a `reviews` row.

Commit `Backend/seed_local.example.json` showing the exact shape so the user can
copy → fill → save as `seed_local.json`:

```json
{
  "topics": [
    {"name": "…", "stack_area": "core", "track": "A", "position": 1,
     "status": "learning", "progress": 0.0, "target_date": null,
     "source_doc": null, "group": "Architecture & pipeline"}
  ],
  "week_plans": [
    {"week_start": "2026-08-25", "focus_a": "…", "focus_b": "…", "note": "…"}
  ],
  "cards": [
    {"front": "…", "parts": ["…","…","…","…","…"], "tag": "core",
     "tether": "…", "topic_name": "…",
     "review": {"due_date": "2026-08-30", "ease": 2.5, "status": "new"}}
  ]
}
```

Notes on the mapping:
- `topics[].group` is optional free text for the Plan board's section headers.
  Add a nullable `group TEXT` column to the `topics` table in §6 for it.
- `cards[].topic_name` is resolved to `topic_id` at seed time (match by `name`;
  skip the FK if no match). `cards[].parts` → the five `partN` columns.
- Dates in the example use IST; keep them ISO `yyyy-mm-dd`.
- The user will hand you the source material to convert into `seed_local.json`
  (a Splunk two-track study board — `study_topics.json`, `recall_cards.json`,
  and a week-plan list). If it is not attached, still ship
  `seed_local.example.json` + the generic fallback, and a one-paragraph
  `Backend/README_seed.md` telling the user how to produce `seed_local.json`.

---

## 7. API surface (name these exactly; every handler returns real data)

- `GET  /api/learning/today` →
  `{ "streak": {"days": int, "last_studied": str|null},
     "week": {"minutes": int, "target_minutes": int},
     "today_plan": {"track_a": str, "track_b": str, "capture": str},
     "recent_activity": [{"date","minutes","topic","notes"}],   // newest first, ≤5
     "due_cards": int }`
- `GET  /api/learning/plan` →
  `{ "state": "ok"|"partial"|"pending",
     "tracks": {"A": [topic...], "B": [topic...]},   // topic = id,name,stack_area,status,progress,position
     "week": {"week_start","focus_a","focus_b","note"} | null }`
- `POST /api/learning/topics`            body `{name, stack_area, track, target_date?}` → the new topic
- `PUT  /api/learning/topics/{id}`       body `{name?, status?, progress?, position?}` → updated topic
- `DELETE /api/learning/topics/{id}`     → `{"deleted": id}` (204-style ok even if already gone)
- `GET  /api/learning/sessions?topic_id=`   → `{"state":..., "sessions":[...]}`
- `POST /api/learning/sessions`         body `{topic_id, minutes, confidence?, notes?}` → the new session (also bumps topic progress)
- `GET  /api/learning/recall` →
  `{ "counts": {"today":int,"pending":int,"all":int},
     "queues": {"today":[card...], "pending":[card...], "all":[card...]} }`
  card = `{review_id, id, front, parts:[5], tag, tether}`
- `POST /api/learning/reviews/{id}/grade`  body `{grade: "again"|"hard"|"good"|"easy"}` → `{"state":"ok"}`
  (SM-2-ish: again→due today status active; hard/good/easy→due +1/+3/+7 days; ease clamped 1.3–2.8; `422` on a bad grade)
- `POST /api/learning/ask`  body `{query}` → **stub** `{"state":"pending","answer":null,"sources":[]}`

All dates are IST (`datetime.now(timezone(timedelta(hours=5, minutes=30)))`).
No `NaN` / `Infinity` in any payload. `GET /api/learning/today` must return `200`
on a fresh empty DB (before seed), with zeros and `null`s, not a 500.

---

## 8. Theme (terminal / CLI) — carry it in the screen's own `app/globals.css`

Reuse the rough build's tokens verbatim:

```css
:root{
  --term-bg:#050505; --term-fg:#e0e0e0; --term-green:#00ff41; --term-cyan:#00ffff;
  --term-amber:#ffb000; --term-violet:#b388ff; --term-red:#ff5555;
  --term-dim:#555555; --term-border:#333333;
  --heat-0:#111111; --heat-1:#003300; --heat-2:#006600; --heat-3:#009900; --heat-4:#00ff41;
}
body{background:var(--term-bg);color:var(--term-fg);font-family:'JetBrains Mono',monospace;margin:0}
```

- Font: `JetBrains Mono` via `next/font/google` (not a raw `@import` — keeps the
  static export self-contained). Fallback `'Fira Code', monospace`.
- `tailwind.config.js`: map `term-*` colours to the CSS vars (see the rough
  build's config — reuse it).
- Nav: a top strip `[KAGE_OS]  TODAY · PLAN · RECALL`, active item in
  `--term-green` with a bottom border. Prompt-style headings (`> TODAY`).
- Grade buttons colour-coded: again=red, hard=amber, good=green, easy=cyan.
- **Red (`--term-red`) is "act now" / destructive only — never decoration**
  (Kage rule; a monetary/again state that is merely negative uses `--term-dim`).
- Charts (the activity heatmap) are **hand-rolled SVG or a CSS grid** — compute
  `index→x`, `value→colour` from real data; no chart library, no hand-drawn
  approximation.
- Every animation is CSS / Tailwind `animate-*` with a `motion-reduce:` off
  switch. `"use client";` is the literal first line of any file using a hook.
- Modals: a plain `fixed inset-0` div with an `Escape` handler.

---

## 9. The rough build to mine — `C:\Users\vkjha\OneDrive\Desktop\New folder\Screens\Learning`

`Page/` (Next 14 app) and `Setup/` (flat FastAPI). **Reusable:** the terminal
theme CSS + tailwind config; `components/Heatmap.tsx`, `RecallCard.tsx`,
`TrackRow.tsx`, `RoadmapNode.tsx`, `StatsBar.tsx`; the SM-2 grade maths in
`Setup/main.py` (`GRADES`, `grade_review`); `schema.sql` shape.

**Content source for `seed_local.json`** (the user will attach these to the
chat — do not invent this data): the repo's old build carried the real board in
`Screens/Learning/Saved_Records/study_topics.json` (a `trackA` / `trackB` →
`group` → `topics[]` tree, each `{id, topic, tier, status}`) and
`recall_cards.json`, plus week plans in
`Calculations/Plan_And_Today_Tab/seed_the_week_plans.py`. Convert that shape into
the flat `seed_local.json` of §6: `trackA`→`track:"A"`, `group`→`group`,
`topic`→`name`, `tier` "must"→`stack_area:"core"` / else `"drip"`, keep
`status`, `position` = order within the track.

**What is WRONG with it — fix all of these:**
- `Page/lib/api.ts` hardcodes `API_BASE = "http://localhost:8001"` (that is
  Finance's port, and cross-origin). Use **same-origin**: `const API_BASE = ""`
  and fetch `\`${API_BASE}${path}\``. No `localhost`, no port literal.
- `Setup/main.py` uses `@app.on_event("startup")` (deprecated) and one flat file.
  Split into `server_for_learning.py` + `services/*.py`; init the DB at import
  time (§4).
- CORS `allow_origins=["*"]` — **delete it**. Same-origin, no CORS needed.
- It has `applications` / Hunt / Resume / interview code — **drop all of it**.
- Next 14 / React 18 → Next 15 / React 19.
- No `screen_definition` / `settings` / Kage server — add them (§3, §4).
- The nav links `/`, `/learn`, `/recall` — rename to `/`, `/plan`, `/recall` to
  match the tabs, and make sure they are `next/link` relative hrefs (no host).

---

## 10. Hard don'ts (top of your working memory)

- No personal data / keys / tokens committed. `.env` + `learning.db` + build
  output gitignored.
- No ORM. stdlib `sqlite3` through the one `connect()`.
- No `framer-motion` / `shadcn` / `@radix` / chart lib / markdown lib /
  `use-sync-external-store`.
- No imports from `Shared_By_All_*`. No imports from another screen.
- Router prefix = sub-segment only (or full path, no sub-router). Handlers never
  `pass`. Long work would be a `BackgroundTask` — but this build has none.
- Don't touch `screen_definition_for_learning.py`.

---

## 11. Verification (run these; all must pass)

1. `pip install -r Screens/Learning/Setup/requirements_for_learning.txt` installs
   only `fastapi`, `uvicorn`, `pydantic` (+ their deps).
2. `python Screens/Learning/Backend/server_for_learning.py` starts on `:8002`;
   `GET /api/learning/today` → `200` on an empty DB (no `NaN`/`Infinity`);
   schema auto-creates; seed makes it non-empty on the next start. With a
   `Backend/seed_local.json` present, its topics/week/cards load; with it
   absent, the generic fallback rows load — both idempotent across restarts.
3. In `Screens/Learning/Page/next_app/`: `npm i && npm run build` → `out/`
   produced; `out/index.html`, `out/plan.html`, `out/recall.html`, `out/_next/…`
   all present. `grep -R "framer-motion\|shadcn\|recharts\|chart.js" out/` empty.
4. With the server running, open `http://127.0.0.1:8002/` → Today renders with
   real seed data; `/_next/*` assets return `200` from the same server; the
   Plan and Recall tabs load; grading a card updates its due date with no
   full-page reload.
5. `grep -R "Shared_By_All" Screens/Learning/` → empty.
   `grep -Rn "sqlite3.connect(" Screens/Learning/Backend/` → only inside `db.py`.
6. `git status` → only code + `schema.sql` + `seed.py` +
   `seed_local.example.json` + `README_seed.md` + configs staged;
   `learning.db*`, `.env`, `seed_local.json`, `node_modules/`, `.next/`,
   `out/` all ignored.
7. `python Start_Inky/start_every_screen.py` → a **LEARNING** row appears at
   menu position 2, links to `:8002`, and opens the Today page — with **no edits**
   to `Main_Menu/` or `Start_Inky/`.

Deliver the full file tree, ready to run.
