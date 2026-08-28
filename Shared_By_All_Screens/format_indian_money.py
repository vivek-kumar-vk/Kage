"""Writes numbers the Indian way.

Most countries group digits in threes:      1,234,567
India groups the last three, then twos:     12,34,567

So 1234567 rupees is "12 lakh 34 thousand 567", and the commas show it.
Getting this wrong makes every figure on screen look foreign.

    format_inr(661952)    ->  "₹6,61,952"
    format_lakh(661952)   ->  "₹6.62 L"
    format_signed(-1700)  ->  "-₹1,700"
    format_inr(None)      ->  "—"        (blank, never ₹0)
"""

from __future__ import annotations


def group_indian(n: int) -> str:
    """Put the commas in the Indian positions.

    How it works: chop off the last three digits and keep them aside,
    then walk backwards through what remains taking two digits at a time.

        1234567  ->  "567" set aside, then "12" and "34"
                 ->  "12,34,567"
    """
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def format_inr(amount, blank: str = "—") -> str:
    """Rupees with a symbol and the right commas.

    A missing value comes back as a dash, never as ₹0. Showing ₹0 for
    something unknown is a claim you cannot back up — it would say you
    own nothing when the truth is you have not measured yet.
    """
    if amount is None:
        return blank
    neg = amount < 0
    whole = int(round(abs(amount)))
    out = "₹" + group_indian(whole)
    return "-" + out if neg else out


def format_lakh(amount, blank: str = "—") -> str:
    """Format as lakh. 661952 -> '₹6.62 L'."""
    if amount is None:
        return blank
    neg = amount < 0
    out = f"₹{abs(amount) / 100000:.2f} L"
    return "-" + out if neg else out


def format_signed(amount, blank: str = "—") -> str:
    """Same, but always shows + or -.

    Used for surplus, where the sign is the entire point. "+₹8,300" and
    "₹8,300" read very differently next to "-₹1,700".
    """
    if amount is None:
        return blank
    return ("+" if amount > 0 else "") + format_inr(amount, blank)
