"""Local retrieval over bundled PUBLIC educational content only.

No FAISS, no sentence-transformers, no torch — a dependency-free TF-IDF cosine
index built from Markdown files under `backend/content/`. FAISS + a real
embedding model are a drop-in future swap behind `retrieve()`.

SECURITY CONTRACT (Phase 6): the vector store is built EXCLUSIVELY from files
under `CONTENT_DIR`. `ingest()` refuses any path outside it. Nothing in this
module ever opens the database, so no transaction / account / holding / lender
string can reach a chunk. `assert_public()` is a second, belt-and-braces filter.
"""
from __future__ import annotations

import math
import pathlib
import re
import threading

CONTENT_DIR = (pathlib.Path(__file__).resolve().parent.parent / "content")

_WORD = re.compile(r"[a-z0-9]+")
# defence in depth — content is already public files, but never emit a chunk that
# somehow contains something account-shaped.
_DENY = re.compile(r"\b(a/c|acct|account\s*no|ifsc|pan\b|[0-9]{9,})\b", re.I)

_lock = threading.Lock()
_index: "_Index | None" = None


def _tok(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def chunk_text(text: str, size: int = 120, overlap: int = 20) -> list[str]:
    """Chunk by word count (size/overlap in words). Small docs -> one chunk."""
    words = text.split()
    if len(words) <= size:
        return [text.strip()] if text.strip() else []
    out = []
    step = max(1, size - overlap)
    for i in range(0, len(words), step):
        piece = " ".join(words[i:i + size]).strip()
        if piece:
            out.append(piece)
        if i + size >= len(words):
            break
    return out


def assert_public(text: str) -> None:
    if _DENY.search(text or ""):
        raise ValueError("refusing to ingest text that looks like account data")


class _Index:
    def __init__(self) -> None:
        self.chunks: list[dict] = []          # {text, source, title}
        self.vecs: list[dict[str, float]] = []  # sparse tf-idf per chunk
        self.idf: dict[str, float] = {}

    def build(self, docs: list[dict]) -> None:
        # docs: [{title, source, text}]
        raw_chunks: list[dict] = []
        for d in docs:
            for c in chunk_text(d["text"]):
                assert_public(c)
                raw_chunks.append({"text": c, "source": d["source"], "title": d["title"]})
        self.chunks = raw_chunks
        n = len(raw_chunks) or 1
        df: dict[str, int] = {}
        tfs: list[dict[str, float]] = []
        for c in raw_chunks:
            toks = _tok(c["text"])
            tf: dict[str, float] = {}
            for t in toks:
                tf[t] = tf.get(t, 0.0) + 1.0
            for t in tf:
                df[t] = df.get(t, 0) + 1
            tfs.append(tf)
        self.idf = {t: math.log((n + 1) / (dfi + 1)) + 1.0 for t, dfi in df.items()}
        self.vecs = [self._vec(tf) for tf in tfs]

    def _vec(self, tf: dict[str, float]) -> dict[str, float]:
        v = {t: (1.0 + math.log(c)) * self.idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def query(self, text: str, k: int) -> list[dict]:
        tf: dict[str, float] = {}
        for t in _tok(text):
            tf[t] = tf.get(t, 0.0) + 1.0
        q = self._vec(tf)
        scored = []
        for i, cv in enumerate(self.vecs):
            small, big = (q, cv) if len(q) < len(cv) else (cv, q)
            s = sum(val * big.get(t, 0.0) for t, val in small.items())
            if s > 0:
                scored.append((s, i))
        scored.sort(reverse=True)
        return [
            {"text": self.chunks[i]["text"], "source": self.chunks[i]["source"],
             "title": self.chunks[i]["title"], "score": round(sc, 4)}
            for sc, i in scored[:k]
        ]


def _title_from(path: pathlib.Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def _load_docs() -> list[dict]:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    docs = []
    for p in sorted(CONTENT_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        docs.append({"title": _title_from(p, text), "source": p.name, "text": text})
    return docs


def _ensure_index() -> "_Index":
    global _index
    with _lock:
        if _index is None:
            idx = _Index()
            idx.build(_load_docs())
            _index = idx
        return _index


def reset_index() -> None:
    global _index
    with _lock:
        _index = None


def ingest(path: str) -> int:
    """Allow-listed ingest: `path` MUST resolve to a file under CONTENT_DIR.
    Returns the number of chunks now in the index."""
    rp = pathlib.Path(path).resolve()
    if CONTENT_DIR not in rp.parents:
        raise ValueError(f"refusing to ingest outside {CONTENT_DIR}: {rp}")
    reset_index()
    return len(_ensure_index().chunks)


def retrieve(query: str, k: int = 5) -> list[dict]:
    return _ensure_index().query(query, k)


def topics() -> list[dict]:
    docs = _load_docs()
    return [{"id": i + 1, "slug": d["source"][:-3], "title": d["title"]}
            for i, d in enumerate(docs)]


def topic(topic_id: int) -> dict | None:
    docs = _load_docs()
    if topic_id < 1 or topic_id > len(docs):
        return None
    d = docs[topic_id - 1]
    related = [r for r in retrieve(d["title"], 4) if r["source"] != d["source"]][:3]
    return {"id": topic_id, "slug": d["source"][:-3], "title": d["title"],
            "content": d["text"], "related": related}


def topic_by_slug(slug: str) -> dict | None:
    for t in topics():
        if t["slug"] == slug:
            return topic(t["id"])
    return None
