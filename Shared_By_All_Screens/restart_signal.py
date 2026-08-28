"""One flag file that means: restart every screen, right now.

WHAT THIS IS
    The signal half of a manual restart. Main_Menu's server writes the
    flag when its "Restart INKY" button is clicked; Start_Inky's
    launcher polls for it once a second and, when it sees one, stops
    and relaunches every screen it started - the same processes it
    already owns, just fresh.

WHY A FLAG FILE, NOT A DIRECT CALL
    Main_Menu is one of the processes a restart would need to kill.
    Terminating your own process mid-request is not something a web
    handler can do cleanly, so it never tries: it drops a flag and
    returns. Whichever process actually owns the child processes - the
    launcher - does the killing and relaunching, on its own next tick.

WHAT IF NOTHING IS POLLING
    The flag just sits there. Nothing breaks, nothing restarts. This
    only works when INKY is running via
    Start_Inky\\start_every_screen.py (what Start_Everything.bat
    calls) - a screen started on its own has no launcher watching for
    the flag.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Shared_By_All_Screens
FLAG_FILE = HERE / "restart_requested.flag"

# India has no daylight saving; fixed offset, same clock as everywhere
# else in this project that stamps a time.
IST = timezone(timedelta(hours=5, minutes=30), "IST")


def request_restart() -> None:
    """Drop the flag. Safe to call more than once before it is picked up."""
    FLAG_FILE.write_text(datetime.now(IST).isoformat(), encoding="utf-8")


def restart_was_requested() -> bool:
    return FLAG_FILE.exists()


def clear_restart_request() -> None:
    """Remove the flag. Missing is not an error - it may already have
    been cleared, or never dropped at all."""
    FLAG_FILE.unlink(missing_ok=True)
