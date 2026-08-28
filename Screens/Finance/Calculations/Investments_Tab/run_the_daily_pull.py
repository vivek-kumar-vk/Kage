"""The daily web pull for every fund INKY tracks - NAVs and full
holdings analysis, written down once a day.

THE CATCH-UP RULE (the whole point)
    The laptop is not always on. There is no scheduler to miss: the
    Finance server calls run_if_due() when it starts, and so can a
    person, Task Scheduler, or anything else. If today's pull already
    ran, it says so and does nothing; if it never ran, or last ran
    three days ago, it runs now and the missed days simply have no row -
    which is the truth, not a gap to paper over with invented data.

WHAT ONE PULL DOES
    1. track_the_nav_ledger.update_the_ledger()  - every fund's NAV,
       appended to fund_nav_ledger.csv (frozen contract v12).
    2. analyse_a_fund.analyse(code) per tracked fund - holdings ledger,
       splits, sector allocation, weighted P/E / P/B, advanced ratios;
       each writes its profile JSON and its fund_analysis_ledger.csv
       row (frozen contract v13).
    3. append_the_price_ledger.update_the_ledger() - today's close per
       held equity/ETF, appended to equity_price_ledger.csv.
    4. fetch_india_ipo_list.fetch_ipo_calendar() - the day's IPO
       calendar into Saved_Records/ipo_calendar.json.

    (The AMFI NAVAll.txt fallback needs no step of its own: it sits
    inside fetch_fund_facts.latest_nav, so step 1 already falls back to
    amfiindia.com whenever mfapi.in is unreachable.)

THE HONESTY RULES
    One fund failing never stops the others. Failures come back listed
    by name, and a fund that failed today keeps yesterday's profile -
    it is not deleted, not overwritten with an empty answer.

RUN IT
    cd <repo root>
    python Screens\\Finance\\Calculations\\Investments_Tab\\run_the_daily_pull.py [--force]
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent          # this tab's maths group
CALCULATIONS = HERE.parent                      # every calculation for this screen
SCREEN = CALCULATIONS.parent                    # the screen folder
PROJECT_ROOT = SCREEN.parent.parent             # the inky folder
sys.path.insert(0, str(PROJECT_ROOT))
for _group in CALCULATIONS.iterdir():           # sibling groups on the path
    if _group.is_dir() and not _group.name.startswith(("_", ".")) \
            and _group.name != "__pycache__":   # so any module here runs
        sys.path.insert(0, str(_group))          # or imports alone
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import analyse_a_fund                           # noqa: E402
import append_the_price_ledger                  # noqa: E402
import fetch_india_ipo_list                     # noqa: E402
import read_portfolio_holdings                  # noqa: E402
import track_the_nav_ledger                     # noqa: E402

STATE_FILE = SCREEN / "Saved_Records" / "daily_pull_state.json"


def _read_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def _write_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def last_pull_date() -> str | None:
    return _read_state().get("last_pull")


# ---------------------------------------------------------------------
# THE PERIODIC PULL
# Changed 2026-08-22 (ADR-075) from one fixed clock slot (17:00 local)
# to a plain interval: every PULL_INTERVAL_HOURS, retry with force=True.
# mfdata.in is a volunteer service and goes down sometimes (HTTP 522
# during testing) - a single daily slot means a bad slot costs a whole
# day. Retrying every 5 hours instead means whatever hour the service
# happens to be back up, the next retry is at most 5 hours away, not up
# to 24. No paid scheduler and no cloud cron: a sleeping thread on this
# laptop is still the whole mechanism, and it still costs nothing to run.
# ---------------------------------------------------------------------
PULL_INTERVAL_HOURS = 5
PULL_INTERVAL_SECONDS = PULL_INTERVAL_HOURS * 3600


def seconds_until_next_pull() -> int:
    """Seconds to the next retry: always the fixed interval.

    Not clock-anchored on purpose (see the note above) - every wait is
    the same length, so whichever hour the service comes back, the next
    attempt is never more than PULL_INTERVAL_HOURS away.
    """
    return PULL_INTERVAL_SECONDS


def run_every_few_hours(stop: "threading.Event | None" = None,
                        sleep=time.sleep) -> None:
    """Blocking loop: sleep the interval, force-pull, repeat. `stop`
    cancels a wait that has not fired yet (used by tests); `sleep` is
    injectable for the same reason."""
    while stop is None or not stop.is_set():
        sleep(seconds_until_next_pull())
        if stop is not None and stop.is_set():
            return
        try:
            result = run_if_due(force=True)
            print(f"[periodic fund pull] {result['date']}: ran={result['ran']} "
                  f"ok={result.get('analyses_ok')} "
                  f"failed={result.get('analyses_failed')}")
        except Exception as problem:                              # noqa: BLE001
            print(f"[periodic fund pull] failed: {problem}")


def _tracked_funds() -> list[dict]:
    """Every mutual-fund holding with an AMFI code, from the snapshot."""
    try:
        holdings = read_portfolio_holdings.read_every_holding()
    except Exception:                                             # noqa: BLE001
        return []
    return [{"scheme_name": h["scheme_name"], "amfi_code": h["amfi_code"]}
            for h in holdings
            if h.get("category") == "mutual_fund"
            and (h.get("amfi_code") or "").strip()]


def run_if_due(today: date | None = None, force: bool = False) -> dict:
    """The one entry point. Safe to call as often as you like."""
    today = today or date.today()
    stamp = today.isoformat()

    if not force and last_pull_date() == stamp:
        return {"ran": False, "date": stamp,
                "reason": "today's pull already ran"}

    nav_result = track_the_nav_ledger.update_the_ledger(today=today)

    analyses = []
    for fund in _tracked_funds():
        try:
            answer = analyse_a_fund.analyse(fund["amfi_code"], today=today)
            analyses.append({
                "amfi_code": fund["amfi_code"],
                "scheme_name": fund["scheme_name"],
                "ok": bool(answer.get("has_data")),
                "note": None if answer.get("has_data") else answer.get("note"),
            })
        except Exception as problem:                              # noqa: BLE001
            analyses.append({
                "amfi_code": fund["amfi_code"],
                "scheme_name": fund["scheme_name"],
                "ok": False,
                "note": f"the analysis itself failed: {problem}",
            })

    # EXTRA STEPS - the equity price ledger and the IPO calendar.
    # Same contract as the analyses above: each step is its own try,
    # one failing never stops the others, and results come back listed
    # by name. (The AMFI NAVAll.txt fallback needs no step of its own -
    # it lives inside fetch_fund_facts.latest_nav, so the NAV ledger
    # above already benefits whenever mfapi.in is down.)
    extra_steps = []
    for step_name, run_step in (
        ("equity_price_ledger",
         lambda: append_the_price_ledger.update_the_ledger(today=today)),
        ("ipo_calendar", fetch_india_ipo_list.fetch_ipo_calendar),
    ):
        try:
            answer = run_step()
            extra_steps.append({
                "step": step_name,
                "ok": bool(answer.get("has_data", True)),
                "note": answer.get("note") if not answer.get("has_data", True)
                        else None,
            })
        except Exception as problem:                              # noqa: BLE001
            extra_steps.append({"step": step_name, "ok": False,
                                "note": f"the step itself failed: {problem}"})

    state = _read_state()
    state["last_pull"] = stamp
    _write_state(state)

    return {
        "ran": True,
        "date": stamp,
        "nav": {"tracked": nav_result["funds_tracked"],
                "written": nav_result["written"],
                "failed": [f["scheme_name"] for f in nav_result["failed"]],
                "untracked": nav_result["untracked"]},
        "analyses": analyses,
        "analyses_ok": sum(1 for a in analyses if a["ok"]),
        "analyses_failed": [a["scheme_name"] for a in analyses if not a["ok"]],
        "extra_steps": extra_steps,
    }


def main() -> None:
    force = "--force" in sys.argv
    result = run_if_due(force=force)
    print("DAILY FUND PULL")
    print("=" * 50)
    if not result["ran"]:
        print(f"  skipped: {result['reason']}")
        return
    print(f"  date            : {result['date']}")
    print(f"  NAV ledger      : {result['nav']['written']} of "
          f"{result['nav']['tracked']} funds written")
    for name in result["nav"]["failed"]:
        print(f"    NAV FAILED    : {name}")
    for name in result["nav"]["untracked"]:
        print(f"    untracked     : {name} (no AMFI code)")
    print(f"  fund analyses   : {result['analyses_ok']} ok, "
          f"{len(result['analyses_failed'])} failed")
    for name in result["analyses_failed"]:
        print(f"    FAILED        : {name}")
    for a in result["analyses"]:
        mark = "ok " if a["ok"] else "no "
        print(f"    [{mark}] {a['scheme_name'][:52]}")
    for step in result.get("extra_steps", []):
        mark = "ok " if step["ok"] else "no "
        note = f" - {step['note']}" if step.get("note") else ""
        print(f"  [{mark}] {step['step']}{note}")


if __name__ == "__main__":
    main()
