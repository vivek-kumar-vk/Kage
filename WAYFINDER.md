# WAYFINDER

The single ordered map of live workstreams, **ranked by importance + dependency**. **One
item at a time.** Status detail lives in [`PLANNED_WORK.md`](PLANNED_WORK.md); design
rules in [`AGENTS.md`](AGENTS.md).

`» ACTIVE` marks what's in flight. Items 1 and 2 run in parallel (different hands).

---

## 1 » ACTIVE — Finance data migration / backfill  *(user-led)*

Port the already-solved CAS parsing (`casparser`), market data (mfapi.in / AMFI /
yfinance), tax/planning rules and ISIN↔AMFI mapping from the previous Finance UI, and
backfill transactions into `finance-os/backend`'s `finance.db`.

- Detail: `finance-os/finance-datamigration.md` *(gitignored — PII; local working doc)*.
- Figures still needed from you: `Screens/Finance/Reference_Data/Human_Checklists/What_To_Fill_In.txt` (term life, EPF, Slice balance, salaried-vs-self-employed, dependants, debt ledger, expenses, brokers, tax year).
- Decisions owed: Q10 (finance AI agent + cloud LLM routing), Q11 (port vs rebuild), Q12 (OmniRoute before/after).
- Claude, in parallel: draft the port plan / Qwen task spec from the old Finance code.

## 2 » ACTIVE — Google Drive private storage layer  *(Qwen 3-Max writes the code)*

`PLANNED_WORK.md` P7 · full spec `immediate_plan.md` Phase 5. One storage seam → Node
Google Drive MCP server → RAG extension → AI-trader seam stub. Nothing personal on local
disk.

- **Track A:** Claude produces a house-style build brief (modeled on
  `Screens/Learning/QWEN_BUILD_PROMPT.md`); you paste into Qwen 3-Max; Claude validates + wires in.

## 3 — Wire finance-os agents through OmniRoute

`PLANNED_WORK.md` P11. Small adapters over `/v1/chat/completions` on `127.0.0.1:8003`.
Blocked on Q10 / Q12 from item 1.

## 4 — The AGENTS screen (agent workspace)

`PLANNED_WORK.md` P3 · plan `.scratch/agents-workspace/`. Rename `Screens/Enhancement/`
→ `Screens/Agents/` (`MENU_LABEL="AGENT DECK"`); rebuild as a 3-pane agent workspace
("Deck" theme). The kanban becomes one room, owned by `Agent_Head`. V1 = shell +
working board + 21 profile stubs + honest stubs, no LLM. V2 = real agents wired through
OmniRoute. Built by Qwen 3-Max one unit per turn (backend/frontend alternating, each
gated). **V1 done 2026-08-30** (all 12 turns applied + verify gate passed).

## 5 — Replace the example Learning seeds

`PLANNED_WORK.md` P6. Real plan, or load seeds from the P7 Drive layer once it lands.
Canonical Learning surface is `Screens/Learning/` (`AGENTS.md` D8).

## 6 — Observability on every tab

`PLANNED_WORK.md` P1. One block per screen → live health / latency / error feed / trace.

## 7 — Remove `Shared_By_All_*`

`PLANNED_WORK.md` P2 / `AGENTS.md` Rule 5. Inline into the one caller, delete; both dirs
trend to empty.

## 8 — Stack migration: Python/FastAPI → Node + Express

`PLANNED_WORK.md` P4. One screen at a time; keep ports and the plain-page fallback.

## 9 — Anime-removal cleanup in the framework UIs

`PLANNED_WORK.md` P5. Layout pass on the Next.js + Svelte Main Menu variants.

## 10 — dsh local-model observability  *(parked)*

`.scratch/dsh-local-model/PLAN.md`. Run the local coder model inside DeepSeek Harness for
a step-by-step web UI. Resume trigger ("after the finance redesign") is now met.

---

## Archived / dropped

- `.scratch/_archive/finance-realism-pass/` — F1 two-livery Finance skin; built then superseded by finance-os V1. (`AGENTS.md` D7)
- `.scratch/_archive/finance-telemetry/` — earlier F1/telemetry skin + X-series. Shared harness stays at `.scratch/finance-telemetry/` (see `HARNESS.md`).
- `.scratch/_archive/model-page-litellm-litellm-tickets/` — LiteLLM+Postgres gateway; replaced by OmniRoute (`AGENTS.md` D6, `Screens/Model/GATEWAY_CONFIG.md`).
- `finance-os-master-plan-final.md`, `learning-tab-plan.md`, `wire-screens-plan.md` — deleted; work shipped.
- `PLANNED_WORK.md` P8, P9 — see its `## Dropped` section.
