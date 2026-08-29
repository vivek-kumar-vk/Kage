# Phase 6 — Learning tab & RAG

Authoritative: master doc §7 (Learning endpoints), §9.5 (Learning Specialist),
§11 (RAG). **Public educational content ONLY is ever embedded** — no user
transaction data, account names, holding names, lender names, PAN ever enters the
vector store or a retrieved chunk.

## META-FIX — see phase0.md.

## Files & responsibilities

- `backend/services/rag.py` — FAISS index at `backend/data/vector_store/`,
  embeddings `sentence-transformers/all-MiniLM-L6-v2` (384-dim). `ingest(path)`
  chunks public Markdown/PDF (Zerodha Varsity style) and adds to the index.
  `retrieve(query, k=5)` returns top-k chunks. A hard filter/allow-list ensures
  only docs under a `content/` public dir are ever ingested; assert no row from
  `transactions`/`holdings`/`accounts` can reach `ingest`.
- `backend/scripts/ingest_varsity.py` — one-shot ingestion of the bundled public
  content directory (create a small placeholder `content/` with 2–3 public
  primers if none exists, so retrieval has something to return).
- `backend/routers/learning.py` — `/learning/topics`, `/learning/topic/{id}`,
  `/learning/personalized` (lessons chosen from portfolio/debt SHAPE — e.g.
  "you hold regular-plan funds → lesson: direct vs regular" — the SELECTION may
  use private data, but the returned CONTENT is public and carries no identifying
  strings).
- `backend/services/agents/learning_specialist.py` — `Retriever` (calls
  `rag.retrieve`), `Personalizer`.
- `frontend/app/finance/learning/page.tsx` + components: topic list, topic
  reader, personalized-lessons strip.

## Gate (`gate_phase6.py`)
seed an account "SecretBank AXJ" + a txn "DR MEHTA CLINIC"; `/learning/topics`
returns content; `/learning/topic/1` and `/learning/personalized` return 200 and
their text contains NONE of: "secretbank axj", "dr mehta", "clinic".
