"""Spine projection (K-04): replay events_*.jsonl into spine.sqlite, idempotently.

Readers call project() (pull-through); there is no scheduler or thread.
Byte offsets live in projector_state so a crash mid-file replays the file.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from Shared_By_All_Screens import spine  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def db_path() -> Path:
    return spine.spine_dir() / "spine.sqlite"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def apply_migrations(conn: sqlite3.Connection) -> int:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        if int(path.name[:4]) <= version:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            conn.executescript("BEGIN;\n" + sql + "\nCOMMIT;")
        except sqlite3.Error:
            conn.rollback()
            raise
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    return version


def _replace_rows(conn: sqlite3.Connection, table: str, path: Path, columns: tuple) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list")
    placeholders = ", ".join("?" for _ in columns)
    with conn:
        conn.execute(f"DELETE FROM {table}")
        for row in data:
            conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                tuple(row[column] for column in columns),
            )
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def load_thresholds(conn: sqlite3.Connection, path: Path) -> int:
    return _replace_rows(conn, "freshness_thresholds", path, ("source", "max_age_hours", "data_lag_hours"))


def load_prices(conn: sqlite3.Connection, path: Path) -> int:
    return _replace_rows(conn, "model_prices", path, ("model", "provider", "usd_per_1k_in", "usd_per_1k_out"))


def project(now: datetime | None = None) -> dict:
    conn = connect()
    try:
        apply_migrations(conn)
        rows_added = 0
        bad_lines = 0
        files = 0
        directory = spine.spine_dir()
        for jsonl in sorted(directory.glob("events_*.jsonl"), key=lambda p: p.name):
            state = conn.execute(
                "SELECT bytes_done FROM projector_state WHERE src_file=?", (jsonl.name,)
            ).fetchone()
            offset = state["bytes_done"] if state else 0
            size = jsonl.stat().st_size
            if size <= offset:
                continue
            files += 1
            with open(jsonl, "rb") as fh:
                fh.seek(0)
                prior_newlines = fh.read(offset).count(b"\n")
                fh.seek(offset)
                chunk = fh.read()
            if not chunk.endswith(b"\n"):
                cut = chunk.rfind(b"\n")
                if cut == -1:
                    continue  # no complete line yet; leave bytes_done where it is
                chunk = chunk[: cut + 1]

            insert_rows = []
            bad_here = 0
            line_no = prior_newlines
            position = 0
            while True:
                end = chunk.find(b"\n", position)
                if end == -1:
                    break
                raw = chunk[position:end]
                line_no += 1
                try:
                    event = json.loads(raw.decode("utf-8"))
                    insert_rows.append(
                        (
                            event["id"], event["ts"], event["producer"], event["type"],
                            event["subject"],
                            json.dumps(event["payload"], ensure_ascii=False, separators=(",", ":")),
                            event.get("model"), event.get("tokens_in"), event.get("tokens_out"),
                            event.get("cost_usd"), event.get("correlation_id"),
                            jsonl.name, line_no,
                        )
                    )
                except Exception:
                    bad_here += 1  # never guessed at; its bytes are still consumed
                position = end + 1
            new_offset = offset + position

            with conn:  # one transaction per file: rows + offset commit together
                for row in insert_rows:
                    cur = conn.execute(
                        "INSERT OR IGNORE INTO events "
                        "(id, ts, producer, type, subject, payload, model, tokens_in, "
                        " tokens_out, cost_usd, correlation_id, src_file, src_line) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        row,
                    )
                    rows_added += cur.rowcount
                conn.execute(
                    "INSERT INTO projector_state (src_file, bytes_done) VALUES (?,?) "
                    "ON CONFLICT(src_file) DO UPDATE SET bytes_done=excluded.bytes_done",
                    (jsonl.name, new_offset),
                )
            bad_lines += bad_here
        lag = projector_lag_bytes()
        projected_at = (now or datetime.now(spine.IST)).isoformat(timespec="seconds")
        return {
            "rows_added": rows_added,
            "files": files,
            "lag_bytes": lag,
            "bad_lines": bad_lines,
            "projected_at": projected_at,
        }
    finally:
        conn.close()


def projector_lag_bytes() -> int:
    conn = connect()
    try:
        total = 0
        for jsonl in sorted(spine.spine_dir().glob("events_*.jsonl"), key=lambda p: p.name):
            state = conn.execute(
                "SELECT bytes_done FROM projector_state WHERE src_file=?", (jsonl.name,)
            ).fetchone()
            total += jsonl.stat().st_size - (state["bytes_done"] if state else 0)
        return total
    finally:
        conn.close()
