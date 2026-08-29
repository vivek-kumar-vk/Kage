# Finance OS V1 — Learning Tab build brief (for Qwen3-Max, Qwen Chat)

Paste everything between the ==== markers into Qwen Chat as the first message. It is
self-contained: Qwen has no repo access, so every contract it needs is inline.

====================================================================

You are a senior full-stack engineer. Build **Tab 5 — "Learning"** of an app called
**Finance OS V1**: backend (FastAPI + Python), frontend (Next.js static export +
React 19), and its **AI agent layer** (a "Learning Specialist" with sub-agents).
Deliver production-quality code that drops into the existing tree unmodified.

--------------------------------------------------------------------
## 1. What Finance OS is

A single-user, fully-local personal-finance dashboard for one person in India.
Five tabs: Overview, Investments, Debt, Tracker, **Learning**. No auth, no cloud DB,
no multi-tenant. Runs on the user's own Windows machine. Data lives in one SQLite
file. It must work **offline** and with **no API keys**.

Design philosophy (applies to your code too):
- **Deterministic core, LLM only for narrative.** Calculations and retrieval are
  plain Python. An LLM is used *only* to phrase an explanation, never to compute a
  number or decide what to show.
- **Privacy boundary is in code, not convention.** User financial data
  (holdings, amounts, account names, PAN, ticker symbols) must never be embedded
  into the vector store and never leave the machine in a cloud-LLM payload.
  Aggregates and percentages only.
- **Every card is standalone** — fetches its own data, has its own loading /
  error / empty states.
- **One step downstream.** For every mechanism you add, also wire the thing that
  consumes it. A new endpoint needs its frontend caller. A new content corpus
  needs its ingestion script. A retrieval function needs its "no results" and
  "index missing" branches.

Stack, pinned and non-negotiable:
- Backend: Python 3.11+, FastAPI, **stdlib `sqlite3` only** (no SQLAlchemy, no
  ORM), `faiss-cpu`, `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim),
  `python-multipart`. LLM access is via an **injected client object**, never a
  module-level `import openai` / `import ollama`.
- Frontend: Next.js 15 (`output: 'export'` — static export, **no `next dev`
  assumptions, no server components doing data fetch**), React 19, TypeScript,
  Tailwind CSS 3.4, Shadcn-style copy-paste components, `lucide-react` icons.
  Three.js (`@react-three/fiber` v9 + `@react-three/drei` v10) is available but
  optional for this tab — if used, it must be `next/dynamic(..., { ssr: false })`
  with a 2D fallback.

--------------------------------------------------------------------
## 2. The repository tree (your files go in the marked spots)

```
finance-os/
  backend/
    main.py                     # do not touch
    app_factory.py              # auto-includes routers/<name>.py if present — see note
    startup.py                  # do not touch
    scripts/schema.sql          # FROZEN for V1 — do NOT add tables or columns
    services/
      db.py                     # the ONLY sqlite entry point — see contract below
      rag.py                    # <-- YOU CREATE (FAISS retrieval)
      agents/
        supervisor.py           # exists — hosts sanitize_for_cloud_llm(); you call it
        specialists.py          # exists — base _Specialist(llm=None); you extend it
        learning_specialist.py  # <-- YOU CREATE
      calculations/             # deterministic helpers (net worth, xirr, ...) — read only
    routers/
      accounts.py imports.py entities.py ...   # pattern to copy
      learning.py               # <-- YOU CREATE (APIRouter named `router`)
    content/
      learning_topics.json      # <-- YOU CREATE (static topic manifest, public text)
      corpus/                   # <-- YOU CREATE (public educational .md files you author)
    scripts/
      ingest_learning.py        # <-- YOU CREATE (build the FAISS index from corpus/)
    data/
      finance.db                # gitignored
      vector_store/             # <-- FAISS index files land here; gitignored
  frontend/
    app/finance/
      layout.tsx                # tab bar already lists "Learning" -> /finance/learning
      learning/page.tsx         # <-- YOU CREATE
    lib/
      api.ts                    # useFinanceData / useSubmit — consume, do NOT edit
      types.ts                  # add your types here
    components/finance/
      Card.tsx  Skeleton.tsx  FormModal.tsx   # exist — reuse
      learning/                 # <-- YOU CREATE your components here
  shared/constants/
    categories.py / categories.ts   # shared enums — import, never redefine
