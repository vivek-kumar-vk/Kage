"""Run the calendar agent by hand, without going through the server.

    python Agent/Calendar_Agent/run_now.py                  # last 3 days
    python Agent/Calendar_Agent/run_now.py --days 7          # last 7 days
    python Agent/Calendar_Agent/run_now.py --day 2026-09-05  # one specific day

Run from Main_Menu/Backend/ so calendar_store and settings_for_main_menu
are importable exactly as the server sees them.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import calendar_agent  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=3,
                         help="how many recent days to re-run (default 3)")
    parser.add_argument("--day", type=str, default=None,
                         help="run one specific day instead (YYYY-MM-DD)")
    args = parser.parse_args()

    state = calendar_agent.brain_state()
    print(f"brain: {state}", file=sys.stderr)
    if state["state"] != "ok":
        sys.exit(1)

    if args.day:
        result = {args.day: calendar_agent.run_for_day(args.day)}
    else:
        result = calendar_agent.run_recent(args.days)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
