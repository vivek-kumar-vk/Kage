"""Reads one screen's settings file.

WHY THIS IS SHARED
    Two different things need to know which port a screen wants:

        Start_Inky\\start_every_screen.py     to start it
        Main_Menu\\Backend\\server_for_main_menu.py   to link to it

    Two copies of "how do I find the port" is how the menu ends up
    linking to a port nothing is listening on. There is one copy, here.

THE ONE PLACE A PORT IS WRITTEN DOWN
    Each screen's own  Backend\\settings_for_<name>.py  file. Nothing
    keeps a second list. If a screen changes its port, both the launcher
    and the menu follow it on the next run without anyone editing them.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path


def settings_file(screen_folder: Path) -> Path | None:
    """The screen's settings file, or None if it has no Backend yet."""
    backend = Path(screen_folder) / "Backend"
    if not backend.is_dir():
        return None
    found = sorted(backend.glob("settings_for_*.py"))
    return found[0] if found else None


def read_settings(path: Path) -> dict:
    """Load a settings file and pull out the few values anyone needs.

    Missing values come back as None rather than a guess. A guessed port
    is how you end up with two servers fighting over 8000.
    """
    path = Path(path)
    spec = importlib.util.spec_from_file_location(f"settings_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return {
        "label": getattr(mod, "SCREEN_LABEL", path.stem),
        "host": getattr(mod, "HOST", "127.0.0.1"),
        "port": getattr(mod, "PORT", None),
        "page": getattr(mod, "PAGE", None),
    }


def web_address(screen_folder: Path) -> str | None:
    """The address to send a browser to, or None if the screen cannot serve.

    None is a real answer here: it means "there is nothing to open yet".
    The menu must show that as plain unclickable text, never as a button
    that looks alive and does nothing.

    Normally an absolute `http://host:port/` - correct when a browser can
    reach every screen's own port directly, which is the only case this
    project ran until now. Behind `Start_Inky\\serve_everything_on_one_port.py`
    (one shared address, for a phone or an ngrok tunnel where only one port
    is actually reachable), `INKY_BEHIND_PROXY` is set and this returns a
    path on that shared origin instead - `/<screen folder name>/` - which
    the proxy already knows how to route. Nothing here names a screen; the
    folder's own name is used exactly as it is.
    """
    path = settings_file(screen_folder)
    if path is None:
        return None

    info = read_settings(path)
    if info["port"] is None:
        return None

    if os.environ.get("INKY_BEHIND_PROXY"):
        return f"/{Path(screen_folder).name.lower()}/"

    return f"http://{info['host']}:{info['port']}/"
