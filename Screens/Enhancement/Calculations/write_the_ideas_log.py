"""A human-readable history of every idea on the Enhancement board,
grouped by screen/tab, regenerated from the real board - never
hand-edited, never a second source of truth.

WHY THIS EXISTS
    manage_enhancement_ideas.py's SQLite board is real and live, but it
    is not something you casually open and read. The owner asked
    (2026-08-28) for an actual file, alongside the board itself, that
    keeps the history of what has been captured and what of it is done
    so far - one place to check before starting work on a tab so
    nothing already said in chat gets forgotten.

WHY GENERATED, NEVER HAND-EDITED
    Two copies of the same list drift the moment one of them is edited
    directly. The board is the one place writes happen (add_idea(),
    set_status(), ...); this file is a rendered view of it, rebuilt
    from scratch every time - the same relationship
    write_the_finance_report.py has with the noticeboard.

RUN IT
    cd <repo root>
    python Screens\\Enhancement\\Calculations\\write_the_ideas_log.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from manage_enhancement_ideas import read_ideas, STATUSES  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30), "IST")
OUT_PATH = SCREEN / "Saved_Records" / "Ideas_And_Plans_Log.md"

STATUS_LABEL = {
    "ideas": "not started",
    "todo": "queued",
    "in_progress": "in progress",
    "done": "done",
}


def _date_of(stamp: str) -> str:
    """An ISO timestamp's date only - this file tracks history in days,
    not seconds; the board itself keeps the full timestamp."""
    try:
        return stamp[:10]
    except Exception:                                          # noqa: BLE001
        return stamp or "?"


def build() -> str:
    ideas = read_ideas()
    generated_at = datetime.now(IST).isoformat(timespec="seconds")

    by_area: dict[str, list[dict]] = {}
    for idea in ideas:
        by_area.setdefault(idea["area"] or "Unsorted", []).append(idea)

    total = len(ideas)
    done = sum(1 for i in ideas if i["status"] == "done")

    lines = [
        "---",
        "title: Ideas And Plans Log",
        "type: log",
        "status: generated - regenerate with write_the_ideas_log.py, never hand-edit",
        f"dated: {generated_at}",
        "scope: cross-cutting",
        "---",
        "",
        "# Ideas And Plans Log",
        "",
        "Every idea captured from chat, grouped by the screen/tab it belongs to, "
        "generated straight from the real Enhancement board "
        "(`Saved_Records/enhancement_board.db`) - never hand-edited. "
        "See it live, drag it between columns, at the Enhancement screen "
        "(port 8004) too; this file is the same data as a history you can read "
        "without opening the app.",
        "",
        f"**{done} of {total} done** as of {generated_at}. Nothing here was fabricated "
        "to look further along than it is - an item with no DONE line below is "
        "genuinely not started, no matter how long ago it was captured.",
        "",
    ]

    for area in sorted(by_area):
        items = by_area[area]
        area_done = sum(1 for i in items if i["status"] == "done")
        lines.append(f"## {area} ({area_done}/{len(items)} done)")
        lines.append("")
        # Open items first (capture -> todo -> in_progress), done last -
        # same reading order as the board itself, so this file and the
        # app never disagree about what "first" means.
        for status in STATUSES:
            for idea in items:
                if idea["status"] != status:
                    continue
                tag = "AI" if idea["source"] == "ai" else "you"
                lines.append(f"- **{idea['key']}** — {idea['title']} "
                             f"[{tag}, {STATUS_LABEL[status]}]")
                if idea["note"]:
                    lines.append(f"  {idea['note']}")
                added = _date_of(idea["added_at"])
                updated = _date_of(idea["updated_at"])
                history = f"  Added {added}"
                if updated != added:
                    history += f" · last moved {updated}"
                if status == "done":
                    history += " · **DONE**"
                lines.append(history)
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
