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
| 2 | Storage seam + hybrid RAG — tail | active |
| 3 | Wire finance agents through OmniRoute | blocked (Q10, Q12) |
| 4 | AGENT DECK — tail + V3 | queued |
| 6 | finance-os Overview — tail | queued |
| 7 | Observability — Main Menu panel | queued |
| 11 | Repoint the Hermes fleet | blocked (owner, per profile) |
| 12 | Learning OS — M6, M7, M8 | **active** |
| 14 | Calendar card | active |
| 15 | Day Plan card becomes agent-owned | queued |
| 16 | Agent roster expansion | blocked (item 4 V2, item 2, item 14) |
| 19 | OpenClaw — configure real channels/models | queued |

Items 1, 2 and 12 may run in parallel; everything else is sequential.
Whole backlog: roughly **70–100 focused hours**, excluding the owner's own figures,
the CAS import, and the hours spent actually studying the Learning rooms.

---

## 1 — Finance data migration / backfill *(active)*

- **Shipped 2026-09-05:** `lots` rebuilt from `my_investments.csv` — 0 → 52 lots across 8 holdings. XIRR non-null (57.7%), net-worth ridge moves. Verified live at `localhost:8001`. Script: `Screens/Finance/Backend/app/scripts/rebuild_lots_from_csv.py`.
- **Checked, not a gap:** 15 CSV identifiers didn't match a holding (TATASTEEL, HINDCOPPER, TRIDENT, MODEFENCE, SYLPH$, GATECH, ITBEES, FILATFASH, AONESILVER, GROWWMETAL, JMFINANCIL, HCC, PILITA, CROPSTER$, plus mutual funds 120716/119128) — every one nets to exactly 0 units (bought and fully sold within the CSV window), so `holdings` correctly carries no row for them. One real miss: GOLDBEES nets to 81.0, matching existing holding `INF204KB17I5` exactly — the CSV ticker vs. the ISIN `holdings.symbol`. Fixed with an `ALIASES` map in the rebuild script, not a new holdings row.
- **The CSV is confirmed stale.** Checked the live Groww account 2026-09-05: it holds 17 shares of GACM Technologies (`GATECH`) that the CSV's GATECH rows (net 0, closed 2026-03-20) don't explain — a trade after the export window is missing. Not fixed (no source data to add it from without guessing). Re-exporting `my_investments.csv` before trusting it further is worth doing alongside the CAS re-import. Detail: `Screens/Finance/finance-datamigration.md` §6.
- **you** Re-import the CAS PDF (Investments → IMPORT CAS PDF) — fills the unrealised STCG/LTCG buckets the CSV rebuild cannot.
- **you** Fill `Screens/Finance/Reference_Data/Human_Checklists/What_To_Fill_In.txt` — term life, EPF, Slice balance, salaried vs self-employed, dependants, debt ledger, expenses, brokers, tax year. `goals` stays empty (and the Monte-Carlo path unexercised) until this lands.
- **you** Decide **Q10** (finance AI agent + cloud LLM routing), **Q11** (port vs rebuild), **Q12** (OmniRoute before or after the migration). Q10 and Q12 block item 3. Locked answers for Q1–Q9: `.scratch/finance-os-port/COLLECTED_ANSWERS.md`.
- Two Groww pages unresolved (100900 HDFC Children's, 120760 UTI Multi Asset) — sheets show honest `pending`; add a slug override in `services/fund_reference.py` `MANUAL_OVERRIDES` when the page is found.
- Market-cap split not shown; it needs per-stock facts and is never guessed.
- AMFI `NAVAll.txt` retires 2026-09-30 — mfapi stays primary, so this is a parser-only change if the fallback is ever needed.
- `GET /api/finance/market/benchmark` does not exist yet; item 6's ridge overlay renders `NO BENCHMARK LOADED` until it does.

- **SIP schedule now known but not wired.** 7 active SIPs, ₹8,000/mo, checked live on Groww 2026-09-05. `GET /investments/visuals/sip-calendar` is currently an honest `state: "pending"` stub (`routers/investments.py:144`) for exactly this reason — a `sips` table + wiring is a real small build now that the data exists. Detail + full list: `finance-datamigration.md` §7.
- **Mutual-fund watchlist not snapshotted** — the DB's `watchlist` table has 46 rows, all from the *stocks* watchlist (2026-09-02); the 10-fund MF watchlist was never captured. Minor.

Detail (gitignored, PII): `Screens/Finance/finance-datamigration.md`. Port brief: `.scratch/finance-os-port/`.

---

## 2 — Storage seam + hybrid RAG — tail

Shipped 2026-09-05 (D32, D33–D33.6): the seam, FTS5 + dense RRF hybrid search, the sanitizer hook, the append-only trader ledger, real status panels on 8009, and the Main Menu `storage:` glyph. Also shipped 2026-09-05 (D40): `KAGE_DATA_DIR` moved repo-relative (`<repo>/kage-data/`, gitignored, Rule 7.1) for phone/Termux hosting, and the agent library convention (`services/library.py`) — `library/<screen>/<tab>/<card>/<card>_<timestamp>.md`, one dated file per write, a `latest` + history read. What is left:

- **you** Pick a free OmniRoute model that is an actual embedder and set `STORAGE_EMBED_MODEL`. Until then, embeddings report "no model configured" honestly and search stays keyword-only.
- **you** Write the real sanitizer rules at `knowledge/_sanitize_rules.json`, and decide whether an LLM scrub pass earns its cost — after reviewing your own data.
- Fusion is RRF (D33) absent your research landing; revisit only if that research says otherwise.
- **Consumers, later:** each screen's own agent starts writing its real state into the library as it's built (calendar, schedule, email, finance, learning notes, documents, finance calculations, ...) — the skeleton is ready, nothing writes into it yet. Finance is likely first — salary transactions from 2026-09-04 on should land via the seam.

---

## 3 — Wire the finance agents through OmniRoute

Small adapters over `/v1/chat/completions` on `127.0.0.1:8010` with `GATEWAY_API_KEY`: the supervisor needs `complete(question, context) -> str`, specialists need `summarize(payload) -> str`. Model choice stays a gateway routing decision, never code. **Blocked on Q10 and Q12** (item 1). The gateway itself is live (D6, D6.1, D6.2).

---

## 4 — AGENT DECK — tail + V3

V2 shipped 2026-09-05 (D27–D27.5): real OmniRoute asks through one path, a `runs` table behind a live panel, per-agent model pinning. End-to-end gateway run verified and TaskBrief dropped for good, 2026-09-05 — see D42. What is left:

- **V3 (optional)** — board × agents: pick an `ENH-n`, ask an agent.
- **`claude -p` test harness** — a way to exercise agent asks before OmniRoute is in the loop. Written up 2026-09-04, never started; pick it up when agent work resumes.
- **Responsive polish (owner-led, ENH-19)** — on canvases under ~790 px tall the integer scale drops to 2× and rooms read small in wide corridors; very small windows crop the plan edge. D18.7 accepted the current rendering.
- 26 profiles today, 34 once item 16's twelve are counted, all still inert.

House-style template for a screen brief: `.scratch/agents-workspace/`.

---

## 6 — finance-os Overview — tail

The Aurum rebuild (D13) and the month selector + benchmark overlay (D28) shipped. Left:

- **SMS import pipeline**, so `sms_last_import` stops going stale by hand. **Not briefed** — needs your SMS export format first.
- **you** One manual browser check owed: the three.js net-worth ridge, its draw-in, drag-to-tilt, and the benchmark overlay were never watched running. Confirmed 2026-09-05 this is not a fixable automation bug — Claude-in-Chrome (non-headless too) reports `visibilityState: "hidden"` and `prefers-reduced-motion: reduce` on every tab it drives, so `NetWorthRidge.tsx`'s own mode check always lands on the SVG fallback for any AI-driven browser. Genuinely needs your own eyes in a normal window; not something Claude can do (Rule 15).

---

## 7 — Observability — Main Menu panel

Finance, Learning and AGENT DECK are done (D30–D30.2); Model is exempt (D30.3). The Main Menu already has the whole backend half — request-trace middleware into the trace ledger, the `health_check` dependency probe, and `GET /api/main_menu/live` SSE — and none of it is surfaced. Wire `/api/main_menu/live` into a small panel once the home-page redesign settles (same wait as item 2's glyph).

---

## 11 — Repoint the Hermes fleet off the dead local endpoint

- **All 15 Hermes profiles still name `local-model-a` @ `localhost:8080`**, a llama-server that is not running and not coming back. Each profile's `model:` block needs `provider: omniroute`. Deliberately not bulk-edited: it changes what every agent costs and how it behaves, so it is a decision per profile (D25.1).
- Only three DeepSeek routes on the gateway answer (`cfp/deepseek-ai/…`); `-free` reports "Model is unavailable" upstream and `opencode/` returns 402. If that changes, revisit the model lists in both `install_*_provider.py` scripts.

---

## 12 — Learning OS — M6, M7, M8 *(active)*

M0–M5 shipped (D16, D17.1): the Ember Studio shell, schema v2, dynamic Path, Today and Focus Session, the room player, Recall and Card Studio, INSIGHTS, the crew shell, the corpus stored, honest zero, and two ground-zero tracks re-seeded.

- **M6** — shipped 2026-09-05 (D35–D37, D38.1). Interview-day preemption
  done: Learning's Today shows a pinned prep card and dims the study plan
  when Office has a `pending` interview today; honest "office offline"
  state. Browser check owed (extension offline) — a test interview is
  left in `office.db` for the owner's look, deletable from Office.
- **M7** — shipped 2026-09-05 (D45–D45.3): OFFICE screen at :8011, five tabs,
  `/api/learning/skills` added, resume-defensibility mirrored + recomputed
  from the ≥2 Good/Easy rule, browser-verified. Rooms 96/95/75 tagged
  sigma/mitre/splunk-es. Left: **you** decide if `kql` / `terraform` should
  point at a room (none matches today) or stay untagged; refine the mapping
  if the three picked are wrong.
- **M8** — Crew live on OmniRoute (Planner, Quizmaster, Tutor, Auditor) plus the SIGNAL verification queue, THM Scout and the Office agents, with per-agent token and cost discipline. **PII routes to local models only** — and there is no local model today, which collides with item 16 D. *10–14 h.* **Gated: plan only until real data is wired; test on dummy data, never the DB.*
- **Room content** — 101 rooms have 0 steps and 0 cards. **Not a manual task and not now** (owner, 2026-09-05): the M8 crew (Planner/Tutor) drafts lesson content once the owner's real schedule and data are wired. Structure stays empty until then — honest zero, not a gap.
- **Deferred cards (each an `ENH-n` on the board):** agents drafting full lesson content; Storage-seam note sync; progress backup; a release radar for the project stack; JD-skill radar feeding the Planner; interview-question radar feeding Quizmaster; preference learning from verification choices; Warden and Quill live. **Never: auto-applying to job portals.**

Plan and mockups: `.scratch/learning-redesign/`. The study-seed maintainer prompt lives at `Screens/Learning/LEARNING_SEED_MAINTAINER.md`.

---

## 14 — Calendar card *(active)*

Google Calendar plus the nightly agent plus WakaTime, on the Main Menu home page (D23.1–D23.7). In progress alongside the home-page redesign. Its WakaTime signal is what item 16's Context Engine reads for office hours.

---

## 15 — Day Plan card becomes agent-owned

The card shipped 2026-09-04 as a hand-kept localStorage checklist (`Main_Menu/.../DayPlanPanel.tsx`). This item is the wiring: each area's agent (Finance, Learning, Anime, Agents) fetches its own real state, plans today, and writes the rows. `Day_Planner_Agent` already exists as the profile that owns it.

---

## 16 — Agent roster expansion: awareness layer + autonomous code agents

Twelve profile folders exist (`description.txt` + `office.json` only) and **none of them run** — `ask_agent` has to be live first. Raised 2026-09-05 from the owner's own asks plus an outside draft, sifted.

**A — Awareness layer.** The load-bearing idea: no agent knows what the owner is currently doing, so every planner guesses.
- **`Context_Engine_Agent`** — the collector everything else reads. Polls WakaTime (item 14), Google Calendar (D23), `git log --since` today, and each screen's health endpoint; writes each into the library (item 2, D40 — `library/<screen>/<tab>/<card>/...`, do not invent a second store). **Rule 8 applies hard:** an unreachable source is written as unreachable, never carried over from the last poll. **Build this first**; the rest of A is worthless without it.
- **`Time_Analyst_Agent`** — evening pass: planned blocks vs logged time, writes the gap report, hands it to `Day_Planner_Agent` (item 15) rather than planning itself.
- **`Pattern_Learner_Agent`** — weekly rolling focus score per time-of-day. Needs ~6 weeks of real history; until then it reports "not enough data", not a guess.
- **`Focus_Guard_Agent`** — one short nudge when current activity has drifted from the planned block. The detection is a comparison, not a judgment — no model call needed for it.
- **A custom Pomodoro tracker** is the data source for non-office hours: the owner starts and stops by hand (no auto-detection), each session logs start, end and — v2 — a task label, with its own Home card and local table. It feeds the four agents above the way WakaTime feeds them for office hours. What comes out: idle gaps, sessions that miss the plan, length and break patterns vs a baseline, which hours produce finished vs abandoned sessions, streaks, and an honest weekly "where the time actually went". **All of it waits on real logged data** and none of it is specified yet. Supersedes item 12's narrower "time-pattern coach" — same idea, whole-day scope, built once here.

**B — Autonomous code agents.** `UI_Steward_Agent` finds drift and writes proposals but edits nothing; these four close the loop.
- **`UI_Builder_Agent`** — plain-English UI request → edits that screen's own `Page/` files → runs its build and lint → reports the diff. One screen per request, never across the HTTP seam (Rule 5).
- **`Code_Explainer_Agent`** — reads the live source, not the docs. Distinct from `Inky_Knowledge_Agent` (stored knowledge, still unscoped).
- **`Bug_Fix_Agent`** — stack trace → patch → *runs it* → reports. A fix it could not verify is reported unverified (Rule 8).
- **`Regression_Watcher_Agent`** — fires after any agent edits a screen, re-runs that screen's tests and build, files a board card on a break. The net under autonomous editing. Overlaps item 18 — build the test gate first.

**C — Job hunt (4 agents).** These belong to the OFFICE screen (item 12 M7) and cannot start before it exists: `Job_Research_Agent` (reads saved JDs, extracts real skill asks — this *is* the deferred "JD-skill radar", one agent not two), `Resume_Agent` (claims only what Learning marked resume-defensible), `Interview_Prep_Agent` (per-interview pack; triggers M6's interview-day preemption), `Application_Tracker_Agent` (staleness over pipeline rows, plain SQL, no model call). **Never auto-apply to job portals.** They are parked in the `learning` department because the Pixel Office floor hard-codes six departments in `Backend/services/office.py` and `roomPlan.ts`; a real `office` department is a later change to both files.

**D — Model: Muse Spark contributor tier** (owner's call 2026-09-05 — an API key plus a large token budget for a $20 top-up, against a subscription that gives no key). Three things to settle before it is real:
1. **The exact model id.** `Screens/Model/GATEWAY_CONFIG.md` records `muse-spark-1.2-contributor-free` in the persisted config — **not 1.3**. Check the dashboard, pin the id, update that file.
2. **Its real per-token price and rate limits.** Neither is verified. A 15-minute Context Engine poll is ~96 calls/day; confirm RPM first and fall back to 30 minutes if it does not fit.
3. **The data-sharing tradeoff.** Contributor tier means prompts and outputs may be used to improve the provider's products, which collides head-on with M8's "PII → local models only" when there is no local model here. Either those agents stay off this tier, or the sanitizer (item 2) earns its place first. **Unresolved. It gates C and every Finance agent; it does not gate A or B**, which read only code, build state and timestamps.

**Blocked on:** item 4 V2 (a real `ask_agent`), item 2 (somewhere to write), item 14 (the WakaTime signal), D above, and item 12 M7 for section C.

---

## 19 — OpenClaw: configure real channels/models

Shipped 2026-09-05 (D44): screen at `:8006`, local repo-relative install, gateway live and reporting real health. What's left is real configuration, not code:

- **you** Run `openclaw onboard` (or `configure`) against the local install to add real chat channels and a model provider. Until then the gateway is up but empty — no channels, no models, honest per the screen's own report.
- Decide whether OpenClaw's model calls should route through OmniRoute (one gateway, one billing surface, same reasoning as Hermes/DeepSeek — D6, D24.1, D25.1) or use OpenClaw's own provider connections directly. Not decided yet.

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
| `.scratch/agent-deck-claude-p/PLAN.md` | Item 4's unstarted `claude -p` test harness |
| `qwen_agent_port/` | Item 1 old-code extracts (gitignored) |

---

## Dropped — do not re-propose

- **The ₹35/month agent cost table** from the pasted draft — arithmetic on a price the repo has never verified. Keep the shape of the estimate (item 16 D), throw away the numbers until the model id and its real price are confirmed.
- **Morning Brief and Schedule Optimizer as new agents** — `Day_Planner_Agent` is already both; item 15 is its wiring.
- **Watch_Dog, Quota Warden, Evolution Analyst as new agents** — all three already exist as profiles.
- **Architecture, Documentation and Project-Manager agents** — they overlap `Doctrine_Planner_Agent`, `Integration_Expert_Agent`, `Mission_Planner_Agent` and `UI_Steward_Agent`. Revisit only if a real gap shows up in use.
- **A separate `KAGE_DATA_DIR/planning/` store and a "trigger dispatcher" runtime** — item 2 owns storage and item 4 V2 owns the runtime. Two owners for one job is how the deleted repo-root `Agents/` pool died.
- **Wiring the old Finance telemetry panels to live endpoints**, and the **F1 two-livery realism pass** — both targeted the frontend that the rebuild replaced (D7).
- **A 30–50 h whole-repo Node migration** — rescoped to nothing by D21.1: each service keeps the runtime whose libraries its work lives in.
