# PLAN — the pending queue

One place for everything not yet shipped. Source of truth for scope:
`C:\Users\vkjha\Project-Audit-OUT\BUILD_ORDER.md` (Fable's audit, tickets K-00…K-24
above the cut line, B-01…B-19 below). Ticket-by-ticket history with deviations is
`OVERNIGHT_LOG.md`. This file is the *queue*; the one open task goes in `NOW.md`.

## Where it stands (2026-09-07)

- **Aggregator fully green** — `.venv\Scripts\python Start_Inky\run_checks.py` → exit 0,
  all 10 checks PASS, no permitted failures.
- **Above the cut line: 18 / 25.** 7 left, all behind one owner decision (K-06).
- **Below the cut line: 3 / 19** (B-02, B-03, B-04). 16 left. B-04 code done; owner
  owes a 2-minute browser pixel pass (§4.7).
- **Whole plan: 21 / 44 ≈ 48%.**
- Branch `vivek/main-menu-rubric-agentic-os` pushed to origin through `dc99df6`.

---

## §1 · START HERE — no decision needed, do in this order

These need nothing from the owner. Each is one focused session; the presentation ones
finish with a browser pass (Rule 15).

| # | Ticket | What | Notes |
|---|--------|------|-------|
| ~~B-04~~ | ~~`[GLM]`~~ | ~~Storage structure cards + drawers~~ | **Code shipped `dc99df6`.** Owner owes the browser pixel pass — §4.7. |
| 1 | **B-07** `[GLM]` | Books shelf + upload button + read-progress control on the Storage page | Backend contract from K-23 is shipped (`POST /books/upload`, `/books/{slug}/read`, `GET /books`). Presentation only. Visual pass. |
| 2 | **B-06** `[GLM]` | Email card compact presentation | `UI_IA_PLAN.md §2.2`. Cosmetic. Visual pass. |
| 3 | **B-17** `[GLM]` | Wire A4–A7 to their endpoints (`/api/learning/research/digest`, `/api/office/applications/read`, weekly books insight, monthly proposals) | Agents exist; verify each endpoint answers before wiring the UI. 3 evenings. |
| 4 | **B-13** `[GLM]` | Pomodoro tray app (Windows) writing the `§13.1` log format into `kage-data/inbox/pomodoro/` | Producer only — the K-23 ingest adapter already consumes that folder. 2 evenings. |

