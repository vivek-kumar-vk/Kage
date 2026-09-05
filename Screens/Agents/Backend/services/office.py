"""Department meta + per-agent office.json reader for the Pixel Office (D12).

Each profile dir in AI_Agents/ may carry office.json {"department", "tier"}.
Drop a profile folder in and it appears on the stage — the roster is
registry-driven, nothing else needs editing.
"""

import json
from pathlib import Path

DEPARTMENTS = [
    {"id": "lobby", "label": "Lobby", "color": "#A0693C"},
    {"id": "model", "label": "Model", "color": "#6F9B8D"},
    {"id": "finance", "label": "Finance", "color": "#C98A2E"},
    {"id": "learning", "label": "Learning", "color": "#7E9463"},
    {"id": "deck", "label": "Agent Deck", "color": "#C96F4A"},
    {"id": "anime", "label": "Anime", "color": "#C77B9E"},
    {"id": "main_menu", "label": "Main Menu", "color": "#FF7A00"},
]

_DEPT_IDS = {dept["id"] for dept in DEPARTMENTS}
_TIERS = {"head", "main", "sub"}


def read_office(agent_dir: Path) -> dict:
    parent = None
    model = None
    models = None
    try:
        data = json.loads((agent_dir / "office.json").read_text(encoding="utf-8"))
        department = data.get("department", "deck")
        tier = data.get("tier", "sub")
        parent = data.get("parent") or None
        model = data.get("model")
        models = data.get("models")
    except (OSError, ValueError):
        department, tier = "deck", "sub"

    if department not in _DEPT_IDS:
        department = "deck"
    if tier not in _TIERS:
        tier = "sub"
    if tier != "sub":
        parent = None  # only subs report to a main

    if not isinstance(model, str) or not model.strip():
        model = None
    if not isinstance(models, list) or not all(
        isinstance(entry, str) and entry.strip() for entry in models
    ):
        models = None

    return {
        "department": department,
        "tier": tier,
        "parent": parent,
        "model": model,
        "models": models,
    }


def dept_color(department: str) -> str:
    for dept in DEPARTMENTS:
        if dept["id"] == department:
            return dept["color"]
    return "#A08762"
