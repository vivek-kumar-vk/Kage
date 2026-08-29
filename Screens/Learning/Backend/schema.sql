CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    stack_area TEXT NOT NULL CHECK(stack_area IN ('core','drip','capture')),
    status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','learning','done')),
    track TEXT NOT NULL DEFAULT 'A' CHECK(track IN ('A','B')),
    position INTEGER DEFAULT 0,
    progress REAL DEFAULT 0.0,
    target_date TEXT,
    source_doc TEXT,
    "group" TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    session_date TEXT NOT NULL,
    minutes INTEGER NOT NULL DEFAULT 0,
    confidence INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS week_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL UNIQUE,
    focus_a TEXT,
    focus_b TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER REFERENCES topics(id),
    front TEXT NOT NULL,
    part1 TEXT NOT NULL,
    part2 TEXT NOT NULL,
    part3 TEXT NOT NULL,
    part4 TEXT NOT NULL,
    part5 TEXT NOT NULL,
    tag TEXT NOT NULL DEFAULT 'core' CHECK(tag IN ('core','drip','capture')),
    tether TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES cards(id),
    due_date TEXT NOT NULL,
    ease REAL NOT NULL DEFAULT 2.5,
    last_result TEXT,
    last_graded_date TEXT,
    status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','active'))
);
