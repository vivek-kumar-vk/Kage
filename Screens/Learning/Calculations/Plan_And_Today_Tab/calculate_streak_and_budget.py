"""The idea worth building, from the guide: a budget you can run down,
not a points count that only ever goes up.

THE MATHS
    Target 5 days out of 7 is 71%, which leaves 2 days of slack a week -
    days you are allowed to miss and still be on target. Every day that
    passes without a session and was not already covered by that slack
    spends one unit of it. Miss a third day and the target for that week
    is already gone, no matter what happens on the remaining days -  that
    is reported plainly rather than hidden behind an average.

    This is the same error-budget shape used for real SLOs at work,
    tried here on the user's own data first (the guide's own words).

WEEK BOUNDARY
    Monday to Sunday, calendar weeks - not a rolling 7 days. A rolling
    window means the budget can recover by walking backwards through
    time as an old miss ages out, which makes "how much slack is left"
    a moving target instead of a plain fact about this week so far.

RUN IT
    cd <repo root>
    python Screens\\Learning\\Calculations\\Plan_And_Today_Tab\\calculate_streak_and_budget.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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

IST = timezone(timedelta(hours=5, minutes=30), "IST")

TARGET_DAYS_PER_WEEK = 5   # the guide's own number: 5 of 7, 71%


@dataclass(frozen=True)
class StudyStreak:
    current_streak_days: int
    last_studied: str | None

    week_start: str
    days_elapsed_this_week: int
    days_studied_this_week: int
    target_days_per_week: int
    slack_days: int                 # 7 - target, at the start of every week
    slack_used: int
    slack_left: int
    target_still_reachable: bool
    on_track_today: bool | None     # None when no day has passed to judge yet


def _study_dates(sessions: list[dict]) -> set[date]:
    return {date.fromisoformat(row["date"]) for row in sessions}


def _streak(study_dates: set[date], today: date) -> tuple[int, str | None]:
    """Consecutive days with at least one session, ending today or
    yesterday. A day with nothing logged does not end the streak until
    that day is actually over - so a streak "survives" until midnight,
    not until the first missed check."""
    if not study_dates:
        return 0, None

    last_studied = max(study_dates)
    anchor = today if today in study_dates else today - timedelta(days=1)
    if anchor < last_studied:
        anchor = last_studied
    if (today - last_studied).days > 1:
        return 0, last_studied.isoformat()

    streak = 0
    cursor = anchor
    while cursor in study_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak, last_studied.isoformat()


def compute(sessions: list[dict] | None = None, today: date | None = None,
           target_days_per_week: int = TARGET_DAYS_PER_WEEK) -> StudyStreak:
    if sessions is None:
        from track_study_sessions import read_sessions
        sessions = read_sessions()
    today = today or datetime.now(IST).date()

    study_dates = _study_dates(sessions)
    streak, last_studied = _streak(study_dates, today)

    week_start = today - timedelta(days=today.weekday())   # Monday
    days_elapsed = (today - week_start).days + 1            # today counts
    studied_this_week = sum(
        1 for d in study_dates if week_start <= d <= today
    )

    slack_days = 7 - target_days_per_week
    days_missed_so_far = days_elapsed - studied_this_week
    slack_used = max(0, days_missed_so_far)
    slack_left = max(0, slack_days - slack_used)

    days_left_in_week = 7 - days_elapsed
    still_needed = max(0, target_days_per_week - studied_this_week)
    target_still_reachable = still_needed <= days_left_in_week

    on_track_today = None
    if days_elapsed > 0:
        on_track_today = slack_used <= slack_days

    return StudyStreak(
        current_streak_days=streak,
        last_studied=last_studied,
        week_start=week_start.isoformat(),
        days_elapsed_this_week=days_elapsed,
        days_studied_this_week=studied_this_week,
        target_days_per_week=target_days_per_week,
        slack_days=slack_days,
        # Uncapped on purpose: "missed 3 with 2 days of slack" is a more
        # honest readout than quietly capping the overrun at 2.
        slack_used=slack_used,
        slack_left=slack_left,
        target_still_reachable=target_still_reachable,
        on_track_today=on_track_today,
    )


def main() -> None:
    result = compute()
    print("STREAK AND BUDGET")
    print("=" * 50)
    if result.current_streak_days:
        print(f"  Current streak: {result.current_streak_days} day(s)")
    else:
        print("  No current streak.")
    print(f"  Last studied: {result.last_studied or 'never'}")
    print()
    print(f"  Week starting {result.week_start}")
    print(f"    studied {result.days_studied_this_week} of "
          f"{result.days_elapsed_this_week} day(s) so far "
          f"(target {result.target_days_per_week}/7)")
    print(f"    slack: {result.slack_left} of {result.slack_days} day(s) left")
    if not result.target_still_reachable:
        print("    TARGET ALREADY MISSED THIS WEEK - not enough days left to reach 5/7")
    print()
    print("  INKY does not turn this into instructions (C5) - it is a fact "
         "about the week, not advice about what to do next.")


if __name__ == "__main__":
    main()
