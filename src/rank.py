"""Training streak.

A streak is consecutive days that were either a run or a *prescribed* rest day.
It counts only from `since` — the date of the first prescription — because runs
that predate the app were never prescribed and are history, not streak.
"""

from datetime import date, timedelta


def streak(run_dates: set[date], rest_dates: set[date], today: date,
           since: date | None) -> int:
    """Count back from today (or yesterday, if today hasn't happened yet)."""
    if since is None:
        return 0

    counted = run_dates | rest_dates
    cursor = today if today in counted else today - timedelta(days=1)

    count = 0
    while cursor >= since and cursor in counted:
        count += 1
        cursor -= timedelta(days=1)
    return count
