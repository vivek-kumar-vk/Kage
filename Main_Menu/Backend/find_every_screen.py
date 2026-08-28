"""Finds every screen, so nothing has to be listed by hand.

WHAT IT DOES
    Looks inside the `Screens` folder, opens any `screen_definition_for_*.py`
    it finds, checks the file is filled in properly, and hands back the
    list sorted by menu position.

WHY IT EXISTS
    So no other file ever has to know the name of any particular screen.
    The main menu asks this, draws whatever comes back, and never
    changes again.

    That is what makes adding a screen cost ONE FOLDER. A folder with no
    `screen_definition_for_*.py` inside it is reported as "not built yet"
    rather than being loaded. Nothing crashes, nothing is hidden.

    NOTE: no screen name may appear anywhere in this file. A test in
    Tests/test_the_rules_are_followed.py fails if one does. That test
    caught this very docstring on the first attempt.

RUN IT ON ITS OWN
    cd <repo root>
    python Main_Menu\\Backend\\find_every_screen.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

# This file sits at  Main_Menu/Backend/find_every_screen.py
# parents[2] climbs back up to the inky folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCREENS_DIR = PROJECT_ROOT / "Screens"

# The four things every screen_definition file must declare. Nothing more
# is allowed, because anything extra would be a way for one screen to
# smuggle logic into the menu.
REQUIRED = ("SCREEN_NAME", "MENU_LABEL", "MENU_ORDER", "TABS")

# Five tabs maximum. Not a style preference - a screen that needs six
# tabs is really two screens that got merged by accident.
MAX_TABS = 5


class DefinitionError(Exception):
    """A screen_definition file does not say what it must say."""


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"definition_{path.parent.name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _check(mod, folder: str) -> None:
    """Check a screen_definition file before trusting it.

    Every failure here stops the app immediately, with the folder name in
    the message. A half-filled definition should stop startup, not
    produce a half-drawn menu that nobody can explain later.
    """
    for field in REQUIRED:
        if not hasattr(mod, field):
            raise DefinitionError(f"{folder}: missing {field}")

    if mod.SCREEN_NAME != folder.lower():
        raise DefinitionError(
            f"{folder}: SCREEN_NAME is '{mod.SCREEN_NAME}', "
            "which must match the folder name in lowercase"
        )

    if len(mod.TABS) > MAX_TABS:
        raise DefinitionError(
            f"{folder}: {len(mod.TABS)} tabs, the most allowed is {MAX_TABS}. "
            "A screen that needs six tabs is two screens."
        )

    keys = [t["key"] for t in mod.TABS]
    if len(keys) != len(set(keys)):
        raise DefinitionError(f"{folder}: two tabs share the key {keys}")

    for tab in mod.TABS:
        if not tab.get("endpoint", "").startswith("/api/"):
            raise DefinitionError(
                f"{folder}: tab '{tab.get('key')}' has no /api/ endpoint"
            )


def discover():
    """Walk the Screens folder and report what is there.

    Hands back two lists:

        built        screens that are ready, sorted by menu position
        not_built    folder names with no screen_definition file yet

    Not-built screens are returned rather than skipped so the menu can
    show them greyed out as plain text. They must never be drawn as
    buttons that look clickable and do nothing.
    """
    built, not_built = [], []

    if not SCREENS_DIR.exists():
        return built, not_built

    for folder in sorted(p for p in SCREENS_DIR.iterdir() if p.is_dir()):
        if folder.name.startswith((".", "__")):
            continue

        # Each screen declares itself in one file named after the folder
        # it sits in:
        #     Screens/<Name>/screen_definition_for_<name>.py
        # Naming the file after its folder means you always know which one
        # you have open. Twenty files all called definition.py is how you
        # end up editing the wrong one.
        definition = folder / f"screen_definition_for_{folder.name.lower()}.py"
        if not definition.exists():
            not_built.append(folder.name)
            continue

        mod = _load(definition)
        _check(mod, folder.name)

        # Remember which folder it came from, so nobody downstream has to
        # rebuild the path from the name and get the capitals wrong.
        mod.SCREEN_FOLDER = folder
        built.append(mod)

    built.sort(key=lambda m: m.MENU_ORDER)
    return built, not_built


def main() -> None:
    built, not_built = discover()

    print("EVERY SCREEN INKY CAN FIND")
    print()
    print(f"{'order':<8}{'folder':<14}{'menu label':<14}tabs")
    print("-" * 60)
    for m in built:
        tabs = ", ".join(t["key"] for t in m.TABS)
        print(f"{m.MENU_ORDER:<8}{m.SCREEN_NAME:<14}{m.MENU_LABEL:<14}{tabs}")

    print()
    print("not built yet (folder exists, no screen_definition file): "
          f"{', '.join(not_built) or 'none'}")
    print(f"built: {len(built)}   not built: {len(not_built)}")


if __name__ == "__main__":
    main()
