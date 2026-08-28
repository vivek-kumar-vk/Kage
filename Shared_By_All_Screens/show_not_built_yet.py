"""Builds the "not built yet" page a screen shows before it has a page.

WHY THIS EXISTS
    A screen with no page used to answer with a wall of raw JSON. That is
    fine for a programmer and useless for anyone else - it looks broken
    even though nothing is wrong.

    This hands back a real page instead: it says plainly that the screen
    is not built, names the file that would replace it, lists the data
    that already works behind it, and offers a way back to the menu.

WHAT IT REFUSES TO DO
    Invent anything. No sample rows, no placeholder chart, no greyed-out
    button that looks like it might work. Empty beats fake.

THE TEMPLATE
    Look_And_Feel/page_not_built_yet.html, with four words swapped in.
    It is a plain HTML file rather than a string in here so the look of
    it lives with the rest of the look.
"""

from __future__ import annotations

import html
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "Look_And_Feel" / "page_not_built_yet.html"

# Where the menu lives. Written down once, here, because every screen's
# "back" button needs the same answer.
MENU_ADDRESS = "http://127.0.0.1:8000/"


def page_html(screen_label: str,
              page_path: Path | str,
              working_endpoints: list[str]) -> str:
    """The finished HTML for one screen's "not built yet" notice.

    `working_endpoints` are addresses on this same screen's server that
    already return real data. They are listed as links so they can be
    clicked and checked, rather than merely claimed.
    """
    if working_endpoints:
        items = "\n      ".join(
            f'<li><a href="{html.escape(e)}">{html.escape(e)}</a></li>'
            for e in working_endpoints
        )
    else:
        items = "<li>Nothing yet. Not even the data behind it.</li>"

    return (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("SCREEN_LABEL_HERE", html.escape(screen_label.upper()))
        .replace("PAGE_PATH_HERE", html.escape(str(page_path)))
        .replace("ENDPOINTS_HERE", items)
        .replace("MENU_ADDRESS_HERE", MENU_ADDRESS)
    )
