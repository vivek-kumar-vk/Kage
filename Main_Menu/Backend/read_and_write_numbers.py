"""Reads and writes the noticeboard — Current_Numbers/all_current_numbers.md.

WHAT THE NOTICEBOARD IS
    One file holding every number the whole system cares about.

    Screens never reach into each other. If one screen needs a figure
    another screen owns, the owner writes it here and the reader reads
    it here. That is the only channel between them.

THE FORMAT IS DELIBERATELY STUPID
        key: value          <- one per line
        # anything          <- a comment
        ## HEADING          <- a group

    Not JSON, not YAML. It has to stay something you can open in
    Obsidian and edit by hand without breaking it. Being easy to edit
    matters more than being elegant to parse.

THE ONE RULE THAT MATTERS
    A blank value comes back as None. NEVER as 0.

        emergency_contribution: 0      -> 0     (really is zero)
        portfolio_total:               -> None  (not measured yet)

    Mixing those two up is how a screen ends up claiming you own nothing
    when the truth is nobody has checked.
"""

from __future__ import annotations

import re
from pathlib import Path

# The noticeboard is still shared - a Finance backfill script reads the
# same file by path - so it stays under Shared_By_All_Screens even though
# this reader moved to its one code caller, the Main Menu.
# because that is exactly what it is: the one thing every screen shares.
STATE_PATH = (Path(__file__).resolve().parents[2] / "Shared_By_All_Screens"
              / "Current_Numbers" / "all_current_numbers.md")

# key: value  (value may be empty)
_LINE = re.compile(r"^([a-z][a-z0-9_]*)\s*:\s*(.*)$")


def _strip_comment(raw: str) -> str:
    return raw.split("#", 1)[0].strip()


def _coerce(text: str):
    """Turn the text after the colon into a number, a word, or None.

    Tries whole number, then decimal, then gives up and keeps it as
    text. An empty value becomes None — see the rule at the top of this
    file. That single choice prevents a whole class of wrong answers.
    """
    if text == "":
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def read_state(path: Path | str = STATE_PATH) -> dict:
    """Return every `key: value` line from the noticeboard as a dict."""
    path = Path(path)
    out: dict = {}
    in_frontmatter = False

    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = raw.rstrip()

        # skip YAML frontmatter, it is Obsidian metadata not state
        if line.strip() == "---":
            if i == 0:
                in_frontmatter = True
                continue
            if in_frontmatter:
                in_frontmatter = False
                continue
        if in_frontmatter:
            continue

        if line.lstrip().startswith(("#", "|", ">", "-")):
            continue

        m = _LINE.match(line)
        if m:
            out[m.group(1)] = _coerce(_strip_comment(m.group(2)))

    return out


def require(state: dict, *keys: str) -> None:
    """Stop with a clear message if something needed is blank.

    Better to fail with "slice_usage_actual is blank" than to quietly
    treat the hole as zero and print a surplus that is ₹28,000 too high.
    Whoever is doing the maths says what they need; this checks it.
    """
    missing = [k for k in keys if state.get(k) is None]
    if missing:
        raise ValueError(
            "The noticeboard is missing a value for: " + ", ".join(missing)
        )


def write_state(values: dict, path: Path | str = STATE_PATH) -> None:
    """Update keys in place. Preserves comments, order, frontmatter — and
    the line endings the file already had.

    That last one is not fussiness. This project is edited on a Windows
    laptop and on a phone under Termux, and the noticeboard is kept in
    git. Reading with the default newline handling turns CRLF into \\n,
    so writing "\\n".join(...) back rewrote every line of the file as LF
    and produced a diff claiming all 77 lines changed when one number
    had moved. Whatever the file uses, it keeps.
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8", newline="")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    remaining = dict(values)
    in_frontmatter = False

    for i, raw in enumerate(lines):
        if raw.strip() == "---":
            if i == 0:
                in_frontmatter = True
                continue
            if in_frontmatter:
                in_frontmatter = False
                continue
        if in_frontmatter or raw.lstrip().startswith(("#", "|", ">", "-")):
            continue

        m = _LINE.match(raw.rstrip())
        if not m or m.group(1) not in remaining:
            continue

        key = m.group(1)
        new = remaining.pop(key)
        comment = ""
        if "#" in m.group(2):
            comment = "  #" + m.group(2).split("#", 1)[1]
        lines[i] = f"{key}: {'' if new is None else new}{comment}"

    if remaining:
        raise KeyError(
            "not present in the noticeboard, refusing to append silently: "
            + ", ".join(remaining)
        )

    path.write_text(newline.join(lines) + newline, encoding="utf-8", newline="")
