"""The RAG index (D11.5.2) - a rebuildable cache, never a copy of record.

Sourced Markdown notes live as real files under KAGE_DATA_DIR, through the
seam. This sqlite file only indexes them for fast search: FTS5 for keyword,
a plain JSON-encoded vector column for dense. Delete it and `reindex`
rebuilds it from the notes - nothing here is data of record.
"""

import sqlite3

import settings_for_storage as cfg

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_path    TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text        TEXT NOT NULL,
    embedding   TEXT,              -- JSON list[float], NULL when not yet embedded
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_path);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);

-- Keep the FTS shadow table in sync with chunks (Rule 8 - a stale index
-- that silently drifts from the real chunks is worse than none).
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
"""


def connect() -> sqlite3.Connection:
    cfg.RAG_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cfg.RAG_INDEX_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
