# active_imple — tonight's build queue (owner asleep, work autonomously)

Ordered longest-task-first, then chronologically inside each. Tick a box only when
its step is done **and committed**. Owner-input points are marked **[OWNER]** —
skip past them, never block. **OpenClaw is off-limits all night (owner's order).**
Board room (AGENT DECK kanban) gets a card/progress note after each shipped step.

Context rule: keep replies lean; the harness compresses automatically — keep working
through it, never stop for it.

---

## Phase A — Learning Ground Zero + agent training (items 12 + 16, the long pole)

- [x] A1. Read the corpus (`Screens/Learning/Context/Master_Context.md`, gitignored PII —
      never copied into git) to ground the content in the owner's actual level and goals.
- [x] A2. Author real room content for **Ground Zero (project)** — rooms 34 (Git & GitHub),
      35 (Linux shell), 36 (Networking: DNS/HTTP/ports/localhost): steps with explain +
      realworld, checkpoints, recall cards. Written as the crew stand-in (owner's call —
      no OmniRoute crew loop tonight).
- [x] A3. Author real room content for **Ground Zero (observability)** — rooms 54
      (Networking TCP/IP), 55 (Linux ground 0, THM-linked).
- [x] A4. Teach the agents: distill what was authored into the Learning crew profiles —
      `Learning_Coach_Agent`, then `Learning_Research_Agent`, one agent at a time —
      shorter, real, correct description files (no stale nomic/local-model references).
- [x] A5. Notes-search agent: point `KB_Librarian_Agent` at the Storage RAG seam
      (`:8009` knowledge/search) as its real tool, with honest down-state wording.
- [x] A6. Verify in Agent Deck (:8004) — roster shows the trained profiles; one real
      `ask_agent` round-trip through OmniRoute (:8010) against the trained agent.
- [x] A7. Board room: file ENH card(s) for the Ground Zero content + training pass.

## Phase B — Finance item 1 tail (SIP date = 6th of each month, owner-confirmed)

- [x] B1. `sips` table + seed (7 active SIPs, ₹8,000/mo, all due the 6th, monthly).
- [x] B2. Replace the `sip-calendar` honest stub (`routers/investments.py:144`) with a
      real endpoint reading `sips` — still honest when empty (Rule 8/22).
- [x] B3. `GET /api/finance/market/benchmark` — hardcoded `^NSEI` (D28.4), served from
      `price_history` via the existing `backfill_benchmark`; 404 path keeps
      `NO BENCHMARK LOADED` on the ridge.
- [x] B4. Try resolving the two Groww pages (100900 HDFC Children's, 120760 UTI Multi
      Asset) — only a verified page lands in `MANUAL_OVERRIDES`; else honest `pending` stays.
- [x] B5. Verify live at :8002, board room card, commit.

## Phase C — Storage sanitizer rules (item 2)

- [ ] C1. Write real starter rules into `knowledge/_sanitize_rules.json` via the seam
      (name / phone / email / PAN / account-number patterns as literal rules per the
      hook's design), reviewed against the actual corpus.
- [ ] C2. LLM scrub pass decision: record it (not worth it tonight — literal rules cover
      the PII that actually flows; revisit when the owner reviews his data). Board card + commit.

## Phase D — Day Plan card agent-owned (item 15)

- [ ] D1. Wire `Day_Planner_Agent`'s real ask path to the Day Plan rows so the card's
      rows come from the agent's plan, not hand-kept localStorage. Scope-checked against
      the existing card code before touching it; if it grows beyond tonight, honest
      partial + board card.
- [ ] D2. Board card + commit.

## Phase E — Job-hunt agents (item 16 C — after Learning, per owner's order)

- [ ] E1. Train `Job_Research_Agent`, `Resume_Agent`, `Interview_Prep_Agent`,
      `Application_Tracker_Agent` profiles with real, correct, short briefs grounded in
      the OFFICE screen's actual API (built and testable — not gated anymore). Light
      training only, per owner. One agent at a time.

## Phase F — Bookkeeping

- [ ] F1. PLAN.md: apply owner's calls — drop SMS import + GACM + 3D check (item 6),
      drop Main-Menu home redesign (item 14 keeps calendar card only, queued), drop
      Muse Spark (item 16 D), item 3 stays owner-later, item 4 closed as "working".
- [ ] F2. AGENTS.md: D-lines for tonight's decisions (Ground Zero authored by Claude as
      crew stand-in; SIP date; sanitizer starter rules; Muse Spark dropped).
- [ ] F3. NOW.md rewritten for the next session. Final commit.

---

## [OWNER] — parked, not blocking (owner reads this after waking)

- Education-loan statement screenshot → real outstanding (finance item 1).
- `kql` / `terraform` skill-tag mapping decision (Learning M7 tail).
- Item 14 calendar card — queued, later.
- Item 7 observability panel — after the owner studies observability.
- Item 3 finance agents — owner's own orchestration plan; build+test first when he's back.
- Item 19 OpenClaw chat channel — **not tonight**, OpenClaw untouchable this session.
