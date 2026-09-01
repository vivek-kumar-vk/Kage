# T3 — Postgres lifecycle & provisioning

Type: grilling
Status: resolved
Blocked by: (none)
Blocks: 04, 07

## Question

Project-managed (Start_Inky installs/starts Postgres, owns the data dir) vs
bring-your-own (`DATABASE_URL` in `.env`). Data-dir location vs the P7 "nothing
personal on local disk" rule. pgvector now or later. Windows vs Termux install
path. Needs a `research` pass on Termux Postgres facts.

## Answer

**Kage installs and manages Postgres** (project-managed, not bring-your-own).
User: "Kage need to install and manage it" — Postgres is Kage's default database
going forward (LiteLLM spend logs now; finance + study RAG next, so **pgvector
from the start**).

Settled:
- Start_Inky owns Postgres lifecycle: first run installs it (per OS), then starts
  it before LiteLLM before the screens; Ctrl+C stops it with everything else.
- A repo-local data dir (e.g. `Start_Inky/pgdata/`), gitignored. It holds
  operational rows, not documents — consistent with P7 (personal *documents* go
  to Drive; the working DB is local infra, like `.venv`).
- Connection by a fixed local DSN Kage owns; `DATABASE_URL` in `.env` only
  overrides it (e.g. the phone host).

Deferred into **T4** (the launcher): exact per-OS install (Windows: EnterpriseDB
/ `winget`; Termux: `pkg install postgresql` + `initdb`), and the
`research` pass on Termux Postgres specifics. pgvector extension enable lands
with the first schema (T7 / the RAG effort).
