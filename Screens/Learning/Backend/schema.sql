-- KAGE Learning OS — schema v2 (D16)
-- Tracks are dynamic (no A/B enum). Rooms hold 4-beat steps; checkpoints
-- record attempts; the ledger is append-only ground truth for Insights.

CREATE TABLE IF NOT EXISTS tracks (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL,
  color      TEXT NOT NULL DEFAULT 'ember',        -- ember | jade | violet | amber
  position   INTEGER NOT NULL DEFAULT 0,
  archived   INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS modules (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  track_id  INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
  name      TEXT NOT NULL,
  position  INTEGER NOT NULL DEFAULT 0,
  archived  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rooms (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  module_id   INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  position    INTEGER NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'todo',        -- todo | learning | done
  archived    INTEGER NOT NULL DEFAULT 0,
  est_minutes INTEGER NOT NULL DEFAULT 20,
  feynman     TEXT,                                -- "explain it back" text
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS steps (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id       INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  position      INTEGER NOT NULL DEFAULT 0,
  title         TEXT NOT NULL,
  minutes       INTEGER NOT NULL DEFAULT 8,
  explain       TEXT,
  realworld     TEXT,
  lab_objective TEXT,
  lab_env       TEXT,
  lab_link      TEXT,
  lab_checklist TEXT NOT NULL DEFAULT '[]',        -- JSON array of strings
  lab_proof     TEXT,                              -- user-pasted proof
  status        TEXT NOT NULL DEFAULT 'todo'       -- todo | current | done
);

CREATE TABLE IF NOT EXISTS checkpoints (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  step_id      INTEGER NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
  position     INTEGER NOT NULL DEFAULT 0,
  kind         TEXT NOT NULL,                      -- mcq | freetext
  question     TEXT NOT NULL,
  options      TEXT NOT NULL DEFAULT '[]',         -- JSON array (mcq)
  answer_idx   INTEGER,                            -- correct index (mcq)
  model_answer TEXT                                 -- for freetext self-check
);

CREATE TABLE IF NOT EXISTS attempts (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  checkpoint_id INTEGER NOT NULL REFERENCES checkpoints(id) ON DELETE CASCADE,
  answer        TEXT,
  correct       INTEGER,                           -- 1 | 0 | NULL (ungraded)
  self_grade    TEXT,                              -- matched | off | skipped
  ts            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cards (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id INTEGER REFERENCES rooms(id) ON DELETE CASCADE,
  front   TEXT NOT NULL,
  part1   TEXT, part2 TEXT, part3 TEXT, part4 TEXT, part5 TEXT,
  tag     TEXT DEFAULT 'core',
  tether  TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id          INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
  due_date         TEXT NOT NULL,
  ease             REAL NOT NULL DEFAULT 2.5,
  last_result      TEXT,
  last_graded_date TEXT,
  status           TEXT NOT NULL DEFAULT 'new'     -- new | active
);

CREATE TABLE IF NOT EXISTS sessions (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id         INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
  started_at      TEXT,
  ended_at        TEXT,
  planned_minutes INTEGER,
  actual_minutes  INTEGER,
  confidence      INTEGER,                          -- 1-5 self-rating at finish
  notes           TEXT
);

CREATE TABLE IF NOT EXISTS notes (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id    INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
  step_id    INTEGER REFERENCES steps(id) ON DELETE SET NULL,
  body       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ledger (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  ts    TEXT NOT NULL DEFAULT (datetime('now')),
  kind  TEXT NOT NULL,                             -- session|attempt|room|path|review|note|crew|system
  ref   TEXT,
  text  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proposals (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  agent      TEXT NOT NULL,
  kind       TEXT NOT NULL,                        -- reorder|cards|relearn|note
  summary    TEXT NOT NULL,
  detail     TEXT,
  status     TEXT NOT NULL DEFAULT 'pending',      -- pending|approved|declined
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  ts      TEXT NOT NULL DEFAULT (datetime('now')),
  agent   TEXT NOT NULL,
  text    TEXT NOT NULL,
  source  TEXT NOT NULL DEFAULT 'sample'           -- sample | live
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_modules_track ON modules(track_id, position);
CREATE INDEX IF NOT EXISTS idx_rooms_module  ON rooms(module_id, position);
CREATE INDEX IF NOT EXISTS idx_steps_room    ON steps(room_id, position);
CREATE INDEX IF NOT EXISTS idx_ckpts_step    ON checkpoints(step_id, position);
CREATE INDEX IF NOT EXISTS idx_reviews_due   ON reviews(due_date, status);
