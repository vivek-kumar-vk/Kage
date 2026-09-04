"""Sanitizer hook (D11.5.3) - runs on every chunk before it leaves the
device to be embedded by OmniRoute.

v1 ships the hook and an empty ruleset. Real rules, and whether an LLM
scrub pass earns its cost, are the owner's call after reviewing his own
data - guessing at redaction rules now would be worse than no rules
(a false sense of safety), so this stays a pass-through until he writes
`knowledge/_sanitize_rules.json` through the seam.
"""

import json

from services import seam

RULES_PATH = "knowledge/_sanitize_rules.json"


def _load_rules() -> list:
    try:
        raw = seam.read_doc(RULES_PATH)
    except FileNotFoundError:
        return []
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return rules if isinstance(rules, list) else []


def sanitize(text: str) -> tuple[str, list]:
    """-> (clean_text, hits). `hits` names which rule fired, if any.

    A rule is {"pattern": "<literal substring>", "replacement": "<str>"} -
    plain substring, not regex, so a malformed rule file can never throw
    mid-embed. Empty ruleset (the default) is a true no-op.
    """
    rules = _load_rules()
    hits = []
    clean = text
    for rule in rules:
        pattern = rule.get("pattern") if isinstance(rule, dict) else None
        if not pattern or pattern not in clean:
            continue
        replacement = rule.get("replacement", "[REDACTED]")
        clean = clean.replace(pattern, replacement)
        hits.append(pattern)
    return clean, hits
