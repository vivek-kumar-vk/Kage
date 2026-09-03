"""Watches CODE files for changes so an open page can refresh itself.

WHAT THIS IS
    The fingerprint half of the live auto-refresh. A page polls its own
    /dev/changed-since endpoint every 30 seconds; this module answers
    whether anything behind that screen has actually changed since the
    page was loaded.

    It fingerprints by path + mtime + size, not content: reading every
    file's bytes thirty times a minute is waste when mtime already says
    "nothing moved". One hash covers all watched folders at once, so a
    page needs no list of files - just one token it got back last time.

WHY DATA FOLDERS ARE EXCLUDED
    Saved_Records changes on every ordinary click (a CSV gets appended
    to). If data writes counted as changes, every click would reload
    the page that caused it. EXCLUDED_DIR_NAMES exists for exactly one
    reason: this must fire on a CODE edit, never on an ordinary data
    write.

THE ONE RULE
    An empty previous fingerprint always means "not changed" - that call
    is a page establishing its baseline on first load, not a comparison.
    Getting this wrong reloads every tab in an infinite loop the moment
    it opens.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # Main_Menu/Backend
PROJECT_ROOT = HERE.parents[2]                  # the inky folder

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# India has no daylight saving; fixed offset, same clock as everywhere.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

# What counts as a code file. Everything else (CSVs, images, logs) is
# invisible to the watcher even inside a watched folder.
CODE_SUFFIXES = {".py", ".js", ".html", ".css", ".json"}

# Folder NAMES never watched, wherever they appear. Data folders, caches,
# and the ledger itself - a trace write must not reload the page that
# caused the trace.
EXCLUDED_DIR_NAMES = {
    "__pycache__", ".venv", ".git", ".pytest_cache",
    "Saved_Records", "Trace_Ledger", "Knowledge_Base",
    "Memory", "Lease_Board", "Daily_Notes", "Dump",
}

# Off switch for the RELOAD behaviour only (e.g. phone/tunnel use).
# Missing file or bad JSON means enabled - fail open, because the worst
# this code can ever do is a harmless reload, never a data problem.
TOGGLE_FILE = HERE / "dev_auto_refresh_toggle.json"


def _iter_code_files(folders: list[Path]):
    """Every code file under the given folders, excluding data folders."""
    seen = set()
    for folder in folders:
        root = Path(folder)
        if not root.exists():
            continue
        resolved = root.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in CODE_SUFFIXES:
                continue
            # Skip anything sitting under an excluded folder name.
            if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
                continue
            yield path


def fingerprint_of(folders: list[Path]) -> dict:
    """One hash covering every code file's path+mtime+size.

    Returns {"fingerprint": <sha256 hex>, "latest_file": <relpath or "">,
    "latest_at": <iso timestamp or "">} - the last two say WHICH file
    moved, so a trace row can record something a person can act on.
    """
    parts: list[str] = []
    latest_file, latest_mtime = "", 0.0
    project_root = PROJECT_ROOT
    for path in _iter_code_files(folders):
        try:
            stat = path.stat()
        except OSError:
            continue                       # vanished mid-scan: skip it
        try:
            rel = str(path.relative_to(project_root))
        except ValueError:
            rel = str(path)                # a folder outside the project
        parts.append(f"{rel}|{stat.st_size}|{stat.st_mtime_ns}")
        if stat.st_mtime > latest_mtime:
            latest_mtime = stat.st_mtime
            latest_file = rel
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    latest_at = ""
    if latest_mtime:
        latest_at = datetime.fromtimestamp(latest_mtime, tz=IST).isoformat()
    return {"fingerprint": digest, "latest_file": latest_file,
            "latest_at": latest_at}


def has_changed(previous_fingerprint: str, folders: list[Path]) -> dict:
    """Compare a stored fingerprint against the disk, honestly.

    An EMPTY previous_fingerprint always returns changed=False - that
    call is a baseline being established, not a real comparison.
    """
    current = fingerprint_of(folders)
    changed = bool(previous_fingerprint) and previous_fingerprint != current["fingerprint"]
    return {"changed": changed, **current}


def is_enabled() -> bool:
    """Read dev_auto_refresh_toggle.json. Missing or broken means ON."""
    try:
        with open(TOGGLE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        return bool(state.get("enabled", True))
    except (OSError, ValueError):
        return True


def main() -> None:
    print("FILE CHANGE WATCHER")
    print("=" * 50)
    print(f"  toggle file : {TOGGLE_FILE.name} "
          f"({'on' if is_enabled() else 'OFF - pages will not auto-reload'})")
    result = fingerprint_of([PROJECT_ROOT])
    n = sum(1 for _ in _iter_code_files([PROJECT_ROOT]))
    print(f"  watching    : {n} code files across the project")
    print(f"  fingerprint : {result['fingerprint'][:16]}…")
    if result["latest_file"]:
        print(f"  last touched: {result['latest_file']} at {result['latest_at']}")


if __name__ == "__main__":
    main()
