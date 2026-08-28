"""An example 14-week study plan, written down once so it has a source file.

WHAT THIS FILE IS
    A generic Splunk-admin / detection-engineering plan, day by day,
    over 14 weeks (dated from a Monday lab-setup day through a Sunday
    consolidation day). Running it fills `Saved_Records/week_plans.json`
    and `Saved_Records/daily_targets.json` through the public doors in
    `manage_week_plans.py` and `manage_daily_targets.py`, so every shape
    rule those files own still applies to what lands here.

    It carries no personal data - it is a template. Edit it to your own
    schedule, or clear the seeded weeks.

WHY THE PLAN LIVES IN A FILE AND NOT ONLY IN THE JSON
    C4 - every value traces to a source file. The JSON is the working
    copy the page edits; this is where it came from. The shape: 22
    Track A topics and 10 Track B topics in dependency order, ~2-2.5h of
    Track A by day, ~1h of Track B in the evening, one rest day, one
    consolidation day.

WHAT IT DOES NOT DO
    It plans; it never records. Every `done` flag is False and every
    study session, recall review and checklist tick stays empty until
    the work is actually done (Rule 12). Re-running it with --replace
    throws away the planned weeks and writes them again - which also
    throws away any day already ticked, so it asks.

RUN IT
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\seed_the_week_plans.py
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\seed_the_week_plans.py --replace
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))         # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import manage_daily_targets as daily_targets    # noqa: E402
import manage_week_plans as week_plans          # noqa: E402

# ---------------------------------------------------------------------
# The shape of a study day, from the Week 01 plan: four 25-minute blocks
# with short breaks between them, then an 18-minute recall block. The
# clocks are the same every study day on purpose - a day whose shape is
# already known is a day that starts without a decision.
# ---------------------------------------------------------------------
CLOCKS = ("0:00–0:25", "0:28–0:53", "0:56–1:21", "1:24–1:49", "1:52–2:10")

TRACK_A_MINUTES = 130       # four blocks plus recall, breaks included
TRACK_B_MINUTES = 60        # the evening hour
STUDY_DAY_MINUTES = TRACK_A_MINUTES + TRACK_B_MINUTES
PREP_DAY_MINUTES = 120
CONSOLIDATION_MINUTES = 120

# Saturday gets no target at all, not a zero: the file's own rule is
# that blank means "not set" and zero would read as "studied nothing".

_DAYS: list[dict] = []


def day(when: str, topic_a: str, title_a: str, chunks, recall,
        topic_b: str, title_b: str, evening_points) -> None:
    """One study day. `chunks` is four (kind, title, points) tuples and
    `recall` is one (title, points) tuple - the fifth block, always."""
    blocks = []
    for index, (kind, title, points) in enumerate(chunks):
        blocks.append({"clock": CLOCKS[index], "kind": kind,
                       "title": title, "points": list(points)})
    blocks.append({"clock": CLOCKS[4], "kind": "recall",
                   "title": recall[0], "points": list(recall[1])})
    _DAYS.append({
        "date": when, "kind": "study",
        "a": title_a, "b": title_b,
        "topicA": topic_a, "topicB": topic_b,
        "chunks": blocks,
        "evening": {"title": title_b, "points": list(evening_points)},
    })


def plain_day(when: str, kind: str, title_a: str, note: str,
              chunks=(), title_b: str = "") -> None:
    """A day that is not four blocks and a card: the prep Monday, every
    Saturday off, every Sunday consolidation, the buffer week. Its
    blocks carry no clocks, because these days are a list of things to
    get through rather than a timed run."""
    _DAYS.append({
        "date": when, "kind": kind,
        "a": title_a, "b": title_b,
        "topicA": "", "topicB": "",
        "note": note,
        "chunks": [{"clock": "", "kind": ck, "title": ct, "points": list(cp)}
                   for ck, ct, cp in chunks],
        "evening": None,
    })


def saturday(when: str) -> None:
    plain_day(when, "off", "Off",
              "No lessons, no cards, no review. The two daily application "
              "passes still happen - they are a twenty-minute habit, not study.")


def sunday(when: str, test_focus: str, audit_focus: str, next_week: str) -> None:
    plain_day(
        when, "consolidation",
        "Consolidation — review, Sunday test, corrections, next week's plan",
        "No new content in either track.",
        chunks=(
            ("recall", "1 · Review the week's cards", [
                "Every card raised this week comes due together. Say all five "
                "parts out loud before revealing, then rate honestly.",
                "An inflated rating only cheats next week's schedule.",
            ]),
            ("study", "2 · Sunday test", [
                test_focus,
                "Mixed questions across both tracks, spoken, not read.",
            ]),
            ("study", "3 · Audit pass", [
                audit_focus,
                "Take the notes to a second model for a technical review. "
                "Bring back anything it flags.",
            ]),
            ("study", "4 · Log corrections", [
                "Anything the audit corrects goes into the corrections block "
                "of the topic file — old text, correct text, reason.",
                "Never silently edit a mistake away.",
            ]),
            ("study", "5 · Plan next week", [
                next_week,
                "Anything rated Again today becomes a re-teach day and pushes "
                "new content back. That is the system working, not a setback.",
            ]),
            ("study", "6 · The week's honest score", [
                "Days completed out of five, applications sent, cards that "
                "actually stuck.",
                "If Track B was cut most days that is fine and by design. If "
                "Track A was, something needs to change.",
            ]),
        ))


# =====================================================================
# WEEK 01 · Mon 31 Aug – Sun 6 Sep · lab setup, then the first lessons
# =====================================================================
plain_day(
    "2026-08-31", "prep", "Set the lab up — three VMs, notes folders, tracker",
    "Tuesday's hands-on block assumes this is already working.",
    chunks=(
        ("lab", "VM1 — Splunk Enterprise", [
            "Linux, 4GB RAM minimum. Indexer and search head in one box for now.",
            "Splunk Enterprise free trial: 60 days, then 500MB/day.",
        ]),
        ("lab", "VM2 — the forwarder host", [
            "Linux, small. The Universal Forwarder goes here on Wednesday and "
            "your log sources live here all term.",
        ]),
        ("lab", "VM3 — spare, left off", [
            "It becomes a second data source later and a cluster peer in Week 08.",
        ]),
        ("lab", "Prove the network before you need it", [
            "VM2 must reach VM1 on 9997. Test with nc -zv <vm1-ip> 9997 once "
            "receiving is on. Open the firewall now so it is not Wednesday's mystery.",
        ]),
        ("study", "Notes, tracker, snapshots", [
            "Notes on the office laptop: Observability-Learning/Splunk/ and "
            "/Detection-Engineering/. One file per topic.",
            "This tracker on the personal laptop only — it holds job-search data.",
            "Snapshot both VMs once Splunk is installed and clean. You will break "
            "something on purpose; a snapshot turns a lost evening into a rollback.",
        ]),
    ))

day("2026-09-01", "trackA-1-1",
    "Splunk architecture I — the data journey and the two core components",
    [("study", "Big picture — why Splunk is split into pieces at all", [
        "The four phases data passes through: input → parsing → indexing → search. "
        "Just the shape today, not the detail.",
        "What distribution solves: one box cannot ingest, store and search "
        "terabytes at once.",
        "Plain-English glossary as the terms arrive: forwarder, indexer, search "
        "head, index, event, bucket.",
      ]),
     ("study", "The indexer and the search head — admin lens", [
        "What each component owns, and what happens when each one fails.",
        "Default ports and who talks on them: 8000 web, 8089 management/REST, "
        "9997 receiving, 8191 KV store. Ports come up in almost every interview.",
        "Where things live on disk: $SPLUNK_HOME/etc, the index database under "
        "$SPLUNK_DB, and $SPLUNK_HOME/var/log/splunk.",
      ]),
     ("lab", "Install it and prove it is alive", [
        "Install Splunk Enterprise on VM1, start it, accept the licence.",
        "./splunk status · ./splunk version · ss -tulpn | grep splunkd — match the "
        "listening ports to what you just learned.",
        "Log into the web UI on :8000 and run index=_internal. Your first search is "
        "Splunk watching itself.",
        "Read splunkd.log for two minutes. Get used to where the truth lives.",
      ]),
     ("study", "What breaks, and three framings of the same fact", [
        "splunkd will not start: port already in use, permissions on $SPLUNK_HOME, "
        "disk full.",
        "Why 'restart Splunk' is not a first move in production, and what you check "
        "instead.",
        "Separate out what the docs state, what teams actually do, and what is safe "
        "to claim in an interview.",
      ])],
    ("Recall — components and the data journey", [
        "Likely follow-up: 'Walk me through how a log line gets from a server into "
        "a search result.'",
        "Raise the card in Recall tonight, not now. Say all five parts aloud first.",
      ]),
    "trackB-1-1", "The Linux logging landscape — syslog, journald, auditd",
    ["Three systems, three jobs: rsyslog is the transport, journald is structured "
     "and systemd-native, auditd is kernel-level security events.",
     "Why security teams cannot just read syslog and need auditd specifically.",
     "Hands-on on VM2: journalctl -n 50, ls /var/log, systemctl status auditd. Look "
     "only, configure nothing.",
     "Close by saying the 60-second elevator out loud. No full card tonight."])

day("2026-09-02", "trackA-1-1",
    "Splunk architecture II — forwarders and the management components",
    [("study", "Universal Forwarder vs Heavy Forwarder", [
        "The most-asked architecture question there is. A UF does not parse — it "
        "forwards an unparsed stream.",
        "What a heavy forwarder adds and costs: filtering before the indexer, "
        "routing to more than one destination, parsing at the edge.",
        "Where this already shows up in your onboarding work — that is your "
        "real example for the card.",
      ]),
     ("study", "The management components", [
        "Deployment Server pushes apps and config to forwarders. Cluster Manager "
        "coordinates indexer replication. License Manager tracks ingest volume. "
        "Monitoring Console shows the platform's own health.",
        "For each: why it exists, when a deployment actually needs it, what breaks "
        "without it.",
        "Small components, big interview weight. Do not skim them.",
      ]),
     ("lab", "Connect a forwarder end to end", [
        "Enable receiving on VM1 on 9997 — through the UI first, then in "
        "inputs.conf, so you see both routes.",
        "Install the Universal Forwarder on VM2 and point it at VM1: "
        "./splunk add forward-server <vm1-ip>:9997.",
        "Confirm from both ends: ./splunk list forward-server on VM2, then "
        "index=_internal host=<vm2> on VM1.",
        "Open the outputs.conf the CLI just wrote. That is the file you will "
        "hand-edit for the rest of your career.",
      ]),
     ("study", "When the forwarder does not connect", [
        "The ordered checklist: is splunkd running on the UF, is receiving enabled "
        "on the indexer, is 9997 reachable, firewall, DNS, is the UF reading "
        "anything to send.",
        "Where it tells you: splunkd.log on VM2, connection errors on VM1.",
        "Break it deliberately — stop receiving on VM1 and watch the UF log it. "
        "Then fix it.",
      ])],
    ("Recall — forwarders and management components", [
        "Trap to be ready for: 'Does a universal forwarder parse events?' Know "
        "exactly why the answer is no.",
      ]),
    "trackB-1-1", "auditd — how kernel auditing actually works",
    ["The pieces: the kernel audit subsystem, the auditd daemon, auditctl for "
     "rules, ausearch and aureport for reading.",
     "Why auditd events are not syslog events, and why that matters the moment you "
     "onboard them into a SIEM.",
     "Hands-on: auditctl -s, auditctl -l, then read raw records in "
     "/var/log/audit/audit.log. They look unreadable at first — that is expected."])

day("2026-09-03", "trackA-1-2",
    "Data ingestion I — inputs.conf and monitoring files",
    [("study", "How Splunk decides what to read", [
        "Anatomy of an inputs.conf stanza — the stanza header is the instruction.",
        "The metadata every event gets at input time: index, sourcetype, source, "
        "host. Getting these wrong at input is expensive to fix later.",
        "Why input-time decisions constrain everything downstream.",
      ]),
     ("study", "Monitor inputs and the fishbucket", [
        "[monitor://...] in depth: recursion, wildcards, whitelist and blacklist, "
        "followTail, crcSalt, initCrcLength.",
        "The fishbucket — how Splunk remembers what it already read, and why it "
        "causes 'my data will not re-ingest' tickets.",
        "Rotated logs: what happens when the file you are monitoring is renamed "
        "underneath you.",
      ]),
     ("lab", "Onboard a real log source", [
        "Create a dedicated index on VM1. Monitor /var/log/ on VM2 into it through "
        "inputs.conf, not the UI.",
        "Watch it land, then check the plumbing: ./splunk list monitor, and inspect "
        "fishbucket state with ./splunk cmd btprobe -d $SPLUNK_DB/fishbucket/"
        "splunk_private_db --file <path> --list.",
        "Now force the classic problem: re-ingest a file Splunk has already read. "
        "Understand why it refuses before you make it comply.",
      ]),
     ("study", "'The logs are not showing up'", [
        "Build the ordered checklist you would actually run on a ticket. This "
        "becomes a permanent piece of your troubleshooting playbook.",
        "Usual causes: file permissions, wrong index, index does not exist, "
        "fishbucket, forwarder not connected, a time zone putting events where you "
        "are not looking.",
        "Write this one down carefully. You will be asked to walk through it.",
      ])],
    ("Recall — inputs and onboarding", [
        "Your resume connection is direct here: end-to-end log source onboarding at "
        "your current role. Say it the way you would say it in the room.",
      ]),
    "trackB-1-1", "Writing auditd rules — watches, syscalls, keys",
    ["File watches with -w, syscall rules with -a, and why -k key naming is what "
     "makes a rule searchable later.",
     "Persistent rules in /etc/audit/rules.d/ versus live auditctl changes, and "
     "which one survives a reboot.",
     "Hands-on: watch /etc/passwd, trigger it, then find your own event with "
     "ausearch -k."])

day("2026-09-04", "trackA-1-2",
    "Data ingestion II — network inputs, scripted inputs and HEC",
    [("study", "TCP and UDP inputs, and the syslog reality", [
        "[tcp://514] and [udp://514] — what they do and where they lose data.",
        "The production pattern that matters: devices → rsyslog → files on disk → "
        "Universal Forwarder → Splunk. Know why this beats pointing syslog straight "
        "at an indexer.",
        "What breaks with direct UDP: no retry, no buffering, and the host field "
        "wrong the moment a relay is in the path.",
      ]),
     ("study", "Scripted inputs and HEC", [
        "Scripted inputs: when polling an API or a command is the only way in, and "
        "the interval and timeout traps.",
        "HTTP Event Collector: tokens, the /services/collector endpoint, indexer "
        "acknowledgement, and why developers like it.",
        "Choosing between them — a short decision table you can recite.",
      ]),
     ("lab", "Three inputs, three ways", [
        "Open a UDP input on VM1 and send to it: logger -n <vm1-ip> -P 514 "
        "'test event from vm2'.",
        "Enable HEC, create a token, and post an event with curl -k "
        "https://<vm1-ip>:8088/services/collector -H 'Authorization: Splunk "
        "<token>' -d '{\"event\":\"hello\"}'.",
        "Add a scripted input that runs a two-line shell script on a schedule.",
        "Compare the metadata each method assigned. They will not match — work out "
        "why.",
      ]),
     ("study", "Failure modes", [
        "HEC: token disabled, SSL mismatch, wrong index missing from the token's "
        "allowed list.",
        "UDP: silent loss under load, and how you would even detect it.",
        "Scripted: the script fails silently, runs too long, or overlaps itself.",
      ])],
    ("Recall — input methods", [
        "Likely follow-up: 'A customer wants to send firewall syslog to Splunk. How "
        "do you set it up?' Answer with the rsyslog pattern, not a raw UDP input.",
      ]),
    "trackB-1-1", "journald and the systemd journal",
    ["Structured fields instead of flat text, and what that buys a detection "
     "engineer.",
     "Volatile versus persistent storage — /etc/systemd/journald.conf, and why your "
     "logs vanish on reboot by default.",
     "Forwarding the journal into rsyslog so it becomes a file a forwarder can "
     "read — the exact bridge back to this morning's Track A lesson.",
     "Hands-on: journalctl -u sshd -o json-pretty, journalctl --disk-usage."])

saturday("2026-09-05")
sunday("2026-09-06",
       "Walk the full path of a log line from a file on VM2 to a search result on "
       "VM1, naming every component and phase it passes through.",
       "All four Track A topics this week are must-know, so all four are "
       "audit-worthy. Architecture and inputs especially.",
       "Week 02 is ingestion at scale and the first three days of parsing.")


# =====================================================================
# WEEK 02 · Mon 7 – Sun 13 Sep · ingestion at scale, parsing opens
# =====================================================================
day("2026-09-07", "trackA-1-2",
    "Data ingestion III — syslog at scale and the collector tier",
    [("study", "Why a syslog collector tier exists", [
        "One indexer receiving UDP from four hundred network devices is a design "
        "you have to be able to argue against.",
        "rsyslog or syslog-ng writes to files per host or per device type; a UF on "
        "that box reads them. Retry, buffering and restarts stop being your problem.",
        "How host is derived when a relay is in the path, and why events arrive "
        "labelled with the collector's name if you do nothing.",
      ]),
     ("study", "Directory layout is a design decision", [
        "/var/log/remote/<sourcetype>/<host>/... — the path itself carries the "
        "metadata, so one monitor stanza with host_segment does the work.",
        "host_segment and host_regex in inputs.conf, and when each is the right tool.",
        "Rotation and retention on the collector: you now own disk on a box that "
        "is not an indexer.",
      ]),
     ("lab", "Build the collector pattern on VM2", [
        "Configure rsyslog on VM2 to write inbound messages into "
        "/var/log/remote/<host>/messages.log.",
        "Send events at it from VM1 with logger -n, and watch the files appear.",
        "Point the UF at that tree with host_segment set, and confirm in Splunk "
        "that host is the sender, not VM2.",
      ]),
     ("study", "The interview version of this answer", [
        "Two sentences: the pattern, then the one reason for it — durability.",
        "Where your migration work touches it: OpenPipeline ingestion and routing "
        "solves the same problem in Dynatrace's shape.",
        "Say what you have run and what you have only read. Keep the line clean.",
      ])],
    ("Recall — syslog at scale", [
        "Trap: 'Just open a UDP input, right?' Know the three specific things you "
        "lose.",
      ]),
    "trackB-1-1", "rsyslog — facilities, severities and forwarding",
    ["Facility and severity, the selector syntax, and how /etc/rsyslog.conf and "
     "rsyslog.d/ fit together.",
     "Forwarding to a remote host over TCP, and writing to a file for a forwarder "
     "to pick up — this morning's pattern, seen from the sending side.",
     "Hands-on: forward VM2's auth logs to VM1's filesystem, then read them in "
     "Splunk. Both tracks meet in one exercise."])

day("2026-09-08", "trackA-1-2",
    "Data ingestion IV — the onboarding runbook, end to end",
    [("study", "What a real onboarding request contains", [
        "The questions you ask before touching a config: what is the source, what "
        "volume, what format, who owns it, which index, what retention, who needs "
        "to search it.",
        "Index naming and why it is a governance decision, not a preference.",
        "Sizing the request against the licence before you say yes.",
      ]),
     ("study", "The runbook itself", [
        "Order of operations: index exists → input defined → parsing correct → "
        "metadata correct → permissions → validation search → sign-off.",
        "What 'done' means: a saved search the requester can run, not 'data is in'.",
        "Where each step goes wrong, and which log tells you.",
      ]),
     ("lab", "Onboard one source properly, start to finish", [
        "Pick something with awkward formatting — a multi-line application log.",
        "Do every step of the runbook in order, writing each command down as you go.",
        "Finish with a validation search and a short sign-off note. That note is "
        "the artefact.",
      ]),
     ("study", "Turn the week into a story", [
        "You have done this in production many times. Shape one instance into STAR: the "
        "source, the problem, what you did, what it proved.",
        "Name the specific input type and the specific failure you fixed. Detail is "
        "what makes it believable.",
      ])],
    ("Recall — the onboarding runbook", [
        "Likely follow-up: 'Walk me through onboarding a new log source.' The "
        "runbook order is the answer; the story is the evidence.",
      ]),
    "trackB-1-1", "PAM and authentication telemetry",
    ["Where authentication actually gets logged: /var/log/secure or auth.log, and "
     "what pam_unix writes on success and on failure.",
     "sudo, su and ssh — three different event shapes for what a report will call "
     "'a login'.",
     "Hands-on: fail an ssh login on purpose, then find every record of it across "
     "journald, auth.log and auditd. Three views of one act."])

day("2026-09-09", "trackA-1-3",
    "The parsing pipeline I — line breaking",
    [("study", "What parsing does to a raw stream", [
        "Three jobs, in order: line breaking (where does one event end), timestamp "
        "extraction, sourcetype assignment.",
        "Why a stream of bytes is not events yet, and why almost every downstream "
        "problem traces back here.",
      ]),
     ("study", "Where parsing happens", [
        "It runs on the first full Splunk Enterprise instance to receive the data — "
        "a heavy forwarder if you have one, otherwise the indexer. Never a UF.",
        "The settings that matter in props.conf: SHOULD_LINEMERGE, LINE_BREAKER, "
        "TRUNCATE, BREAK_ONLY_BEFORE.",
        "LINE_BREAKER with SHOULD_LINEMERGE=false is the modern answer. Know why it "
        "is faster than the merge path.",
      ]),
     ("lab", "Break a log on purpose, then fix it", [
        "Write a multi-line log file — a Java-style stack trace works well — and "
        "onboard it with no props at all. Watch Splunk get it wrong.",
        "Now fix it: set SHOULD_LINEMERGE and LINE_BREAKER, restart, re-ingest, "
        "confirm one event per stack trace.",
        "This is the most valuable hour of the week. Do it slowly.",
      ]),
     ("study", "Which props.conf wins is a different question", [
        "Note it and move on: precedence is Week 03. Chasing it today costs you "
        "the topic you are on.",
        "What you can say now: the setting must live where parsing happens.",
      ])],
    ("Recall — line breaking", [
        "Trap: 'Splunk parses on the search head, right?' Know why that is wrong "
        "and what the correct answer is.",
      ]),
    "trackB-1-1", "File integrity monitoring the honest way",
    ["What FIM actually is, and why 'a file changed' is only useful with who and "
     "with what process.",
     "auditd watches versus AIDE: continuous events versus a periodic baseline diff.",
     "Hands-on: put a watch on /etc/ssh/sshd_config, change it, and read the full "
     "record — uid, auid, comm, exe. auid is the field that survives a sudo."])

day("2026-09-10", "trackA-1-3",
    "The parsing pipeline II — timestamps and time zones",
    [("study", "How Splunk finds a timestamp", [
        "The order it tries: TIME_FORMAT and TIME_PREFIX if you gave them, then "
        "datetime.xml patterns, then the file modification time, then index time.",
        "MAX_TIMESTAMP_LOOKAHEAD and why a long prefix makes parsing slower and "
        "wronger.",
        "DATETIME_CONFIG=CURRENT and NONE — the two escape hatches and their cost.",
      ]),
     ("study", "Time zones, the quiet killer", [
        "TZ in props.conf, the forwarder's own clock, and the user's search "
        "time zone — three places one event can be misread.",
        "Why events look 'missing' when they are five and a half hours away.",
        "Events dated 1970, or dated today when they are a week old: what each "
        "symptom tells you.",
      ]),
     ("lab", "Break the timestamp, then correct it", [
        "Write a log with a date format Splunk cannot guess. Ingest it and watch "
        "the events land at index time.",
        "Fix it with TIME_PREFIX, TIME_FORMAT and MAX_TIMESTAMP_LOOKAHEAD.",
        "Then set TZ wrongly on purpose and watch the whole day shift. Undo it.",
      ]),
     ("study", "The support ticket version", [
        "This is your production experience exactly. Turn it into a clean STAR answer "
        "while it is fresh.",
        "The tell: _time and _indextime far apart. Learn to check that first.",
      ])],
    ("Recall — timestamps and time zones", [
        "Likely follow-up: 'A customer says data is missing for the last hour, but "
        "ingestion looks fine. What do you check?'",
      ]),
    "trackB-1-1", "Reading an intrusion in Linux logs",
    ["Take one simple story — ssh brute force, then a successful login, then a "
     "sudo to root, then a new cron entry — and find every artefact it leaves.",
     "Which log answers which question, and which questions Linux simply cannot "
     "answer without auditd rules in place first.",
     "Hands-on: run the sequence on VM2 yourself and reconstruct it from logs "
     "alone. Write the timeline down."])

day("2026-09-11", "trackA-1-3",
    "The parsing pipeline III — sourcetypes, props and transforms",
    [("study", "The sourcetype is the contract", [
        "Everything downstream keys off it: field extraction, CIM mapping, "
        "retention policy, permissions.",
        "Automatic sourcetype recognition and why you should almost always set it "
        "explicitly instead.",
        "Naming: vendor:product:format. Boring, consistent, searchable.",
      ]),
     ("study", "props.conf and transforms.conf together", [
        "props points at a transform by name; the transform does the work. Neither "
        "is useful alone.",
        "Index-time transforms: overriding host, routing to a different index, "
        "dropping events with nullQueue.",
        "SEDCMD for masking a value before it is written — the one that shows up "
        "the moment anyone says the word compliance.",
      ]),
     ("lab", "Route and mask real events", [
        "Send two kinds of event through one input. Route one of them to a "
        "different index with a transform.",
        "Drop a noisy event type entirely with nullQueue and prove it is gone.",
        "Mask the last digits of a number with SEDCMD and confirm the raw event on "
        "disk is masked, not just the display.",
      ]),
     ("study", "Index time versus search time — the rule", [
        "If it can be done at search time, do it at search time. Index-time changes "
        "are permanent and only fixable by re-ingesting.",
        "The exceptions: routing, masking, host correction, and cutting volume you "
        "are paying to index.",
      ])],
    ("Recall — sourcetypes and transforms", [
        "Trap: 'Can you just re-extract that field for the last six months?' Know "
        "which answer is yes and which is no, and why.",
      ]),
    "trackB-1-1", "Getting Linux telemetry into a SIEM",
    ["The whole track so far, pointed at one job: which files, which sourcetypes, "
     "which fields matter for detection.",
     "Why auditd's raw format needs work before it is searchable, and what a good "
     "add-on does for you.",
     "Sketch the ingestion design you would propose for a hundred Linux hosts. One "
     "page, your own words."])

saturday("2026-09-12")
sunday("2026-09-13",
       "Take one badly-formatted log and say, without notes, every props setting "
       "you would use and in what order you would test them.",
       "Parsing is the easiest topic so far to half-understand without noticing. "
       "Audit those three days hardest.",
       "Week 03 closes parsing, then configuration precedence and buckets.")


# =====================================================================
# WEEK 03 · Mon 14 – Sun 20 Sep · parsing closes, precedence, buckets
# =====================================================================
day("2026-09-14", "trackA-1-3",
    "The parsing pipeline IV — index time versus search time, the whole path",
    [("study", "The complete journey, said out loud", [
        "Input reads bytes and tags them. Parsing makes events. Indexing writes "
        "them to buckets. Search reads them back.",
        "Which queue each phase sits behind, and what a full queue looks like in "
        "the Monitoring Console.",
        "Where a heavy forwarder changes the picture, and where it does not.",
      ]),
     ("study", "Search-time extraction", [
        "EXTRACT and REPORT in props.conf, and how they differ from an index-time "
        "transform.",
        "Field discovery, the KV_MODE settings, and why auto-kv on a huge sourcetype "
        "is a performance decision.",
        "Why search-time is reversible and index-time is not — one line, memorised.",
      ]),
     ("lab", "Prove the boundary yourself", [
        "Extract a field at search time with EXTRACT. Change the regex, reload, and "
        "watch old events pick up the new field.",
        "Now do the same at index time and watch old events not change. That is the "
        "whole lesson in one experiment.",
      ]),
     ("study", "The pipeline as an interview answer", [
        "Two minutes, no notes, from file on disk to a row in a search result.",
        "Include one failure at each phase. That is what makes it an admin's answer "
        "rather than a diagram.",
      ])],
    ("Recall — the whole pipeline", [
        "This card supersedes the seeded pipeline card. Rate honestly; it is due "
        "for its first real review.",
      ]),
    "trackB-1-1", "Linux security telemetry — the wrap-up",
    ["Ten evenings, one elevator answer: what Linux gives you, what it does not, "
     "and what you have to configure to get it.",
     "Write the 5-part recall card properly tonight — this is the first Track B "
     "card of the term.",
     "What you can now claim: auditd and journald hands-on. What you cannot yet: "
     "detection content. Keep the line clean."])

day("2026-09-15", "trackA-2-1",
    "Configuration precedence I — how Splunk decides which setting wins",
    [("study", "The layers, in order", [
        "System default, then app local, then app default, then user. Plus the "
        "system local layer that beats almost everything.",
        "Why $SPLUNK_HOME/etc/system/local is both the easy answer and the wrong "
        "habit.",
        "Never edit a default directory. Say why, not just that.",
      ]),
     ("study", "App directory priority", [
        "How apps are ordered against each other — lexicographic by directory name, "
        "and what that means for a TA you did not write.",
        "Global versus app-scoped context, and why the same file behaves differently "
        "for a search-time setting than for an index-time one.",
      ]),
     ("lab", "Make two settings fight", [
        "Put the same stanza in two apps with conflicting values. Predict the winner "
        "before you check.",
        "Move one to system/local and predict again.",
        "Being wrong once here is worth more than reading the table five times.",
      ]),
     ("study", "Why this is the topic that separates levels", [
        "Almost everyone can edit a conf file. Far fewer can say which one is "
        "actually in effect on a live box.",
        "The honest admin answer to 'why is my setting not working' starts here.",
      ])],
    ("Recall — configuration precedence", [
        "Likely follow-up: 'Your props change had no effect. Walk me through what "
        "you check.'",
      ]),
    "trackB-1-2", "Windows telemetry I — Event Logs and channels (awareness)",
    ["Awareness depth only, by the contract. Know the shape, do not claim hands-on.",
     "Channels: Security, System, Application, and the Operational logs that "
     "matter. Event IDs as a vocabulary, not a memory test.",
     "The handful worth knowing cold: 4624, 4625, 4688, 4672. What each one means "
     "and what it does not prove."])

day("2026-09-16", "trackA-2-1",
    "Configuration precedence II — btool in anger",
    [("study", "What btool actually does", [
        "It merges the layers and shows you the result. It does not read the "
        "running process — a config on disk that has not been reloaded still shows.",
        "./splunk btool props list --debug is the form worth memorising: --debug "
        "prints which file each line came from.",
        "btool check for syntax, and its limits.",
      ]),
     ("study", "Reading a merged config without panic", [
        "Work backwards: find the setting, find its file, then ask why that file "
        "wins.",
        "The REST equivalent — /services/properties and the configs endpoints — "
        "for when you have no shell, which on Cloud is always.",
      ]),
     ("lab", "Diagnose a config you did not write", [
        "Install any TA from Splunkbase onto VM1. Do not read its docs.",
        "Use btool alone to answer: which sourcetypes does it define, which "
        "index-time transforms does it add, what would it change about your data.",
        "Then read the docs and check your answer.",
      ]),
     ("study", "On Cloud you cannot do most of this", [
        "No shell, no btool. What replaces it: the UI, ACS, and support cases.",
        "This is why Cloud admin work is a different skill, and why the ACS topic "
        "later matters more than it looks.",
      ])],
    ("Recall — btool", [
        "Trap: 'btool says the setting is there, so it is applied.' Know the two "
        "reasons that can be false.",
      ]),
    "trackB-1-2", "Windows telemetry II — Sysmon (awareness)",
    ["What Sysmon adds that the built-in logs do not: process creation with command "
     "line and hashes, network connections, image loads.",
     "Config-driven, and the well-known community configurations that shape it.",
     "Read one real Sysmon event of each of the three main types. Recognition is "
     "the goal, not authorship."])

day("2026-09-17", "trackA-2-2",
    "Buckets and retention I — the bucket lifecycle",
    [("study", "Hot, warm, cold, frozen, thawed", [
        "What each state means physically: which directory, writable or not, "
        "searchable or not.",
        "Frozen is the one people get wrong — by default it means deleted, not "
        "archived.",
        "Thawed, and why restoring from frozen is a deliberate manual act.",
      ]),
     ("study", "What a bucket actually contains", [
        "The rawdata journal and the tsidx files, and roughly what each costs in "
        "disk terms.",
        "Bucket naming: db_<newest>_<oldest>_<id>. Being able to read a bucket "
        "directory listing is a real skill.",
        "Why the time range in the name is what makes a search skip buckets "
        "entirely.",
      ]),
     ("lab", "Watch a bucket roll", [
        "Look at the index directories on VM1: db/ colddb/ thaweddb/.",
        "Force a roll with ./splunk _internal call /data/indexes/<index>/roll-hot-"
        "buckets and watch a hot bucket become warm.",
        "Read the new directory name and say out loud what its time span is.",
      ]),
     ("study", "The searches that get slow and why", [
        "All-time searches, and what they do to bucket skipping.",
        "Why a search over a wide time range on a small index is fine and the same "
        "search on a large one is not.",
      ])],
    ("Recall — the bucket lifecycle", [
        "Trap: 'What happens to data when a bucket freezes?' Know the default and "
        "the setting that changes it.",
      ]),
    "trackB-1-2", "Windows telemetry III — PowerShell and Defender (awareness)",
    ["Script block logging, module logging, transcription: three levels, three "
     "different volumes of data.",
     "Why attackers care about PowerShell logging being off, and what event 4104 "
     "gives a defender.",
     "Defender logs as a source of already-triaged signal, and its limits."])

day("2026-09-18", "trackA-2-2",
    "Buckets and retention II — sizing, roll triggers and indexes.conf",
    [("study", "The settings that control the lifecycle", [
        "maxHotBuckets, maxDataSize, maxWarmDBCount, homePath.maxDataSizeMB, "
        "coldPath.maxDataSizeMB.",
        "frozenTimePeriodInSecs, and why it is measured against the event's time "
        "and not the file's.",
        "Which of these triggers a roll and which triggers deletion. Say each one "
        "out loud.",
      ]),
     ("study", "Sizing an index honestly", [
        "Daily volume, retention requirement, replication factor, compression. "
        "The arithmetic is simple; the inputs are what people get wrong.",
        "Why retention is a legal question first and a disk question second.",
        "What you tell a customer who wants seven years on hot storage.",
      ]),
     ("lab", "Write an indexes.conf and defend it", [
        "Create an index with deliberate small limits so you can watch it roll and "
        "freeze inside an hour.",
        "Set coldToFrozenDir and prove that frozen no longer means gone.",
        "Then remove it and confirm the default behaviour is what you said it was.",
      ]),
     ("study", "The volume: prefix", [
        "Volumes let several indexes share a disk budget. What that solves and what "
        "it hides.",
        "When you would use one, and the failure mode when nobody notices a volume "
        "is full.",
      ])],
    ("Recall — retention and sizing", [
        "Likely follow-up: 'How much disk do I need for 50GB a day with 90-day "
        "retention?' Show the working, state the assumptions.",
      ]),
    "trackB-1-2", "Windows telemetry IV — what to claim and what not to",
    ["Four evenings of awareness. Write the card at awareness depth and mark it "
     "clearly as such.",
     "What is safe to say: 'I can read Windows security events and Sysmon output "
     "and map them to a detection.'",
     "What is not safe: deploying or tuning Sysmon at scale. Keep it off the "
     "resume until the Track B labs actually cover it."])

saturday("2026-09-19")
sunday("2026-09-20",
       "Given a config that is not taking effect, name every place you would look "
       "and in what order — then size an index out loud.",
       "Precedence and retention both. Precedence because it is subtle, retention "
       "because the arithmetic must be right in front of a customer.",
       "Week 04 finishes buckets, does user management, and opens SPL.")


# =====================================================================
# WEEK 04 · Mon 21 – Sun 27 Sep · buckets close, users, SPL opens
# =====================================================================
day("2026-09-21", "trackA-2-2",
    "Buckets and retention III — archiving, restoring and data deletion",
    [("study", "coldToFrozenScript and coldToFrozenDir", [
        "The two ways out of frozen, and why a script gives you S3 and a directory "
        "gives you a full disk.",
        "What Splunk hands the script, and what happens when the script fails.",
        "Testing an archive path before you need it, which is the only time anyone "
        "ever does.",
      ]),
     ("study", "Restoring, and deleting on purpose", [
        "Thawing: copy the bucket in, rebuild the index files, restart. Why it is "
        "not automatic.",
        "The delete command versus actually removing data. delete only hides it "
        "from search and it still costs disk.",
        "./splunk clean eventdata and why it is a lab command, never a production "
        "one.",
      ]),
     ("lab", "Archive and bring one back", [
        "Freeze a bucket to a directory, confirm it left the index, then thaw it "
        "and search it again.",
        "Do the whole loop once. It is twenty minutes and it answers a question "
        "interviewers like asking.",
      ]),
     ("study", "The compliance conversation", [
        "'We must keep logs for seven years' almost never means seven years of "
        "searchable Splunk.",
        "Tiering: hot for days, cold for months, cheap object storage for years. "
        "What each tier costs in time-to-answer.",
      ])],
    ("Recall — archiving and deletion", [
        "Trap: 'Does the delete command free disk space?' Know the answer and the "
        "correct alternative.",
      ]),
    "trackB-1-3", "MITRE ATT&CK I — what the matrix actually is",
    ["Tactics are the why, techniques are the how, sub-techniques are the detail. "
     "Procedures are what a specific group did.",
     "Enterprise, Mobile and ICS matrices, and why the Enterprise one is your "
     "whole world for now.",
     "Hands-on: open the Navigator, pick three techniques you have already seen in "
     "logs this month, and read their data sources."])

day("2026-09-22", "trackA-2-2",
    "Buckets and retention IV — index design as a whole",
    [("study", "How many indexes, and why", [
        "One per data source is wrong. One for everything is wrong. The real "
        "drivers: retention, access control, and search performance.",
        "Access control is the one people forget: an index is the unit permissions "
        "act on.",
        "How index count affects search: more indexes searched means more buckets "
        "opened.",
      ]),
     ("study", "Metadata and the internal indexes", [
        "_internal, _audit, _introspection, _telemetry: what each records and when "
        "you reach for it.",
        "The metadata command and the tstats way of asking what is in an index "
        "without reading events.",
      ]),
     ("lab", "Audit the lab's own indexes", [
        "Use | tstats count where index=* by index, sourcetype to see everything "
        "you have onboarded so far.",
        "Compare against | metadata type=sourcetypes index=* and note where the two "
        "disagree.",
        "Write down the index design you would propose if the lab were a customer.",
      ]),
     ("study", "The design review answer", [
        "Given a customer's data list, group it into indexes out loud, giving one "
        "reason per group.",
        "Say what you would ask before deciding. The questions are the answer here.",
      ])],
    ("Recall — index design", [
        "Likely follow-up: 'How would you decide how many indexes a customer needs?'",
      ]),
    "trackB-1-3", "MITRE ATT&CK II — data sources and detection coverage",
    ["The data-source and data-component model: what telemetry a technique is even "
     "visible in.",
     "Mapping backwards — start from the logs you have, find what you could detect, "
     "instead of starting from the matrix.",
     "Hands-on: take the Linux telemetry from Weeks 01-03 and mark on a Navigator "
     "layer what it could and could not see."])

day("2026-09-23", "trackA-2-3",
    "User management I — roles, capabilities and index access",
    [("study", "Users, roles, capabilities", [
        "A user has roles; a role has capabilities; capabilities are what the "
        "product actually checks.",
        "The built-in roles — admin, power, user — and why inheriting from them is "
        "usually a mistake in a real deployment.",
        "srchIndexesAllowed and srchIndexesDefault: the two settings that decide "
        "what a person can even see.",
      ]),
     ("study", "Search quotas and restrictions", [
        "Concurrent search limits per role, disk quota, and the search filter that "
        "silently narrows every search a role runs.",
        "Why a search filter is powerful and dangerous: results look complete and "
        "are not.",
        "Real-time search as a capability worth taking away.",
      ]),
     ("lab", "Build a role that cannot see too much", [
        "Create an index with test data, then a role that can search only it.",
        "Log in as that user and prove the boundary from the inside.",
        "Add a search filter and watch the same query return fewer results without "
        "any warning.",
      ]),
     ("study", "The least-privilege answer", [
        "How you would design roles for a SOC team, an application team and a "
        "manager. Three different shapes.",
        "What you tell someone who asks for admin because it is easier.",
      ])],
    ("Recall — roles and capabilities", [
        "Trap: 'The user is in the right role but still cannot see the data.' Name "
        "the three usual causes.",
      ]),
    "trackB-1-3", "MITRE ATT&CK III — reading a technique properly",
    ["Pick one technique per tactic and read the full page: procedures, "
     "mitigations, detections, references.",
     "Notice how vague the detection guidance often is. That gap is the detection "
     "engineer's actual job.",
     "Write one sentence per technique on what you would need to see in logs."])

day("2026-09-24", "trackA-2-3",
    "User management II — authentication and object permissions",
    [("study", "Where users come from", [
        "Splunk native, LDAP or Active Directory, SAML SSO. The order Splunk tries "
        "them in and what that means when both exist.",
        "Group-to-role mapping, and why a change on the directory side is the usual "
        "cause of 'I lost access this morning'.",
        "Multi-factor and token authentication in outline.",
      ]),
     ("study", "Knowledge object permissions", [
        "Private, app, global — three scopes with different consequences.",
        "Read and write per role, and the way a globally shared broken macro takes "
        "everyone down with it.",
        "Who can promote an object, and why that capability is worth guarding.",
      ]),
     ("lab", "Break and fix access", [
        "Create a saved search as one user, share it at app level, and confirm "
        "another role can and cannot run it.",
        "Then remove the underlying index permission and watch how the failure "
        "presents — it does not say 'permission denied'.",
      ]),
     ("study", "Troubleshooting authentication", [
        "Where it logs: splunkd.log, _audit, and the authentication debug settings.",
        "The order to check: does the user exist, is the mapping right, is the role "
        "right, is the index allowed, is there a search filter.",
      ])],
    ("Recall — authentication and permissions", [
        "Likely follow-up: 'A whole team lost access after an AD change. What do "
        "you do first?'",
      ]),
    "trackB-1-3", "MITRE ATT&CK IV — building a coverage layer",
    ["Navigator layers as a working document: what you can detect, what you could "
     "with more telemetry, what you cannot.",
     "Scoring honestly — a rule that fires on one variant does not cover a "
     "technique.",
     "Hands-on: build your first real layer and save the JSON. It becomes an "
     "artefact for the detection-rules repo later."])

day("2026-09-25", "trackA-2-4",
    "SPL fundamentals I — the shape of a search",
    [("study", "How a search is actually structured", [
        "Search terms first, then pipe to commands. Everything after the first pipe "
        "is a transformation of what came before.",
        "Why filtering early is the single biggest performance decision in SPL.",
        "index, sourcetype, source, host: the four fields that make a search fast "
        "because they are indexed.",
      ]),
     ("study", "The five command families", [
        "Streaming, non-streaming, transforming, generating, orchestrating. Knowing "
        "which is which explains most performance surprises.",
        "Distributable versus centralised: what runs on the indexers and what has "
        "to come back to the search head.",
        "Why stats is fast and why join is not.",
      ]),
     ("lab", "Search your own lab data", [
        "Run twenty searches against the data you have onboarded so far. Time each.",
        "Take one slow search and make it fast by moving a filter to the left of "
        "the first pipe.",
        "Read the job inspector on both versions and see where the time went.",
      ]),
     ("study", "Time is a field and a filter", [
        "The time picker, earliest and latest, and relative time syntax. snap-to "
        "with @ is the part people get wrong.",
        "_time versus _indextime, and the one situation where you must search on "
        "the latter.",
      ])],
    ("Recall — SPL fundamentals", [
        "Trap: 'Does it matter where in the pipeline you filter?' Answer with the "
        "reason, not just yes.",
      ]),
    "trackB-1-3", "MITRE ATT&CK V — from technique to detection idea",
    ["Take three techniques and write, in plain English, what a detection for each "
     "would look for and what would make it noisy.",
     "False positive thinking before rule writing — the habit that separates a "
     "detection engineer from a rule copier.",
     "This is the bridge into Sigma next week. Keep these three; you will write "
     "them as rules."])

saturday("2026-09-26")
sunday("2026-09-27",
       "Design roles for a three-team deployment out loud, then explain why a "
       "search filter is more dangerous than an index restriction.",
       "User management and index design. Both are places where a confident wrong "
       "answer sounds fine and fails in production.",
       "Week 05 is SPL all week — the longest single topic on the board.")


# =====================================================================
# WEEK 05 · Mon 28 Sep – Sun 4 Oct · SPL, all week
# =====================================================================
day("2026-09-28", "trackA-2-4",
    "SPL fundamentals II — the stats family",
    [("study", "stats, and why it is the centre of SPL", [
        "One command, one job: collapse events into rows. Everything else is "
        "arrangement.",
        "The functions worth knowing cold: count, dc, sum, avg, min, max, values, "
        "list, latest, earliest.",
        "by clauses, and what happens to fields that are not in one.",
      ]),
     ("study", "eventstats, streamstats, chart, timechart", [
        "eventstats adds an aggregate back to every event. streamstats does it "
        "cumulatively, in order.",
        "chart and timechart as stats with a second dimension — and the span "
        "argument that decides everything about a timechart.",
        "When streamstats is the right answer: sessionising, deltas, and "
        "'the previous event' problems.",
      ]),
     ("lab", "Rewrite five searches with stats", [
        "Take five searches you wrote on Friday and reduce each to a stats "
        "expression.",
        "Then produce the same numbers with chart and with timechart. Same answer, "
        "three shapes.",
        "Use streamstats to compute the time between consecutive events per host.",
      ]),
     ("study", "Where stats runs", [
        "Why stats is distributable and finishes on the indexers, and what that "
        "means for a large search.",
        "The map-reduce picture: partial results per indexer, merged on the search "
        "head.",
      ])],
    ("Recall — the stats family", [
        "Likely follow-up: 'What is the difference between stats and eventstats?' "
        "Answer with an example, not a definition.",
      ]),
    "trackB-1-3", "MITRE ATT&CK VI — the wrap-up card",
    ["Six evenings. Write the 5-part card: what ATT&CK is, what it is not, and how "
     "you use it in practice.",
     "What it is not: a detection library, a maturity score, or proof of coverage.",
     "Safe claim: 'I map telemetry and detections to ATT&CK techniques and track "
     "coverage in Navigator layers.'"])

day("2026-09-29", "trackA-2-4",
    "SPL fundamentals III — eval, fields and regular expressions",
    [("study", "eval is a language inside the language", [
        "Arithmetic, string functions, if and case, coalesce, and the null handling "
        "that catches everyone.",
        "eval versus where: computing a value and filtering on one are different "
        "jobs with similar syntax.",
        "Multi-value fields: mvcount, mvindex, mvexpand, and why mvexpand can blow "
        "up a search.",
      ]),
     ("study", "rex, erex and field extraction at search time", [
        "rex with named capture groups, in field and max_match.",
        "sed mode for masking inside a search, which does not change what is on "
        "disk.",
        "When to turn a working rex into a permanent props extraction, and when to "
        "leave it in the search.",
      ]),
     ("lab", "Extract three fields from an ugly log", [
        "Pick the worst-formatted source in your lab. Extract three useful fields "
        "with rex.",
        "Then move one of them into props.conf as a permanent extraction and prove "
        "it applies to old events.",
        "Keep the regex. It is card material and interview material.",
      ]),
     ("study", "Performance of search-time work", [
        "Every eval and rex runs per event. Filter first, transform second — the "
        "same rule as always, now with a cost you can measure.",
      ])],
    ("Recall — eval and rex", [
        "Trap: 'Just use rex on everything.' Know the cost and the alternative.",
      ]),
    "trackB-1-4", "Sigma I — what a Sigma rule is",
    ["A vendor-neutral detection format in YAML: logsource, detection, condition. "
     "That is nearly the whole language.",
     "Why it exists: write once, convert to SPL, KQL or anything else. Your SPL "
     "pays off here directly.",
     "Read five real rules from the public repository and say out loud what each "
     "one is looking for."])

day("2026-09-30", "trackA-2-4",
    "SPL fundamentals IV — lookups, subsearches and joins",
    [("study", "Lookups are the right answer more often than join", [
        "lookup, inputlookup, outputlookup — the three doors.",
        "Automatic lookups in props.conf, and why they can quietly slow every "
        "search on a sourcetype.",
        "KV store lookups versus CSV: when the data changes, and how big it is.",
      ]),
     ("study", "Subsearches and their limits", [
        "How a subsearch runs first and passes results up, and the default limits "
        "of 10,000 results and 60 seconds.",
        "The silent failure: a truncated subsearch returns a wrong answer with no "
        "error.",
        "format and return, and why return is usually the cleaner tool.",
      ]),
     ("study", "join, and the three ways to avoid it", [
        "Why join is expensive and often wrong at scale.",
        "The alternatives: stats by a common field, lookup, and appending then "
        "collapsing with stats.",
        "The one case where join genuinely is the clearest answer.",
      ]),
     ("lab", "Solve the same problem three ways", [
        "Correlate two sources in your lab with join, then with stats, then with a "
        "lookup.",
        "Time all three and read the job inspector for each.",
        "Write down which you would defend in a review and why.",
      ])],
    ("Recall — lookups and joins", [
        "Likely follow-up: 'How would you correlate firewall logs with an asset "
        "list?' The answer is a lookup, and you should say why.",
      ]),
    "trackB-1-4", "Sigma II — the rule anatomy in detail",
    ["logsource: category, product and service, and why getting this wrong makes a "
     "rule convert into nonsense.",
     "detection: selection blocks, keywords, modifiers like contains, startswith, "
     "re, and the condition expression.",
     "Hands-on: write one rule by hand for a Linux technique you studied in "
     "Week 01-03. Do not convert it yet."])

day("2026-10-01", "trackA-2-4",
    "SPL fundamentals V — tstats, data models and acceleration",
    [("study", "Why tstats is a different animal", [
        "It reads the index files, not the events. That is why it is fast and why "
        "it can only see indexed fields.",
        "The prestats and summariesonly arguments, and what summariesonly=true "
        "actually excludes.",
        "When a tstats answer and a stats answer legitimately differ.",
      ]),
     ("study", "Data models and acceleration", [
        "A data model is a schema over raw data; acceleration builds summaries "
        "behind it.",
        "Where accelerated summaries live and what they cost in disk and in "
        "indexer load.",
        "Why ES is built on this — and why that makes this lesson matter twice.",
      ]),
     ("lab", "Accelerate something and measure it", [
        "Build a small data model over one of your sourcetypes and accelerate it.",
        "Run the same question as stats and as tstats and compare the times.",
        "Look at the summary directory and confirm you can point at what was built.",
      ]),
     ("study", "Report acceleration and summary indexing", [
        "Three acceleration strategies — report acceleration, summary indexing, "
        "data model acceleration — and when each fits.",
        "The trade every one of them makes: freshness for speed.",
      ])],
    ("Recall — tstats and acceleration", [
        "Trap: 'Why did my tstats search return nothing when the events are "
        "clearly there?' Know the two usual causes.",
      ]),
    "trackB-1-4", "Sigma III — pySigma and sigma-cli",
    ["Installing sigma-cli, listing backends, and converting a rule to Splunk SPL.",
     "Pipelines: why a raw conversion rarely matches your field names, and what a "
     "processing pipeline fixes.",
     "Hands-on: convert last night's rule to SPL and run it against your lab. "
     "Expect it to fail on field names — that is the lesson."])

day("2026-10-02", "trackA-2-4",
    "SPL fundamentals VI — the job inspector and slow searches",
    [("study", "Reading the search job inspector", [
        "The phases it reports and what a large dispatch time versus a large "
        "command time each mean.",
        "Events scanned versus events matched — the ratio that tells you your "
        "filter is wrong.",
        "Where the search was run: how much finished on the indexers.",
      ]),
     ("study", "The usual causes of a slow search", [
        "All-time ranges, leading wildcards, join, mvexpand, transaction, and "
        "search-time extraction on a huge sourcetype.",
        "Search concurrency and queueing — sometimes the search is fine and the "
        "system is busy.",
        "The skipped-searches problem and where it shows.",
      ]),
     ("lab", "Make one search five times faster", [
        "Take the slowest search in your lab and improve it step by step, recording "
        "the time after each change.",
        "Keep the before and after. It is a concrete interview story.",
      ]),
     ("study", "Six days of SPL, one answer", [
        "Say the whole topic in two minutes: how a search runs, where it runs, and "
        "the three things you check when it is slow.",
        "This is a strong resume line once the card is clean twice.",
      ])],
    ("Recall — search performance", [
        "Likely follow-up: 'A user says Splunk is slow. Walk me through it.' Start "
        "with the search, not the servers.",
      ]),
    "trackB-1-4", "Sigma IV — fixing the conversion with a pipeline",
    ["Write a small processing pipeline that maps Sigma field names onto your own "
     "sourcetype's fields.",
     "Re-convert and re-run. Getting a rule to actually fire on data you generated "
     "is the point of the whole evening.",
     "Note what you had to change. That gap is what a detection engineer maintains."])

saturday("2026-10-03")
sunday("2026-10-04",
       "Write, from memory, a search that correlates two sources without using "
       "join — then explain the job inspector output for it.",
       "SPL is six days deep and the most-tested skill on the board. Audit all of "
       "it, especially tstats and acceleration.",
       "Week 06 is knowledge objects, which is where SPL becomes something other "
       "people use.")


# =====================================================================
# WEEK 06 · Mon 5 – Sun 11 Oct · knowledge objects
# =====================================================================
day("2026-10-05", "trackA-2-5",
    "Knowledge objects I — saved searches, reports and alerts",
    [("study", "A saved search is a scheduled job", [
        "Search, schedule, time range, and the cron the scheduler actually uses.",
        "Real-time versus scheduled alerts, and why real-time alerts cost far more "
        "than people expect.",
        "The scheduler's window setting, and how it stops every alert firing at "
        "the top of the hour.",
      ]),
     ("study", "Alert conditions and actions", [
        "Trigger conditions: number of results, per-result, custom condition search.",
        "Throttling — suppress by field for a period. The single most useful "
        "setting for making an alert survivable.",
        "Actions: email, webhook, script, and writing to an index or lookup.",
      ]),
     ("lab", "Build an alert that behaves", [
        "Write an alert on your lab data that would fire constantly, then throttle "
        "it correctly.",
        "Add a webhook action pointed at a local listener so you can see the "
        "payload.",
        "Check the scheduler's own view: index=_internal sourcetype=scheduler.",
      ]),
     ("study", "Skipped searches", [
        "Why searches get skipped: concurrency limits, priority, overlapping "
        "schedules.",
        "Where to see it, and the first three fixes: stagger the cron, widen the "
        "window, reduce the range.",
      ])],
    ("Recall — alerts", [
        "Trap: 'Make it real-time so we do not miss anything.' Know the cost and "
        "the better answer.",
      ]),
    "trackB-1-4", "Sigma V — modifiers, wildcards and false positives",
    ["The modifier list in practice: contains, endswith, all, base64offset, re. "
     "Each one changes what the converted query looks like.",
     "Writing the falsepositives block honestly, because it is the field most "
     "people leave empty.",
     "Hands-on: take one of your rules and deliberately make it noisy, then tighten "
     "it. Record both versions."])

day("2026-10-06", "trackA-2-5",
    "Knowledge objects II — dashboards",
    [("study", "Classic XML and Dashboard Studio", [
        "Two dashboard systems in one product. Know which you are looking at and "
        "what each can do.",
        "Simple XML structure: rows, panels, searches, and the difference between "
        "inline and referenced searches.",
        "Why Studio exists and where it is still weaker.",
      ]),
     ("study", "Tokens, inputs and base searches", [
        "Tokens as the way inputs reach searches, and the eval token trick for "
        "conditional panels.",
        "Base searches and post-process: one search feeding several panels, and its "
        "limits.",
        "Why a dashboard with twelve independent searches is a performance problem "
        "you built yourself.",
      ]),
     ("lab", "Build one dashboard properly", [
        "Four panels over your lab data, driven by one base search and a time "
        "input.",
        "Add a dropdown that filters by sourcetype using a token.",
        "Open it and watch the searches in the job inspector — count how many "
        "actually ran.",
      ]),
     ("study", "The migration angle", [
        "You have rebuilt Splunk dashboards as Dynatrace notebooks. That is the "
        "same skill in two dialects.",
        "What does not translate cleanly, and how you validated parity. Shape this "
        "into a story tonight.",
      ])],
    ("Recall — dashboards", [
        "Likely follow-up: 'This dashboard takes 40 seconds to load. What do you "
        "do?'",
      ]),
    "trackB-1-4", "Sigma VI — rule quality and metadata",
    ["title, id, status, description, references, author, date, tags. Why every "
     "field earns its place in a repository.",
     "ATT&CK tags on rules, tying last week's Navigator layer to this week's rules.",
     "Hands-on: bring your rules up to repository standard. This is the start of "
     "the detection-rules artefact."])

day("2026-10-07", "trackA-2-5",
    "Knowledge objects III — macros, event types and tags",
    [("study", "Macros", [
        "A named piece of SPL with arguments. The tool that stops the same "
        "twenty-line filter being pasted into forty searches.",
        "Definition, arguments, validation, and the backtick syntax.",
        "Why a shared macro is also a shared point of failure.",
      ]),
     ("study", "Event types and tags", [
        "An event type names a set of events; a tag names a set of event types or "
        "field values.",
        "How tags make searches readable: tag=authentication instead of six ORs.",
        "This is the mechanism CIM is built on, which is why it matters before ES.",
      ]),
     ("lab", "Normalise one source by hand", [
        "Define event types over your lab data, tag them, and rewrite a search to "
        "use the tags.",
        "Build a macro for a filter you keep repeating and use it in three searches.",
        "Change the macro once and watch all three change. That is the point.",
      ]),
     ("study", "Where these live and who can see them", [
        "App scope, sharing, and the ordering problem when two apps define the same "
        "macro name.",
        "Debugging a macro that is not resolving: btool, then permissions, then "
        "spelling.",
      ])],
    ("Recall — macros, event types, tags", [
        "Trap: 'What is the difference between an event type and a tag?' A crisp "
        "one-sentence answer each.",
      ]),
    "trackB-1-4", "Sigma VII — a second backend",
    ["Convert the same rules to a second backend and read the differences. The "
     "rule did not change; the query language did.",
     "What this proves about vendor-neutral detection, and where the abstraction "
     "leaks.",
     "Keep both outputs. Being able to show one rule in two query languages is a "
     "strong interview moment."])

day("2026-10-08", "trackA-2-5",
    "Knowledge objects IV — lookups in depth",
    [("study", "The three kinds and their trade-offs", [
        "CSV lookups: simple, versioned in an app, awkward when they change often.",
        "KV store lookups: writable, indexed, and backed by the KV store on 8191.",
        "External and geospatial lookups in outline.",
      ]),
     ("study", "Automatic lookups", [
        "How LOOKUP- entries in props.conf attach a lookup to every search on a "
        "sourcetype.",
        "The performance cost, and how to spot one that is hurting you.",
        "Ordering when several automatic lookups apply.",
      ]),
     ("lab", "Build an asset lookup and use it", [
        "Make a CSV of hosts with owner and criticality. Attach it automatically to "
        "one sourcetype.",
        "Search using only the new fields and confirm they are there without an "
        "explicit lookup command.",
        "Then rebuild the same thing as a KV store collection and write to it from "
        "a search with outputlookup.",
      ]),
     ("study", "Keeping a lookup current", [
        "The scheduled-search-to-outputlookup pattern, and its failure mode: nobody "
        "notices when it stops.",
        "Why a stale lookup is worse than no lookup — it looks authoritative.",
      ])],
    ("Recall — lookups", [
        "Likely follow-up: 'How do you keep an asset list up to date inside "
        "Splunk?'",
      ]),
    "trackB-1-4", "Sigma VIII — testing a rule against real data",
    ["Generate the activity, run the converted rule, confirm it fires. If it does "
     "not fire, the rule is a draft, not a detection.",
     "Building a small test corpus so a rule can be re-tested after a change.",
     "Hands-on: prove three of your rules fire on activity you generate on VM2."])

day("2026-10-09", "trackA-2-5",
    "Knowledge objects V — field extraction and the knowledge bundle",
    [("study", "Every way a field can come to exist", [
        "Indexed fields, search-time extractions, calculated fields, lookups, "
        "event types and tags.",
        "The precedence between them when two produce the same field name.",
        "Calculated fields with EVAL- in props.conf, and why they are cheaper than "
        "an eval in every search.",
      ]),
     ("study", "The knowledge bundle", [
        "What the search head sends to the indexers before every search, and what "
        "is in it.",
        "Why a huge lookup file makes every search slower for everyone, and the "
        "replication blacklist that fixes it.",
        "Bundle push errors and where they appear.",
      ]),
     ("lab", "Inspect a bundle", [
        "Find the bundle directory on VM1 and look at what is actually being "
        "replicated.",
        "Add a large lookup, push again, and watch the size change.",
        "Blacklist it and confirm the bundle shrinks.",
      ]),
     ("study", "The week as one answer", [
        "Knowledge objects are how one person's search becomes forty people's "
        "tooling. Say it that way.",
        "Name the five object types and one reason each exists.",
      ])],
    ("Recall — knowledge objects overall", [
        "Trap: 'Why is every search on the cluster slower since Tuesday?' The "
        "bundle is a legitimate answer and few candidates give it.",
      ]),
    "trackB-1-4", "Sigma IX — maintaining rules over time",
    ["Versioning, deprecation, and what happens when the log source changes shape "
     "under a rule.",
     "CI for detections in outline: linting rules, converting them, running tests.",
     "Sketch what your own detection-rules repository will look like. You will "
     "build it in Week 14."])

saturday("2026-10-10")
sunday("2026-10-11",
       "Explain, without notes, every mechanism that can create a field, and which "
       "one wins when two collide.",
       "Knowledge objects and lookups. The bundle in particular — it is the kind of "
       "detail that marks real cluster experience.",
       "Week 07 is deployment and the start of troubleshooting.")


# =====================================================================
# WEEK 07 · Mon 12 – Sun 18 Oct · deployment, troubleshooting opens
# =====================================================================
day("2026-10-12", "trackA-2-6",
    "Deployment basics I — the deployment server and serverclass.conf",
    [("study", "What the deployment server is for", [
        "One place that decides which forwarder gets which app. Without it, config "
        "management is a spreadsheet and ssh.",
        "The vocabulary: deployment client, server class, deployment app, phone "
        "home.",
        "The phone-home interval and what it costs at ten thousand clients.",
      ]),
     ("study", "serverclass.conf", [
        "whitelist and blacklist by hostname, IP or client name, and the ordering "
        "of the two.",
        "restartSplunkd and restartSplunkWeb per app, and why getting this wrong "
        "restarts a fleet.",
        "stateOnClient: enabled, disabled, noop — the setting that decides whether "
        "the app is on when it lands.",
      ]),
     ("lab", "Push an app to VM2", [
        "Make VM1 a deployment server. Put a simple inputs app in "
        "etc/deployment-apps.",
        "Define a server class for VM2 and reload with ./splunk reload deploy-server.",
        "Watch the app arrive, confirm from the client with ./splunk list "
        "deploy-clients on the server.",
      ]),
     ("study", "When a client does not check in", [
        "The ordered checklist: deploymentclient.conf targetUri, 8089 reachable, "
        "clientName, server class match, phone home interval.",
        "Where both sides log it.",
      ])],
    ("Recall — the deployment server", [
        "Likely follow-up: 'How do you manage config on five hundred forwarders?'",
      ]),
    "trackB-1-4", "Sigma X — the wrap-up card",
    ["Ten evenings on the core authoring skill of detection engineering. Write the "
     "5-part card tonight.",
     "Safe claim once the card is clean twice: 'I write Sigma rules, convert them "
     "with pySigma pipelines, and test them against generated activity.'",
     "Not yet claimable: production detection engineering at scale. Keep the line "
     "honest."])

day("2026-10-13", "trackA-2-6",
    "Deployment basics II — apps, add-ons and forwarder management at scale",
    [("study", "What an app actually is", [
        "A directory with a known shape: default, local, metadata, bin, static.",
        "Technology add-ons versus apps: a TA carries parsing and field knowledge, "
        "an app carries the UI.",
        "Why local always beats default, and why an upgrade that overwrites local "
        "is the classic self-inflicted outage.",
      ]),
     ("study", "Managing a fleet", [
        "Naming and versioning deployment apps so you can say what is where.",
        "Rolling a change out to a subset first, and the server-class design that "
        "makes that possible.",
        "The forwarder upgrade question: what breaks, what does not, and why "
        "forwarders are usually safe to leave behind a version.",
      ]),
     ("lab", "Build and push a real TA", [
        "Write a small TA with props and transforms for one of your lab sources.",
        "Push it to VM2 with the deployment server, restart, and confirm the "
        "parsing changed.",
        "Then change it and push again. Watch the version discipline problem appear "
        "immediately.",
      ]),
     ("study", "Where deployment servers stop working", [
        "Client count limits and the tuning that goes with them.",
        "Why a deployment server is not a config management system, and where "
        "customers try to make it one.",
      ])],
    ("Recall — apps and add-ons", [
        "Trap: 'Why did our settings disappear after an app upgrade?' Answer with "
        "default versus local.",
      ]),
    "trackB-1-5", "Emulate and detect I — the detection lifecycle",
    ["The loop: idea, telemetry check, rule, test, tune, deploy, maintain. Skipping "
     "the test step is the most common failure.",
     "Detection as code: rules in git, reviewed, versioned, tested.",
     "Set up the loop on paper for the three rules you already wrote."])

day("2026-10-14", "trackA-2-6",
    "Deployment basics III — the deployer, and apps in a clustered world",
    [("study", "Three things that push config, and they are not the same", [
        "Deployment server pushes to forwarders. The deployer pushes to a search "
        "head cluster. The cluster manager pushes to indexer peers.",
        "Using the wrong one is a real and common mistake. Say each one's target "
        "out loud.",
        "Why a search head cluster member must never be a deployment client for "
        "its own apps.",
      ]),
     ("study", "The deployer and the shcluster bundle", [
        "apply shcluster-bundle, what it copies, and what it does to the members.",
        "Why local changes made on a member get overwritten, and where user-created "
        "objects actually live.",
        "The captain's role in replicating knowledge objects, which is a different "
        "mechanism entirely.",
      ]),
     ("lab", "Read the three paths on paper", [
        "Draw the deployment topology of your own lab, then draw what it would look "
        "like clustered.",
        "For each config file you have edited so far, say which mechanism would "
        "deliver it in production.",
        "This drawing is the artefact for the card.",
      ]),
     ("study", "The interview version", [
        "'How does config get to an indexer in a cluster?' has a precise answer and "
        "most candidates blur it.",
      ])],
    ("Recall — deployer versus deployment server", [
        "Trap: 'Just push it with the deployment server.' Know the three targets "
        "and their three tools.",
      ]),
    "trackB-1-5", "Emulate and detect II — Atomic Red Team",
    ["What Atomic Red Team is: small, safe, documented tests mapped to ATT&CK "
     "techniques.",
     "Reading an atomic before running it, so you know exactly what it changes on "
     "the host. Never run one blind.",
     "Hands-on: run two Linux atomics on VM2 and find the telemetry each produced."])

day("2026-10-15", "trackA-2-7",
    "Troubleshooting playbook I — the method and the internal indexes",
    [("study", "A method, not a list of tricks", [
        "Define the symptom precisely. Establish when it started. Establish what "
        "changed. Then bisect the pipeline.",
        "Input, parsing, indexing, search — the same four phases become the "
        "diagnostic frame.",
        "Say what you expect before you check. Being wrong on purpose is how you "
        "learn the system.",
      ]),
     ("study", "The internal indexes as instruments", [
        "index=_internal for splunkd's own view, sourcetype=splunkd for errors, "
        "component= to narrow.",
        "index=_audit for who did what, index=_introspection for resource usage.",
        "The metrics.log group fields: per-queue, per-index, per-sourcetype volume.",
      ]),
     ("lab", "Learn the searches before you need them", [
        "Build five saved searches you would want at 2am: ingestion by index, "
        "errors by component, blocked queues, forwarder connections, skipped "
        "searches.",
        "Break something on purpose and watch which one tells you first.",
      ]),
     ("study", "Queue blocking, read properly", [
        "A blocked queue upstream means the problem is downstream. Learn to read "
        "the chain in that direction.",
        "What blocked parsing versus blocked indexing each imply.",
      ])],
    ("Recall — the troubleshooting method", [
        "Likely follow-up: 'Ingestion has stopped for one source. Walk me through "
        "it.' The method is the answer.",
      ]),
    "trackB-1-5", "Emulate and detect III — closing the loop",
    ["Run an atomic, check whether your rule fires, tune, run again. Write down "
     "each iteration.",
     "What to do when the telemetry simply is not there: the answer is an "
     "onboarding change, not a cleverer rule.",
     "This is where Track A and Track B are the same job wearing two hats."])

day("2026-10-16", "trackA-2-7",
    "Troubleshooting playbook II — ingestion problems",
    [("study", "No data at all", [
        "The full chain, in order: source produces, forwarder reads, forwarder "
        "connects, indexer accepts, index exists, user can see it.",
        "The permission and fishbucket cases from Week 01, now inside a method.",
        "Licence violations and what actually stops when you exceed.",
      ]),
     ("study", "Data, but wrong", [
        "Wrong timestamps, wrong host, wrong sourcetype, events merged or split "
        "incorrectly. Each maps to a specific parsing setting.",
        "Duplicate events: the four causes and how to tell them apart.",
        "Missing events under load — queue blocking, and where the drop happened.",
      ]),
     ("lab", "Diagnose three broken sources", [
        "Break three things on purpose on VM2: permissions, a bad LINE_BREAKER, and "
        "a wrong index name.",
        "Fix each using only searches and logs, no memory of what you broke.",
        "Time yourself. Write the checklist you actually used.",
      ]),
     ("study", "The support-case shape", [
        "What a good escalation contains: symptom, scope, timeline, what you "
        "checked, what you ruled out.",
        "This is your day job. Say it as a process, not as an anecdote.",
      ])],
    ("Recall — ingestion troubleshooting", [
        "Trap: 'The forwarder is connected so the data must be arriving.' Name "
        "three ways both can be true and there is still no data.",
      ]),
    "trackB-1-5", "Emulate and detect IV — BOTS and investigation practice",
    ["Boss of the SOC v3 as a dataset: real attack traffic, already indexed, with "
     "questions to answer.",
     "Working an investigation with SPL rather than a rule — pivoting, not "
     "alerting.",
     "Hands-on: load the dataset and work three questions. Write down the pivots, "
     "not just the answers."])

saturday("2026-10-17")
sunday("2026-10-18",
       "Given 'ingestion stopped an hour ago', say every check in order without "
       "notes, and name the log that answers each.",
       "Deployment especially — the three push mechanisms are easy to blur and "
       "expensive to get wrong in an interview.",
       "Week 08 finishes troubleshooting, does the config-file reference, and "
       "opens clustering.")


# =====================================================================
# WEEK 08 · Mon 19 – Sun 25 Oct · troubleshooting closes, conf files,
#                                  clustering opens
# =====================================================================
day("2026-10-19", "trackA-2-7",
    "Troubleshooting playbook III — search and resource problems",
    [("study", "Slow, failing, or wrong", [
        "Three different symptoms with three different first checks. Do not treat "
        "them as one problem.",
        "Wrong results: permissions, search filters, time zone, or an accelerated "
        "summary that is behind.",
        "Failing searches: quotas, disk, memory limits, and the messages that "
        "actually say so.",
      ]),
     ("study", "Resource contention", [
        "CPU, memory, IO and the specific way Splunk uses each.",
        "index=_introspection for per-process resource usage, and the Monitoring "
        "Console views that summarise it.",
        "Concurrency: max_searches_per_cpu, the scheduler's share, and what "
        "happens when ad-hoc users take it all.",
      ]),
     ("lab", "Starve the lab on purpose", [
        "Run several heavy searches at once on VM1 and watch the queueing and "
        "skipping appear.",
        "Find it three ways: the UI message, _internal, and _introspection.",
        "Then fix it by changing one limit and confirm the change.",
      ]),
     ("study", "When it is not Splunk", [
        "Storage latency, network between tiers, a virtualisation host under "
        "pressure. How you would prove it is not the application.",
        "The professional value of being able to say 'it is not us' with evidence.",
      ])],
    ("Recall — search and resource troubleshooting", [
        "Likely follow-up: 'Scheduled searches are being skipped. What now?'",
      ]),
    "trackB-1-5", "Emulate and detect V — a second investigation",
    ["Work three more BOTS questions, this time timing yourself and writing the "
     "search before running it.",
     "Notice which SPL commands you reach for repeatedly. That set is your real "
     "working vocabulary.",
     "Keep the queries. They are evidence of hands-on investigation work."])

day("2026-10-20", "trackA-2-7",
    "Troubleshooting playbook IV — write the playbook, then use it",
    [("study", "Turning four days into one document", [
        "Structure it by symptom, not by component — that is how tickets arrive.",
        "Each entry: symptom, first three checks, the search that proves it, the "
        "usual cause.",
        "Keep it short enough that you would actually open it under pressure.",
      ]),
     ("study", "The escalation boundary", [
        "What you fix, what you escalate, and what you gather before you escalate.",
        "Diag files: what a diag contains and why you generate one before a "
        "restart, not after.",
        "Support case hygiene, which is a real differentiator for a TSE role.",
      ]),
     ("lab", "A mock ticket, start to finish", [
        "Have the lab in an unknown broken state — break it, wait a day, come back "
        "to it cold.",
        "Work it using only the playbook you wrote. Note every place the playbook "
        "failed you and fix those entries.",
      ]),
     ("study", "This is a resume line", [
        "'Built and worked from a written troubleshooting playbook' is worth more "
        "than a list of tools.",
        "Two clean reviews and it goes on. Not before.",
      ])],
    ("Recall — the playbook", [
        "Trap: 'Have you got a process, or do you just know it?' Have the document "
        "and be able to describe its shape.",
      ]),
    "trackB-1-5", "Emulate and detect VI — detection engineering as a job",
    ["What the role actually involves day to day: backlog, coverage, tuning, "
     "on-call feedback, metrics.",
     "Detection metrics that mean something: true positive rate, time to tune, "
     "coverage change over time.",
     "Where your observability background is an advantage: you already own the "
     "telemetry pipeline end of it."])

day("2026-10-21", "trackA-2-8",
    "Configuration files reference I — the files that matter",
    [("study", "The ten worth knowing cold", [
        "inputs, outputs, props, transforms, indexes, server, serverclass, "
        "deploymentclient, authentication, authorize.",
        "For each: one sentence on what it owns and which tier it belongs on.",
        "limits.conf as the eleventh, and why it is the one you touch last.",
      ]),
     ("study", "Where each file belongs", [
        "A settings-on-the-wrong-tier problem is silent: the file is valid, it "
        "simply never applies.",
        "Forwarder, indexer, search head, cluster manager — walk each file to its "
        "tier out loud.",
        "The .conf.spec files in etc/system/README as the authoritative reference "
        "you can read offline.",
      ]),
     ("lab", "Map your own lab", [
        "List every conf file you have edited across both VMs and say which tier "
        "and which layer each is in.",
        "Find one setting you put in the wrong place. There will be one.",
      ]),
     ("study", "Reading a spec file", [
        "How to answer a question you do not know the answer to, without internet "
        "access, in front of a customer.",
        "This skill is worth more than memorising any individual setting.",
      ])],
    ("Recall — the config file map", [
        "Likely follow-up: 'Which file, and on which server?' asked about five "
        "different settings in a row.",
      ]),
    "trackB-1-5", "Emulate and detect VII — tuning against a real corpus",
    ["Take your noisiest rule and tune it against BOTS data until the false "
     "positives are defensible.",
     "Record what you changed and why. Tuning history is what makes a detection "
     "repository trustworthy.",
     "The honest question to end on: would you page someone on this rule?"])

day("2026-10-22", "trackA-2-8",
    "Configuration files reference II — reading a deployment cold",
    [("study", "The order to look in", [
        "Topology first: what talks to what. Then data in. Then data out. Then who "
        "can see it.",
        "server.conf tells you the role of a box faster than anything else.",
        "What the presence of certain apps tells you about history.",
      ]),
     ("study", "Documenting what you find", [
        "A one-page deployment summary: tiers, counts, indexes, retention, "
        "authentication, notable customisations.",
        "Why this document is the first thing a new engineer should be handed and "
        "almost never is.",
      ]),
     ("lab", "Read your own lab as if it were a stranger's", [
        "Write the one-page summary for VM1 and VM2 from the config files alone.",
        "Check it against what you know. Every gap is a file you cannot yet read "
        "fluently.",
      ]),
     ("study", "The consultant version of this skill", [
        "Being dropped into an unfamiliar environment and having something useful "
        "to say in an hour.",
        "That is exactly what an implementation or migration engineer is paid for.",
      ])],
    ("Recall — reading a deployment", [
        "Trap: 'How would you get up to speed on our environment?' Have a method, "
        "not enthusiasm.",
      ]),
    "trackB-1-5", "Emulate and detect VIII — the wrap-up card",
    ["Eight evenings. Write the 5-part card on the detection lifecycle, with the "
     "emulate-tune-retest loop as the elevator answer.",
     "Safe claim: 'I run adversary emulation with Atomic Red Team and tune "
     "detections against the telemetry it produces.'",
     "Keep the iteration notes. They are the proof behind the claim."])

day("2026-10-23", "trackA-3-1",
    "Clustering I — why cluster, and the two numbers that define it",
    [("study", "What clustering is actually for", [
        "Availability of data, and availability of search. Two different problems "
        "solved by two different clusters.",
        "Indexer clustering replicates buckets. Search head clustering replicates "
        "configuration and scheduling.",
        "Why neither is a backup, and why saying so in an interview is a good sign.",
      ]),
     ("study", "Replication factor and search factor", [
        "RF is how many copies of the raw data exist. SF is how many of those are "
        "searchable, with index files.",
        "SF can never exceed RF. The disk cost of each searchable copy.",
        "What survives the loss of one peer at RF=3 SF=2, said precisely.",
      ]),
     ("study", "The components", [
        "Cluster manager, peer nodes, search heads, and where the manager is and is "
        "not in the data path.",
        "What happens to the cluster when the manager is down — less than people "
        "expect, and worth knowing exactly.",
      ]),
     ("lab", "Turn VM3 on and plan the cluster", [
        "Bring up the spare VM and get Splunk installed and clean on it.",
        "Write down the topology you are about to build and the RF and SF you will "
        "set, with a reason for each.",
      ])],
    ("Recall — RF and SF", [
        "Trap: 'We have RF=3 so we can lose two indexers, right?' Know what is "
        "true and what is not.",
      ]),
    "trackB-1-6", "AWS identity I — the model",
    ["Users, groups, roles, policies. The role is the important one and the one "
     "people understand last.",
     "Identity-based versus resource-based policies, and how the two combine.",
     "Hands-on: in a free-tier account, create a role and assume it. Read the "
     "resulting CloudTrail event end to end."])

saturday("2026-10-24")
sunday("2026-10-25",
       "Walk a broken environment from symptom to root cause out loud, naming the "
       "file and the tier at every step.",
       "The config-file map and the playbook. Both are reference knowledge that "
       "decays fast without a second pass.",
       "Week 09 is clustering, all week — the deepest Track A topic left.")


# =====================================================================
# WEEK 09 · Mon 26 – Sun 1 Nov · clustering, all week
# =====================================================================
day("2026-10-26", "trackA-3-1",
    "Clustering II — the manager, the peers and bucket states",
    [("study", "How a bucket becomes replicated", [
        "A hot bucket exists on one peer and is streamed to its replication "
        "targets as it is written.",
        "Primary and searchable copies: which peer answers a search for a given "
        "bucket.",
        "Bucket fixing: what the manager does when a copy goes missing.",
      ]),
     ("study", "Cluster states and what they mean", [
        "Complete, incomplete, and the difference between 'all data searchable' and "
        "'replication factor met'.",
        "The manager's dashboard and the CLI equivalents: ./splunk show "
        "cluster-status and the REST endpoints behind it.",
        "Why a cluster can be searchable and still not safe.",
      ]),
     ("lab", "Build the cluster", [
        "Make VM1 the manager and cluster peers of VM2 and VM3 with a small RF and "
        "SF.",
        "Index data, then look at the bucket directories on both peers and identify "
        "which copies are searchable.",
        "Read cluster-status and say what every field means before you look it up.",
      ]),
     ("study", "The manager is a coordinator, not a proxy", [
        "It never sees your data. Say why that matters for sizing and for failure "
        "planning.",
      ])],
    ("Recall — bucket replication", [
        "Likely follow-up: 'Where does a search for last Tuesday's data actually "
        "run in a cluster?'",
      ]),
    "trackB-1-6", "AWS identity II — STS and AssumeRole",
    ["Temporary credentials, the assume-role call, session names and durations.",
     "Why AssumeRole events are the backbone of cloud detection: they are how "
     "privilege actually moves.",
     "Hands-on: chain two roles, then find both hops in CloudTrail and note which "
     "fields tie them together."])

day("2026-10-27", "trackA-3-1",
    "Clustering III — search head clustering",
    [("study", "What an SHC replicates", [
        "Configuration through the deployer, and knowledge objects through the "
        "replication of the members' own state.",
        "The captain: what it schedules, what it coordinates, and why it is elected "
        "rather than configured.",
        "Why an even number of members is a bad idea.",
      ]),
     ("study", "Captain election and quorum", [
        "How an election is triggered and what happens during one.",
        "Static captain as an emergency measure, and its cost.",
        "The split-brain scenario and why quorum exists.",
      ]),
     ("lab", "Read the SHC surface without building one", [
        "Your lab has three boxes and two are peers; building an SHC properly needs "
        "more than you have.",
        "Instead: read the full command surface — ./splunk show shcluster-status, "
        "bootstrap, add-shcluster-member, apply shcluster-bundle — and write down "
        "what each does.",
        "Say plainly on the card that this topic is read, not run. Honesty here is "
        "the whole point of the audit habit.",
      ]),
     ("study", "Where user objects live in an SHC", [
        "Created on one member, replicated to the others. What happens to them when "
        "a member is removed.",
        "Why the deployer must not push things that members create themselves.",
      ])],
    ("Recall — search head clustering", [
        "Trap: 'Do you deploy apps to a search head cluster with the deployment "
        "server?' Know why not.",
      ]),
    "trackB-1-6", "AWS identity III — Organizations and SCPs",
    ["Accounts as a boundary, organizational units, and service control policies as "
     "a ceiling rather than a grant.",
     "Why an SCP denying an action beats any identity policy allowing it.",
     "Hands-on: read a real-world SCP example and predict what it blocks before "
     "reading the explanation."])

day("2026-10-28", "trackA-3-1",
    "Clustering IV — maintenance, rolling restarts and upgrades",
    [("study", "Maintenance mode", [
        "What it stops the manager doing, and why you enter it before planned work.",
        "The cost of forgetting to leave it: bucket fixing never resumes and "
        "nobody notices for days.",
      ]),
     ("study", "Rolling restart", [
        "How the manager sequences peer restarts to keep data searchable.",
        "searchable rolling restart and what it costs in time.",
        "Why a rolling restart is not free and should not be routine.",
      ]),
     ("study", "Upgrading a cluster", [
        "The order: manager, then peers, then search heads. Why that order and not "
        "another.",
        "Version compatibility between tiers during the upgrade window.",
        "Your post-upgrade validation experience belongs here — shape it "
        "into a story tonight.",
      ]),
     ("lab", "Do a rolling restart and watch it", [
        "Enter maintenance mode, restart a peer, and observe the cluster status "
        "through the whole cycle.",
        "Then do a proper rolling restart and time it.",
      ])],
    ("Recall — cluster maintenance", [
        "Likely follow-up: 'Walk me through upgrading a clustered deployment.' "
        "Order, validation, rollback.",
      ]),
    "trackB-1-6", "AWS identity IV — CloudTrail in depth",
    ["Management events versus data events, and why data events are off by default "
     "and expensive on.",
     "The event record structure: userIdentity, eventSource, eventName, "
     "requestParameters, responseElements.",
     "Hands-on: onboard CloudTrail JSON into Splunk on VM1 and write three "
     "searches over it. Both tracks in one exercise."])

day("2026-10-29", "trackA-3-1",
    "Clustering V — failure scenarios",
    [("study", "Losing a peer", [
        "What happens immediately, what the manager does next, and how long "
        "recovery takes.",
        "Why the cluster gets slower during fixing, and what that means for a "
        "customer conversation.",
      ]),
     ("study", "Losing the manager, or the whole site", [
        "What still works without a manager and what stops.",
        "Manager redundancy options and their honest limitations.",
        "The disk-full peer: the failure that looks like a network problem.",
      ]),
     ("lab", "Break the cluster three ways", [
        "Stop a peer and watch fixing run. Fill a peer's disk and watch a different "
        "failure. Stop the manager and see what still searches.",
        "Write the symptom, the log line, and the recovery for each.",
      ]),
     ("study", "The answer that shows real experience", [
        "Most candidates can define RF and SF. Far fewer can describe what the "
        "cluster does in the ten minutes after a peer dies.",
        "That difference is the whole reason this topic gets six days.",
      ])],
    ("Recall — cluster failure", [
        "Trap: 'Is the data safe if we lose two peers at RF=3?' Give the precise "
        "answer, including what happens to in-flight hot buckets.",
      ]),
    "trackB-1-6", "AWS identity V — GuardDuty and CloudWatch",
    ["GuardDuty as managed detection: what it covers, what it does not, and how its "
     "findings are structured.",
     "CloudWatch Logs versus CloudTrail versus VPC Flow Logs — three different "
     "questions answered by three different sources.",
     "Hands-on: read one GuardDuty finding in full and map it to an ATT&CK "
     "technique."])

day("2026-10-30", "trackA-3-1",
    "Clustering VI — multisite, and the whole topic as one answer",
    [("study", "Multisite clustering", [
        "site_replication_factor and site_search_factor: origin and total.",
        "Search affinity, and why a search head prefers its own site.",
        "When multisite is the right answer and when it is expensive theatre.",
      ]),
     ("study", "Sizing a cluster", [
        "Daily volume, retention, RF and SF, and the arithmetic that turns those "
        "into disk and peer count.",
        "Indexer count driven by search concurrency rather than storage — the case "
        "people miss.",
      ]),
     ("lab", "Size one on paper and defend it", [
        "Given 200GB/day, 90-day retention, RF=3 SF=2, produce a peer count and a "
        "disk figure with the working shown.",
        "State every assumption. An answer without assumptions is a guess.",
      ]),
     ("study", "Six days into two minutes", [
        "Say the whole topic: why cluster, the two numbers, the components, one "
        "failure, one maintenance procedure.",
        "This is the strongest single Track A card on the board once it is clean "
        "twice.",
      ])],
    ("Recall — clustering overall", [
        "Likely follow-up: 'Design an indexer cluster for this customer.' The "
        "questions you ask first are half the answer.",
      ]),
    "trackB-1-6", "AWS identity VI — Access Analyzer and least privilege",
    ["Access Analyzer for external access findings, and policy generation from "
     "CloudTrail history.",
     "Why least privilege in AWS is an iterative process rather than a design "
     "decision.",
     "Hands-on: generate a policy from your own account activity and read what it "
     "produced."])

saturday("2026-10-31")
sunday("2026-11-01",
       "Design a cluster out loud for a stated volume and retention, then describe "
       "what happens in the ten minutes after a peer fails.",
       "Clustering. Six days deep and the topic most likely to be probed hard for "
       "a 3+ year role.",
       "Week 10 is SmartStore, ACS and the Monitoring Console.")


# =====================================================================
# WEEK 10 · Mon 2 – Sun 8 Nov · SmartStore, ACS, Monitoring Console
# =====================================================================
day("2026-11-02", "trackA-3-2",
    "SmartStore I — decoupling storage from compute",
    [("study", "What SmartStore changes", [
        "Warm buckets live in object storage; the indexer keeps a local cache. "
        "Compute and storage scale separately.",
        "What does not change: hot buckets are still local, and parsing and "
        "indexing are unchanged.",
        "Why this is the architecture behind Splunk Cloud, which makes it worth "
        "more than its two days.",
      ]),
     ("study", "The cache manager", [
        "Eviction policy, how a search pulls a bucket back, and what a cache miss "
        "costs in search time.",
        "hotlist_recency_secs and the settings that keep recent data local.",
        "Why a badly sized cache turns a fast cluster into a slow one without any "
        "error appearing.",
      ]),
     ("study", "What it means for the admin", [
        "Bucket lifecycle changes: no more cold tier in the old sense.",
        "Retention is now driven by the remote store, and freezing works "
        "differently.",
        "Backup and disaster recovery become the object store's problem, which is "
        "a real advantage worth stating.",
      ]),
     ("lab", "Read the configuration surface", [
        "Your lab has no object store, so this is a reading day: indexes.conf "
        "remotePath, the volume stanza with storageType=remote, and the "
        "cachemanager settings in server.conf.",
        "Write down exactly which settings you would need and where. Mark the card "
        "as read, not run.",
      ])],
    ("Recall — SmartStore", [
        "Trap: 'So searches are slower with SmartStore?' The honest answer is "
        "'sometimes, and here is exactly when'.",
      ]),
    "trackB-1-6", "AWS identity VII — logging architecture across accounts",
    ["Organization trails, a central logging account, and why CloudTrail should "
     "never live only in the account it watches.",
     "S3 bucket policies and KMS for log integrity, plus log file validation.",
     "Sketch the multi-account logging design you would propose. One page."])

day("2026-11-03", "trackA-3-2",
    "SmartStore II — migration and when not to use it",
    [("study", "Migrating an existing index", [
        "The one-way nature of it, and why that makes the decision a real one.",
        "What happens to existing buckets during migration and how long it takes.",
        "The prerequisites people miss: cluster health, version, and free local "
        "disk during the move.",
      ]),
     ("study", "When SmartStore is the wrong answer", [
        "Small deployments where the operational complexity buys nothing.",
        "Workloads that search old data constantly, where the cache never helps.",
        "High-latency object storage, where every miss is felt.",
      ]),
     ("study", "The conversation with a customer", [
        "What they gain: elastic capacity, cheaper long retention, simpler DR.",
        "What they give up: predictable search latency on cold data, and some "
        "operational simplicity.",
        "Name both sides. C5 applies to your own advice too — state the costs, do "
        "not push the choice.",
      ]),
     ("lab", "Write the migration runbook", [
        "Produce the steps you would follow, with the check at each stage that "
        "tells you it is safe to continue.",
        "Include the rollback position at each step, even where the honest answer "
        "is 'there is none past here'.",
      ])],
    ("Recall — SmartStore migration", [
        "Likely follow-up: 'Would you recommend SmartStore for this customer?' "
        "Give the conditions, not a verdict.",
      ]),
    "trackB-1-6", "AWS identity VIII — detections over CloudTrail",
    ["The classic ones: root usage, MFA disabled, access key created, policy "
     "attached, trail stopped.",
     "Writing two of them as Sigma rules and converting to SPL against the data "
     "you onboarded last week.",
     "The noise problem: automation looks exactly like an attacker in CloudTrail. "
     "Tune accordingly."])

day("2026-11-04", "trackA-3-3",
    "ACS I — administering Splunk Cloud without a shell",
    [("study", "What ACS is", [
        "The Admin Config Service: a REST API for the Cloud admin tasks that used "
        "to need a support case.",
        "Authentication with a bearer token, and where that token comes from.",
        "The CLI wrapper, and why the API is worth knowing directly anyway.",
      ]),
     ("study", "What you can actually do with it", [
        "Index management, HEC tokens, IP allow lists, private apps, users and "
        "roles, outbound ports.",
        "What still needs a support case, which is the boundary that defines Cloud "
        "admin work.",
      ]),
     ("study", "Why this topic matters more than it looks", [
        "Half the Splunk jobs on the market now are Cloud, and Cloud admin is a "
        "different daily job to Enterprise admin.",
        "Being able to say 'I know what I can and cannot do myself on Cloud' is a "
        "differentiator at your level.",
      ]),
     ("lab", "Read the API surface properly", [
        "Go through the ACS endpoint reference and write the curl call you would "
        "use for five common tasks.",
        "No tenant to run against, so mark the card as read. Say so plainly in "
        "interviews too.",
      ])],
    ("Recall — ACS", [
        "Trap: 'On Cloud, how do you add an index?' Know the ACS answer and the "
        "UI answer, and when each applies.",
      ]),
    "trackB-1-6", "AWS identity IX — IMDS, instance roles and credential theft",
    ["How an EC2 instance gets credentials, what IMDSv1 allowed, and what IMDSv2 "
     "changed.",
     "SSRF to credential theft as a chain, and what each step looks like in logs.",
     "Hands-on: read the CloudTrail signature of credentials used from outside the "
     "instance they were issued to."])

day("2026-11-05", "trackA-3-3",
    "ACS II — the Cloud admin's week",
    [("study", "The recurring jobs", [
        "Onboarding a source on Cloud: what changes when you have no filesystem.",
        "Private app packaging and vetting, and how long that actually takes.",
        "Token and allow-list management as a routine, not an event.",
      ]),
     ("study", "Cloud constraints as an architecture", [
        "No shell, no btool, no direct conf editing. What replaces each.",
        "The support boundary: what Splunk operates and what you still own.",
        "Why heavy forwarders often reappear in Cloud designs, and what problem "
        "they solve there.",
      ]),
     ("lab", "Redo an Enterprise task the Cloud way", [
        "Take the onboarding runbook from Week 02 and rewrite it for Cloud, step by "
        "step.",
        "Every step that used a shell needs a replacement. Find all of them.",
      ]),
     ("study", "Your own Cloud experience, stated accurately", [
        "You have supported Splunk Cloud in production. Be precise about which parts you "
        "operated and which parts Splunk did.",
        "Precision here reads as seniority. Vagueness reads as inflation.",
      ])],
    ("Recall — Cloud administration", [
        "Likely follow-up: 'What is different about running Splunk Cloud versus "
        "Enterprise?' Have four concrete differences.",
      ]),
    "trackB-1-6", "AWS identity X — the wrap-up card",
    ["Ten evenings across IAM, STS, Organizations, CloudTrail, GuardDuty and "
     "Access Analyzer. Write the 5-part card.",
     "Safe claim: 'I can read and reason about AWS identity events and design "
     "multi-account log collection.'",
     "Not yet: securing a production AWS estate. The labs next week move that line "
     "a little, not all the way."])

day("2026-11-06", "trackA-4-1",
    "Monitoring Console — the platform watching itself (awareness)",
    [("study", "What the MC is", [
        "A pre-built app over the internal indexes. Nothing it shows is unavailable "
        "to a search you could write yourself.",
        "Standalone versus distributed mode, and what setting it up in distributed "
        "mode actually requires.",
      ]),
     ("study", "The views worth knowing", [
        "Indexing performance, search activity, resource usage, forwarder "
        "connections, licence usage.",
        "How to read the indexing queue view, which is the one you will use most.",
      ]),
     ("lab", "Set it up and read it", [
        "Enable the MC on VM1 in distributed mode against your cluster peers.",
        "Generate load, then find the same fact three ways: MC view, _internal "
        "search, and a metrics.log line.",
      ]),
     ("study", "Awareness depth, and why", [
        "The contract marks this topic aware, not must. The reason: the MC is a "
        "convenience over knowledge you already have.",
        "Claim familiarity, not expertise. The underlying searches are the real "
        "skill.",
      ])],
    ("Recall — Monitoring Console", [
        "Trap: 'Do you need the MC to troubleshoot?' No, and knowing why is the "
        "better answer.",
      ]),
    "trackB-1-7", "Cloud labs I — flaws.cloud",
    ["A guided vulnerable AWS environment. Work the first levels and read the "
     "explanation for each one after solving it.",
     "What each level teaches about a real misconfiguration, not just the trick to "
     "beat it.",
     "Write down which CloudTrail events your own actions would have produced."])

saturday("2026-11-07")
sunday("2026-11-08",
       "Explain SmartStore's trade-off precisely, then list four ways Cloud admin "
       "differs from Enterprise admin.",
       "SmartStore and ACS were both read rather than run. Audit them harder for "
       "exactly that reason.",
       "Week 11 is the awareness layer: Cloud, Victoria, upgrades and 10.x.")


# =====================================================================
# WEEK 11 · Mon 9 – Sun 15 Nov · the awareness layer
# =====================================================================
day("2026-11-09", "trackA-4-2",
    "Splunk Cloud basics I — what actually changes (awareness)",
    [("study", "The shape of the service", [
        "What Splunk operates, what you configure, and where the line sits.",
        "Ingest-based and workload-based pricing in outline, and why the pricing "
        "model changes design decisions.",
        "Stack sizing and what a search head or indexer even means when you cannot "
        "see them.",
      ]),
     ("study", "Getting data in on Cloud", [
        "The Splunk Cloud data manager, HEC, forwarders with the Cloud credentials "
        "package, and inputs data managers for cloud services.",
        "Why the universal forwarder story is almost unchanged, and what the "
        "credentials package actually contains.",
      ]),
     ("lab", "Reading day, done properly", [
        "Work through the Cloud admin documentation and write your own comparison "
        "table against Enterprise.",
        "One row per admin task, three columns: Enterprise, Cloud, who does it.",
      ]),
     ("study", "The honest claim", [
        "You supported Cloud in production. That is real experience with the "
        "product, and worth stating clearly.",
        "It is not the same as having architected a Cloud stack. Keep them "
        "separate when you speak.",
      ])],
    ("Recall — Splunk Cloud", [
        "Likely follow-up: 'What can you not do on Cloud?' A confident, specific "
        "list is impressive here.",
      ]),
    "trackB-1-7", "Cloud labs II — finishing flaws.cloud",
    ["Complete the remaining levels. Write one sentence per level on the "
     "misconfiguration it represents.",
     "Group them: public access, over-permissive roles, credential exposure, "
     "metadata abuse.",
     "That grouping is the beginning of your own cloud security checklist."])

day("2026-11-10", "trackA-4-2",
    "Splunk Cloud basics II — the support boundary (awareness)",
    [("study", "What a support case is for on Cloud", [
        "The tasks that are still Splunk's: certain config changes, stack resizing, "
        "some app installs, anything at the infrastructure layer.",
        "What a good Cloud support case contains, from the customer side and from "
        "yours.",
      ]),
     ("study", "Maintenance windows and upgrades", [
        "Splunk upgrades your stack. What you get told, when, and what you should "
        "validate afterwards.",
        "Why post-upgrade validation is still your job, which is exactly the work "
        "you have done in production.",
      ]),
     ("lab", "Write the validation checklist", [
        "Produce the post-upgrade validation list you would run on a Cloud stack: "
        "ingestion, searches, alerts, dashboards, integrations.",
        "You have done this for real. Write down the version you actually used.",
      ]),
     ("study", "Where TSE work lives on Cloud", [
        "The support engineer's daily job on Cloud is triage, data problems and "
        "the boundary itself.",
        "That is your existing job. Say it in the language of the role you are "
        "applying for.",
      ])],
    ("Recall — the Cloud support boundary", [
        "Trap: 'Splunk manages it, so there is nothing to do.' Name five things "
        "that remain yours.",
      ]),
    "trackB-1-7", "Cloud labs III — CloudGoat, first scenarios",
    ["A deliberately vulnerable AWS environment you deploy yourself with Terraform. "
     "Destroy it when you are done, every time.",
     "Work two scenarios and keep notes on the privilege escalation path in each.",
     "Cost discipline: check the account afterwards. A forgotten resource is a "
     "real bill."])

day("2026-11-11", "trackA-4-5",
    "Victoria Experience — what it is and why it matters (awareness)",
    [("study", "Victoria versus Classic", [
        "Two Splunk Cloud experiences with different app installation, different "
        "administration and different limits.",
        "Self-service app installation on Victoria, and the vetting that goes with "
        "it.",
        "How you tell which one a stack is, and why a customer might still be on "
        "Classic.",
      ]),
     ("study", "What changes for the admin", [
        "ACS coverage differs between them. So do the available endpoints and "
        "self-service tasks.",
        "Migration between them exists and is a project, not a setting.",
      ]),
     ("lab", "Extend the comparison table", [
        "Add a Victoria column to Monday's table. Fill it from the documentation.",
        "Mark the rows where you are unsure. Unsure and marked beats confident and "
        "wrong.",
      ]),
     ("study", "How to talk about it", [
        "This is a term that appears in job descriptions and that many candidates "
        "cannot define.",
        "Two clear sentences here reads as current knowledge of the product.",
      ])],
    ("Recall — Victoria", [
        "Likely follow-up: 'Have you worked on Victoria or Classic?' Answer "
        "precisely about what you have seen.",
      ]),
    "trackB-1-7", "Cloud labs IV — CloudGoat, harder scenarios",
    ["Two more scenarios, this time writing down the detection opportunity at each "
     "step of the attack.",
     "Which CloudTrail events would have caught you, and which would have been "
     "invisible.",
     "That list is a detection backlog. Keep it."])

day("2026-11-12", "trackA-4-3",
    "The upgrade process — Enterprise, end to end (awareness)",
    [("study", "Before you touch anything", [
        "Release notes and the deprecation list. Checking app compatibility, "
        "including Python version changes.",
        "Backups: what is actually worth backing up on each tier.",
        "The rollback plan, written before the upgrade, not during it.",
      ]),
     ("study", "The upgrade itself", [
        "Order across tiers, the migration prompt, and what happens to conf files "
        "on upgrade.",
        "Forwarders last, and usually not at all in the same window.",
      ]),
     ("lab", "Upgrade the lab", [
        "Snapshot first. Upgrade VM1, then the peers, in the correct order.",
        "Validate after each step with your own checklist from Tuesday.",
        "If something breaks, fix it before rolling back. The failure is the "
        "lesson.",
      ]),
     ("study", "The interview story", [
        "You did post-upgrade validation in production. Now you have also driven an "
        "upgrade yourself, in a lab, and can say what you checked.",
        "State which was production and which was lab. Always.",
      ])],
    ("Recall — upgrades", [
        "Trap: 'Do you upgrade forwarders at the same time?' Know the compatibility "
        "rule and why it exists.",
      ]),
    "trackB-1-7", "Cloud labs V — Stratus Red Team",
    ["Atomic Red Team's cloud equivalent: granular, documented cloud attack "
     "techniques you can run and then revert.",
     "Run three techniques, capture the telemetry, and check them against the "
     "detection backlog you wrote yesterday.",
     "Warm up, detonate, revert. Use the revert every time."])

day("2026-11-13", "trackA-4-4",
    "Splunk 10.x currency — what is new and why (awareness)",
    [("study", "Reading a major release honestly", [
        "Go to the official release notes first, not a blog. Note the version you "
        "are reading and the date.",
        "Separate: new features, changed defaults, deprecations, removals. "
        "Deprecations matter most to an admin.",
        "Anything you cannot verify in the docs is tagged unverified in your notes. "
        "The same rule this project runs on.",
      ]),
     ("study", "What to actually remember", [
        "Three or four genuine changes, said accurately, beats a list you half "
        "recall.",
        "Where a change affects something you learned earlier this term — that is "
        "the connection worth making.",
      ]),
     ("lab", "Write the currency note", [
        "One page: version, date read, source link, the changes that matter to an "
        "admin, and what you have not verified.",
        "This note is what keeps you current after the term ends. Plan to redo it "
        "each release.",
      ]),
     ("study", "The awareness layer is finished today", [
        "Five awareness topics done. None of them go on the resume as expertise.",
        "What they buy you: not being surprised by a question. That is enough.",
      ])],
    ("Recall — release currency", [
        "Likely follow-up: 'What is new in the latest Splunk release?' Answer with "
        "three specifics and where you read them.",
      ]),
    "trackB-1-7", "Cloud labs VI — writing the detections",
    ["Turn the best three items from the detection backlog into Sigma rules and "
     "convert them to SPL.",
     "Test them against the CloudTrail data your own lab activity produced.",
     "Three tested cloud detections, written by you, against attacks you ran. That "
     "is a portfolio piece."])

saturday("2026-11-14")
sunday("2026-11-15",
       "Answer four awareness questions in a row — Cloud, Victoria, upgrades, "
       "10.x — in two sentences each, no padding.",
       "The awareness topics are the easiest to over-claim. Audit for exactly that.",
       "Weeks 12 and 13 are Enterprise Security — the last and largest Track A "
       "topic.")


# =====================================================================
# WEEK 12 · Mon 16 – Sun 22 Nov · Enterprise Security, first half
# =====================================================================
day("2026-11-16", "trackA-6-1",
    "ES I — what Enterprise Security actually is",
    [("study", "A premium app, not a product apart", [
        "ES runs on Splunk. Everything you learned about indexes, knowledge "
        "objects, data models and acceleration is what ES is built from.",
        "That is why the contract puts it last: without the rest, ES is a UI you "
        "cannot reason about.",
        "Licensing and deployment shape: dedicated search head, and what that costs.",
      ]),
     ("study", "The moving parts", [
        "Data models and their acceleration, correlation searches, notable events, "
        "the incident review UI, adaptive response.",
        "Where each of those actually lives, in terms you already know.",
        "The ES search head is a search head. Everything about SHC still applies.",
      ]),
     ("study", "Where it sits against your experience", [
        "You did SOC alert investigation and multi-source correlation in production. "
        "That is the analyst side of this app.",
        "The admin side — content management, tuning, data model health — is what "
        "these two weeks add.",
      ]),
     ("lab", "Set expectations for the fortnight", [
        "You may not have an ES licence. Plan honestly: which parts you can run, "
        "which you will read.",
        "Splunk Security Essentials is free and shows much of the same content "
        "shape. Install it on VM1 and use it where ES itself is out of reach.",
      ])],
    ("Recall — what ES is", [
        "Trap: 'Is ES a SIEM or is Splunk a SIEM?' Have a precise answer about "
        "what the app adds.",
      ]),
    "trackB-1-7", "Cloud labs VII — the wrap-up",
    ["Eight evenings of cloud attack and detect. Write the 5-part card on cloud "
     "attack paths and their telemetry.",
     "Safe claim: 'I have run cloud attack simulations and written detections "
     "against the resulting CloudTrail evidence.'",
     "Collect the rules and notes in one place. They are the security-telemetry "
     "capstone's raw material."])

day("2026-11-17", "trackA-6-1",
    "ES II — CIM and normalisation",
    [("study", "Why a common model exists", [
        "Forty products log an authentication forty ways. A detection cannot be "
        "written per product.",
        "The Common Information Model is a set of data models with agreed field "
        "names, and a set of tags to select events into them.",
        "This is Week 06's event types and tags, at scale and with a standard.",
      ]),
     ("study", "Making a source CIM compliant", [
        "The work: field aliases, calculated fields, event types, tags — mapped to "
        "the model's expected fields.",
        "Why a good TA does most of this for you, and what you do when there is no "
        "TA.",
        "Validating compliance: the data model audit, and searching the model "
        "rather than the index.",
      ]),
     ("lab", "Make one lab source CIM compliant", [
        "Install the CIM app on VM1. Pick your auth data and map it into the "
        "Authentication model by hand.",
        "Prove it with a tstats search against the model that returns your events.",
        "This one exercise is the whole topic in miniature.",
      ]),
     ("study", "Why this is the highest-value ES skill", [
        "Most ES problems are data problems. An engineer who can fix CIM "
        "compliance is worth more than one who can click through notables.",
        "It is also directly your onboarding skill, one layer up.",
      ])],
    ("Recall — CIM", [
        "Likely follow-up: 'A correlation search returns nothing. Where do you "
        "start?' CIM compliance is the right first answer.",
      ]),
    "trackB-1-7", "Cloud labs VIII — closing the loop on cloud detection",
    ["Re-run two earlier scenarios and confirm your rules now fire. A detection "
     "you have not re-tested is a claim, not a control.",
     "Note what changed in the environment between runs. Drift is the real enemy.",
     "Tear everything down and verify the account is clean."])

day("2026-11-18", "trackA-6-1",
    "ES III — notable events and incident review",
    [("study", "What a notable event is", [
        "An event written to a dedicated index by a correlation search, with "
        "status, urgency, owner and a lifecycle.",
        "Why it is a workflow object rather than a log line.",
        "How urgency is derived from severity and asset priority — which is why "
        "assets matter next week.",
      ]),
     ("study", "The incident review workflow", [
        "Triage, assignment, investigation, closure. The statuses and who can "
        "change them.",
        "What good looks like: notables that get closed with a reason, not "
        "abandoned.",
        "Where analysts and admins disagree, and why tuning is the answer to both.",
      ]),
     ("lab", "Follow one notable end to end", [
        "In Security Essentials or ES if you have it, trace one piece of content "
        "from search to notable to review.",
        "Write down each object involved. Every one of them is something you "
        "learned in Weeks 04-06.",
      ]),
     ("study", "The analyst answer you already have", [
        "Your SOC investigation work is this workflow. Describe it in ES "
        "vocabulary tonight.",
        "Do not claim you administered ES. Claim you investigated. The difference "
        "is the whole point of the honesty rule.",
      ])],
    ("Recall — notable events", [
        "Trap: 'Is a notable an alert?' Know the distinction and why it matters "
        "operationally.",
      ]),
    "trackB-1-8", "Cloud-native I — containers and Kubernetes security basics",
    ["The attack surface: images, registries, the runtime, the orchestrator, and "
     "the network between pods.",
     "Where the security telemetry comes from: audit logs, runtime sensors, and "
     "the control plane.",
     "Your day job deploys OneAgent across Kubernetes clusters. That is real "
     "context — name what you have actually seen."])

day("2026-11-19", "trackA-6-1",
    "ES IV — correlation searches",
    [("study", "Anatomy of a correlation search", [
        "A scheduled search over an accelerated data model, with a trigger "
        "condition and a notable-creating action.",
        "Why they are written against data models and not indexes.",
        "Scheduling, throttling and the same skipped-search problems from Week 06.",
      ]),
     ("study", "Tuning as the real work", [
        "Every out-of-the-box correlation search is a starting point, never a "
        "finished control.",
        "Suppression, allow lists, and adjusting thresholds — and recording why "
        "each was done.",
        "The governance question: who is allowed to disable a detection.",
      ]),
     ("lab", "Write one, by hand", [
        "Write a search against the CIM Authentication model that would make a "
        "sensible correlation search.",
        "Define the trigger condition and the throttling you would set, and say "
        "what would make it noisy.",
        "Convert one of your Sigma rules into this shape. Both tracks meet again.",
      ]),
     ("study", "Content management at scale", [
        "Splunk's own content updates, versioning, and the discipline of not "
        "editing shipped content in place.",
        "Which is the same default-versus-local rule you learned in Week 07.",
      ])],
    ("Recall — correlation searches", [
        "Likely follow-up: 'How do you handle a correlation search that fires two "
        "hundred times a day?'",
      ]),
    "trackB-1-8", "Cloud-native II — OAuth2, OIDC, JWT and SAML",
    ["Four things people say interchangeably that are not the same. One sentence "
     "each, precisely.",
     "What a JWT actually contains, why signature validation is the whole game, "
     "and the classic validation failures.",
     "Hands-on: decode a real token and read every claim. Then say what an "
     "attacker would want to change."])

day("2026-11-20", "trackA-6-1",
    "ES V — risk-based alerting",
    [("study", "Why RBA exists", [
        "One suspicious event is noise. Five different suspicious events on one "
        "user in a day is a case.",
        "Risk rules attribute score to an object rather than raising a notable "
        "each time.",
        "The risk index, risk objects, and the risk incident rule that fires on "
        "accumulation.",
      ]),
     ("study", "Designing risk sensibly", [
        "Scores are arbitrary unless the scale is agreed and written down.",
        "Why ATT&CK annotations on risk rules make coverage visible — Track B "
        "meeting Track A again.",
        "The failure mode: everything scores, nothing accumulates, and the SOC "
        "stops looking.",
      ]),
     ("lab", "Design a small risk model", [
        "Take five of the detections you have written this term and assign each a "
        "risk score and a risk object, with a reason.",
        "Define the threshold at which you would raise an incident. Defend the "
        "number.",
      ]),
     ("study", "This is a genuinely current skill", [
        "RBA is what modern ES deployments are moving to, and it is a good "
        "interview topic because opinions differ.",
        "Have a view, and be able to name the trade-off in it.",
      ])],
    ("Recall — risk-based alerting", [
        "Trap: 'Does RBA reduce alerts?' Yes and no — know both halves of the "
        "answer.",
      ]),
    "trackB-1-8", "Cloud-native III — Terraform and CI/CD as an attack surface",
    ["State files with secrets in them, over-permissive pipeline roles, and "
     "supply-chain risk in modules.",
     "What CI/CD logs tell you, and why pipeline identity is the most "
     "over-privileged identity in most estates.",
     "Read a real Terraform plan and say what it would grant. You already run "
     "CloudGoat's Terraform — read it this time."])

saturday("2026-11-21")
sunday("2026-11-22",
       "Explain how a raw event becomes a notable event, naming every object it "
       "passes through.",
       "CIM especially. It is the ES skill most likely to be tested with a real "
       "scenario rather than a definition.",
       "Week 13 finishes ES: assets and identities, threat intel, investigation, "
       "and the honest resume line.")


# =====================================================================
# WEEK 13 · Mon 23 – Sun 29 Nov · Enterprise Security, second half
# =====================================================================
day("2026-11-23", "trackA-6-1",
    "ES VI — assets and identities",
    [("study", "Why ES needs to know your estate", [
        "An event about a server means little until you know the server is a "
        "domain controller.",
        "Asset and identity lookups: what fields they need and where the data comes "
        "from.",
        "How priority feeds urgency, which is what an analyst actually sorts by.",
      ]),
     ("study", "Keeping them current", [
        "The correlation of a CMDB, AD, and cloud inventory into one lookup, and "
        "why it is always partly wrong.",
        "The stale-lookup problem from Week 06, now with consequences.",
      ]),
     ("lab", "Build an asset list for the lab", [
        "Make an asset lookup for your three VMs with priority and category, in the "
        "ES-expected format.",
        "Then write a search that changes its output because of it.",
      ]),
     ("study", "The conversation nobody wants", [
        "'Who owns this server' is an organisational question, not a technical one, "
        "and ES exposes that gap immediately.",
        "How you would approach it as a consultant, without promising to solve it.",
      ])],
    ("Recall — assets and identities", [
        "Likely follow-up: 'Why does urgency differ between two identical notables?'",
      ]),
    "trackB-1-8", "Cloud-native IV — Kubernetes audit logs",
    ["The audit policy, what each level records, and the fields that identify who "
     "did what to which object.",
     "Three detections worth having: exec into a pod, a privileged pod created, a "
     "service account token used from outside.",
     "Hands-on: read a real audit log sample and find each of those shapes."])

day("2026-11-24", "trackA-6-1",
    "ES VII — the threat intelligence framework",
    [("study", "How ES consumes intel", [
        "Threat intel downloads, the local lookups it builds, and the modular "
        "inputs behind them.",
        "How events are matched against intel, and where that matching costs "
        "performance.",
        "Indicators versus context: why an IP list ages badly.",
      ]),
     ("study", "Using intel well", [
        "Confidence and source quality. A free feed with no provenance produces "
        "confident nonsense.",
        "Why intel is best as enrichment and worst as a standalone detection.",
      ]),
     ("lab", "Add a small intel source", [
        "Build a small local indicator list, load it the way ES expects, and match "
        "it against your lab data.",
        "Deliberately include one indicator that will produce a false positive, and "
        "watch what happens.",
      ]),
     ("study", "The measured opinion", [
        "Threat intel is a topic where interviewers like to hear scepticism backed "
        "by reasoning.",
        "State what it is good for and what it is not. Do not recommend a purchase.",
      ])],
    ("Recall — threat intelligence in ES", [
        "Trap: 'Should we alert on every threat-intel match?' Have the reasoned "
        "answer ready.",
      ]),
    "trackB-1-8", "Cloud-native V — container runtime and image security",
    ["Image scanning, signing and admission control — three different controls at "
     "three different moments.",
     "Runtime detection: what a sensor sees that an audit log cannot.",
     "What you can honestly claim from your day job here, and what you cannot."])

day("2026-11-25", "trackA-6-1",
    "ES VIII — investigation and adaptive response",
    [("study", "Adaptive response actions", [
        "Actions attached to a notable: enrichment, notification, or an active "
        "change to another system.",
        "Why the last kind needs governance, not just a token.",
        "Response as automation's entry point, without calling it SOAR.",
      ]),
     ("study", "The investigation workbench", [
        "Timeline, artefacts, notes. How an analyst records what they did.",
        "Why a written investigation is the difference between a closed case and a "
        "forgotten one.",
      ]),
     ("lab", "Run one investigation properly", [
        "Take a BOTS question from Week 07 and work it as a full investigation, "
        "with a written timeline and artefacts.",
        "That write-up is a portfolio piece and an interview story at the same "
        "time.",
      ]),
     ("study", "The analyst-to-engineer bridge", [
        "Every investigation should end with a question: could a detection have "
        "caught this earlier.",
        "That question is the whole detection-engineering feedback loop, and it is "
        "where your two tracks finally become one job.",
      ])],
    ("Recall — investigation and response", [
        "Likely follow-up: 'Walk me through investigating a suspicious login.' "
        "You have done this for real. Structure it.",
      ]),
    "trackB-1-8", "Cloud-native VI — identity in the cloud-native stack",
    ["Workload identity: service accounts, IRSA, federated identity. How a pod "
     "gets an AWS role.",
     "The failure that follows: a compromised pod holding a role that can read the "
     "whole account.",
     "Trace the trust chain from container to cloud API on paper."])

day("2026-11-26", "trackA-6-1",
    "ES IX — deploying and operating ES",
    [("study", "What deploying ES actually involves", [
        "A dedicated search head, data model acceleration capacity, and the "
        "indexer load that comes with it.",
        "The sizing conversation, and why ES is where under-sized clusters get "
        "found out.",
        "ES on Cloud: what Splunk operates, and what you still configure.",
      ]),
     ("study", "Operating it", [
        "Data model health as a daily check. Skipped searches as a weekly one.",
        "Content lifecycle: enabling, tuning, disabling, and documenting all three.",
        "The upgrade story for a premium app on top of the platform.",
      ]),
     ("lab", "Write the ES operations checklist", [
        "Daily, weekly and monthly checks you would run if you owned an ES "
        "deployment.",
        "Every item should name the search or view that answers it.",
      ]),
     ("study", "Why this closes the whole term", [
        "ES needs indexes, buckets, roles, SPL, knowledge objects, data models, "
        "acceleration and clustering — all of it, working.",
        "That is the argument for the order the contract put these topics in.",
      ])],
    ("Recall — operating ES", [
        "Trap: 'ES is slow.' The answer is a diagnostic path, and it goes through "
        "data model acceleration first.",
      ]),
    "trackB-1-8", "Cloud-native VII — putting the track together",
    ["Eight evenings across Kubernetes, identity protocols, Terraform and CI/CD.",
     "Write the 5-part card, and be strict about the awareness-versus-hands-on "
     "line in it.",
     "Note which parts your day job genuinely covers. That part is experience, "
     "not study."])

day("2026-11-27", "trackA-6-1",
    "ES X — the honest resume line",
    [("study", "What two weeks of ES actually earns", [
        "Read, understood, and partly run in a lab, on top of real SOC "
        "investigation experience.",
        "That is a strong, defensible position. It is not 'ES administrator'.",
        "The contract is explicit: Splunk ES hands-on stays off the resume until "
        "the work is genuinely done and the card is clean twice.",
      ]),
     ("study", "Write the two sentences", [
        "One for the resume, one for the interview. Both true, both specific.",
        "Name what you did: CIM mapping by hand, a correlation search written, an "
        "investigation documented, a risk model designed.",
      ]),
     ("lab", "Consolidate the fortnight", [
        "Collect every artefact from the two weeks: the CIM mapping, the "
        "correlation search, the risk model, the investigation write-up, the "
        "operations checklist.",
        "One folder, one index note. That folder is what you talk from.",
      ]),
     ("study", "Track A is finished today", [
        "Twenty-two topics, thirteen weeks, in the order the contract set.",
        "What is left is not new content: it is proving you can say it under "
        "pressure. That is next week.",
      ])],
    ("Recall — ES overall", [
        "This is the last new Track A card of the term. Rate it honestly; it is "
        "the one most likely to be inflated.",
      ]),
    "trackB-1-8", "Cloud-native VIII — the wrap-up card",
    ["Finish the card started yesterday and rate it properly.",
     "Safe claim: 'I can reason about Kubernetes and cloud identity attack paths "
     "and the telemetry that reveals them.'",
     "The two remaining Track B items are scope reading and artefacts. Both are "
     "next week."])

saturday("2026-11-28")
sunday("2026-11-29",
       "Explain the full ES stack from raw event to risk incident without notes, "
       "then state your honest ES resume line out loud.",
       "The whole of ES. It is the topic where over-claiming is most tempting and "
       "most easily caught.",
       "Week 14 is buffer: re-teach, mock interviews, the migration story, and the "
       "artefacts.")


# =====================================================================
# WEEK 14 · Mon 30 Nov – Sun 6 Dec · buffer, mock interviews, artefacts
# =====================================================================
day("2026-11-30", "",
    "Buffer — re-teach whatever is still rated Again",
    [("study", "Pull the list first", [
        "Every card rated Again this term, plus anything marked unverified in the "
        "notes.",
        "Sort by how likely it is to be asked, not by how uncomfortable it is.",
      ]),
     ("study", "Re-teach the top three", [
        "Full lesson treatment, not a re-read. Explain each one out loud as if to "
        "someone else.",
        "If it cannot be explained without notes, it is not learned yet.",
      ]),
     ("study", "Fix the notes while you are there", [
        "Anything an audit corrected goes into the corrections block properly, with "
        "the reason.",
        "Any figure without a source gets tagged unverified or removed.",
      ]),
     ("lab", "Prove one of them on the lab", [
        "Whichever of the three can be demonstrated, demonstrate. Hands beat "
        "reading for retention every time.",
      ])],
    ("Recall — the re-taught three", [
        "Re-rate them today and again in Sunday's consolidation. Two clean reviews "
        "is still the rule.",
      ]),
    "trackB-1-9", "AWS Security Specialty — scope only (awareness)",
    ["Read the exam guide and map its domains against what you have actually "
     "covered this term.",
     "Decide honestly whether this certification is worth the time, given the job "
     "search comes first.",
     "No study plan tonight. Just the scope and the decision."])

day("2026-12-01", "",
    "Buffer — assemble the migration narrative",
    [("study", "The story you already own", [
        "SPL to DQL conversion, dashboards and notebooks rebuilt, OneAgent "
        "deployed, OpenPipeline ingestion and routing.",
        "It never needed studying separately — it assembles itself now that Splunk "
        "is solid.",
      ]),
     ("study", "Structure it properly", [
        "Scope, approach, parity validation, sign-off. Numbers where you have them "
        "and no numbers where you do not.",
        "The dashboard count is still unresolved between two versions. Settle it "
        "today or say 'dozens' and stop quoting a number.",
      ]),
     ("study", "The SPL-to-DQL comparison", [
        "Five real conversions, written out both ways. That is the artefact almost "
        "nobody else applying has.",
        "Where the two languages genuinely differ, not just in syntax.",
      ]),
     ("study", "Say it in two minutes", [
        "Practise it out loud three times. This is your strongest interview story "
        "and it should not be improvised.",
      ])],
    ("Recall — the migration story", [
        "Trap: an interviewer asking for a number you are unsure of. Have the "
        "honest phrasing ready.",
      ]),
    "trackB-1-9", "AWS Security Specialty — the decision, written down",
    ["If yes: when, and what it displaces. If no: what you do instead with the "
     "same hours.",
     "Write the decision in the loose-items list on the Plan tab so it is a "
     "commitment rather than an intention.",
     "Either answer is fine. An undecided one is not."])

day("2026-12-02", "",
    "Buffer — mock interview: architecture, onboarding and parsing",
    [("study", "Warm up on the fundamentals", [
        "Components, ports, the data journey, UF versus HF. Fifteen minutes, spoken "
        "aloud, no notes.",
      ]),
     ("study", "The scenario round", [
        "Onboard a new syslog source for a customer. Design it out loud, including "
        "the questions you would ask first.",
        "Then: the data is arriving with the wrong timestamps. Diagnose it live.",
      ]),
     ("study", "The pressure round", [
        "Have someone interrupt with 'why' three times on any answer. Depth shows "
        "up under repetition.",
      ]),
     ("study", "Write down what failed", [
        "Every hesitation is a card that needs another review. Log them, do not "
        "just remember them.",
      ])],
    ("Recall — the weak answers from today", [
        "Re-rate whatever wobbled. Honest ratings today are worth more than a "
        "comfortable evening.",
      ]),
    "trackB-1-10", "Artefacts I — the detection-rules repository",
    ["Create the repository properly: rules, pipelines, tests, and a README that "
     "explains the loop.",
     "Every rule from this term, tidied to the metadata standard from Week 06.",
     "A public repository is evidence. Make it readable by someone who has ten "
     "minutes."])

day("2026-12-03", "",
    "Buffer — mock interview: troubleshooting, clustering and Cloud",
    [("study", "The troubleshooting round", [
        "Three symptoms, cold: ingestion stopped, searches slow, a user cannot see "
        "data. Method first, every time.",
      ]),
     ("study", "The clustering round", [
        "RF and SF, a peer failure, a rolling restart, and a sizing question with "
        "the working shown.",
      ]),
     ("study", "The Cloud round", [
        "What is different, what you cannot do, and what ACS is for.",
        "Be precise about what you have operated versus what you have read.",
      ]),
     ("study", "The one about weaknesses", [
        "Name a real gap and what you are doing about it. The board on this screen "
        "is the answer.",
      ])],
    ("Recall — the weak answers from today", [
        "Same rule as yesterday. Log the hesitations as cards.",
      ]),
    "trackB-1-10", "Artefacts II — the security-telemetry capstone",
    ["One write-up tying the whole of Track B together: telemetry sources, "
     "detections, emulation, cloud.",
     "Structure: what was built, why, what it catches, what it does not.",
     "The 'what it does not' section is what makes the rest believable."])

day("2026-12-04", "",
    "Buffer — the resume and the board, together",
    [("study", "Read the board honestly", [
        "Every topic that has a card rated Good or Easy twice is resume-eligible. "
        "Nothing else is.",
        "Mark the board's statuses to match reality — done means done, not covered.",
      ]),
     ("study", "Update the resume", [
        "Add only what the board earned. Fix the Splunk-to-Dynatrace migration "
        "direction if it is still wrong.",
        "The two title variants: observability-leaning for the main search, "
        "security-leaning kept aside.",
      ]),
     ("study", "The skills still held back", [
        "Sigma, ATT&CK hands-on, Terraform, KQL, Splunk ES hands-on. Check each "
        "against its card, one by one.",
        "Add only what genuinely passed. This is the rule the whole term was built "
        "around.",
      ]),
     ("study", "Plan what comes after", [
        "Fourteen weeks is not the end of learning; it is the end of this plan.",
        "Decide the next thing before Sunday, so the habit has somewhere to go.",
      ])],
    ("Recall — the term's five hardest cards", [
        "Pick the five you least want to be asked. Do those. That is the whole "
        "technique.",
      ]),
    "trackB-1-10", "Artefacts III — publish and link",
    ["Finish both artefacts, publish them, and put the links on the resume and the "
     "LinkedIn profile.",
     "One paragraph each on what it demonstrates, in the language of the roles you "
     "are applying for.",
     "Then stop building and go back to applying. That was always the point."])

saturday("2026-12-05")
sunday("2026-12-06",
       "The full mock: forty minutes, mixed, no notes, spoken. Record it and "
       "listen back once.",
       "Everything still rated Again. If the list is empty, audit the three cards "
       "you are most confident about instead — confidence is where errors hide.",
       "This is the last planned week. Decide what the next fourteen look like, "
       "and add the first week of it here.")

# The buffer week is not new content, and the board should not pretend
# it is. Marked after the fact so the day helper stays one shape.
for _entry in _DAYS:
    if _entry["date"] >= "2026-11-30" and _entry["kind"] == "study":
        _entry["kind"] = "buffer"


# =====================================================================
# THE FOURTEEN WEEKS - each one's two focus lines
# Keyed by the Monday it starts on, so a week can never be attached to
# the wrong dates by a counting mistake.
# =====================================================================
WEEK_FOCUS = {
    "2026-08-31": ("Splunk architecture, then data ingestion",
                   "Linux security telemetry"),
    "2026-09-07": ("Ingestion at scale, then the parsing pipeline",
                   "Linux security telemetry"),
    "2026-09-14": ("Parsing closes, configuration precedence, buckets",
                   "Linux telemetry ends; Windows telemetry (awareness)"),
    "2026-09-21": ("Buckets and retention, user management, SPL opens",
                   "MITRE ATT&CK literacy"),
    "2026-09-28": ("SPL fundamentals, all week",
                   "ATT&CK closes; Sigma opens"),
    "2026-10-05": ("Knowledge objects",
                   "Sigma end-to-end"),
    "2026-10-12": ("Deployment, then troubleshooting opens",
                   "Sigma closes; emulate and detect"),
    "2026-10-19": ("Troubleshooting closes, config files, clustering opens",
                   "Emulate and detect; AWS identity opens"),
    "2026-10-26": ("Clustering, all week",
                   "AWS identity and logging"),
    "2026-11-02": ("SmartStore, ACS, Monitoring Console",
                   "AWS identity closes; cloud attack labs open"),
    "2026-11-09": ("The awareness layer: Cloud, Victoria, upgrades, 10.x",
                   "Cloud attack and detect labs"),
    "2026-11-16": ("Enterprise Security, first half",
                   "Cloud labs close; cloud-native and identity depth"),
    "2026-11-23": ("Enterprise Security, second half",
                   "Cloud-native and identity depth"),
    "2026-11-30": ("Buffer: re-teach, mock interviews, the migration story",
                   "AWS Security Specialty scope; the artefacts"),
}

TARGET_BY_KIND = {
    "study": STUDY_DAY_MINUTES,
    "buffer": STUDY_DAY_MINUTES,
    "prep": PREP_DAY_MINUTES,
    "consolidation": CONSOLIDATION_MINUTES,
    # "off" is deliberately absent: Saturday gets no target at all,
    # because blank means "not set" and a 0 would read as "studied nothing".
}


def _monday_of(day_iso: str) -> str:
    when = date.fromisoformat(day_iso)
    return (when - timedelta(days=when.weekday())).isoformat()


def build() -> list[list[dict]]:
    """Group the authored days into their weeks and check the shape
    before anything is written. A plan with a missing Wednesday should
    fail here, loudly, not appear on the page as a gap."""
    weeks: dict[str, list[dict]] = {}
    for entry in _DAYS:
        weeks.setdefault(_monday_of(entry["date"]), []).append(entry)

    problems = []
    if sorted(weeks) != sorted(WEEK_FOCUS):
        problems.append("the weeks written and the weeks with focus lines differ")
    for start, days in weeks.items():
        if len(days) != 7:
            problems.append(f"week starting {start} has {len(days)} days, not 7")
        wanted = [(date.fromisoformat(start) + timedelta(days=n)).isoformat()
                  for n in range(7)]
        if sorted(d["date"] for d in days) != wanted:
            problems.append(f"week starting {start} does not hold its own seven dates")
    if problems:
        raise SystemExit("the plan does not hold together:\n  - "
                         + "\n  - ".join(problems))

    ordered = []
    for start in sorted(weeks):
        days = sorted(weeks[start], key=lambda d: d["date"])
        for day_entry in days:
            when = date.fromisoformat(day_entry["date"])
            day_entry["d"] = DAY_NAMES_LOCAL[when.weekday()]
            day_entry.setdefault("note", "")
            day_entry["done"] = False        # planning, never recording
        ordered.append(days)
    return ordered


DAY_NAMES_LOCAL = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def main() -> None:
    replace = "--replace" in sys.argv
    weeks = build()

    existing = week_plans.read_weeks()
    if existing and not replace:
        print("There are already", len(existing), "planned week(s) in "
              "week_plans.json.")
        print("Re-run with --replace to throw them away and write these 14.")
        print("That also throws away any day already ticked done, which is why "
              "it is not the default.")
        return
    for week in list(existing):
        week_plans.delete_week(week["id"])

    written = 0
    for days in weeks:
        start = days[0]["date"]
        focus_a, focus_b = WEEK_FOCUS[start]
        week = week_plans.add_week(start, focus_a, focus_b)
        week_plans.save_week(week["id"], days=days)
        for day_entry in days:
            minutes = TARGET_BY_KIND.get(day_entry["kind"])
            daily_targets.set_target(day_entry["date"], minutes)
        written += 1

    lessons = sum(1 for d in _DAYS if d["kind"] in ("study", "buffer"))
    print("THE STUDY PLAN, WRITTEN")
    print("=" * 50)
    print(f"  {written} weeks, {len(_DAYS)} days")
    print(f"  {lessons} lesson days, first one "
          f"{min(d['date'] for d in _DAYS if d['kind'] == 'study')}")
    print(f"  {sum(1 for d in _DAYS if d['kind'] == 'off')} days off, "
          f"{sum(1 for d in _DAYS if d['kind'] == 'consolidation')} consolidation")
    print("  every day starts not done - this plans, it does not record")


if __name__ == "__main__":
    main()
