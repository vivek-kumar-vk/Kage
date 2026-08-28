# Wayfinder map — Model page on a local LiteLLM gateway

Tracker: local-markdown (`.scratch/model-page-litellm/`). Child tickets in
`issues/`. Resolve **one ticket per session**. Full charted rationale:
`~/.claude/plans/abundant-foraging-waffle.md`.

## Destination

The RUBRIC Main Menu has a **real navigation layer**: nodes map to screens,
clicking **Model** routes to a themed in-app page (same tab), back + mobile
handled. A new **`Screens/Model/`** screen (React 19 / Tailwind / Next.js, own
`Backend/` FastAPI server + `settings_for_model.py`, own port) serves that page as
a **complete independent component** — zero `Shared_By_All_*` imports, and any
such file it would touch is inlined into its one caller and deleted (AGENTS
rule 5, P2). Behind it runs a **project-managed local LiteLLM proxy** (port 8003,
started by Start_Inky, Postgres-backed, portable to a Termux phone host) doing
auto-routing + fallback. The Model page's blocks each read one LiteLLM REST
endpoint through a thin backend proxy holding the master key. LiteLLM is also the
OpenAI-compatible endpoint Kage's future agents call.

## Notes

- Scope is **laptop + phone**; nothing Android/phone-host-specific is built until
  the user says so (D-W7).
- Consult installed skills before falling back to defaults (AGENTS rule 1):
  `simplify`, `codebase-design`, `dataviz` (for T7), `prototype` (T1/T7).
- Verify UI work in a real browser via Chrome MCP (user habit), not just build.
- After T1, bring up both the Kage UI and LiteLLM's own browser UI to eyeball the
  whole setup (user request).

## Decisions so far

<!-- one line per closed ticket; detail lives in the ticket -->

- [T1 — Main Menu real navigation layer](issues/01-main-menu-real-nav.md):
  navigation is discovered from the existing `/api/main_menu/navigation`, not
  from clickable ring nodes. First shipped as a floating `NavRail`; **superseded
  in T2** by a `NavPanel` housed in the reference's top-left "MICRO APPS" panel
  (user request), same panel design. **Model** routes same-tab.
- [T2 — Model screen scaffold](issues/02-model-screen-scaffold.md):
  `Screens/Model/` built as a **fully independent component** (zero
  `Shared_By_All_*` imports; own theme CSS; own 4-line fetch), discovered at
  MENU_ORDER 3, port **8005**. `GET /api/model/overview` = honest thin proxy to
  the gateway (`ok|unreachable|error`). NavPanel now lists Model via discovery;
  the T1 in-app `/model/` placeholder + `NavRail.tsx` + `MicroAppsPanel.tsx`
  deleted; `EXTERNAL_LINKS` emptied (D-W2). Verified live: click-through Home →
  MODEL renders the themed screen with an honest "gateway unreachable" state.
  **Follow-up applied:** NavPanel now leads with **Model** and has no Home row;
  Main Menu rebranded **RUBRIC Agentic OS → Kage.GG**, byline **Jay E |
  RoboNuggets → Vivek Kumar | KageEnsui** (`CenterCore.tsx`, `layout.tsx`).
- [T3 — Postgres lifecycle](issues/03-postgres-lifecycle.md): **Kage installs
  and manages Postgres** (project-managed). It becomes Kage's default DB
  (LiteLLM now, finance/study RAG next → **pgvector from the start**). Start_Inky
  owns its lifecycle; repo-local gitignored data dir; `DATABASE_URL` in `.env`
  only overrides. Per-OS install + Termux research fold into T4.
- [T4 — LiteLLM orchestration](issues/04-litellm-orchestration.md): **gateway
  live, verified end-to-end.** `Tools/` holds `settings_for_tools.py`,
  `manage_postgres.py`, `run_litellm.py` (+ `.bat`), `litellm_config.yaml`,
  `requirements_for_tools.txt`. Repo-local Postgres cluster on **5433**; LiteLLM
  on **8003** (`/health`, `/v1/models`, `/ui` all respond; Admin UI login = `admin`
  + master key). `Screens/Model` → **GATEWAY UP** + model list. `Start_Everything
  .bat` installs Tools deps + auto-picks Python **3.11–3.13** (`import prisma`
  hangs on 3.14); `serve_everything_on_one_port.py` routes `/llm/` → 8003;
  `run_litellm.py` stops Postgres on Ctrl+C.
- [T5 — config.yaml](issues/05-litellm-config.md) (partial): **keys deferred** —
  user will create provider API keys now that the LiteLLM UI is up. `config.yaml`
  ships `os.environ/<VAR>` placeholders (claude-sonnet / gpt-4o / local-llama +
  a fallback chain); LiteLLM runs fine with none set. Provider list / routing /
  final master key revisited once keys exist.
- [T6 — secrets & config surface](issues/06-secrets-config-surface.md): done with
  T4. `.env` (gitignored, generated master key + UI creds + blank provider keys),
  `.env.example` committed, `!.env.example` + `pgdata/` + `Tools/*.log` in
  `.gitignore`. Minimal per-consumer `.env` readers; real env vars always win
  (phone host exports its own).

## Not yet specified

- Auth on the LAN/tunnel path once the phone reaches LiteLLM over the network.
- Whether Kage's future agents get their own LiteLLM virtual keys + per-agent
  usage attribution.
- pgvector / RAG schema for finance + study (own later effort).
- Full node→screen map for the non-Model ring nodes (T1 sets the mechanism;
  filling every node may spill to a follow-up).

## Out of scope

- The Android app wrapper and hosting Kage on the phone — no build until asked
  (D-W7). This effort only keeps the setup from precluding them.
- Retiring/porting the Python screen backends (P4). LiteLLM's third-party-service
  exemption (D-W3) does not change P4.
- Building the finance/study RAG — only the database choice is settled here.
