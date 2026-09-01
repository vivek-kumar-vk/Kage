# T1 — Main Menu real navigation layer

Type: prototype
Status: resolved
Blocked by: (none)
Blocks: 02, 08

## Question

`Main_Menu/Page/next_app/app/page.tsx` is a static export with no router — 30
decorative `aria-hidden` ring nodes, four dead header icons. Kage already exposes
`GET /api/main_menu/navigation` (built screens + `address`, `not_built`,
`EXTERNAL_LINKS` pills); the old plain-HTML / Svelte menus consumed it, the RUBRIC
rebuild dropped it.

Decide and build the real navigation layer:

- node/entry → screen model; how an entry is labelled/identified
- route mechanism: themed **in-app route, same tab** (resolved: not a new browser
  tab)
- back + mobile behaviour
- reconciliation with the existing `/api/main_menu/navigation` endpoint +
  `EXTERNAL_LINKS`
- must be a complete independent component (D-W6): its own fetch, its own data
  shape, no shared frontend module

Ends with: clicking **Model** lands on a themed placeholder page.

## Answer

**Mechanism: a persistent `NavRail`, not clickable ring nodes.** The 30 ring
nodes stay decorative/`aria-hidden` (moving hit targets = bad UX, and the RUBRIC
exact-copy is owner-approved as-is). Navigation is a separate thin themed bar:
left-vertical on desktop (`min-width: 1101px`, `.home-grid` gets `padding-left`),
a bottom dock on a phone (`env(safe-area-inset-bottom)`, `body` bottom padding so
the last panel clears it).

**Data source: the existing `GET /api/main_menu/navigation`** — the same endpoint
the old plain-HTML/Svelte menus used (`server_for_main_menu.py`). NavRail fetches
it client-side, keeps only screens with a non-null `address`, and renders them
between a fixed **Home** (`/`) and **Model** (`/model/`) entry. It owns the Model
entry itself and drops any `EXTERNAL_LINKS` `models`/`model` pill the API returns,
so Model never doubles. Built screens on their own port → plain same-tab `<a>`;
in-app routes → `next/link`. Offline endpoint → still shows Home + Model + a
muted "screen list offline" note (honest empty state, C12).

**Route: in-app, same tab.** `next.config.ts` gains `trailingSlash: true` so the
static export emits `out/<route>/index.html` — the screen's FastAPI server mounts
`out/` with `StaticFiles(html=True)`, which resolves `/model/` exactly like `/`.
Without it a multi-route export 404s on every route but `/`.

**Model landing (T1 scope): themed placeholder** at `app/model/page.tsx`, served
from the Main Menu's own export. RUBRIC surface language (`.rubric-panel`,
`.rubric-label`, amber accent, mono), a "wiring in progress" note pointing at
T2–T8, a preview list of the future blocks, a "← Back to menu" pill, and NavRail.
**T2 replaces this** with `Screens/Model/` and repoints NavRail's Model `href` at
that screen's discovered address — NavRail itself does not change.

### Files
- `Main_Menu/Page/next_app/app/components/NavRail.tsx` — new, self-contained
  (own fetch, own inline glyph set, zero `Shared_By_All_*`).
- `Main_Menu/Page/next_app/app/model/page.tsx` — new placeholder route.
- `Main_Menu/Page/next_app/app/globals.css` — `.nav-rail*` rules + grid/`body`
  padding for the fixed rail.
- `Main_Menu/Page/next_app/app/page.tsx` — mounts `<NavRail />` (fragment wrap).
- `Main_Menu/Page/next_app/next.config.ts` — `trailingSlash: true`.

### Verification
`npm run build` clean (TS + eslint pass; routes `/`, `/model` prerendered).
Static-served (`out/` + a stub `/api/main_menu/navigation`): `/`, `/model/`,
`/api/main_menu/navigation` all 200; NavRail markup + Model entry present in the
exported `index.html`; Model page renders themed. **Not yet done in a live
browser** — the Chrome extension was disconnected this session; discovered-screen
hydration + the click-through need an eyeball pass (rolls into T8, or a quick
`npm run dev` check).

### Follow-ups surfaced
- Non-Model ring nodes / the other screens' glyphs: NavRail already lists every
  discovered screen; a richer node→screen story stays fog.
- The four dead RUBRIC header icons (edit/search/apps/info) are still inert — out
  of T1 scope, noted.
