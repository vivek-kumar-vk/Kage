#!/usr/bin/env python
"""bump.py <task-id> <status> [log message...]

Update progress.json: set a task's status, recompute counts, set `current`
to the first non-clean task, append an optional log line. Keeps the
dashboard + progress.md in sync.
status in: queued | sent | written | clean | rework
"""
from __future__ import annotations
import json, sys, time, pathlib

HERE = pathlib.Path(__file__).resolve().parent
P = HERE / "progress.json"
MD = HERE / "progress.md"

STATUS_ICON = {"queued": "⬜", "sent": "\U0001f7e1", "written": "\U0001f535",
               "clean": "\U0001f7e2", "rework": "\U0001f534"}


def main() -> None:
    task_id = sys.argv[1]
    status = sys.argv[2]
    msg = " ".join(sys.argv[3:]).strip()
    now = time.strftime("%Y-%m-%d %H:%M:%S%z")

    d = json.loads(P.read_text(encoding="utf-8"))
    for t in d["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            break
    counts = {k: 0 for k in ("queued", "sent", "written", "clean", "rework")}
    for t in d["tasks"]:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    d["counts"] = counts
    nxt = next((t["id"] for t in d["tasks"] if t["status"] not in ("clean",)), None)
    d["current"] = nxt
    d["updated"] = now
    done = counts["clean"]
    total = len(d["tasks"])
    d["phase"] = f"building — {done}/{total} clean" if nxt else "done — all tasks clean"
    if msg:
        d.setdefault("log", []).append({"t": now[11:19], "m": f"[{task_id}] {msg}"})
    P.write_text(json.dumps(d, indent=2), encoding="utf-8")

    # regenerate the progress.md table + log from the same data
    rows = "\n".join(
        f"| {t['id']} | `{t['file']}` | {t['owner']} | {STATUS_ICON.get(t['status'], t['status'])} | {t['note']} |"
        for t in d["tasks"]
    )
    loglines = "\n".join(f"- `{l['t']}` {l['m']}" for l in d.get("log", [])[-60:]) or "- _(build not started)_"
    head = MD.read_text(encoding="utf-8").split("| # |")[0].rstrip()
    MD.write_text(
        f"{head}\n\n"
        f"| # | File | Owner | Status | Notes |\n"
        f"|---|------|-------|--------|-------|\n"
        f"{rows}\n\n## Log\n\n{loglines}\n",
        encoding="utf-8",
    )
    print(f"{task_id} -> {status}  ({done}/{total} clean; next: {nxt})")


if __name__ == "__main__":
    main()
