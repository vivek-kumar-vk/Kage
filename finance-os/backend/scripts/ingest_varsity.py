"""One-shot ingestion of the bundled PUBLIC learning content.

`backend/content/*.md` ships with the repo (public primers only). This script
just rebuilds the local retrieval index from them. Safe to run repeatedly.
"""
from __future__ import annotations

import sys

from services import rag


def main() -> int:
    rag.CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    md = sorted(rag.CONTENT_DIR.glob("*.md"))
    if not md:
        print(f"no markdown under {rag.CONTENT_DIR} — nothing to ingest")
        return 1
    rag.reset_index()
    n = 0
    for p in md:
        n = rag.ingest(str(p))
    print(f"ingested {len(md)} docs -> {n} chunks in the index")
    return 0


if __name__ == "__main__":
    sys.exit(main())
