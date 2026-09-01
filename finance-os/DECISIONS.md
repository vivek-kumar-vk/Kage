# finance-os — decisions

Numbered per `AGENTS.md` Rule 8 (`FD1`, `FD1.1`, …). Highest sub-number is in force;
parents stay as history. Repo-wide decision is `AGENTS.md` D7 (finance-os is the Finance
screen of record).

> This file was regenerated 2026-08-30 — the phase-0 gate only checked its presence and
> the local model had written a stray React component into it. Content below is from
> `finance-os-master-plan-final.md` v3 §13 and phase-0 spec.

## FD1 — Data at rest: OS-level disk encryption, **not** SQLCipher (V1)

`finance.db` is the sole database (SQLite, stdlib `sqlite3`). Protection for V1:

- **OS-level disk encryption** — BitLocker (Windows) / FileVault (macOS). `startup.py`
  runs a **non-fatal** `check_encrypted_volume()` at boot and logs a warning if the DB
  dir does not look encrypted.
- `chmod 600 finance.db`.
- `.gitignore` covers `finance.db`, `data/backups/`, `data/vector_store/`, `.env`.

**SQLCipher was considered and rejected for V1.** It would force swapping `sqlite3` for
`pysqlcipher3` across the whole backend from Phase 0, plus key-management code — real
implementation risk for a 7B local author, for a single-user local app whose threat
model ("laptop lost or stolen") is already covered by full-disk encryption. **Revisit
only if** the app starts syncing to a second device or a remote server — disk encryption
stops protecting data the moment it leaves the machine.

## FD2 — Stack

Backend: **FastAPI** + stdlib `sqlite3` (no ORM). Frontend: **React 19 / Next.js**
(`output: "export"`, static) + Tailwind. One SQLite database. `PRAGMA foreign_keys = ON`
on every connection; the only `sqlite3.connect(` in `backend/` is in `services/db.py`.

## FD3 — No provider API keys in the tree

`.env` (gitignored) holds API keys and paths. No keys committed, no keys hard-coded.
LLM access for the finance agents routes through the OmniRoute gateway
(`127.0.0.1:8003`) — see `PLANNED_WORK.md` P11 — so model/provider choice is a gateway
routing decision, not finance-os code.

## FD4 — Deletion model: soft-delete by default

`archived_at` timestamp is the default deletion path. Hard delete / `ON DELETE CASCADE`
is reserved for a separate, restricted path — not the blanket default.
