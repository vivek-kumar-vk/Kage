"""Hybrid RAG on top of the seam (D11.5.1, D11.5.2).

Retrieval = keyword (SQLite FTS5) + dense (OmniRoute embeddings) fused by
Reciprocal Rank Fusion (RRF) - a safe, parameter-light default; the fusion
method was left as an owner research item in PLAN.md item 2 and RRF is
what this build picks absent that research landing (D33, AGENTS.md).

Dense search degrades honestly: an unreachable gateway or a non-embedding
model never breaks a search - it returns keyword-only results with
state="partial" and says so.
"""

import json
import math
import time
import urllib.error
import urllib.request

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

import settings_for_storage as cfg
from db import connect
from services import sanitize, seam

router = APIRouter()

NOTES_PREFIX = "knowledge/notes"


# =====================================================================
# CHUNKING
# =====================================================================
def chunk_text(text: str, words: int = None, overlap: int = None) -> list:
    words = words or cfg.CHUNK_WORDS
    overlap = overlap if overlap is not None else cfg.CHUNK_OVERLAP_WORDS
    tokens = text.split()
    if not tokens:
        return []
    chunks = []
    step = max(words - overlap, 1)
    for start in range(0, len(tokens), step):
        piece = tokens[start:start + words]
        if piece:
            chunks.append(" ".join(piece))
        if start + words >= len(tokens):
            break
    return chunks


# =====================================================================
# EMBEDDINGS (OmniRoute, D11.5.1) - stdlib urllib, no new dependency
# =====================================================================
class EmbeddingError(RuntimeError):
    pass


