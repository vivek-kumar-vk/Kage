"""The Plan tab's topic tree - two example tracks, tiered honestly.

WHAT THIS FILE OWNS
    `Saved_Records/study_topics.json` - the topic list behind the Plan
    tab, grouped under Track A (Splunk admin) and Track B (Detection
    Engineering / Cloud Security). Every topic carries a tier (`must`,
    `aware`, `defer`) and a status (`todo`, `doing`, `done`) that only
    ever changes through set_status().

THE STARTER SEED
    The topic list below is a generic study plan for those two exam
    tracks, shipped so the Plan tab has something to show on first run.
    It carries no personal data - edit it to your own plan, or clear it.

WHY DETERMINISTIC IDS
    Seeded topics get ids derived from their position (`trackA-1-2`),
    not random ones, so the seed file is identical every time it is
    written and an id never silently points at a different topic after
    a re-seed.

RUN IT
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\manage_study_topics.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SAVED_RECORDS = SCREEN / "Saved_Records"
TOPICS_FILE = SAVED_RECORDS / "study_topics.json"
SEED_MARKER = SAVED_RECORDS / "study_topics_starter_seed.json"

IST = timezone(timedelta(hours=5, minutes=30), "IST")

TRACKS = ("trackA", "trackB")
VALID_TIERS = ("must", "aware", "defer")
VALID_STATUSES = ("todo", "doing", "done")


class NoSuchTopic(Exception):
    """Raised by set_status() for a topic id that is not in the file -
    most likely a typo, never silently ignored."""


# The starter plan. Group order matters: it is a sensible study order
# for these two tracks. No personal data - replace with your own.
TRACK_A_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Architecture & pipeline", [
        ("Architecture + component roles (SH, Indexer, UF, HF, "
         "Deployment Server, Cluster Manager, License Manager)", "must"),
        ("Data ingestion & log onboarding (UF vs HF, inputs.conf, "
         "TCP/UDP/HEC/syslog/monitor/script inputs)", "must"),
        ("Parsing \u2192 indexing pipeline (line breaking, timestamp "
         "extraction, sourcetype/host/source)", "must"),
    ]),
    ("Admin operations", [
        ("Configuration precedence + btool", "must"),
        ("Buckets & retention (hot/warm/cold/frozen/thawed, sizing, "
         "roll triggers)", "must"),
        ("User management \u2014 roles, capabilities, auth, permissions",
         "must"),
        ("SPL fundamentals", "must"),
        ("Knowledge objects (searches, alerts, dashboards, macros, "
         "lookups, tags)", "must"),
        ("Deployment basics \u2014 deployment server, forwarder "
         "management, app push", "must"),
        ("Troubleshooting playbook", "must"),
        ("Configuration files reference", "must"),
    ]),
    ("Scale & cloud (core)", [
        ("Clustering (indexer + SHC, captain, replication/search factor)",
         "must"),
        ("SmartStore", "must"),
        ("ACS", "must"),
    ]),
    ("Awareness layer", [
        ("Monitoring Console", "aware"),
        ("Splunk Cloud basics", "aware"),
        ("Upgrade process", "aware"),
        ("Splunk 10.x currency", "aware"),
        ("Victoria experience", "aware"),
    ]),
    ("Deferred (after hired)", [
        ("ITSI", "defer"),
        ("DSP, KV Store, REST API, Python SDK, indexer tuning, "
         "deployment automation", "defer"),
    ]),
    ("ES \u2014 studied last", [
        ("ES (in-depth, once everything above is done)", "must"),
    ]),
]

TRACK_B_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Detection Engineering / Cloud Security", [
        ("Linux security telemetry (auditd, journald, syslog, PAM, "
         "file integrity)", "must"),
        ("Windows telemetry (Sysmon, Event Logs, PowerShell logging, "
         "Defender logs) \u2014 awareness only", "aware"),
        ("MITRE ATT&CK literacy", "must"),
        ("Sigma end-to-end (pySigma, sigma-cli, SPL + KQL backends)",
         "must"),
        ("Emulate \u2192 detect loop (Atomic Red Team, detection "
         "lifecycle, BOTS v3)", "must"),
        ("AWS identity + logging (IAM, STS/AssumeRole, Orgs/SCPs, "
         "CloudTrail/GuardDuty/CloudWatch)", "must"),
        ("Cloud attack/detect labs (flaws.cloud, CloudGoat, Stratus "
         "Red Team)", "must"),
        ("Cloud-native + identity depth (K8s/Docker security, "
         "OAuth2/JWT/SAML/OIDC, Terraform + CI/CD)", "must"),
        ("AWS Security Specialty", "aware"),
        ("Artifacts (detection-rules repo, security-telemetry capstone)",
         "must"),
    ]),
]


def _empty_book() -> dict:
    return {track: [] for track in TRACKS}


def _build_book() -> dict:
    """The seed structure, with one deterministic id per topic. Every
    row carries `starter: true` - the label that keeps honest starter
    data from ever masquerading as history (Phase-1 CS-4)."""
    book = _empty_book()
    for track, groups in (("trackA", TRACK_A_GROUPS),
                          ("trackB", TRACK_B_GROUPS)):
        for g_index, (group, topics) in enumerate(groups, start=1):
            entry = {"group": group, "topics": []}
            for t_index, (topic, tier) in enumerate(topics, start=1):
                entry["topics"].append({
                    "id": f"{track}-{g_index}-{t_index}",
                    "topic": topic,
                    "tier": tier,
                    "status": "todo",
                    "starter": True,
                })
            book[track].append(entry)
    return book


def seed_topics_if_empty() -> bool:
    """Write the real topic list on first run. Returns True when the
    seed was written, False when real data already existed - a re-run
    must never overwrite statuses the user has been moving.

    Seeding happens ONCE, ever. Once the marker file exists, an empty
    or deleted topic file stays empty: the person deleted their starter
    board, and a reseed that quietly brought it back would turn their
    deletion into a lie (Phase-1 CS-4)."""
    if TOPICS_FILE.exists():
        return False
    if SEED_MARKER.exists():
        return False
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    TOPICS_FILE.write_text(json.dumps(_build_book(), indent=2),
                           encoding="utf-8")
    SEED_MARKER.write_text(json.dumps({
        "seeded_at": datetime.now(IST).isoformat(timespec="seconds"),
        "what": "the two-track starter topic board",
        "note": ("seeding is one-time; this marker is why deleting "
                 "topics stays deleted after a restart"),
    }, indent=2), encoding="utf-8")
    return True


def read_topics() -> dict:
    """The whole book. An absent file is an honest empty book, not an
    error - call seed_topics_if_empty() to fill it with the real list."""
    if not TOPICS_FILE.exists():
        return _empty_book()
    return json.loads(TOPICS_FILE.read_text(encoding="utf-8"))


def _write_book(book: dict) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    TOPICS_FILE.write_text(json.dumps(book, indent=2), encoding="utf-8")


def set_status(topic_id: str, status: str) -> dict:
    """Move one topic to todo/doing/done and return the updated topic.
    Anything else is refused loudly rather than written quietly."""
    if status not in VALID_STATUSES:
        raise ValueError(
            f"status must be one of {VALID_STATUSES}, got {status!r}")
    book = read_topics()
    for track in TRACKS:
        for group in book.get(track, []):
            for topic in group["topics"]:
                if topic["id"] == topic_id:
                    topic["status"] = status
                    _write_book(book)
                    return topic
    raise NoSuchTopic(f"no topic with id '{topic_id}'")


def progress(track: str = "trackA") -> dict:
    """Done vs total for one track, as plain counts and a whole-number
    percent. A track with no topics is 0 of 0 at 0 percent - there is
    simply nothing studied yet, nothing invented to soften it."""
    if track not in TRACKS:
        raise ValueError(f"track must be one of {TRACKS}, got {track!r}")
    done = total = 0
    for group in read_topics().get(track, []):
        for topic in group["topics"]:
            total += 1
            if topic["status"] == "done":
                done += 1
    pct = round(done * 100 / total) if total else 0
    return {"done": done, "total": total, "pct": pct}


def main() -> None:
    seeded = seed_topics_if_empty()
    if seeded:
        print("  Seeded study_topics.json with the real two-track plan.")
    print("STUDY TOPICS")
    print("=" * 50)
    for track, label in (("trackA", "Track A - Splunk admin"),
                         ("trackB", "Track B - Detection Eng / Cloud Sec")):
        p = progress(track)
        print(f"  {label}: {p['done']}/{p['total']} done ({p['pct']}%)")


if __name__ == "__main__":
    main()

