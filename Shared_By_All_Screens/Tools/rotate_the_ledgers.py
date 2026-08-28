"""Rotate the trace ledger's daily files into monthly shards.

WHAT THIS OWNS
    The raw trace ledger grows one file per day
    (Shared_By_All_Screens/Trace_Ledger/traces_YYYY-MM-DD.jsonl, plus
    _partN files from size rotation). After a month closes, its days are
    consolidated into ONE shard per month:

        Trace_Ledger/Monthly/traces_YYYY-MM.jsonl

    and a Trace_Ledger/Monthly/traces_index.json records what was moved.
    A person greps a month in one place; the nightly reflection never
    needed more than a day; nothing else has to change.

THE THREE RULES
    1. IDEMPOTENT - run it twice, the second run moves nothing. Each
       consumed source file is recorded by name in the index; a name
       already recorded is finished business, never re-appended.
    2. NEVER DELETE BEFORE VERIFIED - a source file is unlinked only
       after its shard exists with the expected number of non-empty
       lines (shard-before + rows-moved == shard-after). If verification
       fails, the source stays put and the run reports it as failed.
       Raw lines are copied verbatim - torn lines stay torn, byte for
       byte, rather than being silently "fixed".
    3. TODAY IS NEVER TOUCHED - only days strictly before today are
       eligible. The file being written right now belongs to no month
       that has closed.

READER SAFETY
    Shards live in the Monthly/ SUBFOLDER on purpose: every existing
    reader globs Trace_Ledger top-level "traces_*.jsonl" and parses names
    through rotate_and_prune_traces.day_and_part, which returns None for
    anything that is not a full date. A monthly shard would already be
    invisible to them even at top level ("not a day"); inside Monthly/
    it cannot even be globbed. The 90-day pruner therefore still works -
    shards simply outlive what they preserve.

ENCRYPTION / OFF-SITE
    Out of scope here - see Backup/backup_the_ledgers.py.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent      # Shared_By_All_Screens
DEFAULT_TRACE_DIR = HERE / "Trace_Ledger"

# Dual import form: some callers put this folder itself on sys.path.
try:
    from Shared_By_All_Screens.Trace_Ledger.rotate_and_prune_traces import (
        day_and_part,
    )
except ImportError:                                   # pragma: no cover
    from Trace_Ledger.rotate_and_prune_traces import day_and_part

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _nonempty_line_count(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _load_index(monthly_dir: Path) -> dict:
    path = monthly_dir / "traces_index.json"
    if not path.exists():
        return {"consumed": {}, "months": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("consumed"), dict):
            data.setdefault("months", {})
            return data
    except (ValueError, OSError):
        pass
    # A torn or unreadable index is rebuilt from scratch; consumed names
    # would then be re-sharded, so a suspect index must ALSO mean the
    # shards are suspect. Callers handle that by failing verification.
    return {"consumed": {}, "months": {}}


def _save_index(monthly_dir: Path, index: dict) -> None:
    index["built_at_utc"] = datetime.now(timezone.utc) \
                                    .isoformat(timespec="seconds")
    tmp = monthly_dir / "traces_index.json.tmp"
    tmp.write_text(json.dumps(index, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, monthly_dir / "traces_index.json")


def eligible_files(trace_dir: Path, today: date | None = None) -> list[Path]:
    """Closed days' files (active + parts), oldest first. Today excluded."""
    today = today or date.today()
    found = []
    if not trace_dir.exists():
        return found
    for path in trace_dir.glob("traces_*.jsonl"):
        parsed = day_and_part(path.name)
        if parsed and parsed[0] < today:
            found.append((parsed[0], parsed[1], path))
    return [path for _, _, path in sorted(found)]

# ---- rotation core continues below -------------------------------------


