"""Stands finance-os up on its own.

PORT — 8002, NOT 8000.
    8000 is the Main Menu (`Main_Menu/Backend/settings_for_main_menu.py`).
    Running this on 8000 hijacks the address the Main Menu lives at, and
    the menu then either refuses to bind or is silently replaced by
    Finance — which looks exactly like "my main app page disappeared".

    The port is read from the Finance screen's own settings file so there
    is still only ONE place a port is written down. The literal below is
    only the fallback for running this tree detached from Kage.

NORMALLY YOU DO NOT RUN THIS
    `Start_Inky/start_every_screen.py` starts every screen, and the
    Finance screen's `Screens/Finance/Backend/server_for_finance.py`
    mounts this same app on 8002. Use this file only to work on
    finance-os alone.
"""

from app_factory import create_app

app = create_app()


def _port(default: int = 8002) -> int:
    """Read PORT out of the Finance screen's settings, or fall back."""
    import pathlib
    import re

    settings = (pathlib.Path(__file__).resolve().parents[2]
                / "Screens" / "Finance" / "Backend" / "settings_for_finance.py")
    if settings.is_file():
        found = re.search(r"^PORT\s*=\s*(\d+)",
                          settings.read_text(encoding="utf-8"), re.M)
        if found:
            return int(found.group(1))
    return default


if __name__ == "__main__":
    import uvicorn

    port = _port()
    print(f"Finance OS -> http://127.0.0.1:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False)
