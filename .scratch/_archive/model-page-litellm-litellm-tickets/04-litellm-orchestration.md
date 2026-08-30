# T4 — LiteLLM in the Start_Inky orchestration

Type: grilling
Status: resolved
Blocked by: 03
Blocks: 06, 08

## Question

Create `Tools/run_litellm.*` (cross-platform, not `.bat`-only) — referenced by
`Start_Inky/Start_Everything.bat:71` but never created. How `start_every_screen.py`
(only starts `Screens/*/Backend/`) also brings up Postgres + LiteLLM in order.
Whether LiteLLM is routed through `serve_everything_on_one_port.py` under a prefix
(e.g. `/llm/`) so one tunnel/port reaches it from the phone. LiteLLM port 8003
(already assumed by `Screens/Finance/Backend/server_for_finance.py:918`).

## Answer (in progress — built this session)

**Files created (`Tools/`):**
- `settings_for_tools.py` — one place for PG bin/data/port (5433, not 5432 so a
  system PG can coexist), `LITELLM_HOST/PORT` (127.0.0.1:8003), config path,
  default `DATABASE_URL`. Every value env-overridable (phone host).
- `manage_postgres.py` — `init / start / stop / status / ensure`. Drives the
  already-installed EDB binaries (`C:\Program Files\PostgreSQL\17\bin`); inits a
  **repo-local cluster** at `Start_Inky/pgdata/` (gitignored), trust auth on
  localhost. `start` fires `pg_ctl` then polls the port (Windows `pg_ctl -w`
  hangs).
- `run_litellm.py` — loads `.env`, ensures Postgres up + `litellm` db exists,
  generates the Prisma client if missing, forces UTF-8 (banner glyphs crash
  cp1252), puts `.venv/Scripts` on PATH (litellm shells out to `prisma`), execs
  `litellm --config Tools/litellm_config.yaml --host 127.0.0.1 --port 8003`.
- `run_litellm.bat` — thin Windows wrapper (Start_Everything.bat already calls it).
- `litellm_config.yaml` — 3 placeholder models (`os.environ/` keys), fallback
  chain, `store_model_in_db`, `master_key`/`database_url` from env.
- `requirements_for_tools.txt` — `litellm[proxy]` + `prisma`.

**Wiring:**
- `Start_Inky/Start_Everything.bat` — installs `Tools/requirements_*.txt`; gate
  now also checks litellm; **prefers Python 3.11–3.13** (see gotcha below).
- `Start_Inky/serve_everything_on_one_port.py` — adds `llm` → 127.0.0.1:8003 to
  the routing table, so `/llm/v1/...` and `/llm/ui` reach the gateway through the
  one tunnelled port (phone).
- `.gitignore` — `Start_Inky/pgdata/`, `Tools/*.log`, `!.env.example`.
- `.env` (gitignored) written with a generated `LITELLM_MASTER_KEY` + UI creds;
  `.env.example` committed.

**Gotchas hit & fixed:**
1. LiteLLM banner → `UnicodeEncodeError` on cp1252 → force `PYTHONUTF8=1`.
2. `litellm[proxy]` no longer pins `prisma` → added explicitly; `prisma generate`
   needs `.venv/Scripts` on PATH (spawns `prisma-client-py`).
3. **`import prisma` hangs forever on Python 3.14.** Fine on 3.11. → `.venv`
   rebuilt on the uv-managed CPython 3.11.16; `Start_Everything.bat` now
   auto-selects `py -3.13/-3.12/-3.11`.

**VERIFIED END-TO-END (live, this session):**
- `.venv` rebuilt on CPython **3.11.16** (uv-managed). `litellm[proxy]` (>=1.98)
  and `prisma` 0.15 import fine.
- Postgres cluster up on 127.0.0.1:5433; `litellm` db has 73 tables (Prisma
  `db push`).
- Gateway up on 127.0.0.1:8003: `/health/liveliness` -> `"I'm alive!"`,
  `/v1/models` -> claude-sonnet / gpt-4o / local-llama (needs the master key),
  `/ui/` -> 200, Admin UI **login page renders** (username `admin`, password =
  `LITELLM_MASTER_KEY`; `kage`/`UI_PASSWORD` also set in `.env`).
- `Screens/Model` server on 8005: `/api/model/overview` -> `gateway: ok` with the
  3 model ids; the page shows a green **GATEWAY UP** badge + the list. The
  Model backend now reads `LITELLM_MASTER_KEY` from `.env` itself (still no
  `Shared_By_All_*` / `Tools/` import - D-W6 intact) and sends it as a bearer
  token; `/health/liveliness` (no auth) is the reachability probe, `/v1/models`
  (auth) is the list.
- `run_litellm.py` now stops the Postgres cluster on exit (Ctrl+C), unless
  `KAGE_KEEP_POSTGRES=1` - satisfies T3's "stops with everything else".
- **No Redis.** LiteLLM warns that per-worker rate-limit / budget / router state
  isn't shared without it. Kage runs one gateway worker (laptop and phone), so
  that state is already correct - `LITELLM_DISABLE_NO_REDIS_WARNING=true` set in
  `run_litellm.py` + `.env`/`.env.example` rather than run a cache nobody needs
  (AGENTS rule 2.1).

**Left as a small follow-up (not blocking):** `Start_Everything.bat` starts
`run_litellm.bat` in its own window and `start_every_screen.py` starts the
screens; the two Ctrl+C paths are separate. Fine for now (each cleans up its
own), tidy later if it bites.
