"""Seed for office.db.

TWO KINDS OF SEED
    1. The tracked skills (Sigma, MITRE, Terraform, KQL, Splunk-ES) - the
       ones D17.5 says stay off-resume until earned. Inserted every boot
       with INSERT OR IGNORE so the readiness gate always has something to
       measure. Not personal data.
    2. A handful of example pipeline / interview / work-log rows so the
       page renders on first open. Written ONCE (guarded by a settings
       marker); office.db is gitignored so these never ship. Delete them
       from the UI - they won't come back.
"""

from __future__ import annotations

from db import connect
from services.common import today_str

# skill name -> skill_tag used on Learning rooms
TRACKED_SKILLS = {
    "Sigma": "sigma",
    "MITRE ATT&CK": "mitre",
    "Terraform": "terraform",
    "KQL": "kql",
    "Splunk ES": "splunk-es",
}

EXAMPLE_APPLICATIONS = [
    ("Acme Observability", "Detection Engineer", "LinkedIn",
     "https://example.com/jobs/1", "applied", "referred by ex-colleague"),
    ("Northwind SOC", "Security Analyst II", "company site",
     "https://example.com/jobs/2", "screen", "recruiter call booked"),
    ("Globex Cloud", "SRE (Security)", "Wellfound",
     "https://example.com/jobs/3", "saved", "needs Terraform - not defensible yet"),
]

EXAMPLE_INTERVIEWS = [
    # (company, role, round, scheduled_at, mode, prep_pack)
    ("Northwind SOC", "Security Analyst II", "Recruiter screen",
     today_str(2) + " 11:00", "phone", ""),
    ("Acme Observability", "Detection Engineer", "Tech round 1",
     today_str(5) + " 15:30", "video",
     "Likely: Sigma rule authoring, ATT&CK mapping, a detection-tuning story.\n"
     "STAR: the noisy-alert cleanup at $CURRENT_JOB."),
]

EXAMPLE_WORK_LOG = [
    (today_str(0), "Bindplane", "Built a routing pipeline for a new log source",
     "Split by team, dropped debug spam before the gateway.", 90),
    (today_str(-1), "Dynatrace", "Chased a latency spike on the ingest path",
     "Root cause was a GC pause on the collector node.", 60),
]


def run() -> None:
    with connect() as conn:
        for name, tag in TRACKED_SKILLS.items():
            conn.execute(
                "INSERT OR IGNORE INTO skills (name, skill_tag) VALUES (?,?)",
                (name, tag),
            )

        done = conn.execute(
            "SELECT value FROM settings WHERE key='examples_seeded'"
        ).fetchone()
        if not done:
            for a in EXAMPLE_APPLICATIONS:
                conn.execute(
                    """INSERT INTO applications
                       (company, role, portal, link, stage, notes)
                       VALUES (?,?,?,?,?,?)""",
                    a,
                )
            for iv in EXAMPLE_INTERVIEWS:
                conn.execute(
                    """INSERT INTO interviews
                       (company, role, round, scheduled_at, mode, prep_pack)
                       VALUES (?,?,?,?,?,?)""",
                    iv,
                )
            for w in EXAMPLE_WORK_LOG:
                conn.execute(
                    """INSERT INTO work_log
                       (log_date, tech, summary, detail, minutes)
                       VALUES (?,?,?,?,?)""",
                    w,
                )
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('examples_seeded','1')"
            )
        conn.commit()
