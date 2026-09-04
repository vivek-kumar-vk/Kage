# Storage — the one seam

`Screens/Storage/` is the repo's single local-disk storage seam (D11.5,
AGENTS.md): every screen's own persistence funnels through here instead of
writing scattered local files. Backend on port **8009**.

## What's built (this pass)

- `services/seam.py` — `read_doc` / `write_doc` / `list_docs` / `delete_doc`
  / `search`, addressed by **logical path** (a real, validated subpath of
  `KAGE_DATA_DIR`). Routes: `GET /api/storage/docs?prefix=`,
  `GET /api/storage/doc?path=`, `PUT /api/storage/doc?path=` (body
  `{"content": "..."}`), `DELETE /api/storage/doc?path=`,
  `GET /api/storage/search?q=`.
- A logical path must be lowercase `a-z0-9._-` per `/`-separated segment,
  depth ≤ 6, extension in `{.md, .txt, .json}`, no `..`. `write_doc` is
  atomic (tmp file + `os.replace`); `delete_doc` moves the file to
  `KAGE_DATA_DIR/.trash/<date>/<ms>-<name>` — recoverable, never
  annihilation (Rule 8).
- `GET /api/storage/status` — data dir, document count, free disk space.
  Honest states throughout: an unreachable data dir is `state: "error"`
  with the real problem, never a fabricated zero.

## Config (repo-root `.env`, gitignored)

`KAGE_DATA_DIR` (default `~/kage-data`; a phone/Termux deploy repoints it
to `/sdcard/kage-data`). Nothing personal lives inside this repo — the data
directory is outside the tree by design (Rule 7).

## Not built yet

- **Hybrid RAG** (`services/rag.py`) — FTS5 keyword + dense embeddings via
  OmniRoute (D11.5.1), fused (fusion method still an owner decision),
  sourced Markdown notes, sanitizer hook before anything is embedded.
- **Trader ledger stub** (`services/trader.py`) — append-only decisions
  log via the seam; the trader agent itself stays unbuilt, in its own
  screen later.
- The status page's KNOWLEDGE / EMBEDDINGS / TRADER LEDGER panels say so
  plainly rather than showing empty tables.

See `PLAN.md` item 2 for the full build-phase list.