**B-18** `[GLM]` (delete dead code: `the_fallback_chain.py`, `Agent/Calendar_Agent/calendar_agent.py`,
Finance `services/agents/*.py`, `Screens/Storage/Backend/services/sanitize.py`, archive
`Master_Context.md`) is *mostly* safe now but its last item ("delete
`Fourteen_Week_Plan_Seeded_Into_INKY.md` after B-09") waits on B-09 — do the safe deletions
whenever, hold that one line.

---

## §2 · BLOCKED on the K-06 decision — the big unlock

**Decision:** retire agent-declared `data_sources` (adopt the audit design) **or** keep the
shipped ask-path feature. K-06 was implemented and reverted (`137659d`) because as written it
leaves `test_read_office_roundtrip` red. See §4.1.

Once answered, this chain runs in order (K-08/K-09/K-10 already done):

1. **K-06** `[GLM]` — `office.py` reads the new agent config shape. If "adopt audit design", the
   ticket must also update `test_read_office_roundtrip` (and K-07/K-11 follow the new shape).
2. **K-07** `[GLM]` — collapse the fleet 37 folders → 8. Pre-checked: `AI_Agents/` holds exactly
   the 37 dirs the ticket lists. Data ticket, exempt from the three-file cap.
3. **K-11** `[GLM]` — `POST /api/agents/llm` + bounded prompt assembly. Needs K-06 shape + K-07.
4. **K-20** `[SONNET]` — the arbiter: one ranked decision per day. Needs K-11.
5. **K-21** `[SONNET]` — day-view data contract `GET /api/main_menu/day`. Needs K-20.
6. **K-22** `[GLM]` — the day-view page (presentation). Needs K-21. Visual pass.
7. **K-24** `[GLM]` — every model call goes through the seam. Needs K-11. Also bakes in D-16/D-17
   (see §4.4) — confirm those before it runs.

**B-08** `[GLM]` (Finance Review narrative button → `finance_analyst`, first A2 consumer) also
waits on K-07.

---

## §3 · BLOCKED on a smaller owner decision

| Ticket | Owner | Needs | What |
|--------|-------|-------|------|
| **B-01** | owner | — | Install the `gh` CLI (repo rule 18 before any push). 10 min. |
| **B-12** `[owner+GLM]` | D-06 | Local 7B as an OmniRoute provider (`local-llama`, llama.cpp `/v1`), then the phone 0.9B row. Enables tier T0. |
| **B-05** `[Sonnet]` | D-12 | Backup/restore with `sqlite3 .backup` + integrity check + `backup_completed` event; launcher restarts a dead child once/hour. `§17.3/§17.4`. |
| **B-10** `[Sonnet]` | D-15 | YouTube fetch job (Data API via existing OAuth, or Takeout converter) writing `inbox/youtube/watch_*.json`. Freshness row already exists from K-04. |
| **B-11** `[Sonnet]` | D-10 | Phone migration: `port_pid` without `netstat`, one-port proxy with `X-Kage-Token`, `kage-data` on the 32 GB partition. |
| **B-19** `[Sonnet]` | D-07 | `_cost_tax` date-exact long-term boundary (`EV-MONEY-04`). Changes reported tax buckets — money correctness the owner must okay. |
| **D-05** | — | Model prices. The budget gate (K-09) refuses unpriced paid models *by design* until this lands; every paid rung is dead until then. |

**Not startable regardless:** B-09 `[Sonnet]` (Learning `today`/`path/export`/coach — its own
`LEARNING_AND_BOOKS_PLAN.md` scope, no blocker but large), B-14 `[Sonnet]` (desktop/Android
clients — "after everything"), B-15 `[GLM]` (Playwright harness — only if the owner wants
automation over manual visual checks, ~200 MB deps), B-16 `[GLM]` (eval runner — needs a week
of real data first).

---

## §4 · OWNER DECISION QUEUE — answering these unblocks §2 and §3

### 4.1 · K-06 vs the shipped `data_sources` feature  ← the one that unblocks 7 tickets

K-06's contract says agent-declared `data_sources` is retired (always `None`). But the shipped
ask-path context-injection feature (`f901a44`) has agents declare loopback `data_sources` URLs,
enforced by `test_context_injection.py::test_read_office_roundtrip`. K-06 as written doesn't
touch that test, so it can't leave the suite green.

- **Adopt the audit design** → K-06 amended to also rewrite `test_read_office_roundtrip`; K-07,
  K-11, K-20, K-21, K-22, K-24, B-08 unblock.
- **Keep the shipped feature** → K-06 goes back to Fable for redesign; the chain stays parked.

### 4.2 · D-05 — model prices
Supply per-model input/output $/1k for the paid rungs, or confirm "T0/local only for now".
Until then K-09's gate refuses every unpriced paid model.

### 4.3 · D-15 — YouTube watch-history source
Data API (via the existing OAuth project) **or** Google Takeout converter. Gates B-10 and the
YouTube half of the K-23 ingest adapter.

### 4.4 · D-16 / D-17 — inside K-24
D-16: retire the nightly calendar agent. D-17: delete `/chat` + `local_ai`. K-24 bakes both in —
confirm the recommendations before it runs.

### 4.5 · D-06 / D-07 / D-10 / D-12
Gate B-12 / B-19 / B-11 / B-05 respectively (see §3).

### 4.6 · K-15 visual pass
One minute with the calendar card open at `127.0.0.1:8000`: footer text, hover popover time,
reduced-motion, 390×844. Code shipped (`bb45945`); only the human check is outstanding.

### 4.7 · B-04 visual pass  ← ~2 minutes at `127.0.0.1:8009`
Code shipped (`dc99df6`), verified headless (render fns run against the live endpoints).
Not verified in a real browser — the Claude-in-Chrome extension was not connected. Check:
three cards fit one row at 1440×900, a drawer opens <200 ms with no layout shift behind it,
`prefers-reduced-motion` disables the slide, Esc closes, at 390×844 the cards stack.

### 4.8 · D-14 — `test_the_rules_are_followed.py`
The rotate module exists on the live box; this test does not (absent from Fable's export).
Owner says whether to write it.

### 4.9 · B-15 — Playwright harness at all?
Yes/no on automating the presentation-ticket visual checks. (Would remove the need for §4.6
and §4.7 hand-checks.)

---

## §5 · LOOSE ENDS (nits, not blocking)

- **Pre-commit hook is fake-green.** `.git/hooks/pre-commit` runs `run_checks.py` on PATH
  Python (no `pytest-asyncio`) → async tests silently skip → hook shows green even when the
  venv run is red. Documented since `b5cdbdc`. The honest gate is the explicit
  `.venv\Scripts\python Start_Inky\run_checks.py`. Owner's file — untouched.
- **Dead constant.** `settings_for_agents.py:63–65` still parses `DEMO_EVENTS`; nothing reads
  it after B-02. Port-settings file (protected) — owner deletes the 3 lines by hand.
- **Generator stderr noise.** `generate_structure_docs.py` scanning some backend `.py` files
  raises `SyntaxWarning: invalid escape sequence` (a pre-existing non-raw regex string in a
  scanned file). Harmless; generator exits 0. Fix the offending scanned file some day.

---

## Reference — what these docs are (Rule 24)

| File | Role |
|------|------|
| `CLAUDE.md` | rules — read first every session |
| `NOW.md` | the one open task + its "done when" |
| `PLAN.md` | this file — the pending queue |
| `AGENTS.md` | numbered decisions `D<n>` |
| `OVERNIGHT_LOG.md` | ticket-by-ticket build record with every deviation |
| `C:\Users\vkjha\Project-Audit-OUT\` | Fable's frozen audit (BUILD_ORDER + specs) |
