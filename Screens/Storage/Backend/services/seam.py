"""The storage seam (D11.5) - read_doc / write_doc / list_docs / delete_doc
/ search, addressed by logical path.

A logical path IS a real subpath under KAGE_DATA_DIR: validated, then
opened directly. No path->id map, no database of record - the filesystem
is the source of truth, and RAG's index is a rebuildable cache on top.

Honest states (Rule 8): a document that doesn't exist is a 404, never an
empty string; a write always lands or raises - it never silently no-ops.
"""

import os
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import settings_for_storage as cfg

router = APIRouter()

# One path segment: starts with a letter, digit or underscore (a leading
# underscore marks a system file, e.g. _seed_marker.json), then word
# chars/._- , any number of "/segment" repeats, ending in one of the
# allowed extensions. No "..", no leading dot on a segment, no absolute path.
_PATH_RE = re.compile(
    r"^[a-z0-9_][a-z0-9._-]*(?:/[a-z0-9_][a-z0-9._-]*)*$"
)


class PathError(ValueError):
    """A logical path failed validation - always a 422, never a 500."""


def _validate(logical_path: str) -> Path:
    if not logical_path or ".." in logical_path or logical_path.startswith("/"):
        raise PathError("bad path")

    depth = logical_path.count("/") + 1
    if depth > cfg.MAX_PATH_DEPTH:
        raise PathError(f"path too deep (max {cfg.MAX_PATH_DEPTH})")

    ext = Path(logical_path).suffix
    if ext not in cfg.ALLOWED_EXTENSIONS:
        raise PathError(f"extension must be one of {sorted(cfg.ALLOWED_EXTENSIONS)}")

    if not _PATH_RE.match(logical_path):
        raise PathError("path must be lowercase a-z0-9._- per segment")

    resolved = (cfg.KAGE_DATA_DIR / logical_path).resolve()
    root = cfg.KAGE_DATA_DIR.resolve()
    if root not in resolved.parents and resolved != root:
        raise PathError("path escapes the data root")

    return resolved


def read_doc(logical_path: str) -> str:
    """-> the document's text. Raises FileNotFoundError if it doesn't exist."""
    path = _validate(logical_path)
    return path.read_text(encoding="utf-8")


def write_doc(logical_path: str, content: str) -> dict:
    """Atomic write (tmp + os.replace) - a reader never sees a half-written file."""
    path = _validate(logical_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
    stat = path.stat()
    return {"path": logical_path, "bytes": stat.st_size, "updated_at": stat.st_mtime}


def list_docs(prefix: str = "") -> list:
    """Every logical path under KAGE_DATA_DIR/<prefix>, sorted. Never lists .trash."""
    root = cfg.KAGE_DATA_DIR
    base = (root / prefix).resolve() if prefix else root.resolve()
    if root.resolve() not in base.parents and base != root.resolve():
        raise PathError("prefix escapes the data root")
    if not base.is_dir():
        return []

    out = []
    for entry in base.rglob("*"):
        if not entry.is_file():
            continue
        if ".trash" in entry.relative_to(root).parts:
            continue
        if entry.suffix not in cfg.ALLOWED_EXTENSIONS:
            continue
        rel = entry.relative_to(root).as_posix()
        stat = entry.stat()
        out.append({"path": rel, "bytes": stat.st_size, "updated_at": stat.st_mtime})
    return sorted(out, key=lambda d: d["path"])


def delete_doc(logical_path: str) -> dict:
    """Moves to KAGE_DATA_DIR/.trash/<date>/ - recoverable, never annihilation (Rule 8)."""
    path = _validate(logical_path)
    if not path.is_file():
        raise FileNotFoundError(logical_path)

    date = time.strftime("%Y-%m-%d")
    trash_dir = cfg.TRASH_DIR / date
    trash_dir.mkdir(parents=True, exist_ok=True)
    dest = trash_dir / f"{int(time.time() * 1000)}-{path.name}"
    os.replace(path, dest)
    return {"path": logical_path, "trashed_to": str(dest.relative_to(cfg.KAGE_DATA_DIR))}


def search(query: str, limit: int = 20) -> list:
    """Keyword search over doc contents - a plain substring scan.

    This is the seam's own fallback search, always available even when
    RAG's FTS5 index is offline. It is not ranked, it is not fuzzy - it
    is honest: every hit really contains the query, case-insensitively.
    """
    query_lower = query.lower()
    hits = []
    for doc in list_docs():
        full = cfg.KAGE_DATA_DIR / doc["path"]
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if query_lower in text.lower():
            idx = text.lower().find(query_lower)
            start = max(0, idx - 40)
            snippet = text[start:idx + len(query) + 40].replace("\n", " ")
            hits.append({"path": doc["path"], "snippet": snippet})
        if len(hits) >= limit:
            break
    return hits


# =====================================================================
# ROUTES
# =====================================================================
@router.get(cfg.API_PREFIX + "/docs")
def api_list_docs(prefix: str = ""):
    try:
        return {"state": "ok", "docs": list_docs(prefix)}
    except PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})


@router.get(cfg.API_PREFIX + "/doc")
def api_read_doc(path: str):
    try:
        content = read_doc(path)
    except PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})
    except FileNotFoundError:
        return JSONResponse(
            status_code=404, content={"state": "error", "problem": "no such document"}
        )
    return {"state": "ok", "path": path, "content": content}


@router.put(cfg.API_PREFIX + "/doc")
def api_write_doc(path: str, body: dict):
    content = body.get("content")
    if not isinstance(content, str):
        return JSONResponse(
            status_code=422, content={"state": "error", "problem": "content must be a string"}
        )
    try:
        result = write_doc(path, content)
    except PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})
    return {"state": "ok", **result}


@router.delete(cfg.API_PREFIX + "/doc")
def api_delete_doc(path: str):
    try:
        result = delete_doc(path)
    except PathError as exc:
        return JSONResponse(status_code=422, content={"state": "error", "problem": str(exc)})
    except FileNotFoundError:
        return JSONResponse(
            status_code=404, content={"state": "error", "problem": "no such document"}
        )
    return {"state": "ok", **result}


@router.get(cfg.API_PREFIX + "/search")
def api_search(q: str, limit: int = 20):
    if not q.strip():
        return JSONResponse(
            status_code=422, content={"state": "error", "problem": "empty query"}
        )
    return {"state": "ok", "query": q, "results": search(q, limit)}
