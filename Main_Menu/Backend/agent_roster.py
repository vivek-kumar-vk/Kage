"""The agent ring's data feed - one read-only fetch to the Agent Deck.

WHAT THIS FILE DOES
    Asks the Agent Deck screen (over HTTP, its own port, never an import)
    for the live roster and the per-agent unread counts, and shapes them
    into the compact node list the home page's ring renders: one node per
    agent, mains with their model id, unread counts for the glow.

WHAT THIS FILE MUST NEVER DO
    Invent an agent. If the Agent Deck is unreachable the state says so
    and the list is empty (Rule 8) - the ring shows an honest offline
    note instead of a fake roster.

    The naming of the other screen lives here (like email_digest.py, the
    ADR-089 pattern): the server file itself never names a screen.
"""

import requests

import settings_for_main_menu as cfg


def fetch_roster():
    """Combine /workspace (roster) + /unread (counts) into node data.

    Returns {"state": "ok", "agents": [...], "deck_url": ...} or
    {"state": "agents offline", "agents": [], "note": ...} - never a
    partial fabrication.
    """
    base = cfg.AGENTS_SCREEN_URL.rstrip("/")
    try:
        ws = requests.get(
            f"{base}/api/agents/workspace", timeout=cfg.AGENTS_ROSTER_TIMEOUT
        )
        ws.raise_for_status()
        workspace = ws.json()
    except Exception as exc:
        return {
            "state": "agents offline",
            "agents": [],
            "note": f"{type(exc).__name__}: {exc}",
        }

    try:
        unread_response = requests.get(
            f"{base}/api/agents/unread", timeout=cfg.AGENTS_ROSTER_TIMEOUT
        ).json()
        unread = unread_response.get("agents", {})
    except Exception:
        # Roster is the load-bearing half; unread is decoration. An
        # unread failure degrades to zero shown, stated honestly.
        unread = {}

    agents = []
    for agent in workspace.get("agents", []):
        agents.append(
            {
                "name": agent.get("name") or "",
                "role": agent.get("role") or "",
                "department": agent.get("department") or "",
                "tier": agent.get("tier") or "sub",
                "parent": agent.get("parent"),
                "model": agent.get("model"),
                "unread": int(unread.get(agent.get("name") or "", 0)),
            }
        )

    return {
        "state": "ok",
        "agents": agents,
        "deck_url": f"{base}/workspace",
        "unread_total": sum(unread.values()),
    }
