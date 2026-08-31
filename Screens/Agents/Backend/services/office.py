"""Department meta + per-agent office.json reader for the Pixel Office (D12).

Each profile dir in AI_Agents/ may carry office.json {"department", "tier"}.
Drop a profile folder in and it appears on the stage — the roster is
registry-driven, nothing else needs editing.
"""

import json
from pathlib import Path

DEPARTMENTS = [
    {"id": "lobby", "label": "Lobby", "color": "#F4F2EE"},
    {"id": "model", "label": "Model", "color": "#6E8BA0"},
    {"id": "finance", "label": "Finance", "color": "#3FD9A4"},
    {"id": "learning", "label": "Learning", "color": "#F2A93B"},
    {"id": "deck", "label": "Agent Deck", "color": "#FF7A00"},
    {"id": "anime", "label": "Anime", "color": "#B18CFF"},
]

_DEPT_IDS = {dept["id"] for dept in DEPARTMENTS}
_TIERS = {"head", "main", "sub"}


def read_office(agent_dir: Path) -> dict:
    parent = None
    try:
        data = json.loads((agent_dir / "office.json").read_text(encoding="utf-8"))
        department = data.get("department", "deck")
        tier = data.get("tier", "sub")
        parent = data.get("parent") or None
    except (OSError, ValueError):
        department, tier = "deck", "sub"

    if department not in _DEPT_IDS:
        department = "deck"
    if tier not in _TIERS:
        tier = "sub"
    if tier != "sub":
        parent = None  # only subs report to a main

    return {"department": department, "tier": tier, "parent": parent}


def dept_color(department: str) -> str:
    for dept in DEPARTMENTS:
        if dept["id"] == department:
            return dept["color"]
    return "#8B9099"
