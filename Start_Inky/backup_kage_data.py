"""Zips kage-data/ (item 17) - the only single point of data loss in the
project, since D40 moved it repo-relative.

WHY THIS EXISTS
    kage-data/ lives on one disk. Nothing in git covers it (Rule 7.1 - it
    is gitignored on purpose). This is a manual export, run by hand, until
    the real destination (phone-hosted, synced from a future desktop app)
    exists - see PLAN.md item 17 and NOW.md for that decision.

WHAT IT DOES NOT DO
    No scheduling, no automatic trigger, no upload anywhere. You run it
    when you want a backup. It never guesses a destination - point it at
    one explicitly, every time, so a backup never silently lands somewhere
    you didn't choose (Rule 8/22).

RUN IT
    .venv\\Scripts\\python.exe Start_Inky\\backup_kage_data.py --dest D:\\some\\folder
    (or set KAGE_BACKUP_DIR once and omit --dest)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent
STORAGE_BACKEND = PROJECT_ROOT / "Screens" / "Storage" / "Backend"
sys.path.insert(0, str(STORAGE_BACKEND))

import settings_for_storage as cfg  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
STATUS_FILE = "_backup_status.json"


def _resolve_dest(cli_dest: str | None) -> Path:
    """Never guess a destination - CLI flag, then env var, then a clear
    error telling you to pick one."""
    raw = cli_dest or os.environ.get("KAGE_BACKUP_DIR")
    if not raw:
        print(
            "No backup destination given. Pass --dest <folder> or set "
            "KAGE_BACKUP_DIR. Not guessing one (Rule 22).",
            file=sys.stderr,
        )
        sys.exit(1)
    return Path(raw).expanduser().resolve()


def _zip_kage_data(dest_dir: Path) -> Path:
    """Zips every file under KAGE_DATA_DIR into one timestamped archive."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(IST)
    archive_path = dest_dir / f"kage-data-backup-{now.strftime('%Y%m%d-%H%M%S')}.zip"

    data_dir = cfg.KAGE_DATA_DIR
    file_count = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in data_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(data_dir))
                file_count += 1

    return archive_path, file_count, now


def _write_status(archive_path: Path, file_count: int, now: datetime) -> None:
    """Records the last backup as a system file inside kage-data/ itself
    (D33.3 convention: a leading underscore marks a system file), so
    Storage's /status endpoint can report it honestly."""
    status = {
        "last_backup_at": now.isoformat(),
        "destination": str(archive_path),
        "files": file_count,
        "bytes": archive_path.stat().st_size,
    }
    (cfg.KAGE_DATA_DIR / STATUS_FILE).write_text(
        json.dumps(status, indent=2), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", help="Folder to write the backup zip into")
    args = parser.parse_args()

    dest_dir = _resolve_dest(args.dest)
    if not cfg.KAGE_DATA_DIR.is_dir():
        print(f"KAGE_DATA_DIR does not exist: {cfg.KAGE_DATA_DIR}", file=sys.stderr)
        return 1

    archive_path, file_count, now = _zip_kage_data(dest_dir)
    _write_status(archive_path, file_count, now)

    print(f"Backed up {file_count} file(s) from {cfg.KAGE_DATA_DIR}")
    print(f"  -> {archive_path} ({archive_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
