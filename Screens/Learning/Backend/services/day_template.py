"""Day-template settings (M6 slice 2): named minute-blocks per weekday/weekend,
seeded from the owner's Master Context defaults, editable later in-app."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.common import jdump, jload

IST = timezone(timedelta(hours=5, minutes=30))
SETTING_KEY = "day_template"

# Master_Context.md: "My daily default": Core 45-60, Drip ~15, Capture ~5, apply
# 2x/day, THM slot protects the standing-lab streak. Weekday/weekend split kept
# equal until the owner edits it — no weekend-specific numbers are on record.
DEFAULT_TEMPLATE = {
    "weekday": [
        {"key": "core", "label": "Core", "minutes": 60,
         "note": "one Track A concept, ends in recall format"},
        {"key": "drip", "label": "Drip", "minutes": 15,
         "note": "one Track B concept, exposure only"},
        {"key": "thm", "label": "TryHackMe", "minutes": 20,
         "note": "protects the standing-lab streak"},
        {"key": "capture", "label": "Capture", "minutes": 5,
         "note": "a line on today's day-job work, phrased as an interview answer"},
        {"key": "apply", "label": "Apply block", "minutes": 15, "count": 2,
         "note": "morning pass + evening pass"},
    ],
    "weekend": [
        {"key": "core", "label": "Core", "minutes": 60,
         "note": "one Track A concept, ends in recall format"},
        {"key": "drip", "label": "Drip", "minutes": 15,
         "note": "one Track B concept, exposure only"},
        {"key": "thm", "label": "TryHackMe", "minutes": 20,
         "note": "protects the standing-lab streak"},
        {"key": "capture", "label": "Capture", "minutes": 5,
         "note": "a line on today's day-job work, phrased as an interview answer"},
        {"key": "apply", "label": "Apply block", "minutes": 15, "count": 2,
         "note": "morning pass + evening pass"},
    ],
}


def ensure_default(conn) -> None:
    """Seed the setting once. Never overwrites an existing (possibly
    owner-edited) value."""
    row = conn.execute("SELECT 1 FROM settings WHERE key=?", (SETTING_KEY,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            (SETTING_KEY, jdump(DEFAULT_TEMPLATE)),
        )
        conn.commit()


def get_template(conn) -> dict:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (SETTING_KEY,)).fetchone()
    return jload(row["value"] if row else None, DEFAULT_TEMPLATE)


def set_template(conn, template: dict) -> None:
    """Replace the whole template (both day-types). Commits."""
    for day_type in ("weekday", "weekend"):
        if day_type not in template or not isinstance(template[day_type], list):
            raise ValueError(f"template must have a '{day_type}' list of blocks")
        for block in template[day_type]:
            if "key" not in block or "label" not in block or "minutes" not in block:
                raise ValueError("each block needs key, label and minutes")
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (SETTING_KEY, jdump(template)),
    )
    conn.commit()


def today_blocks(conn) -> list[dict]:
    """This IST day's blocks: weekday (Mon-Fri) or weekend (Sat-Sun)."""
    is_weekend = datetime.now(IST).weekday() >= 5
    template = get_template(conn)
    return template["weekend" if is_weekend else "weekday"]
