# Immediate Plan

A running log of near-term plans for this codebase. Newest entry at the bottom.

---

## 2026-08-28 — Add Google Drive as private storage

Start a fresh, separate public GitHub repo for the Inky code (**Kage**,
`github.com/vivek-kumar-vk/Kage`). Keep all personal data out of the repo
entirely and store it in Google Drive as the private storage layer instead.

### Phase 1–4 — done in this pass

- **Repo hygiene**: `git init`, `.gitignore` covering every private/runtime
  path (`Secrets_Keys/`, `My_Investement_details/`, `Dump/`, all
  `Saved_Records/`, `Knowledge_Base/`, `Trace_Ledger/`, agent `Memory/`,
  `*.db`, the Google credential, `.env`).
- **Sanitization**: removed the Anime screen (piracy scraper/proxy code);
  stripped real portfolio values, employer name, and personal study content
  from source, leaving generic example seeds; scrubbed author machine paths.
- **Public-facing**: README rewritten as the project's front page; MIT
  license added.

### Phase 5 — the Drive-backed "smart storage" (next, not built yet)

Goal: **nothing personal on local disk**. Reads and writes both go through
to Google Drive, into the right folder.

- **One storage seam** — a single module every screen's persistence funnels
  through (`read_doc` / `write_doc` / `list_docs` / `delete_doc` / `search`),
  logical-path addressed. Replaces the scattered inline `json`/`csv` helpers
  in each screen's `Calculations/` modules.
- **Transport** — the app is an MCP client to an adopted open-source
  (Node.js) Google Drive MCP server. The server runs as its own process the
  app connects to (Inky never spawns an MCP server — house rule). Config in
  a repo-tracked `mcp_servers.json`; the Google service-account credential
  stays in a gitignored file. Portable: laptop now, a phone host later.
- **RAG / smart retrieval** — extend the existing
  `Shared_By_All_Screens/add_and_search_the_knowledge_base.py` pattern
  (local embeddings + cosine + sourced Markdown notes) so retrieval returns
  exactly the source docs a query needs. Add chunk overlap and a real index
  when the corpus outgrows a few thousand rows.
- **AI-trader hook (seam only)** — a future trader reads portfolio state via
  `build_the_portfolio_review.read_review()` and market data via the
  `Screens/Finance/Calculations/Shared_Market_Data/fetch_*` modules, pulls
  context through the retrieval layer, and writes decisions to a new
  append-only ledger. It must live in its own screen/agent — the Finance
  screen's rule against recommending buy/sell stays.

### Follow-ups noted during Phase 1–4

- The optional Next.js/Svelte richer UIs had their Anime cards removed;
  give them a full pass when they're next built.
- `seed_the_week_plans.py` and the Learning topic seeds are now generic
  example content — replace with your own plan.