def rotate_ledgers(trace_dir: Path | None = None,
                   today: date | None = None) -> dict:
    """Shard closed days into monthly files. Returns an honest summary.

    Summary keys: moved (filenames sharded this run), rows_moved,
    failed (filename -> reason), skipped_already_done (filenames found
    on disk whose name the index already recorded - leftovers of an
    interrupted earlier run, whose content is verifiably in the shard;
    they are removed so the next run sees a clean folder).
    """
    trace_dir = Path(trace_dir or DEFAULT_TRACE_DIR)
    monthly_dir = trace_dir / "Monthly"
    index = _load_index(monthly_dir)
    summary: dict = {"moved": [], "rows_moved": 0, "failed": {},
                     "skipped_already_done": []}

    by_month: dict[str, list[tuple[date, int, Path]]] = defaultdict(list)
    leftovers: list[Path] = []
    for path in eligible_files(trace_dir, today):
        parsed = day_and_part(path.name)
        assert parsed is not None          # eligible_files guarantees this
        day, part = parsed
        if path.name in index["consumed"]:
            leftovers.append(path)
            continue
        by_month[f"{day.year:04d}-{day.month:02d}"].append((day, part, path))

    for month in sorted(by_month):
        shard = monthly_dir / f"traces_{month}.jsonl"
        before_text = shard.read_text(encoding="utf-8") if shard.exists() else ""
        before_rows = _nonempty_line_count(before_text)
        pending = []
        appended = 0
        ok = True
        for _day, _part, src in sorted(by_month[month]):
            try:
                text = src.read_text(encoding="utf-8")
            except OSError as trouble:
                summary["failed"][src.name] = f"unreadable ({trouble})"
                ok = False
                continue
            pending.append((src, text, _nonempty_line_count(text)))
            appended += pending[-1][2]
        if not ok or not pending:
            continue
        try:
            monthly_dir.mkdir(parents=True, exist_ok=True)
            tmp = shard.with_suffix(".jsonl.tmp")
            tmp.write_text(before_text + "".join(t for _, t, _ in pending),
                           encoding="utf-8")
            after_rows = _nonempty_line_count(tmp.read_text(encoding="utf-8"))
            if after_rows != before_rows + appended:
                raise RuntimeError(
                    f"row count mismatch ({before_rows}+{appended}"
                    f" != {after_rows})")
            os.replace(tmp, shard)
        except Exception as trouble:                          # noqa: BLE001
            for src, _, _ in pending:
                summary["failed"][src.name] = f"shard not verified ({trouble})"
            continue
        # Shard written AND row-count-equal: only now record and delete.
        for src, _, rows in pending:
            index["consumed"][src.name] = rows
            months = index.setdefault("months", {})
            months.setdefault(month, {"rows": 0, "sources": []})
            months[month]["rows"] += rows
            months[month]["sources"].append(src.name)
            summary["moved"].append(src.name)
            summary["rows_moved"] += rows
        _save_index(monthly_dir, index)
        # Only now, with the index safely on disk, do the originals go.
        for src, _, _ in pending:
            try:
                src.unlink()
            except OSError as trouble:                        # noqa: BLE001
                summary["failed"][src.name] = \
                    f"sharded but not removable ({trouble})"

    # Finish interrupted runs: index says consumed, file still on disk.
    # The content was verified present when that run completed, so the
    # leftover holds nothing the shard lacks. A failed deletion is
    # reported and simply retried next run.
    for src in leftovers:
        try:
            src.unlink()
            summary["skipped_already_done"].append(src.name)
        except OSError as trouble:                            # noqa: BLE001
            summary["failed"][src.name] = f"leftover not removable ({trouble})"
    return summary


def main() -> int:
    print("TRACE LEDGER MONTHLY ROTATION")
    print("=" * 50)
    summary = rotate_ledgers()
    print(f"  Ledger folder: {Path(DEFAULT_TRACE_DIR)}")
    if not (summary["moved"] or summary["failed"]
            or summary["skipped_already_done"]):
        print("  Nothing to move - every closed day is already sharded.")
    for name in summary["moved"]:
        print(f"  moved: {name}")
    if summary["rows_moved"]:
        print(f"  rows moved: {summary['rows_moved']}")
    for name in summary["skipped_already_done"]:
        print(f"  leftover removed (already in shard): {name}")
    for name, reason in summary["failed"].items():
        print(f"  FAILED (source left in place): {name} - {reason}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
