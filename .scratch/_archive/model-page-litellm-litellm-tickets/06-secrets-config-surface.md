# T6 — Secrets & config surface

Type: grilling
Status: resolved
Blocked by: 04, 05
Blocks: 07, 08

## Question

Exact `.env` keys (`LITELLM_MASTER_KEY`, provider keys, `DATABASE_URL`), the
committed `.env.example` + sample `config.yaml`, `.gitignore` deltas (already
covers `.env`, `.env.*`, `Secrets_Keys/`), and how the phone host gets its
secrets.

## Answer (done as part of T4)

**`.env` keys** (repo root, gitignored): `LITELLM_MASTER_KEY` (generated
`sk-...`), `DATABASE_URL` (`postgresql://postgres@127.0.0.1:5433/litellm` —
trust auth, localhost), `STORE_MODEL_IN_DB=true`, `UI_USERNAME` / `UI_PASSWORD`
(generated), blank `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` for T5.

**Committed:** `.env.example` (same keys, `REPLACE_ME` values + master-key
generate command) and `Tools/litellm_config.yaml` (no secrets — every `api_key`
is `os.environ/<VAR>`).

**`.gitignore` deltas:** `!.env.example` (the `.env.*` rule was hiding it),
`Start_Inky/pgdata/`, `Tools/*.log`.

**Readers:** `Tools/run_litellm.py` has a minimal KEY=VALUE `.env` loader
(existing env wins → a host overrides per value). `Screens/Model` has its own
tiny reader for just `LITELLM_MASTER_KEY`, staying independent of `Tools/`.

**Phone host:** does not copy `.env` — it exports `LITELLM_MASTER_KEY`,
`DATABASE_URL` (its own Postgres) and provider keys in the Termux shell profile.
Every consumer already prefers a real env var over the `.env` line.
