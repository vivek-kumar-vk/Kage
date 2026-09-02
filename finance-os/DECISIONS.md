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
(`127.0.0.1:8003`) — see `PLAN.md` item 3 — so model/provider choice is a gateway
routing decision, not finance-os code.

## FD4 — Deletion model: soft-delete by default

`archived_at` timestamp is the default deletion path. Hard delete / `ON DELETE CASCADE`
is reserved for a separate, restricted path — not the blanket default.

## FD5 — The Overview wears the "Aurum" skin

The Overview tab is the Aurum private-wealth terminal: near-black ground, gold `#E4C07C`
accent, Fraunces serif hero numbers, JetBrains Mono for figures, a 12-column panel grid,
and hand-rolled SVG charts — no chart library. Ported from
`.scratch/finance-redesign/mockups/overview.html`. Repo-wide decision: `AGENTS.md` D13.

Additive, not a replacement: `.card` and the racing palette still serve Investments,
Debt, Tracker and Scenario. Coral `#FF7A6B` marks a monetary loss only — nothing
decorative is red.

The net-worth ridge is react-three-fiber (`components/finance/three/NetWorthRidge.tsx`),
dynamically imported with `ssr:false`, and falls back to a static gold SVG built from the
same real series on no-WebGL, on `prefers-reduced-motion`, or when a mounted WebGL
context has not painted in 1.5 s. The panel labels whichever renderer drew.

## FD6 — Never write a price for a day the feed did not publish

`price_history` holds published quotes only. Two paths were manufacturing rows —
`market_data.batch_refresh` stamped a stale NAV (and any cached price) with
`date.today()`, and `night_worker.weekly_gap_only_refresh` carried the last price forward
one row per calendar day. Both left the two newest rows per symbol holding the same
number, so `portfolio_pulse`'s day change read a false `0.00`.

Rules: a quote is stored under the feed's own date; a cached read is not a quote and
writes nothing; the gap refresh inserts the feed's real points past `MAX(date)`. A day
with no published NAV simply has no row. Where a series is too sparse to mean anything,
the card says so rather than drawing a curve (the Portfolio Pulse sparkline does this
while `lots` is empty).
