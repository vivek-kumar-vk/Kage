# Learning Screen — build plan (personal IT / tech-stack learning tracker)

> Standalone. This plan covers only the new **Learning** screen — a brand-new Main Menu
> tab, entirely separate from every other screen. Nothing here is shared with or derived
> from any other screen's plan.

## Context

Add a **new first-class Kage screen** `Screens/Learning/` — a personal tracker for learning
the IT tech stack you build models with, paired conceptually with the Model screen and
reachable from the main-menu ring. The repo already anticipates it: `Main_Menu/Page/
next_app/app/components/NavPanel.tsx` carries a `learning` book glyph, and
`Screens/Model/screen_definition_for_model.py` notes menu order "Finance 1, **Learning 2**,
Enhancement 4". The screen is a **complete independent component** — it imports nothing from
`Shared_By_All_Screens/` or `Shared_By_All_Agents/`; it carries its own theme CSS and its
own API. You supply the page plan + visual design; this plan is the "must match Kage"
envelope to hand to the coding model (Qwen3-Max) for frontend + backend.

## 1. Frontend stack to state

- **Next.js 16.3.x**, `output: "export"` (static export), `images.unoptimized: true` — match
  `Main_Menu/Page/next_app`.
- **React 19.2, TypeScript 5, Tailwind CSS v4** (`@tailwindcss/postcss`).
- **Three.js `^0.169` + `@react-three/fiber ^9` + `@react-three/drei ^10`** — only if the
  design has 3D. Load lazily: `dynamic(() => import("./X"), { ssr: false })`, always with a
  2D fallback and a `prefers-reduced-motion` guard that freezes motion.
- **No other UI libraries.** Banned: `framer-motion`, `shadcn/ui`, `@radix-ui/*`, any chart
  library, any markdown library, `use-sync-external-store`. Animations = CSS / Tailwind
  (`animate-*` + `motion-reduce:`). Charts = **hand-rolled SVG** — compute the path from the
  data (`index → x`, `value → y` via real min/max), never hand-draw an approximation.
  Modals = a plain `fixed inset-0` div with an Escape handler.
- `"use client";` as the literal first line of any file that uses a hook. Path alias `@/*`
  (`tsconfig.json` `"paths": { "@/*": ["./*"] }` — Next does not add this for you).
- **Data fetching:** the screen fetches its **own** `/api/learning/...` endpoints (the way
  `NavPanel` fetches its own `/api/main_menu/navigation`). Ship a small `lib/api.ts` with
  `useResource<T>(path)` (returns `{data, isLoading, error, refetch}`, 3 explicit states) and
  `useSubmit(path, method)` (POST → refetch). No cross-screen imports.
- Deep-link safe: static export emits `learning/<tab>.html`; the serve layer already does
  `StaticFiles(html=True)`. Pages render **content only**; tabs/header live in the screen layout.

## 2. Backend stack to state

- **FastAPI + `uvicorn[standard]` only** (match `Screens/Model/Setup/requirements_for_model.txt`
  minimalism). Python 3.11. **Pydantic v2** for request/response models.
- **Standard-library `sqlite3` ONLY** — no ORM, no SQLAlchemy. One `services/db.py:connect()`
  helper: `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL`, `row_factory=sqlite3.Row`.
  Every DB open goes through it; grep-ban bare `sqlite3.connect(` elsewhere.
- App mounts the router with prefix `/api/learning`. The router's own
  `APIRouter(prefix="/<sub>")` uses **only the sub-segment** (`/topics`, `/reviews`), never
  `/api/learning` (double-prefix → every route 404s).
- Route handlers have **real bodies, never `pass`**. DB access = a `_db()` generator
  dependency (`conn = connect(); try: yield conn; finally: conn.close()`), injected with
  `Depends(_db)`. No `Depends()` for auth.
- Any network or long job (Drive sync, embedding) runs as a FastAPI `BackgroundTask` or in
  `night_worker.py` — **never inline in a request**. No module-level LLM/embedding client
  import in a route module; inject it.
- A **shared enum module** (`shared/constants/learning.py` or a tiny JSON) for
  `stack_area` / `status`, importable by backend and frontend — a bad value is `422`, not silent.

## 3. Data storage — Drive → RAG → DB (keep the three layers separate)

**Layer 1 — Source of truth: Google Drive (read-only pull).**
`services/drive_sync.py`: a service-account or OAuth token (in `.env`, **never committed**)
pulls one Drive folder to a local `content/` cache. List files, download only changed ones
(compare `modifiedTime` / `md5Checksum`), write raw file + a manifest row
`{file_id, name, hash, pulled_at}`. Idempotent — re-run fetches deltas only.

**Layer 2 — RAG index: derived, disposable.**
`services/rag.py`: build a local vector store from `content/` —
- chunk (~500 tokens, ~50 overlap), embed with **`sentence-transformers` `all-MiniLM-L6-v2`**
  (384-dim, CPU, no API key)
- store in **local FAISS** (`vector_store/index.faiss` + `chunks.jsonl` of
  `{chunk_id, file_id, text, offset}`)
- `search(query, k) -> top-k chunks with source attribution`
- rebuilt by the night worker whenever the Drive manifest hash changes; safe to delete and
  regenerate
- **your-own / public content only** — nothing secret ever gets embedded.

**Layer 3 — Structured state: local SQLite `learning.db`** (only queryable records, not prose):
- `topics` (id, name, stack_area, parent_id, status['todo'|'learning'|'done'], target_date, source_doc)
- `sessions` (id, topic_id, date, minutes, notes, confidence 1-5)
- `resources` (id, topic_id, kind['doc'|'video'|'repo'], url, drive_file_id, status)
- `milestones` (id, topic_id, title, done_at)
- `reviews` (spaced repetition: id, topic_id, due_date, ease, last_result)
- singleton `sync_state` (id CHECK(id=1), last_drive_pull, last_index_build, doc_count,
  chunk_count) — `UPDATE ... WHERE id=1`, never `INSERT`.
