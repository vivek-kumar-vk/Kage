-- OFFICE screen - job-hunt workbench (M7, D17.4/D17.5)
-- office.db is gitignored: it holds real company names, notes, packs.

CREATE TABLE IF NOT EXISTS applications (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  company    TEXT NOT NULL,
  role       TEXT NOT NULL,
  portal     TEXT,
  link       TEXT,
  stage      TEXT NOT NULL DEFAULT 'saved',   -- saved|applied|screen|interview|offer|reject
  notes      TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS interviews (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  application_id INTEGER REFERENCES applications(id) ON DELETE SET NULL,
  company        TEXT NOT NULL,
  role           TEXT,
  round          TEXT,                         -- "Recruiter screen", "Tech round 1", ...
  scheduled_at   TEXT NOT NULL,                -- ISO: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM'
  mode           TEXT,                         -- phone|video|onsite
  prep_pack      TEXT,                         -- free markdown: likely Qs, STAR notes
  outcome        TEXT NOT NULL DEFAULT 'pending',  -- pending|passed|failed|withdrawn
  created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS work_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  log_date   TEXT NOT NULL,                    -- YYYY-MM-DD
  tech       TEXT,                             -- free-text tag, e.g. "Bindplane"
  summary    TEXT NOT NULL,
  detail     TEXT,
  minutes    INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Skills tracked for the resume. `defensible` / `good_easy` / `rooms_tagged`
-- are MIRRORED from Learning's /api/learning/skills - never written by hand.
CREATE TABLE IF NOT EXISTS skills (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  name           TEXT NOT NULL UNIQUE,
  skill_tag      TEXT NOT NULL,                -- tag used on Learning rooms
  on_resume      INTEGER NOT NULL DEFAULT 0,   -- the owner's claim
  defensible     INTEGER NOT NULL DEFAULT 0,   -- mirrored: >=2 good/easy
  good_easy      INTEGER NOT NULL DEFAULT 0,   -- mirrored
  rooms_tagged   INTEGER NOT NULL DEFAULT 0,   -- mirrored
  learning_state TEXT NOT NULL DEFAULT 'never checked',
  fetched_at     TEXT
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_apps_stage   ON applications(stage);
CREATE INDEX IF NOT EXISTS idx_iv_sched     ON interviews(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_wl_date      ON work_log(log_date);
