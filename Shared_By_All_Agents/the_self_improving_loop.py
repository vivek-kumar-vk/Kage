"""The self-improving loop, as code: Do -> Learn -> Improve.

Wires the Do -> Learn -> Improve loop (originally documented in this
folder's own guide, deleted 2026-08-28 along with every other guide) so
any agent can use it without importing another agent (C8 - this lives in
Shared_By_All_Agents, which is nobody's folder and everybody's).

The pipeline, each stage a plain function:

    record_error_fix      episodic row, JSONL, correlation_id attached
    detect_patterns       Tier 0 - grouping arithmetic, no model
    propose_a_fact        semantic fact PROPOSED, never self-approved
    approve_a_fact        the human gate - only this writes approvals
                          (and minting the version-controlled skill .md)

Honesty rules inherited from CLAUDE.md:
- An error without a stated fix is refused. Empty beats fake.
- Nothing here calls a model by itself. `propose_a_fact` accepts an
  optional `summarizer` callable (the caller's choice, normally local
  Model A) purely to phrase the fact; the deterministic template is
  the default and always available offline.
- Approval can never be granted by this module on its own initiative;
  `approve_a_fact` records whoever is named as approver, and production
  facts wait for the owner.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

LEDGER_NAME = "errors_fixes_ledger.jsonl"
PENDING_NAME = "facts_pending_approval.jsonl"
APPROVED_NAME = "approved_facts.jsonl"
SKILLS_FOLDER = "skills"

# The repo root, so callers never need to pass it in production.
_DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def _memory_dir(root, agent_name) -> Path:
    where = Path(root if root is not None else _DEFAULT_ROOT) \
        / "Agents" / agent_name / "Memory"
    where.mkdir(parents=True, exist_ok=True)
    return where


def _append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(text) -> str:
    return " ".join(str(text or "").split())


def _signature(error: str) -> str:
    """Deterministic fingerprint: caseless, punctuation-collapsed.

    Two records share a signature when a human would call them the
    same error. No model is needed to notice that.
    """
    lowered = error.lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


# =====================================================================
# stage 1: Do -> Learn (episodic memory)
# =====================================================================
def record_error_fix(agent_name, error, fix, correlation_id="", root=None):
    """Append one honest row to the agent's errors_fixes_ledger.jsonl."""
    error = _clean(error)
    fix = _clean(fix)
    correlation_id = _clean(correlation_id)

    if not agent_name or not error or not fix:
        return {"has_data": False, "learned": False,
                "note": ("an error AND its fix must both be stated to "
                         "learn anything; nothing was written")}

    target = _memory_dir(root, agent_name) / LEDGER_NAME
    _append_jsonl(target, {
        "ts": _now(),
        "agent": agent_name,
        "error": error[:300],
        "fix": fix[:300],
        "correlation_id": correlation_id[:120],
    })
    return {"has_data": True, "learned": True,
            "ledger": str(Path("Agents") / agent_name / "Memory" / LEDGER_NAME),
            "total_rows": len(_read_jsonl(target))}


def read_the_ledger(agent_name, root=None):
    """Every recorded error+fix row for one agent, oldest first."""
    return _read_jsonl(_memory_dir(root, agent_name) / LEDGER_NAME)


# =====================================================================
# stage 2: Learn (pattern detection - pure Tier 0)
# =====================================================================
def detect_patterns(agent_name, min_occurrences=2, root=None):
    """Group the ledger by signature; a pattern needs real repetition.

    One occurrence is an event. Two is the start of a lesson. This
    threshold IS the difference between noticing and overfitting.
    """
    buckets = {}
    for row in read_the_ledger(agent_name, root=root):
        buckets.setdefault(_signature(row["error"]), []).append(row)

    patterns = []
    for signature, rows in buckets.items():
        if len(rows) < min_occurrences:
            continue
        fixes = {}
        for row in rows:
            fixes[row["fix"]] = fixes.get(row["fix"], 0) + 1
        best_fix = max(fixes.items(), key=lambda kv: kv[1])[0]
        patterns.append({
            "signature": signature,
            "occurrences": len(rows),
            "example_error": rows[0]["error"],
            "suggested_fix": best_fix,
            "correlation_ids": [r["correlation_id"] for r in rows
                                if r.get("correlation_id")],
        })
    patterns.sort(key=lambda p: (-p["occurrences"], p["signature"]))
    return patterns


