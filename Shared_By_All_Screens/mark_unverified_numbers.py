"""Marks any number that cannot be traced back to a source.

THE RULE
    Every figure on screen either came from a file you can point at, or
    it carries [UNVERIFIED] next to it. There is no third option.

WHY IT MATTERS
    A wrong number that looks confident is worse than no number. You act
    on it. The tag makes "I am not sure about this one" impossible to
    miss.

NOTE — THIS IS NOT THE SAME AS THE VIOLET AI MARKER
    Two different questions, often confused:

        [UNVERIFIED]  ->  can I trace where this came from?
        violet border ->  did a model write this, or did I type it?

    A number you typed yourself can be unverified. A number a model
    produced can be perfectly traceable. Both marks can appear together.
"""

from __future__ import annotations

UNVERIFIED = "[UNVERIFIED]"


def tag(rendered: str, source: str | None) -> str:
    """Attach provenance to an already-formatted value.

        tag("₹6,61,952", "loan_statement.pdf")  ->  "₹6,61,952"
        tag("₹6,61,952", None)                  ->  "₹6,61,952 [UNVERIFIED]"

    The caller must say where the number came from. There is deliberately
    no default — a default would let an untraced figure slip through
    looking clean, which is the exact failure this file exists to stop.
    """
    return rendered if source else f"{rendered} {UNVERIFIED}"


def is_verified(source: str | None) -> bool:
    """True when a source was given at all."""
    return bool(source)
