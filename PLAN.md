# PLAN — open work only

One line per thing that is not done. Shipped work is deleted the day it ships (Rule 12);
the record is git history plus a decision line in [`AGENTS.md`](AGENTS.md). Rules live in
[`CLAUDE.md`](CLAUDE.md). Whatever is being worked on **right now** is in [`NOW.md`](NOW.md),
one task at a time — this file is the queue, not the desk.

Item numbers never change (Rule 11). Gaps mean that item closed.

## Order

| # | Item | Status |
|---|------|--------|
| 1 | Finance data migration / backfill | **active** |
| 2 | Storage seam + hybrid RAG — tail | **active** |
| 3 | Wire finance agents through OmniRoute | blocked (owner's orchestration plan) |
| 6 | finance-os Overview — tail | closed (owner: 3D later, SMS dropped) |
| 7 | Observability — Main Menu panel | queued (after owner studies observability) |
| 11 | Repoint the Hermes fleet | blocked (owner, per profile) |
| 12 | Learning OS — content + crew | **active** |
| 14 | Calendar card | queued (home redesign dropped by owner) |
| 15 | Day Plan card becomes agent-owned | **shipped 2026-09-06** |
| 16 | Agent roster expansion | **active** (learning → job → finance) |
| 19 | OpenClaw — configure real channels/models | queued (owner, not Claude) |

Items 1, 2 and 12 may run in parallel; everything else is sequential.
Whole backlog: roughly **70–100 focused hours**, excluding the owner's own figures,
the CAS import, and the hours spent actually studying the Learning rooms.

---

## 1 — Finance data migration / backfill *(active)*

- **Shipped 2026-09-05:** `lots` rebuilt from `my_investments.csv` — 0 → 52 lots across 8 holdings. XIRR non-null (57.7%), net-worth ridge moves. Verified live at `localhost:8001`. Script: `Screens/Finance/Backend/app/scripts/rebuild_lots_from_csv.py`.
- **Checked, not a gap:** 15 CSV identifiers didn't match a holding (TATASTEEL, HINDCOPPER, TRIDENT, MODEFENCE, SYLPH$, GATECH, ITBEES, FILATFASH, AONESILVER, GROWWMETAL, JMFINANCIL, HCC, PILITA, CROPSTER$, plus mutual funds 120716/119128) — every one nets to exactly 0 units (bought and fully sold within the CSV window), so `holdings` correctly carries no row for them. One real miss: GOLDBEES nets to 81.0, matching existing holding `INF204KB17I5` exactly — the CSV ticker vs. the ISIN `holdings.symbol`. Fixed with an `ALIASES` map in the rebuild script, not a new holdings row.
- **The CSV is confirmed stale.** Checked the live Groww account 2026-09-05: it holds 17 shares of GACM Technologies (`GATECH`) that the CSV's GATECH rows (net 0, closed 2026-03-20) don't explain — a trade after the export window is missing. Not fixed (no source data to add it from without guessing). Re-exporting `my_investments.csv` before trusting it further is worth doing alongside the CAS re-import. Detail: `Screens/Finance/finance-datamigration.md` §6.
- **CAS handled 2026-09-06 (D49).** The owner's statement is a **CDSL** CAS, which `casparser` cannot parse — read via `pdfminer` text this session. It only *confirmed* the portfolio (finance.db holdings are fresher — Aug SIPs in) and added two folio numbers + folio-level cost basis for the three external funds. No dated LTCG/STCG lots in a CDSL CAS. A real importable CAS needs a CAMS/KFintech mailback export, or a CDSL parser — undecided. Detail: `finance-datamigration.md` §9.
- **§2 gaps filled 2026-09-06 (D50).** term life 0, EPF ₹60k, Slice ₹0, salaried/₹70k-fixed take-home, no dependants (uncle is a creditor), uncle ₹96k, expenses match `fixed_bills`, Groww + 3 folios only, FY25-26 new regime → ₹0 tax. `goals` table now seeded (4 rows). **Still owed by you:** education-loan statement screenshot (outstanding left at ₹6,54,750 with a marker), and whether to flip `verified_by_a_person` in the tax JSON (needs an incometax.gov.in check).
- **Q11 decided (D48):** port the old finance code, rebuild only where it doesn't fit the schema. **you** still owe **Q10** (finance AI agent + cloud LLM routing) and **Q12** (OmniRoute timing) — both block item 3; owner's sequence is OmniRoute → OpenClaw → finance agent. Locked answers for Q1–Q9: `.scratch/finance-os-port/COLLECTED_ANSWERS.md`.
- Two Groww pages unresolved (100900 HDFC Children's, 120760 UTI Multi Asset) — sheets show honest `pending`. Tried again 2026-09-06: every slug variant 404s and the search API is unreachable from this box; add a slug override in `services/fund_reference.py` `MANUAL_OVERRIDES` only when a page whose scheme_code matches is actually found.
- Market-cap split not shown; it needs per-stock facts and is never guessed.
- AMFI `NAVAll.txt` retires 2026-09-30 — mfapi stays primary, so this is a parser-only change if the fallback is ever needed.

- **SIP schedule shipped 2026-09-06 (D53).** `sips` table seeded with the owner's real plan (7 active, ₹8,000/mo, all due the 6th, AMFI-linked to holdings); `GET /investments/visuals/sip-calendar` serves the standing plan with next-due; the SipStrip panel shows the STANDING PLAN line. Verified live at :8002.
- **Benchmark endpoint shipped 2026-09-06 (D53).** `GET /api/finance/market/benchmark` serves the NIFTY 50 indexed series from the local ledger (1,823 closes); empty ledger is a 404, which still renders `NO BENCHMARK LOADED` (D28.4). `POST /market/benchmark/backfill` pulls fresh ^NSEI closes.
- GACM trade (19 rupees) ignored by owner's call. SMS import dropped completely by owner's call (he has another plan for it).
- **Still owed by the owner:** education-loan statement screenshot (outstanding left at ₹6,54,750 with a marker).

Detail (gitignored, PII): `Screens/Finance/finance-datamigration.md`. Port brief: `.scratch/finance-os-port/`.

---

## 2 — Storage seam + hybrid RAG — tail

Shipped 2026-09-05 (D32, D33–D33.6): the seam, FTS5 + dense RRF hybrid search, the sanitizer hook, the append-only trader ledger, real status panels on 8009, and the Main Menu `storage:` glyph. Also shipped 2026-09-05 (D40): `KAGE_DATA_DIR` moved repo-relative (`<repo>/kage-data/`, gitignored, Rule 7.1) for phone/Termux hosting, and the agent library convention (`services/library.py`) — `library/<screen>/<tab>/<card>/<card>_<timestamp>.md`, one dated file per write, a `latest` + history read. What is left:

- **Embeddings live 2026-09-06 (D51):** `jina-ai/jina-embeddings-v5-text-nano` (768-dim) through OmniRoute — owner's Jina free-tier key added as the `jina-ai` provider. Storage `embeddings/status` = `ok`, dense search working. OmniRoute has no keyless embedder, so this cost one free key; D11.5.1's "free model id" premise footnoted.
- **Sanitizer rules written 2026-09-06 (D54, owner delegated).** `knowledge/_sanitize_rules.json` now carries 9 literal rules covering every identifier actually present in the corpus (name, email, phone variants, LinkedIn URL + handles); provenance note at `knowledge/_sanitize_rules_note.md`. **LLM scrub pass decided against for now** — literal rules cover what exists; revisit when the corpus grows.
- Fusion is RRF (D33) absent your research landing; revisit only if that research says otherwise.
- **Consumers, later:** each screen's own agent starts writing its real state into the library as it's built — the Day Plan card is the first consumer (item 15, D55); the Context Engine went live 2026-09-06 (item 16 A, D57).

---

## 3 — Wire the finance agents through OmniRoute

Small adapters over `/v1/chat/completions` on `127.0.0.1:8010` with `GATEWAY_API_KEY`: the supervisor needs `complete(question, context) -> str`, specialists need `summarize(payload) -> str`. Model choice stays a gateway routing decision, never code. **Owner's call 2026-09-06:** he has his own orchestration plan and will wire this once the agents are built and tested — build the finance agents (item 16 order: learning → job → finance), test them, leave the wiring to him.

---

## 4 — AGENT DECK — tail + V3 *(closed by owner, 2026-09-06)*

V2 shipped 2026-09-05 (D27–D27.5); end-to-end gateway run verified (D42). The owner closed the tail: V3 (board × agents) and the `claude -p` test harness are **not wanted** — agent asks already work, including through OpenClaw's Claude Pro route. Responsive polish stays owner-led (ENH-19). The board room itself is the running record (ENH-33+ cards).

---

## 6 — finance-os Overview — tail *(closed by owner, 2026-09-06)*

The Aurum rebuild (D13) and the month selector + benchmark overlay (D28) shipped; the benchmark endpoint itself shipped 2026-09-06 (D53). Owner closed the tail: the **SMS import pipeline is dropped completely** (he has another plan for it) and the **3D ridge manual browser check is parked** until he next feels like watching it — the card is known-good, automated browsers always hit the SVG fallback (Rule 15's honest limit, D13.2's own degrade path).

---

## 7 — Observability — Main Menu panel

Finance, Learning and AGENT DECK are done (D30–D30.2); Model is exempt (D30.3). The Main Menu already has the whole backend half — request-trace middleware into the trace ledger, the `health_check` dependency probe, and `GET /api/main_menu/live` SSE — and none of it is surfaced. Owner's call 2026-09-06: this waits until **he has studied observability** (it is a future plan, not a blocker); the home-page redesign prerequisite is gone because he dropped that redesign entirely.

---

## 11 — Repoint the Hermes fleet off the dead local endpoint

- **All 15 Hermes profiles still name `local-model-a` @ `localhost:8080`**, a llama-server that is not running and not coming back. Each profile's `model:` block needs `provider: omniroute`. Deliberately not bulk-edited: it changes what every agent costs and how it behaves, so it is a decision per profile (D25.1).
- Only three DeepSeek routes on the gateway answer (`cfp/deepseek-ai/…`); `-free` reports "Model is unavailable" upstream and `opencode/` returns 402. If that changes, revisit the model lists in both `install_*_provider.py` scripts.

---

## 12 — Learning OS — content + crew *(active)*

M0–M7 shipped (D16, D17.1, D35–D38.1, D45–D45.3). Owner's call 2026-09-06: **the OmniRoute crew loop (old M8) is not the plan any more** — Claude does the crew's work directly and encodes what it learns into the agent profiles ("train the agent"), one agent at a time; the agents are briefed on real endpoints and rules so they start working, not hard-trained.

- **Ground Zero content shipped 2026-09-06 (D52).** All five Ground Zero rooms (34–36, 54–55) authored: 20 steps with checkpoints, 15 five-part recall cards, via the idempotent `scripts/author_ground_zero.py`. Verified in the 14-test Learning suite.
- **Learning crew trained 2026-09-06 (D52).** `Learning_Coach_Agent`, `Learning_Research_Agent`, `KB_Librarian_Agent` (now the notes-search agent over the Storage RAG seam) carry real, short, correct briefs; a placeholder `identity.md` shadowing real briefs was found and fixed. Verified: briefs served at :8004, real ask round-trip through OmniRoute answered from the new brief.
- **Remaining content:** the other ~96 rooms stay honest-zero until authored the same way — next candidates are the owner's actual study priorities (Splunk the hunt, DQL/DPL). One module at a time, owner's daily plan decides which.
- **Owner still decides:** `kql` / `terraform` skill-tag mapping (no matching rooms exist today); M6 browser check owed (extension offline).
- **Deferred cards (each an `ENH-n` on the board):** Storage-seam note sync; progress backup; a release radar for the project stack; JD-skill radar feeding the Planner; interview-question radar feeding Quizmaster; preference learning from verification choices; Warden and Quill live. **Never: auto-applying to job portals.**

Plan and mockups: `.scratch/learning-redesign/`. The study-seed maintainer prompt lives at `Screens/Learning/LEARNING_SEED_MAINTAINER.md`.

---

## 14 — Calendar card *(queued)*

Google Calendar plus the nightly agent plus WakaTime, on the Main Menu home page (D23.1–D23.7). Owner's call 2026-09-06: keep for later; the **Main Menu home-page redesign is dropped from the plan entirely** (he is happy with what he has). Its WakaTime signal is what item 16's Context Engine reads for office hours — the dependency still holds when this wakes up.

---

## 15 — Day Plan card becomes agent-owned *(shipped 2026-09-06, D55)*

Wired end to end: `DayPlanPanel` reads `library/main_menu/day_plan/today/latest` from the Storage library seam first — a plan dated today takes over the timeline (done-state stays local, rows not hand-editable); no plan for today falls back to the old hand-kept localStorage list, honestly labelled. `Day_Planner_Agent`'s brief carries the full write contract (path, JSON shape, real data sources: Learning :8003, Finance sips, Office preemption) and today's real plan was written as the first snapshot. GET-only CORS allowlist added to Storage for the menu origin. Verified live at :8000 (ENH-36).

---

## 16 — Agent roster expansion: awareness layer + autonomous code agents

Owner's order 2026-09-06: **learning agents first (done), then job agents (done), then finance agents** — light training only, "so they can start working". **Muse Spark (section D) is removed from the plan entirely.** Item 3's wiring is the owner's own orchestration plan once the agents are built and tested.

**Shipped 2026-09-06:**
- **C — job-hunt agents trained (ENH-37).** `Job_Research_Agent`, `Resume_Agent`, `Interview_Prep_Agent`, `Application_Tracker_Agent` re-briefed with real OFFICE endpoints (:8011), the 2+ Good/Easy defensibility rule, the fixed targeting rules (four portals, Bangalore/Hyderabad/remote, never auto-apply) and the 5-part recall prep format.
- **Learning crew + notes-search agent trained** (see item 12, D52).

**Still open, in build order:**
- **A — Awareness layer.** The load-bearing idea: no agent knows what the owner is currently doing, so every planner guesses. **The collector is built 2026-09-06 (D57):** `context_engine.py` on :8004 — one run polls WakaTime (via the Main Menu summary endpoint — actually live, `state: ok`, not the "not wired" the briefs assumed), Google Calendar (D23), `git log --since` today, and every screen's health (discovered by reading each `settings_for_*.py`, never a hardcoded list), writing one honest snapshot per source to `library/context_engine/<source>/today/` (D40). Unreachable written as unreachable (Rule 8). Sync route handlers on purpose — an async handler froze the event loop and the self-probe timed out. 14 offline tests; `Time_Analyst_Agent`'s brief now reads `GET :8004/api/agents/context-engine/latest`. Still open in A: `Pattern_Learner_Agent` (needs ~6 weeks of real history; reports "not enough data" until then), `Focus_Guard_Agent` (a comparison, not a judgment — no model call). The custom Pomodoro tracker stays unspec'd until real logged data exists.
- **Finance agents** (last in the owner's order): `Finance_Main_Agent`, `Finance_MF_Agent`, `Market_Data_Agent`, `Portfolio_Analyst_Agent` profiles exist; train them on the real Finance endpoints (`sips`, `market/benchmark`, the analysis routers) the same way.
- **B — Autonomous code agents** (`UI_Builder_Agent`, `Code_Explainer_Agent`, `Bug_Fix_Agent`, `Regression_Watcher_Agent`): unchanged below.
- **A custom Pomodoro tracker** is the data source for non-office hours; all of it waits on real logged data (supersedes item 12's "time-pattern coach").

**B — Autonomous code agents.** `UI_Steward_Agent` finds drift and writes proposals but edits nothing; these four close the loop.
- **`UI_Builder_Agent`** — plain-English UI request → edits that screen's own `Page/` files → runs its build and lint → reports the diff. One screen per request, never across the HTTP seam (Rule 5).
- **`Code_Explainer_Agent`** — reads the live source, not the docs. Distinct from `Inky_Knowledge_Agent` (stored knowledge, still unscoped).
- **`Bug_Fix_Agent`** — stack trace → patch → *runs it* → reports. A fix it could not verify is reported unverified (Rule 8).
- **`Regression_Watcher_Agent`** — fires after any agent edits a screen, re-runs that screen's tests and build, files a board card on a break. The net under autonomous editing. Overlaps item 18 — build the test gate first (`run_checks.py` exists, D39).

**C — Job hunt (4 agents): trained 2026-09-06.** Belong to the OFFICE screen (item 12 M7); they are parked in the `learning` department because the Pixel Office floor hard-codes six departments in `Backend/services/office.py` and `roomPlan.ts`; a real `office` department is a later change to both files. **Never auto-apply to job portals.**

---

## 19 — OpenClaw: configure real channels/models

Shipped 2026-09-05 (D44): screen at `:8006`, local repo-relative install, gateway live and reporting real health. **Model provider done 2026-09-06 (D44.2):** owner chose his **Claude Pro subscription** directly — `openclaw onboard --auth-choice anthropic-cli`, model refs on the `claude-cli` runtime (OpenClaw reuses the logged-in Claude Code, Pro limits; no setup token stored). This settles the OmniRoute-vs-own-providers question: **own providers, Anthropic direct.** Gateway moved to token auth (`run_openclaw.py` `--auth token`, token in `openclaw.json` `gateway.auth`; still loopback-only). Verified: `openclaw agent -m` returns a real Claude reply; screen reports `openclaw: ok`. What's left:

- **you** Add one real chat channel (Settings → Channels in the Control UI, or `openclaw channels add`): Telegram botToken is the easiest; WhatsApp is QR pairing. The Control UI may ask for the gateway token once — `openclaw config get gateway.auth` prints it.

---

## Reference material kept on disk

Anything in `.scratch/` that is not listed here is deletable (D34.1).

| Path | What it is |
|------|-----------|
| `.scratch/qwen/` | Paste-ready Qwen briefs, numbered; `01_rebuild_lots.md` shipped, `02_thm_standing_lab.md` is item 12's current task |
| `.scratch/finance-os-port/` | Item 1 port brief, apply plan, locked answers Q1–Q9 |
| `.scratch/glm-briefs/2_FINANCE_backend_lots_history*.md` | Item 1's backend brief and its context pack |
| `.scratch/learning-redesign/` | Item 12 plan (`PLAN_V3.md`) + the Ember Studio mockups |
| `.scratch/finance-redesign/mockups/` | Aurum mockups — the reference for any tab not yet re-skinned (Rule 13) |
| `.scratch/finance-os-build/gates/check_{backend,frontend}_hygiene.py` | Live dependency of `Start_Inky/run_checks.py` (D39) — not deletable. `gate_phaseN.py` in the same folder are dead. |
| `.scratch/agents-workspace/` | The house-style template for writing a screen brief |
| `qwen_agent_port/` | Item 1 old-code extracts (gitignored) |

---

## Dropped — do not re-propose

- **Muse Spark contributor tier** (item 16 D) — removed entirely by the owner, 2026-09-06. Its open questions (model id, price, data-sharing) die with it.
- **The Main Menu home-page redesign** — removed by the owner, 2026-09-06; he is happy with the current home page.
- **The ₹35/month agent cost table** from the pasted draft — arithmetic on a price the repo has never verified. Keep the shape of the estimate, throw away the numbers.
- **Morning Brief and Schedule Optimizer as new agents** — `Day_Planner_Agent` is already both; item 15 is its wiring.
- **Watch_Dog, Quota Warden, Evolution Analyst as new agents** — all three already exist as profiles.
- **Architecture, Documentation and Project-Manager agents** — they overlap `Doctrine_Planner_Agent`, `Integration_Expert_Agent`, `Mission_Planner_Agent` and `UI_Steward_Agent`. Revisit only if a real gap shows up in use.
- **A separate `KAGE_DATA_DIR/planning/` store and a "trigger dispatcher" runtime** — item 2 owns storage and item 4 V2 owns the runtime. Two owners for one job is how the deleted repo-root `Agents/` pool died.
- **Wiring the old Finance telemetry panels to live endpoints**, and the **F1 two-livery realism pass** — both targeted the frontend that the rebuild replaced (D7).
- **A 30–50 h whole-repo Node migration** — rescoped to nothing by D21.1: each service keeps the runtime whose libraries its work lives in.
