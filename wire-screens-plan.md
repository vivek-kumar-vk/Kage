# Wire Finance (finance-os) + Learning into the Main Menu — plan

Date 2026-08-30. Branch `vivek/main-menu-rubric-agentic-os`.

## Goal
1. Click **Finance** in Main Menu → land on the **finance-os** app (the current
   finance work), keep working there.
2. **Learning** → bring the rough OneDrive build in, but the real conformant
   build is done by **Qwen 3-Max** from a spec this plan produces.
3. Everything runs via `Start_Inky/Start_Everything.bat` (no-proxy mode: each
   screen on its own port, Main Menu :8000, links are `http://127.0.0.1:<port>/`).
4. Later, separate task: OmniRoute / Model gateway config.

## Architecture facts (why the approach below)
- `start_every_screen.py` launches every `Screens/<X>/Backend/server_for_*.py`
  that also has `settings_for_*.py` with a `PORT`. Each server serves BOTH its
  page at `/` and `/api/<x>/*` on that port.
- No-proxy mode: assets are fetched same-origin (`http://127.0.0.1:8001/_next/...`)
  so a screen server just has to serve `/_next/*` itself. finance-os's
  `app_factory._spa` already does (exact static file match). **No basePath needed.**
- Proxy mode (`serve_everything_on_one_port.py`) has a pre-existing `/_next/*`
  collision for every Next screen; out of scope here (user runs the .bat).

## Finance — steps (hands-on)
1. `finance-os/frontend/lib/api.ts` and `app/finance/investments/page.tsx`:
   default API base `"http://127.0.0.1:8000"` → `""` (same-origin).
2. `python finance-os/build.py` → refreshes `finance-os/backend/static/`.
3. Replace `Screens/Finance/Backend/server_for_finance.py` with a thin wrapper:
   - add `finance-os/backend` to `sys.path`
   - `app = FastAPI()`; `@app.get("/")` → `FileResponse(static/"finance.html")`
     (skips the flaky root `redirect('/finance')` export)
   - `app.mount("/", create_app())` — fos app handles `/finance*`, `/api/finance/*`,
     `/_next/*`, deep links
   - `uvicorn.run(app, host=cfg.HOST, port=cfg.PORT)` (8001)
4. `Screens/Finance/Backend/settings_for_finance.py`: keep `PORT=8001`,
   `HOST`; set `USE_NEXT_UI=False` (no longer used).
5. `Screens/Finance/screen_definition_for_finance.py`: TABS → finance-os tabs
   (overview / investments / debt / tracker / learning). Label FINANCE, order 1.
6. Old `Screens/Finance/{Calculations,Page,Reference_Data,Saved_Records,Setup}`
   stay on disk unused (git history). Not deleted in this pass.

## Learning — steps
- Running screen left as-is for now (old build, already in menu, serves its
  fallback page). 
- Deliver `Screens/Learning/QWEN_BUILD_PROMPT.md`: full house-style spec built
  from `learning-tab-plan.md` + Kage rules (AGENTS.md 3/4/5), the exact stack,
  the API surface, the theme, hard don'ts, and a pointer to the rough build at
  `C:\Users\vkjha\OneDrive\Desktop\New folder\Screens\Learning` as reference.
  Qwen's output replaces `Screens/Learning/` wholesale.

## Run & verify
- `python Start_Inky/start_every_screen.py`.
- Claude-in-Chrome: open `http://127.0.0.1:8000`, click Finance → Overview +
  one sub-tab render; click Learning → loads.

## Later (separate)
- OmniRoute: `Screens/Model/Backend/settings_for_model.py` `GATEWAY_BASE_URL` +
  `GATEWAY_API_KEY`; `server_for_model.py` `/api/model/overview` already proxies
  a gateway health + `/v1/models`. Wire once OmniRoute is up.

## Unresolved questions
- Finance old tree: delete now or keep as dead weight? (plan keeps it)
- Learning: after Qwen delivers, port stays 8002 / tabs today·plan·recall — keep
  or let Qwen's `screen_definition` redefine tabs?
- OmniRoute: is it running yet, and at what base URL / key?
