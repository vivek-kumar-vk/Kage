# T2 — Model screen scaffold

Type: grilling
Status: resolved
Blocked by: 01
Blocks: 07

## Question

Create `Screens/Model/` following the Finance/Learning/Enhancement pattern:
`Backend/server_for_model.py` + `settings_for_model.py` (own port, e.g. 8005),
`Page/next_app/`, `USE_NEXT_UI` flag, discovery-startable by
`Start_Inky/start_every_screen.py`. Zero `Shared_By_All_*` imports; inventory any
shared file it would use, inline it into its one caller, delete it (D-W6, P2).
Repoint the Main Menu nav's Model entry from the T1 placeholder to this screen.

## Answer

`Screens/Model/` created, discovered by `find_every_screen.py` at **MENU_ORDER 3**
(Finance 1, Learning 2, Model 3, Enhancement 4), one tab `overview`.

**Independent component (D-W6):** `server_for_model.py` and `settings_for_model.py`
import **nothing** from `Shared_By_All_Screens/` or `Shared_By_All_Agents/` — no
trace ledger, no health_check, no `read_screen_settings`. The page carries its
**own** theme (`Page/theme_for_model.css`) with the RUBRIC palette rather than
`@import`-ing `/shared/colours_and_fonts.css` (rule 5's sanctioned duplication).
Its fetch helper is 4 lines of `urllib`, not a shared HTTP module.

**Files**
- `Screens/Model/screen_definition_for_model.py` — SCREEN_NAME/MENU_LABEL/
  MENU_ORDER/TABS.
- `Screens/Model/Backend/settings_for_model.py` — PORT **8005** (8003 = LiteLLM,
  8004 = Enhancement), `LITELLM_BASE_URL` (env-overridable), `USE_NEXT_UI=False`
  + `NEXT_DIST` ready for T7.
- `Screens/Model/Backend/server_for_model.py` — standalone FastAPI: `/` serves
  the page (Next-export flag parity), `GET /api/model/overview` is a thin honest
  proxy to the gateway's `/v1/models` returning `gateway: ok|unreachable|error`,
  `/page` static mount.
- `Screens/Model/Page/page_for_model.html` + `theme_for_model.css` — themed
  placeholder: gateway-status panel (live fetch, honest states), "wiring in
  progress" panel, back link.
- `Screens/Model/Setup/requirements_for_model.txt` — fastapi + uvicorn only.
- `Main_Menu/Backend/settings_for_main_menu.py` — `EXTERNAL_LINKS` emptied (the
  old `Models → :8003/ui` LiteLLM-dashboard pill is replaced by this real
  screen, per D-W2).

**Nav repoint (T1 follow-through):** the T1 in-app `/model/` placeholder route
was **removed** from the Main Menu next_app (`app/model/` deleted, `trailingSlash`
reverted). The T1 `NavRail` floating bar was replaced this session by a
`NavPanel` living inside the reference's top-left "MICRO APPS" panel (user
request — same panel design: `.rubric-panel`, icon+label header, `↻ Refresh`
pill, glyph-badge rows). `MicroAppsPanel.tsx` and `NavRail.tsx` deleted. NavPanel
lists a fixed **Home** + every discovered screen (Model now among them via
`/api/main_menu/navigation`) and only falls back to a hardcoded Model row when
the endpoint is offline.

**Verification (live browser, preview server):** Home renders NavPanel in the
MICRO APPS slot; clicking **MODEL** navigates to `/model` and the independent
Model screen page renders themed with an honest amber "gateway unreachable"
badge (LiteLLM not set up — expected until T3–T6). `npm run build` + eslint
clean; `find_every_screen.py` lists `model`; no page console errors.

**Follow-ups:** `Screens/Model/Page/next_app/` (React rebuild) deferred to T7 with
the data/representation design. Model page's "back to menu" uses `/` (correct
behind `serve_everything_on_one_port.py`; direct-port dev it stays on 8005).
