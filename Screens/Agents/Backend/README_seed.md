# Agent Deck seed

`seed.py` runs automatically when the Agent Deck backend starts. On a fresh database it seeds the Board and Runs rooms, then seeds ideas either from `Backend/seed_local.json` (if that file exists and parses to a dict with an `ideas` list) or from the built-in generic starter set. The local file is git-ignored and private; commit only `seed_local.example.json`. The seed marks `meta.seeded=yes`, so deleting all idea rows later does not force the starter data back in.

## Per-agent model pinning (V2)

`office.json` accepts two optional keys, read defensively by `services/office.py`:

```jsonc
{ "department": "finance", "tier": "main",
  "model": "qwen2.5-coder:7b",              // pinned; optional
  "models": ["qwen2.5-coder:7b", "gpt-4o-mini"] }  // preference order; optional
```

Resolution order for an ask: `model` → first entry of `models` → whatever the
gateway's own `_resolve_model` picks. The chosen model is recorded on the run
(`runs.model`). A malformed or absent key is dropped silently — this file is
read at boot and the gateway may be down, so nothing here is validated against
it. These files are the user's own registry; nothing in this repo writes them.

## Runs table (V2)

Every `ask` is a row in `runs` (`schema.sql`), closed by `UPDATE` — never
deleted. `GET /api/agents/runs?agent=<name>&limit=50` lists them newest first;
`GET /api/agents/runs/{id}` returns one in full. A run left `status='running'`
because the server died is swept to `status='error'` on the next boot
(`runs.mark_interrupted_runs()`, 10-minute cutoff) rather than shown as a false
"ok".
