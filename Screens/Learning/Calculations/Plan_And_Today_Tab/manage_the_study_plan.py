"""The Plan tab's own record: what you intend to study and by when.

WHY THIS FILE INVENTS NOTHING
    There is no real source anywhere in INKY for "what certification is
    next" - that is a decision only the user can make. So this file
    starts empty and stays empty until a plan item is added by hand
    through the UI. No sample certification, no example target date
    (Rule 12) - a screen that pre-fills "AWS Solutions Architect" because
    it sounded plausible would be exactly the fabricated data C4 exists
    to rule out.

WHY JSON, NOT A FROZEN CSV
    A plan item gets edited and reordered by the person who owns it -
    title changed, target date pushed back, marked done. A frozen column
    contract is a promise that a column's MEANING never changes once
    something depends on it; a small hand-edited list of plan items has
    no second reader to keep a promise to, so a plain JSON file (the same
    choice Models made for my_mcp_servers.json) is enough.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\manage_the_study_plan.py
"""

from __future__ import annotations

import json
import sys
import uuid
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
PLAN_FILE = SAVED_RECORDS / "study_plan.json"


class NoSuchPlanItem(Exception):
    """Raised by mark_done() and remove_item() for an id that is not on
    the list - most likely already removed, never silently ignored."""


def read_plan() -> list[dict]:
    """Every plan item, target date first, undated ones last. Empty by
    default - see the module docstring for why that is not a gap to fill
    with an example."""
    if not PLAN_FILE.exists():
        return []
    items = json.loads(PLAN_FILE.read_text(encoding="utf-8"))
    return sorted(items, key=lambda i: (i.get("done", False), i.get("target_date") or "9999-99-99"))


def _write_plan(items: list[dict]) -> None:
    SAVED_RECORDS.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def add_item(title: str, target_date: str = "", notes: str = "") -> dict:
    title = (title or "").strip()
    if not title:
        raise ValueError("a plan item needs a title")

    items = json.loads(PLAN_FILE.read_text(encoding="utf-8")) if PLAN_FILE.exists() else []
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": title,
        "target_date": (target_date or "").strip(),
        "notes": (notes or "").strip(),
        "done": False,
    }
    items.append(item)
    _write_plan(items)
    return item


def mark_done(item_id: str, done: bool = True) -> dict:
    items = json.loads(PLAN_FILE.read_text(encoding="utf-8")) if PLAN_FILE.exists() else []
    for item in items:
        if item["id"] == item_id:
            item["done"] = done
            _write_plan(items)
            return item
    raise NoSuchPlanItem(f"no plan item with id '{item_id}'")


def remove_item(item_id: str) -> None:
    items = json.loads(PLAN_FILE.read_text(encoding="utf-8")) if PLAN_FILE.exists() else []
    kept = [i for i in items if i["id"] != item_id]
    if len(kept) == len(items):
        raise NoSuchPlanItem(f"no plan item with id '{item_id}'")
    _write_plan(kept)


def main() -> None:
    items = read_plan()
    print("STUDY PLAN")
    print("=" * 50)
    if not items:
        print("  Nothing on the plan yet. Add the first item from the Plan tab.")
        return
    for item in items:
        mark = "[x]" if item["done"] else "[ ]"
        when = item["target_date"] or "no target date"
        print(f"  {mark} {item['title']:<40} {when}")


if __name__ == "__main__":
    main()
