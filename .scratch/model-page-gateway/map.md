# Wayfinder map — Model page + model gateway

Tracker: local-markdown (`.scratch/model-page-gateway/`). Child tickets in `issues/`.
Full charted rationale: `~/.claude/plans/abundant-foraging-waffle.md`.

> **Gateway design changed (2026-08-30).** The original plan (T3–T6) ran a
> project-managed **LiteLLM + Postgres** stack in `Tools/`. That was built, then
> **removed** (`6ad5e79` "drop Tools/litellm") and replaced by **OmniRoute**. Those
> four tickets are archived at `.scratch/_archive/model-page-litellm-litellm-tickets/`.
> **T1 + T2 (nav layer + Model screen + Kage.GG rebrand) shipped and stand.**

## Destination (current)

The RUBRIC / Kage.GG Main Menu has a **real navigation layer**: nodes map to screens,
clicking **Model** routes to a themed in-app page (same tab), back + mobile handled.
A **`Screens/Model/`** screen (own `Backend/` FastAPI server + `settings_for_model.py`,
port **8005**) serves that page as a **complete independent component** — zero
`Shared_By_All_*` imports.

Behind it runs **OmniRoute** (npm package `omniroute`, an OpenAI-compatible AI gateway):

| | |
|---|---|
| Launch | `Start_Inky/run_omniroute.py`, chained from `Start_Everything.bat` |
| Bind | `127.0.0.1:8003`, `REQUIRE_API_KEY=true` |
| State | `~/.omniroute/` (`storage.sqlite` + server dirs) — **not in the repo** |
| Secrets | `OMNIROUTE_JWT_SECRET` / `_API_KEY_SECRET` / `_INITIAL_PASSWORD` generated into repo-root `.env` (gitignored) on first run |
| Provider | one free connection `opencode` (no auth), 63 models incl. `glm-5.x`, Claude, Gemini, GPT, Grok, DeepSeek, Qwen, Kimi |
| Health | `GET /api/monitoring/health` |
| No | project-managed Postgres, no `Tools/` dir, no pgvector-from-the-start |

The Model page reads one OmniRoute REST endpoint (`/v1/models`) through
`server_for_model.py`'s thin proxy holding `GATEWAY_API_KEY`. OmniRoute is also the
OpenAI-compatible endpoint Kage's future agents will call — see `PLANNED_WORK.md` P11.

Config detail (providers, model list, aliases, API key, features):
**`Screens/Model/GATEWAY_CONFIG.md`**.

## Notes

- Scope is **laptop + phone**; nothing phone-host-specific is built until asked (D-W7).
- Verify UI work in a real browser via Chrome MCP (user habit), not just build.

## Decisions so far

- [T1 — Main Menu real navigation layer](issues/01-main-menu-real-nav.md):
  navigation discovered from `/api/main_menu/navigation`. Shipped as a floating
  `NavRail`, **superseded in T2** by a `NavPanel` in the reference's top-left
  "MICRO APPS" panel. **Model** routes same-tab.
- [T2 — Model screen scaffold](issues/02-model-screen-scaffold.md):
  `Screens/Model/` built as a **fully independent component**, discovered at
  MENU_ORDER 3, port **8005**. `GET /api/model/overview` = honest thin proxy to
  the gateway (`ok|unreachable|error`). T1 in-app `/model/` placeholder +
  `NavRail.tsx` + `MicroAppsPanel.tsx` deleted; `EXTERNAL_LINKS` emptied (D-W2).
  Main Menu rebranded **RUBRIC Agentic OS → Kage.GG**, byline **→ Vivek Kumar |
  KageEnsui** (`CenterCore.tsx`, `layout.tsx`). Verified live.
- **Gateway (P10, `AGENTS.md` D6/D6.1/D6.2, 2026-08-30):** OmniRoute on `127.0.0.1:8003`
  replaces the LiteLLM/Postgres design. Health path `/api/monitoring/health` (the old
  `/health/liveliness` 404'd → false "unreachable"). Model screen shows GATEWAY UP +
  model list against it. Detail in `GATEWAY_CONFIG.md`.
- **T7 / D10 — Model screen iframes OmniRoute's dashboard (2026-08-30).**
  Instead of building custom proxy endpoints + hand-rolled data panels, the
  Model page embeds OmniRoute's built-in dashboard (`127.0.0.1:8003`) in an
  iframe within the RUBRIC-themed shell. The backend's `/api/model/overview`
  health probe gates whether the iframe shows or a fallback panel appears.
  "Open in new tab" link provided for full-screen dashboard access.
- ~~T3 Postgres lifecycle · T4 LiteLLM orchestration · T5 config.yaml · T6 secrets~~
  → **archived** (`.scratch/_archive/model-page-litellm-litellm-tickets/`).

## Not yet specified

- Auth on the LAN/tunnel path once the phone reaches OmniRoute over the network.
- Whether Kage's future agents get their own OmniRoute API keys + per-agent usage
  attribution (P11).
- Full node→screen map for the non-Model ring nodes.

## Out of scope

- The Android app wrapper and hosting Kage on the phone — no build until asked (D-W7).
- Retiring/porting the Python screen backends (P4).