def embed_texts(texts: list) -> list:
    """-> one embedding vector per input text. Raises EmbeddingError with a
    human sentence on any failure - the caller decides what "partial" means."""
    if not cfg.STORAGE_EMBED_MODEL:
        raise EmbeddingError("no STORAGE_EMBED_MODEL configured")

    payload = json.dumps({"model": cfg.STORAGE_EMBED_MODEL, "input": texts}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cfg.GATEWAY_API_KEY:
        headers["Authorization"] = f"Bearer {cfg.GATEWAY_API_KEY}"

    request = urllib.request.Request(
        cfg.OMNIROUTE_URL.rstrip("/") + "/v1/embeddings",
        data=payload, headers=headers, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:  # noqa: S310
            body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise EmbeddingError(f"gateway rejected the embed request (HTTP {exc.code})") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise EmbeddingError(
            f"OmniRoute unreachable at {cfg.OMNIROUTE_URL} — start the gateway first"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EmbeddingError("gateway returned non-JSON") from exc

    data = body.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise EmbeddingError("gateway reply had no usable embeddings — is this an embedding model?")
    try:
        return [row["embedding"] for row in data]
    except (KeyError, TypeError) as exc:
        raise EmbeddingError("gateway reply had no embedding field") from exc


def embeddings_status() -> dict:
    if not cfg.STORAGE_EMBED_MODEL:
        return {"state": "error", "problem": "no STORAGE_EMBED_MODEL configured",
                "gateway": cfg.OMNIROUTE_URL, "model": None}
    try:
        embed_texts(["ping"])
    except EmbeddingError as exc:
        return {"state": "error", "problem": str(exc),
                "gateway": cfg.OMNIROUTE_URL, "model": cfg.STORAGE_EMBED_MODEL}
    return {"state": "ok", "problem": None,
            "gateway": cfg.OMNIROUTE_URL, "model": cfg.STORAGE_EMBED_MODEL}


def _cosine(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# =====================================================================
# INDEXING
# =====================================================================
def _index_note(conn, doc_path: str, content: str, embed: bool) -> int:
    conn.execute("DELETE FROM chunks WHERE doc_path = ?", (doc_path,))
    chunks = chunk_text(content)
    now = time.strftime("%Y-%m-%dT%H:%M:%S")

    vectors = [None] * len(chunks)
    if embed and chunks:
        clean_chunks = [sanitize.sanitize(c)[0] for c in chunks]
        try:
            vectors = embed_texts(clean_chunks)
        except EmbeddingError:
            vectors = [None] * len(chunks)

    for i, text in enumerate(chunks):
        embedding = json.dumps(vectors[i]) if vectors[i] is not None else None
        conn.execute(
            "INSERT INTO chunks (doc_path, chunk_index, text, embedding, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_path, i, text, embedding, now),
        )
    conn.commit()
    return len(chunks)


def reindex() -> dict:
    """Rebuilds the whole index from the notes on disk - the index is a
    cache, this is always safe to run."""
    conn = connect()
    try:
        conn.execute("DELETE FROM chunks")
        conn.commit()
        notes = [d for d in seam.list_docs(NOTES_PREFIX) if d["path"].endswith(".md")]
        total_chunks = 0
        for note in notes:
            content = seam.read_doc(note["path"])
            n = _index_note(conn, note["path"], content, embed=bool(cfg.STORAGE_EMBED_MODEL))
            total_chunks += n
        return {"state": "ok", "notes": len(notes), "chunks": total_chunks}
    finally:
        conn.close()


# =====================================================================
# SEARCH
# =====================================================================
def keyword_search(query: str, limit: int) -> list:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.doc_path, c.text, bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [dict(row) for row in rows]
    except Exception:  # noqa: BLE001 - a malformed FTS query must not 500 (Rule 8)
        return []
    finally:
        conn.close()


def dense_search(query: str, limit: int) -> list:
    try:
        query_vec = embed_texts([query])[0]
    except EmbeddingError:
        return []

    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, doc_path, text, embedding FROM chunks WHERE embedding IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()

    scored = []
    for row in rows:
        vec = json.loads(row["embedding"])
        scored.append((row, _cosine(query_vec, vec)))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [dict(row) for row, _score in scored[:limit]]


def hybrid_search(query: str, limit: int = 10) -> dict:
    """Reciprocal Rank Fusion of keyword + dense (D33). A chunk's score is
    the sum of 1/(k + rank) across whichever lists it appears in - no
    normalization needed, no dependence on either list's raw score scale."""
    K = 60
    keyword_hits = keyword_search(query, limit * 2)
    dense_hits = dense_search(query, limit * 2) if cfg.STORAGE_EMBED_MODEL else []

    fused = {}
    for rank, hit in enumerate(keyword_hits):
        fused.setdefault(hit["id"], {"hit": hit, "score": 0.0})
        fused[hit["id"]]["score"] += 1.0 / (K + rank)
    for rank, hit in enumerate(dense_hits):
        fused.setdefault(hit["id"], {"hit": hit, "score": 0.0})
        fused[hit["id"]]["score"] += 1.0 / (K + rank)

    ranked = sorted(fused.values(), key=lambda entry: entry["score"], reverse=True)[:limit]
    results = [
        {"doc_path": entry["hit"]["doc_path"], "text": entry["hit"]["text"],
         "score": entry["score"]}
        for entry in ranked
    ]

    if not cfg.STORAGE_EMBED_MODEL or not dense_hits:
        return {
            "state": "partial" if keyword_hits or not cfg.STORAGE_EMBED_MODEL else "ok",
            "note": "dense search offline — keyword-only results" if not dense_hits else None,
            "results": results,
        }
    return {"state": "ok", "note": None, "results": results}


# =====================================================================
# ROUTES
# =====================================================================
@router.get(cfg.API_PREFIX + "/knowledge/notes")
def list_notes():
    return {"state": "ok", "notes": seam.list_docs(NOTES_PREFIX)}


@router.put(cfg.API_PREFIX + "/knowledge/notes")
def write_note(path: str, body: dict = Body(...)):
    content = body.get("content")
    if not isinstance(content, str) or not content.strip():
        return JSONResponse(
            status_code=422, content={"state": "error", "problem": "content must be a non-empty string"}
        )
    if not path.startswith(NOTES_PREFIX + "/"):
        return JSONResponse(
            status_code=422,
            content={"state": "error", "problem": f"notes must live under {NOTES_PREFIX}/"},
        )
    if "**Source:**" not in content:
        return JSONResponse(
            status_code=422,
            content={"state": "error", "problem": "a note needs a **Source:** line"},
        )

    try:
        result = seam.write_doc(path, content)
    except seam.PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})

    conn = connect()
    try:
        chunk_count = _index_note(conn, path, content, embed=bool(cfg.STORAGE_EMBED_MODEL))
    finally:
        conn.close()

    return {"state": "ok", **result, "chunks": chunk_count}


@router.get(cfg.API_PREFIX + "/knowledge/search")
def api_search(q: str, limit: int = 10):
    if not q.strip():
        return JSONResponse(status_code=422, content={"state": "error", "problem": "empty query"})
    return hybrid_search(q, limit)


@router.post(cfg.API_PREFIX + "/knowledge/reindex")
def api_reindex():
    return reindex()


@router.get(cfg.API_PREFIX + "/embeddings/status")
def api_embeddings_status():
    return embeddings_status()
