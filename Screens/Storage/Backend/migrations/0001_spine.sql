-- K-04: spine event store, projector state, thresholds, prices, views.
-- One deviation from BUILD_ORDER.md's verbatim SQL, proven empirically on
-- SQLite 3.49.1: julianday('now','+05:30') is now-UTC shifted +5.5h, while
-- julianday of an event stamp carrying '+05:30' normalizes to true UTC, so
-- the ticket's mixed form overstates age by 5.5h in production. Plain
-- julianday('now') against the offset-bearing stamp is consistent and
-- reproduces EV-FRESH-01's pinned 63.0h exactly.
CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, ts TEXT NOT NULL, producer TEXT NOT NULL, type TEXT NOT NULL, subject TEXT NOT NULL, payload TEXT NOT NULL, model TEXT, tokens_in INTEGER, tokens_out INTEGER, cost_usd REAL, correlation_id TEXT, src_file TEXT NOT NULL, src_line INTEGER NOT NULL);
CREATE INDEX idx_events_type_subject_seq ON events(type, subject, seq DESC);
CREATE INDEX idx_events_ts ON events(ts);
CREATE TABLE projector_state (src_file TEXT PRIMARY KEY, bytes_done INTEGER NOT NULL DEFAULT 0);
CREATE TABLE freshness_thresholds (source TEXT PRIMARY KEY, max_age_hours INTEGER NOT NULL, data_lag_hours INTEGER NOT NULL);
CREATE TABLE model_prices (model TEXT PRIMARY KEY, provider TEXT NOT NULL, usd_per_1k_in REAL NOT NULL, usd_per_1k_out REAL NOT NULL);
CREATE VIEW v_source_freshness AS
  WITH att AS (SELECT subject AS source, MAX(ts) AS last_attempt_at FROM events WHERE type='fetch_attempted' GROUP BY subject),
       ok  AS (SELECT subject AS source, MAX(seq) AS seq FROM events WHERE type='fetch_succeeded' GROUP BY subject),
       okrow AS (SELECT e.subject AS source, e.ts AS last_ok_at, json_extract(e.payload,'$.data_as_of') AS data_as_of FROM events e JOIN ok ON ok.seq=e.seq),
       fail AS (SELECT subject AS source, MAX(seq) AS seq FROM events WHERE type='fetch_failed' GROUP BY subject),
       failrow AS (SELECT e.subject AS source, e.ts AS last_fail_at, json_extract(e.payload,'$.error') AS last_error FROM events e JOIN fail ON fail.seq=e.seq)
  SELECT t.source, att.last_attempt_at, okrow.last_ok_at,
         CASE WHEN failrow.last_fail_at > COALESCE(okrow.last_ok_at,'') THEN failrow.last_error ELSE NULL END AS last_error,
         okrow.data_as_of, t.max_age_hours, t.data_lag_hours,
         CASE WHEN okrow.last_ok_at IS NULL THEN NULL ELSE ROUND((julianday('now') - julianday(okrow.last_ok_at)) * 24.0, 1) END AS age_hours,
         CASE WHEN okrow.last_ok_at IS NULL THEN 1 WHEN (julianday('now') - julianday(okrow.last_ok_at)) * 24.0 > t.max_age_hours THEN 1 ELSE 0 END AS stale,
         CASE WHEN okrow.last_ok_at IS NULL THEN NULL ELSE datetime(okrow.last_ok_at, '+' || t.max_age_hours || ' hours') END AS stale_since,
         CASE WHEN okrow.data_as_of IS NULL THEN 0 WHEN (julianday(okrow.last_ok_at) - julianday(okrow.data_as_of)) * 24.0 > t.data_lag_hours THEN 1 ELSE 0 END AS lagging
  FROM freshness_thresholds t LEFT JOIN att USING(source) LEFT JOIN okrow USING(source) LEFT JOIN failrow USING(source);
CREATE VIEW v_llm_spend_day AS SELECT substr(ts,1,10) AS day, COUNT(*) AS calls, SUM(tokens_in) AS tokens_in, SUM(tokens_out) AS tokens_out, SUM(cost_usd) AS cost_usd, SUM(CASE WHEN json_extract(payload,'$.tier')='T2' THEN 1 ELSE 0 END) AS calls_t2 FROM events WHERE type='llm_call' GROUP BY day;
CREATE VIEW v_llm_spend_agent_day AS SELECT substr(ts,1,10) AS day, subject, SUM(cost_usd) AS cost_usd, COUNT(*) AS calls FROM events WHERE type='llm_call' GROUP BY day, subject;
CREATE VIEW v_unfinished_count AS SELECT COUNT(*) AS count FROM (SELECT o.subject FROM events o WHERE o.type='ticket_opened' AND NOT EXISTS (SELECT 1 FROM events c WHERE c.type='ticket_closed' AND c.subject=o.subject AND c.seq>o.seq));
CREATE VIEW v_latest_numbers AS SELECT e.subject AS key, json_extract(e.payload,'$.value') AS value, json_extract(e.payload,'$.unit') AS unit, json_extract(e.payload,'$.data_as_of') AS data_as_of, e.ts FROM events e JOIN (SELECT subject, MAX(seq) AS seq FROM events WHERE type='number_set' GROUP BY subject) m ON m.seq=e.seq;
CREATE VIEW v_decisions_today AS SELECT p.subject AS decision_id, json_extract(p.payload,'$.rank') AS rank, json_extract(p.payload,'$.kind') AS kind, json_extract(p.payload,'$.severity') AS severity, json_extract(p.payload,'$.score') AS score, json_extract(p.payload,'$.status') AS status, json_extract(p.payload,'$.text') AS text, json_extract(p.payload,'$.why') AS why, p.model, EXISTS(SELECT 1 FROM events t WHERE t.type='decision_taken' AND t.subject=p.subject) AS taken, EXISTS(SELECT 1 FROM events d WHERE d.type='decision_dismissed' AND d.subject=p.subject) AS dismissed, substr(p.ts,1,10) AS day FROM events p WHERE p.type='decision_proposed';
CREATE VIEW v_watchdog_latest AS SELECT e.subject AS "check", json_extract(e.payload,'$.verdict') AS verdict, json_extract(e.payload,'$.detail') AS detail, e.ts FROM events e JOIN (SELECT subject, MAX(seq) AS seq FROM events WHERE type='watchdog_verdict' GROUP BY subject) m ON m.seq=e.seq;
CREATE VIEW v_screens AS SELECT e.subject AS screen, json_extract(e.payload,'$.port') AS port, CASE WHEN e.type='screen_started' THEN 'up' ELSE 'down' END AS state, e.ts FROM events e JOIN (SELECT subject, MAX(seq) AS seq FROM events WHERE type IN ('screen_started','screen_stopped') GROUP BY subject) m ON m.seq=e.seq;
PRAGMA user_version = 1;