```

**Router auto-include contract:** `app_factory.py` does
`importlib.import_module(f"routers.{name}")` for a fixed list that already
includes `"learning"`, then `app.include_router(mod.router, prefix="/api/finance")`.
So `routers/learning.py` **must** expose a module-level `router = APIRouter()`.
If the module raises on import, it is **silently skipped** — so it must import
cleanly with zero side effects (no DB calls, no index load at import time).

--------------------------------------------------------------------
## 3. Hard rules (violating any of these fails the task)

Backend:
1. Every DB access goes through `from services.db import connect` /
   `get_db`. **Never** `import sqlite3` + `sqlite3.connect(` anywhere else.
   `connect()` returns a `sqlite3.Connection` with `row_factory = sqlite3.Row`,
   `PRAGMA foreign_keys=ON`, WAL. Use `with connect() as db:` and `db.commit()`.
2. `scripts/schema.sql` is **frozen**. You get no new tables/columns. Store topic
   metadata in `content/learning_topics.json`; store the vector index in
   `data/vector_store/`. The only tables you may read for personalization are
   `active_holdings` (a VIEW — already excludes archived), `debts`, `goals`,
   `salary`, `snapshots`. You may write `research_notes` (`note_type='learn'`)
   and `agent_memory` if you record advice given.
3. **No module-level LLM import** in `learning_specialist.py` or `specialists.py`.
   The LLM client is passed into `__init__(self, llm=None)`. If `llm is None`,
   every method must still return a useful deterministic result (retrieved text,
   rule-based lesson list) — the LLM only rephrases.
4. Any cloud-LLM payload is built from **aggregates only** and passed through
   `supervisor.sanitize_for_cloud_llm(payload)` first (it drops keys named
   pan/aadhaar/account_number/cvv/password/otp recursively — but you must also
   not put holding names, ticker symbols, lender names, or raw rupee amounts in
   there yourself; use bands like "₹10–20L" or percentages).
5. Any slow loop (embedding a corpus, N network calls) in a request path runs as
   a FastAPI `BackgroundTasks` job or is precomputed by a script — the HTTP
   request returns immediately.
6. Time-series / list endpoints return an explicit state discriminator, e.g.
   `{"state": "ok" | "empty" | "index_missing", "items": [...]}` — never a bare
   `[]` that the UI can't distinguish from an error.
7. The RAG corpus contains **only public educational text you author or quote
   from public sources** (concepts: SIP, index funds, expense ratio, asset
   allocation, emergency fund, debt avalanche vs snowball, XIRR, rebalancing,
   term vs endowment insurance, etc.). **Zero** user data. Add a test that greps
   the corpus for digits-heavy PII patterns and fails if found.

Frontend:
8. First line of any component that uses hooks/state is exactly `"use client";`
   (with the double quotes).
9. Data fetching is only via `useFinanceData<T>(endpoint)` and `useSubmit()` from
   `@/lib/api`. Do not add fetch/axios/react-query. Contract:
   ```ts
   const { data, isLoading, error, refetch } = useFinanceData<T>('/api/finance/learning/topics');
   const submit = useSubmit(); // submit(endpoint, { method:'POST', body: JSON.stringify(x), headers:{'Content-Type':'application/json'} })
   ```
   `useSubmit` mutations auto-invalidate the module cache and bump a version that
   subscribed `useFinanceData` hooks re-read — so after a submit, other cards
   refresh without a remount. Don't reimplement caching.
10. Colors come only from the Tailwind theme tokens below. No raw hex in JSX.
    ```
    carbon.DEFAULT #1a1a1a  carbon.light #2d2d2d  carbon.dark #0f0f0f
    racing.red #e10600 (reserved for "act now" only) racing.yellow #f9a800
    racing.blue #00d2ff  racing.green #00ff87  racing.silver #c0c0c0
    fonts: font-sans (Inter), font-mono (JetBrains Mono)
    shadow-neon-red, shadow-neon-blue
    ```
    Reuse `<Card title=... action=...>` from `components/finance/Card.tsx` and
    `<Skeleton/>` for loading.
11. Every card handles three states explicitly: `isLoading` → `<Skeleton/>`;
    `error` → inline error line; `data` empty → a helpful empty state (e.g.
    "Run the learning ingest script to enable topics").
12. Every animation is wrapped in a `prefers-reduced-motion` guard.
13. Output **one complete file per code block**, first line a comment with the
    repo-relative path, e.g. `// frontend/app/finance/learning/page.tsx` or
    `# backend/routers/learning.py`. No partial diffs.

--------------------------------------------------------------------
## 4. Schema you may read (reference — already created)

```sql
CREATE VIEW active_holdings AS  -- h.* for non-archived holdings in non-archived accounts
  SELECT h.* FROM holdings h JOIN accounts a ON a.id=h.account_id
  WHERE h.archived_at IS NULL AND a.archived_at IS NULL;
-- holdings(id, account_id, symbol, name, type['stock'|'mutual_fund'|'etf'|'bond'|'other'],
--   units, avg_cost, currency, direct_regular['direct'|'regular'], benchmark, archived_at)
-- debts(id, lender, type, outstanding, interest_rate, emi, next_due, remaining_months, status)
-- goals(id, name, target_amount, current_amount, target_date, start_date, priority, status)
-- salary(id, monthly_gross, monthly_net, effective_date)   -- current = MAX(effective_date) <= today
-- snapshots(date UNIQUE, net_worth, cash, debt, investments, emergency_months)
-- research_notes(id, holding_id, note_type['what_is'|'benchmark'|'expense'|'risk'|'learn'], content)
-- agent_memory(id, advice, user_decision, outcome, timestamp, reason, confidence)
```

--------------------------------------------------------------------
## 5. Backend deliverables

### 5.1 `backend/content/learning_topics.json`
A static array of topics. Each: `{ "id": "sip-basics", "title": "SIP & rupee-cost
averaging", "level": "beginner"|"intermediate"|"advanced", "summary": "<=200 chars",
"tags": ["investing","mutual-funds"], "corpus_files": ["sip.md","index-funds.md"] }`.
Ship ~12 topics covering the concept list in rule 7.

### 5.2 `backend/content/corpus/*.md`
The public educational text, one file per concept, ~300–800 words each, plain
Markdown, headings + short paragraphs. Neutral, India-context where relevant
(NSE/BSE, AMFI, ELSS, NPS). No user data. No investment advice framed as
"you should" — explain the concept.

### 5.3 `backend/scripts/ingest_learning.py`
CLI script (`python -m scripts.ingest_learning` from `backend/`). Reads
`content/corpus/*.md`, splits each into ~500-token overlapping chunks (keep
heading context in each chunk), embeds with `all-MiniLM-L6-v2`, writes a FAISS
index (`IndexFlatIP` on L2-normalized vectors) plus a sidecar
`chunks.jsonl` (`{id, topic_id, file, heading, text}`) into
`data/vector_store/`. Idempotent: rebuilds from scratch each run. Prints
chunk/topic counts. Must run with no network and no GPU.

### 5.4 `backend/services/rag.py`
No import-time model load. Lazy singletons:
- `def get_index() -> tuple[faiss.Index, list[dict]] | None` — loads index +
  chunks from `data/vector_store/`, returns `None` if absent.
- `def embed(texts: list[str]) -> np.ndarray` — lazy-loads the sentence
  transformer once, L2-normalizes.
- `def search(query: str, k: int = 5, topic_id: str | None = None) -> list[dict]`
  — returns `[{score, topic_id, file, heading, text}]`; empty list if index
  missing or no hits above a small score floor. Optional `topic_id` filter.
- Never raises on a cold/missing index — callers branch on the return.

### 5.5 `backend/services/agents/learning_specialist.py`
```python
from services.agents.specialists import _Specialist   # base: __init__(self, llm=None), .run(data)

class Retriever(_Specialist):
    name = "retriever"
    # .run({"query": str, "k": int, "topic_id": optional}) -> {"state","chunks":[...]}
    # pure RAG: calls services.rag.search; no LLM.

class Personalizer(_Specialist):
    name = "personalizer"
    # .run({"facts": {...aggregates...}}) -> {"lessons":[{topic_id,title,reason}], "state"}
    # DETERMINISTIC rule engine mapping portfolio/debt facts -> relevant topic ids:
    #   e.g. has regular-plan MF  -> "direct-vs-regular"
    #        debt.interest_rate>18 & investing -> "debt-vs-invest"
    #        emergency_months<6 -> "emergency-fund"
    #        single holding weight>25% -> "concentration-risk"
    #        no ELSS & salaried -> "tax-saving-elss"
    # If self.llm: use it ONLY to write the one-line `reason`, from sanitized bands.

class LearningSpecialist(_Specialist):
    name = "learning"
    def __init__(self, llm=None):
        super().__init__(llm)
        self.retriever = Retriever(llm=None)
        self.personalizer = Personalizer(llm)   # llm passed for narrative only
    # .answer(question, topic_id=None) -> {"answer": str, "sources":[{heading,file,topic_id}], "state"}
    #    retrieve -> if llm: grounded-generate an answer that cites only retrieved text,
    #                with a "based on educational material, not personalized advice" disclaimer;
    #                if no llm: return the top chunk text verbatim as the answer.
    # .personalized(facts) -> delegates to Personalizer.
```
`facts` for `.personalized` is built by the router from aggregates only:
`{ "emergency_months": float, "num_holdings": int, "top_weight_pct": float,
"has_regular_plan": bool, "max_debt_rate": float|None, "is_salaried": bool,
"net_worth_band": "under-10L"|"10-25L"|"25-50L"|"50L-1Cr"|"over-1Cr" }`.

### 5.6 `backend/routers/learning.py`  (`router = APIRouter()`)
| Method & path (prefix `/api/finance`) | Body | Response |
|---|---|---|
| `GET /learning/topics` | — | `{"state":"ok","items":[<topic minus corpus_files>]}` |
| `GET /learning/topic/{topic_id}` | — | `{"state":"ok","topic":{...},"content":"<concatenated corpus markdown>","related":[topic_id,...]}` or 404 |
| `GET /learning/personalized` | — | `{"state":"ok"|"empty","lessons":[{"topic_id","title","reason"}]}` — router assembles `facts` from `active_holdings`/`debts`/`snapshots`/`salary`, calls `LearningSpecialist(llm=<injected or None>).personalized(facts)` |
| `POST /learning/ask` | `{"question": str, "topic_id"?: str}` | `{"state":"ok"|"index_missing","answer": str,"sources":[{"heading","file","topic_id"}]}` |
| `GET /learning/search?q=&k=` | — | `{"state":..., "chunks":[{score,heading,text,topic_id}]}` (raw retrieval, for debugging + the UI search box) |

The injected LLM client: accept it via a small provider function
`def _llm(): return None` for now (a later phase wires Ollama). Everything must
work with `_llm()` returning `None`.

Also expose a helper the Debt tab reuses:
`def learning_content_for(topic: str) -> dict` (used by `routers/debt.py`'s
`GET /debt/learning/{topic}` — you may leave a one-line import there).

### 5.7 Tests — `backend/tests/test_learning.py` (pytest)
- corpus PII grep test (rule 7).
- `rag.search` returns `[]` cleanly when `data/vector_store/` is empty.
- After running ingest into a temp dir: `search("what is an expense ratio")`
  top hit's `topic_id == "expense-ratio"`.
- `/learning/topics` and `/learning/personalized` return `state:"ok"` against a
  fresh empty DB (personalized may be `empty`).
- `/learning/ask` with no index returns `state:"index_missing"`, HTTP 200.
- `sanitize_for_cloud_llm` drops a `pan` key nested in the facts payload.

--------------------------------------------------------------------
## 6. Frontend deliverables

### 6.1 `frontend/app/finance/learning/page.tsx`  (`"use client";`)
Layout (single column, `space-y-6`, matches Overview):
1. **Header strip** — title "Learning", subtitle "Concepts explained. Grounded in
   public educational material — not personalized advice."
2. **Personalized-for-you card** (`<Card title="Suggested for you">`) — calls
   `useFinanceData('/api/finance/learning/personalized')`; renders each lesson as
   a row: title + one-line `reason` + a "Read" button that scrolls to / opens the
   topic. Empty state: "Add holdings or debts to get tailored suggestions."
3. **Ask box** — a text input + "Ask" button; on submit calls
   `useSubmit()('/api/finance/learning/ask', {method:'POST', ...})`; shows the
   `answer` in a `<Card>` with a "Sources" disclosure listing `heading — file`.
   `index_missing` state → "Run `python -m scripts.ingest_learning` to enable
   Q&A." Keep the last 3 Q&As in local `useState` (no persistence).
4. **Topic library** — grid of topic cards from `/learning/topics`, filterable by
   `level` and `tag` (client-side). Clicking one opens a `<TopicReader>`.

### 6.2 `frontend/components/finance/learning/TopicReader.tsx`
Renders `/learning/topic/{id}` markdown content. Use a tiny inline markdown
renderer (headings, paragraphs, lists, inline code, bold) — **do not add a
markdown npm package**. Show `related` topics as chips at the bottom.

### 6.3 `frontend/components/finance/learning/*` — small pieces
`LessonRow.tsx`, `TopicCard.tsx`, `AskPanel.tsx`, `SourceList.tsx`. Each
`"use client";` where it uses state.

### 6.4 `frontend/lib/types.ts` — append
`LearningTopic`, `LearningLesson`, `AskResponse`, `SearchChunk` interfaces
matching the response shapes above.

### 6.5 (optional) `frontend/components/finance/learning/KnowledgeOrbit.tsx`
A subtle Three.js decoration for the header — nodes = topics, orbiting slowly.
`next/dynamic({ ssr:false })`, `<Suspense>` fallback = a static SVG, frozen under
`prefers-reduced-motion`. Skip if it costs correctness time.

--------------------------------------------------------------------
## 7. Acceptance gate (this is how the work is judged)

1. `python -m scripts.ingest_learning` builds an index with >0 chunks, no network.
2. `GET /api/finance/learning/topics` → `state:"ok"`, ≥12 topics.
3. `POST /api/finance/learning/ask {"question":"what is an expense ratio?"}` with
   an index present → an answer whose `sources` include the `expense-ratio` topic;
   with no index → `state:"index_missing"`, HTTP 200, no stack trace.
4. `GET /api/finance/learning/personalized` on a DB with one regular-plan mutual
   fund → a lesson list containing `direct-vs-regular`.
5. grep of `content/corpus/` finds no PAN/Aadhaar/rupee-amount/account-number
   patterns; nothing from `holdings`/`transactions` is ever embedded.
6. `routers/learning.py` imports with zero side effects (no DB, no model load).
7. Frontend `learning/page.tsx` renders on a fresh empty DB with no
   `undefined`/`NaN`, correct loading/empty/error states, theme tokens only.
8. `pytest backend/tests/test_learning.py` green; `tsc --noEmit` clean.

--------------------------------------------------------------------
## 8. Do NOT

- add DB tables/columns, or a second sqlite connection path
- `import openai`/`ollama`/`litellm` at module level, or send holdings names /
  tickers / rupee amounts / PAN to any LLM
- embed or log user financial data into the vector store
- add npm packages beyond what's listed (no react-query, axios, markdown libs,
  chart libs)
- use `next dev`-only features / server-component data fetching (static export)
- return bare `[]`/`null` where a `{state, ...}` envelope is specified
- output partial files or diffs

--------------------------------------------------------------------
## 9. How to respond

1. Start with a 5–10 line plan and any assumptions.
2. List up to 5 concise clarifying questions **only if truly blocking**;
   otherwise proceed.
3. Then emit every file, one per fenced block, path comment as the first line,
   backend before frontend, tests last.
4. End with: the exact commands to ingest + run + test, and a short "what a
   reviewer should click through" list.

====================================================================
