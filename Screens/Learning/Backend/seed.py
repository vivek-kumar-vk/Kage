"""Seeds the Learning OS v3 board (D17 — honest zero).

Order of duty, every server start:
  1. d17_zero()  — one-time (guarded by the 'd17_zero_done' settings marker):
                   every demo row is wiped and the board is re-seeded as the
                   two D17 tracks — real titles, EMPTY steps. A room with no
                   steps is "planned, not taught" and says so; nothing records
                   work that has not happened. Back up learning.db out of band
                   before removing the marker.
  2. board()     — fresh installs (no tracks at all): the same D17 board.

There is no dummy lesson content and no fake history in this module — D17.1.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db import connect

IST = timezone(timedelta(hours=5, minutes=30))

DEFAULT_SETTINGS = (
    ("weekly_budget_minutes", "450"),
    ("default_session_minutes", "25"),
    ("grace_days", "1"),
)

# ---------------------------------------------------------------- the board
# Two tracks (D17.2), each opening at ground 0. Detection engineering does not
# get its own track: job-currency pieces live where they pay, the rest parks
# archived inside Track 2. Nothing deleted, nothing hidden.

TRACKS = [
    {
        "name": "Project → DevOps",
        "color": "ember",
        "modules": [
            ("Ground Zero (project)", 0, [
                "Git & GitHub from basics",
                "Linux shell from basics",
                "Networking the project uses (DNS, HTTP, ports, localhost)",
            ]),
            # D21.1 — structure only, no lessons (D46). Kept in sync with
            # D21_1_ROOMS below, which back-fills it into an existing board.
            ("Two runtimes, one launcher", 0, [
                "Why two runtimes — a runtime per service",
                "The HTTP seam — no imports across the line",
                "One port per screen, written once",
                "One launcher starts both runtimes",
            ]),
            ("AI agenting", 0, [
                "Agent anatomy — registry, roster, profiles",
                "Event-driven agents — SSE streams + append-only events",
                "Proposals & approve-gates — agents that never act unilaterally",
                "MCP — Model Context Protocol (dt-agent pattern)",
                "Hermes agent",
                "DeepSeek harness",
            ]),
            ("Multi-model routing", 0, [
                "Local vs open vs cloud vs paid — trade-offs",
                "OmniRoute — one gateway seam, keys, health",
                "Cost routing — cheap by default, escalate on demand",
            ]),
            ("RAG architecture", 0, [
                "Chunking & overlap",
                "Embeddings & cosine (nomic-embed-text)",
                "RAG on the Storage seam (D11.3 pattern)",
                "Finance-data RAG — Drive + SQLite → RAG → agent",
            ]),
            ("DevOps", 0, [
                "Containers — Dockerize a KAGE screen",
                "CI/CD for this repo",
                "Cloud concepts, early",
            ]),
            ("LLM observability", 0, [
                "Arize — tracing your own agents",
            ]),
        ],
    },
    {
        "name": "Observability (job-driven)",
        "color": "jade",
        "modules": [
            ("Ground Zero (observability)", 0, [
                "Networking from ground 0 (TCP/IP, ports & protocols)",
                "Linux from ground 0 (filesystem, processes, services, logs)",
            ]),
            ("Splunk (the hunt)", 0, [
                "Architecture + component roles (SH, Indexer, UF, HF, DS, CM, LM)",
                "Data ingestion & log onboarding (UF vs HF, inputs.conf, HEC/syslog)",
                "Parsing → indexing pipeline (line breaking, timestamps, sourcetype)",
                "Configuration precedence + btool",
                "Buckets & retention (hot/warm/cold/frozen/thawed)",
                "User management — roles, capabilities, auth, permissions",
                "SPL fundamentals",
                "Knowledge objects (searches, alerts, dashboards, macros, lookups)",
                "Deployment basics — deployment server, forwarder management",
                "Troubleshooting playbook",
                "Configuration files reference",
                "Clustering (indexer + SHC, captain, replication/search factor)",
                "SmartStore",
                "ACS",
                "Monitoring Console (aware)",
                "Splunk Cloud basics (aware)",
                "Victoria experience (aware)",
                "Upgrade process (aware)",
                "Splunk 10.x currency (aware)",
                "Enterprise Security (studied last)",
            ]),
            ("Dynatrace (the differentiator)", 0, [
                "DQL — the query language",
                "DPL — the pattern language",
                "OneAgent — deployment & host groups",
                "OpenPipeline → Grail (ingestion, parsing, bucket routing)",
                "The migration story — SPL↔DQL parity validation",
                "Bindplane (day job)",
                "Davis AI & problem detection (aware)",
            ]),
            ("Real observability", 0, [
                "Signals — logs, metrics, traces",
                "SLOs & error budgets",
                "Alert design & on-call hygiene",
                "AWS identity + logging (IAM, CloudTrail/GuardDuty/CloudWatch)",
            ]),
            ("Open-source stack labs (on KAGE)", 0, [
                "Prometheus — scrape KAGE's screens",
                "Grafana — dashboards over real data",
                "OpenTelemetry — instrument a FastAPI service",
                "Bindplane on KAGE — pipeline telemetry",
            ]),
            ("Deferred (after hired)", 0, [
                "ITSI",
                "DSP, KV Store, REST API, Python SDK, indexer tuning",
            ]),
            # Dissolved Track B: visible, reviewable, never scheduled (D17.2).
            ("Detection (parked)", 1, [
                "Linux security telemetry (auditd, journald, syslog, PAM, FIM)",
                "Windows telemetry (Sysmon, Event Logs, PowerShell logging)",
                "MITRE ATT&CK literacy",
                "Sigma end-to-end (pySigma, sigma-cli, SPL + KQL backends)",
                "Emulate → detect loop (Atomic Red Team, detection lifecycle)",
                "Cloud attack/detect labs (flaws.cloud, CloudGoat, Stratus Red Team)",
                "Cloud-native + identity depth (K8s/Docker security, OAuth2/JWT/SAML, CI/CD)",
                "AWS Security Specialty (aware)",
                "Artifacts (detection-rules repo, security-telemetry capstone)",
            ]),
        ],
    },
]


def ist_now() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")


def _insert_board(cur) -> None:
    for t_pos, track in enumerate(TRACKS):
        cur.execute(
            "INSERT INTO tracks (name, color, position) VALUES (?,?,?)",
            (track["name"], track["color"], t_pos),
        )
        track_id = cur.lastrowid
        for m_pos, (module_name, archived, rooms) in enumerate(track["modules"]):
            cur.execute(
                "INSERT INTO modules (track_id, name, position, archived) VALUES (?,?,?,?)",
                (track_id, module_name, m_pos, archived),
            )
            module_id = cur.lastrowid
            for r_pos, room_name in enumerate(rooms):
                cur.execute(
                    "INSERT INTO rooms (module_id, name, position) VALUES (?,?,?)",
                    (module_id, room_name, r_pos),
                )


def board(cur) -> bool:
    """Fresh installs: create the D17 board when no tracks exist."""
    if cur.execute("SELECT COUNT(*) c FROM tracks").fetchone()["c"]:
        return False
    _insert_board(cur)
    rooms = cur.execute("SELECT COUNT(*) c FROM rooms").fetchone()["c"]
    cur.execute(
        "INSERT INTO ledger (ts, kind, ref, text) VALUES (?,?,?,?)",
        (ist_now(), "system", None,
         f"D17 board created — {len(TRACKS)} tracks, {rooms} rooms, no lessons written yet"),
    )
    return True


HISTORY_TABLES = ("reviews", "cards", "attempts", "checkpoints", "steps",
                  "sessions", "notes", "proposals", "agent_runs", "ledger")


def d17_zero(cur) -> bool:
    """One-time cutover to the honest zero (D17.1): wipe every demo row, reset
    settings, drop the old board, seed the D17 board with empty rooms."""
    done = cur.execute(
        "SELECT value FROM settings WHERE key='d17_zero_done'"
    ).fetchone()
    if done:
        return False

    for t in ("rooms", "modules", "tracks"):     # board (children first is
        cur.execute(f"DELETE FROM {t}")          # handled by CASCADE; explicit anyway)
    for t in HISTORY_TABLES:                     # every record of work done
        cur.execute(f"DELETE FROM {t}")
    cur.execute("DELETE FROM settings")          # demo budgets go too

    _insert_board(cur)
    rooms = cur.execute("SELECT COUNT(*) c FROM rooms").fetchone()["c"]
    for key, value in DEFAULT_SETTINGS:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?,?)", (key, value))
    cur.execute(
        "INSERT INTO settings (key, value) VALUES ('d17_zero_done','1')")
    cur.execute(
        "INSERT INTO ledger (ts, kind, ref, text) VALUES (?,?,?,?)",
        (ist_now(), "system", None,
         "D17 honest zero — demo history wiped, settings reset; board re-seeded "
         f"as two ground-0 tracks ({rooms} rooms, no lessons written yet)"),
    )
    return True


# ---------------------------------------------------------------- D21.1 rooms
# The "two runtimes, one launcher" module (D21.1) landed after the board was
# already seeded, so it needs its own idempotent back-fill. Fresh installs get
# it from TRACKS above and this is a no-op; keyed on the module name.
D21_1_TRACK = "Project → DevOps"
D21_1_MODULE = "Two runtimes, one launcher"
D21_1_ROOMS = [
    "Why two runtimes — a runtime per service",
    "The HTTP seam — no imports across the line",
    "One port per screen, written once",
    "One launcher starts both runtimes",
]


def d21_1_rooms(cur) -> bool:
    """Ensure the D21.1 module + its four empty rooms sit in Track
    'Project → DevOps' at position 1 (right after Ground Zero). Idempotent:
    a no-op once the module exists (or on a fresh TRACKS board). Structure
    only — no steps, no cards (D46)."""
    track = cur.execute(
        "SELECT id FROM tracks WHERE name=?", (D21_1_TRACK,)
    ).fetchone()
    if not track:
        return False
    track_id = track["id"]
    if cur.execute(
        "SELECT 1 FROM modules WHERE track_id=? AND name=?",
        (track_id, D21_1_MODULE),
    ).fetchone():
        return False
    cur.execute(
        "UPDATE modules SET position = position + 1 "
        "WHERE track_id=? AND position >= 1", (track_id,),
    )
    cur.execute(
        "INSERT INTO modules (track_id, name, position, archived) "
        "VALUES (?,?,1,0)", (track_id, D21_1_MODULE),
    )
    module_id = cur.lastrowid
    for r_pos, room_name in enumerate(D21_1_ROOMS):
        cur.execute(
            "INSERT INTO rooms (module_id, name, position) VALUES (?,?,?)",
            (module_id, room_name, r_pos),
        )
    cur.execute(
        "INSERT INTO ledger (ts, kind, ref, text) VALUES (?,?,?,?)",
        (ist_now(), "system", None,
         f"D21.1 module seeded — '{D21_1_MODULE}', {len(D21_1_ROOMS)} empty "
         "rooms (structure only, no lessons — D46)"),
    )
    return True


def run() -> None:
    with connect() as conn:
        cur = conn.cursor()
        d17_zero(cur)
        board(cur)
        d21_1_rooms(cur)
        conn.commit()


if __name__ == "__main__":
    run()
    print("seed ok")