Schema in `scripts/schema.sql`, created on startup if the DB is missing.

**Flow:** Drive folder → `drive_sync` (delta pull) → `content/` + manifest → `rag` (chunk +
embed) → FAISS → `POST /api/learning/ask` does retrieve-then-answer (retrieval local;
generation via the **Model gateway** — the same one the Model screen fronts). UI progress
writes straight to `learning.db`. Night worker: pull → reindex → recompute `sync_state` →
generate due `reviews`.

**Kage gitignore (public repo — no personal data ever):** `learning.db`, `vector_store/`,
`content/`, `.env`, every pulled Drive file. Commit only code + `schema.sql` + empty-state fixtures.

## 4. API surface (name these so the coding model scaffolds them)

- `GET /api/learning/overview` — counts by status, streak, hours this week, reviews due, sync freshness
- `GET /api/learning/topics` (filters `stack_area`, `status`) · `POST` · `GET|PUT|DELETE /topics/{id}`
- `GET /api/learning/roadmap` — topics as a tree/graph for the wayfinder
- `GET /api/learning/sessions?topic_id=` · `POST /api/learning/sessions`
- `GET /api/learning/resources?topic_id=` · `POST /api/learning/resources`
- `GET /api/learning/reviews/due` · `POST /api/learning/reviews/{id}/grade`
- `POST /api/learning/ask` — `{query}` → `{answer, sources[]}` (RAG over Drive docs)
- `POST /api/learning/sync` (returns immediately, BackgroundTask) · `GET /api/learning/sync/status`
- Time-series / history endpoints return `{"state": "ok"|"partial"|"pending", ...}`, never a bare `[]`.

## 5. UI / wayfinder conventions

- **Discovery, not hardcoding.** Ship `Screens/Learning/screen_definition_for_learning.py`:
  `SCREEN_NAME="learning"`, `MENU_LABEL="LEARNING"`, `MENU_ORDER=2`,
  `TABS=[{key,label,endpoint}, ...]`. The menu row then appears with **zero** changes to
  `Main_Menu/` or `Start_Inky/`.
- **Theme — match `Screens/Model/Page/theme_for_model.css` exactly** so Learning and Model
  read as siblings. Carry the RUBRIC palette in the screen's **own** CSS (do not `@import`
  shared): `--void:#0F0F0F`, `--panel:#141212`, `--line:#333333`, `--bone:#FFFFFF`,
  `--dim:#8B9099`, `--amber:#FF7A00`. Font **IBM Plex Sans**. `.wrap` max-width ~860px,
  column, gap 20px. `.panel` = `--panel` bg + 1px `--line` border + 4px radius.
  `.panel-label` uppercase 11px/700/0.14em. `.title` with a trailing `.accent` in `--amber`.
  `.sub` 9px uppercase `--dim`.
- **Wayfinder view** = a top-level map of the learning graph: nodes = topics / stack areas,
  edges = prerequisites, node colour by status (`--dim` todo → `--amber` learning → `--bone`
  done). Hand-rolled SVG or a lazy Three.js force layout (ssr:false, reduced-motion →
  static). Node positions are **computed from the `/roadmap` payload**, never hand-placed.
  Click a node → route `/learning/topic/<id>`.
- **Tabs** (e.g. Overview · Roadmap · Topics · Review · Ask) live in the screen layout; each
  page renders content only.
- **States:** every panel has visibly distinct loading / error / empty; empty copy is honest
  ("No sessions logged yet"), never an endless spinner.
- **Self-contained:** inline the glyph set (no icon font — static export stays portable),
  own theme CSS, own per-screen nav fetch if needed. Import nothing from `Shared_By_All_*`.

## 6. Hard don'ts (Kage rules — put these at the top of the coding-model prompt)

- Public repo → **no personal data, keys, tokens, PANs, or Drive file contents committed.**
  `.env` + all pulled/derived data gitignored.
- No ORM — stdlib `sqlite3` through one `connect()`.
- No `framer-motion` / `shadcn` / `@radix` / chart libs / markdown libs.
- No new shared code — the screen is a drop-in independent component.
- Router prefix = sub-segment only. POST bodies via a Pydantic model / `Body(...)`, not
  scalar params. Long jobs = BackgroundTask / night worker, never inline.

## Verification (after the coding model delivers)

1. `python -m pip install -r Screens/Learning/Setup/requirements_for_learning.txt` — only
   `fastapi` + `uvicorn` (+ `sentence-transformers`, `faiss-cpu`, `google-api-python-client`
   for the worker) should appear.
2. `uvicorn ...:app` → `GET /api/learning/overview` returns 200 on an empty DB with no
   `NaN`/`Infinity`; schema auto-creates.
3. `npm run build` in the screen's `Page/` → static `out/` produced, no `framer-motion` /
   chart-lib in the bundle; `grep -R "Shared_By_All" Screens/Learning/` is empty.
4. Start the menu (`Start_Inky/`) → a **LEARNING** row appears in position 2 with the book
   glyph, with **no edits** to `Main_Menu/` — pure discovery via `screen_definition_for_learning.py`.
5. Drop 1-2 docs in the Drive folder → `POST /api/learning/sync` → `GET /sync/status` shows
   `doc_count`/`chunk_count` rise → `POST /api/learning/ask` returns an answer with `sources[]`.
6. `git status` shows only code + `schema.sql` staged — `learning.db`, `content/`,
   `vector_store/`, `.env` all ignored.