# =====================================================================
# stage 3: Improve, proposed (never self-approved)
# =====================================================================
def propose_a_fact(agent_name, correlation_id="", summarizer=None,
                   min_occurrences=2, root=None):
    """Turn detected patterns into semantic facts awaiting a human.

    `summarizer`, when given, receives the pattern and must return one
    sentence - it phrases, it never decides. Its output is stored next
    to the deterministic phrasing so a person can compare both.
    """
    patterns = detect_patterns(agent_name, min_occurrences, root=root)
    if not patterns:
        return {"has_data": False, "proposed": [],
                "note": ("no pattern repeated enough to teach anything "
                         "yet - that is a real empty, not a failure")}

    memory = _memory_dir(root, agent_name)
    pending_path = memory / PENDING_NAME
    existing = {_row_key(p["statement"]) for p in _read_jsonl(pending_path)}
    existing.update({_row_key(f["statement"])
                     for f in _read_jsonl(memory / APPROVED_NAME)})

    proposed = []
    cid = _clean(correlation_id)
    for pattern in patterns:
        statement = (_factual_phrase(pattern) if summarizer is None
                     else _clean(summarizer(pattern))[:300])
        key = _row_key(statement)
        if key in existing:
            continue
        row = {
            "fact_id": f"{agent_name}-{_now().replace(':', '')}-{len(proposed)}",
            "ts": _now(),
            "agent": agent_name,
            "statement": statement,
            "deterministic_statement": _factual_phrase(pattern),
            "status": "pending_human_approval",
            "occurrences": pattern["occurrences"],
            "example_error": pattern["example_error"],
            "suggested_fix": pattern["suggested_fix"],
            "correlation_id": cid,
            "source_correlation_ids": pattern["correlation_ids"],
        }
        _append_jsonl(pending_path, row)
        proposed.append(row)
        existing.add(key)

    return {"has_data": bool(proposed), "proposed": proposed,
            "note": ("facts stay pending until approve_a_fact is called "
                     "by a human decision - proposing is not approving")}


def _row_key(statement: str) -> str:
    return _signature(statement)[:200]


def _factual_phrase(pattern: dict) -> str:
    return (f"When '{pattern['example_error']}' happens, "
            f"the fix that worked ({pattern['occurrences']} times) is: "
            f"{pattern['suggested_fix']}")


# =====================================================================
# stage 4: Improve, gated (the human says yes)
# =====================================================================
def approve_a_fact(agent_name, fact_id, approver="owner", root=None):
    """Move one pending fact to approved - and mint its skill file.

    Only a call to this function creates an approval or a skill. The
    approver name is recorded verbatim; this module never fills it in
    on anyone's behalf.
    """
    memory = _memory_dir(root, agent_name)
    pending_path = memory / PENDING_NAME
    rows = _read_jsonl(pending_path)
    chosen = None
    remaining = []
    for row in rows:
        if row.get("fact_id") == fact_id and chosen is None:
            chosen = row
        else:
            remaining.append(row)
    if chosen is None:
        return {"has_data": False, "approved": False,
                "note": f"no pending fact id '{fact_id}' - nothing approved"}

    chosen["status"] = "approved"
    chosen["approved_by"] = _clean(approver) or "unnamed-approver"
    chosen["approved_ts"] = _now()
    _append_jsonl(memory / APPROVED_NAME, chosen)

    pending_path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in remaining),
        encoding="utf-8")

    skill_path = _write_skill_file(memory, chosen)
    return {"has_data": True, "approved": True,
            "approved_by": chosen["approved_by"],
            "skill_file": str(skill_path)}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "lesson"


def _write_skill_file(memory: Path, fact: dict) -> Path:
    skills = memory / SKILLS_FOLDER
    skills.mkdir(parents=True, exist_ok=True)
    name = f"skill_for_{_slugify(fact['statement'])}.md"
    body = (
        f"# Skill: {fact['statement']}\n\n"
        f"- agent: {fact['agent']}\n"
        f"- seen: {fact['occurrences']} time(s)\n"
        f"- example error: {fact['example_error']}\n"
        f"- fix that worked: {fact['suggested_fix']}\n"
        f"- approved by: {fact['approved_by']} at {fact['approved_ts']}\n"
        f"- source correlation ids: "
        f"{', '.join(fact.get('source_correlation_ids', [])) or 'none'}\n\n"
        "Minted by the_self_improving_loop.approve_a_fact. Version-\n"
        "controlled like every other lesson; refined or superseded when\n"
        "a better approach appears, never silently edited.\n")
    path = skills / name
    path.write_text(body, encoding="utf-8")
    return path



# =====================================================================
# lifebot-style read-only insight (Phase 9.2) - what THIS agent's own
# ledgers say, specifically. Never generic tips; an agent with nothing
# recorded gets an honest empty, not a fortune cookie.
# =====================================================================
def summarize_agent_patterns(agent_name, root=None):
    memory = _memory_dir(root, agent_name)
    rows = read_the_ledger(agent_name, root=root)
    approved = _read_jsonl(memory / APPROVED_NAME)
    pending = _read_jsonl(memory / PENDING_NAME)
    patterns = detect_patterns(agent_name, root=root)

    insights = []
    if patterns:
        top = patterns[0]
        insights.append(
            f"Your most repeated failure ({top['occurrences']}x) is: "
            f"{top['example_error']}. The fix that worked is: "
            f"{top['suggested_fix']}. Wire it in before it bites again.")
    if approved:
        latest = approved[-1]
        insights.append(
            f"You hold {len(approved)} owner-approved lesson(s); the "
            f"newest: {latest['statement'][:160]}")
    if pending:
        insights.append(
            f"{len(pending)} proposed fact(s) sit awaiting the owner - "
            f"the oldest has waited since {pending[0]['ts']}. Nudge, "
            f"do not self-approve.")
    if not rows:
        return {"has_data": False,
                "insights": [],
                "note": (f"{agent_name} has no recorded error+fix yet - "
                         "nothing honest to generalize from")}
    if not insights:
        insights.append(
            f"{len(rows)} error+fix row(s) recorded but none repeated "
            "twice yet - no pattern is honest to claim.")
    return {"has_data": True, "insights": insights,
            "rows_read": len(rows),
            "patterns_found": len(patterns),
            "approved_facts": len(approved),
            "pending_facts": len(pending)}
