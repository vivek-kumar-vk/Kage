"""Empties every screen's fetched-data cache, without naming a screen.

WHAT THIS IS
    Some screens keep a local copy of slow or rate-limited API answers
    - fund history, market prices - under their own
    Saved_Records\\*_cache folder, so a page load does not have to hit
    an external API every time. This walks Screens\\ looking for any
    folder shaped that way and empties it out, exactly the way
    find_every_screen.py and start_every_screen.py find screens: by
    looking, never by a list that names one.

WHAT "CLEARING" MEANS
    Every file inside a *_cache folder is deleted; the folder itself
    stays, so whatever code fetches into it does not need to recreate
    it first. Nothing outside a folder whose name ends in "_cache" is
    ever touched - this is not a general Saved_Records cleaner.

WHAT IT COSTS
    Whatever gets cleared has to be re-fetched from the outside world
    the next time a screen needs it - real API calls, some of them
    rate-limited. This is meant for a deliberate "start clean" action,
    not something to run on every ordinary restart of a dev server.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCREENS_DIR = PROJECT_ROOT / "Screens"


def clear_every_data_cache() -> list[dict]:
    """Empty every Saved_Records\\*_cache folder under Screens\\.

    Returns one entry per cache folder found, whether or not it had
    anything in it:

        {"screen": <folder name>, "cache": <cache folder name>,
         "files_deleted": <count>}
    """
    cleared: list[dict] = []
    if not SCREENS_DIR.is_dir():
        return cleared

    for screen_folder in sorted(SCREENS_DIR.iterdir()):
        records = screen_folder / "Saved_Records"
        if not records.is_dir():
            continue
        for cache_folder in sorted(records.iterdir()):
            if not cache_folder.is_dir() or not cache_folder.name.endswith("_cache"):
                continue
            deleted = 0
            for item in cache_folder.rglob("*"):
                if item.is_file():
                    item.unlink()
                    deleted += 1
            cleared.append({
                "screen": screen_folder.name,
                "cache": cache_folder.name,
                "files_deleted": deleted,
            })
    return cleared
