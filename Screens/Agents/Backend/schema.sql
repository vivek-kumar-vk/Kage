CREATE TABLE IF NOT EXISTS ideas (
    id          TEXT PRIMARY KEY,
    enh_key     TEXT UNIQUE,
    title       TEXT NOT NULL,
    note        TEXT DEFAULT '',
    area        TEXT DEFAULT '',
    source      TEXT CHECK (source IN ('user','ai')) DEFAULT 'user',
    status      TEXT CHECK (status IN ('ideas','todo','in_progress','done')) DEFAULT 'ideas',
    priority    TEXT CHECK (priority IN ('low','medium','high','critical')) DEFAULT 'medium',
    order_index REAL,
    added_at    TEXT,
    updated_at  TEXT
);

CREATE TABLE IF NOT EXISTS comments (
    id         TEXT PRIMARY KEY,
    idea_id    TEXT REFERENCES ideas(id),
    text       TEXT NOT NULL,
    author     TEXT CHECK (author IN ('user','ai')) DEFAULT 'user',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS rooms (
    id         TEXT PRIMARY KEY,
    kind       TEXT CHECK (kind IN ('board','agent','system')) NOT NULL,
    name       TEXT NOT NULL,
    agent_name TEXT,
    position   REAL,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id         TEXT PRIMARY KEY,
    room_id    TEXT NOT NULL REFERENCES rooms(id),
    author     TEXT CHECK (author IN ('user','agent','system')) NOT NULL DEFAULT 'user',
    agent_name TEXT,
    body       TEXT NOT NULL,
    idea_id    TEXT REFERENCES ideas(id),
    created_at TEXT
);

-- Pixel Office event stream (D12). Append-only; SSE replays the tail then goes live.
-- sim = 1 marks generated ambient activity (demo), never presented as real.
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT,
    source     TEXT,               -- run | demo | board | ui
    sim        INTEGER DEFAULT 0,
    agent_name TEXT,
    department TEXT,
    type       TEXT,               -- started | thinking | output | done | error | note
    text       TEXT DEFAULT '',
    artifact   TEXT
);
