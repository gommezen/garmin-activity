"""The prescriber: decide today's session from recent load, deterministically.

Rules are ordered — rest, long, tempo, easy — and the first match wins. Every
rule also produces the evidence rows the brief shows, so the advice can always
show its work.
"""

from datetime import date, timedelta

import pandas as pd

from src import queries

REST_ACWR = 1.4
MAX_CONSECUTIVE_DAYS = 3
SPACING_WINDOW_DAYS = 7
TIME_BASED_GOALS = {"break_45"}
EASY_FRACTION = 0.7
LONG_FACTOR = 1.4
LONG_CAP_GROWTH = 1.10
PACE_BAND_HALF_WIDTH_S = 10
HR_CAP_MARGIN = 5
HR_CAP_FRACTION = 0.78
WEEK_GROWTH = 1.10
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _is_time_based(profile: dict) -> bool:
    if profile.get("goal_type") in TIME_BASED_GOALS:
        return True
    return profile.get("goal_type") == "other" and bool(profile.get("goal_target"))


def _week_start(today: date) -> date:
    """Monday of today's calendar week — used for weekly *volume* only."""
    return today - timedelta(days=today.weekday())


def _long_day(days_available: list[str]) -> str | None:
    """The latest available day in the week owns the long run."""
    present = [d for d in DAY_NAMES if d in days_available]
    return present[-1] if present else None


def _hard_effort_recently(df: pd.DataFrame, today: date) -> bool:
    """A run in the faster 40% of the last 28 days, inside the rolling window.

    Rolling rather than calendar-week: on a Monday a calendar week contains
    only today, so yesterday's tempo would be invisible and the engine would
    stack two hard days back to back.
    """
    window = queries.runs_in_window(df, today, 28).dropna(subset=["pace_min_km"])
    if window.empty:
        return False
    threshold = window["pace_min_km"].quantile(0.40)
    recent = queries.runs_in_window(window, today, SPACING_WINDOW_DAYS)
    if recent.empty:
        return False
    return bool((recent["pace_min_km"] < threshold).any())


def _long_run_recently(df: pd.DataFrame, today: date) -> bool:
    """A run at least 1.25x the 28-day mean, inside the rolling window."""
    mean_dist = queries.mean_run_distance(df, today)
    if mean_dist is None:
        return False
    recent = queries.runs_in_window(df, today, SPACING_WINDOW_DAYS)
    if recent.empty:
        return False
    return bool((recent["distance_km"] >= mean_dist * 1.25).any())


def prescribe(profile: dict, df: pd.DataFrame, today: date,
              last_feel: str | None) -> dict:
    """Decide today's session. Pure — pass `today` explicitly."""
    days_available = profile.get("days_available") or []
    today_name = DAY_NAMES[today.weekday()]

    ratio = queries.acwr(df, today)
    consecutive = queries.consecutive_run_days(df, today)
    base = queries.weeks_with_min_runs(df, today)
    mean_dist = queries.mean_run_distance(df, today)
    easy_pace_s = queries.median_easy_pace_s(df, today)
    easy_hr = queries.median_easy_hr(df, today)
    longest = queries.longest_run_km(df, today, days=28)

    week_start = _week_start(today)
    km_so_far = queries.km_since(df, week_start, today)
    prev_week_km = queries.km_in_window(df, week_start - timedelta(days=1), 7)
    target_km = round(prev_week_km * WEEK_GROWTH, 1)

    evidence: list[dict] = []
    session_type = None
    distance_km = None

    # ── Rule 1: rest ──
    if today_name not in days_available:
        session_type = "rest"
        evidence.append({"label": "Because", "value": f"{today_name} is not a training day"})
    elif ratio is not None and ratio > REST_ACWR:
        session_type = "rest"
        evidence.append({"label": "Because", "value": f"Load ratio {ratio:.2f} — above 1.40"})
    elif consecutive >= MAX_CONSECUTIVE_DAYS:
        session_type = "rest"
        evidence.append({"label": "Because", "value": f"{consecutive} days running in a row"})
    elif last_feel == "wrecked":
        session_type = "rest"
        evidence.append({"label": "Because", "value": "You said the last one wrecked you"})

    # ── Rule 2: long ──
    if session_type is None and base and today_name == _long_day(days_available) \
            and not _long_run_recently(df, today):
        session_type = "long"
        distance_km = round((mean_dist or 5.0) * LONG_FACTOR, 1)
        if longest:
            distance_km = round(min(distance_km, longest * LONG_CAP_GROWTH), 1)
        evidence.append({"label": "Because", "value": "Week's long run still owed"})

    # ── Rule 3: tempo ──
    if session_type is None and _is_time_based(profile) and base \
            and not _hard_effort_recently(df, today):
        session_type = "tempo"
        distance_km = round((mean_dist or 5.0) * 0.9, 1)
        evidence.append({"label": "Because", "value": "No hard effort yet this week"})

    # ── Rule 4: easy ──
    if session_type is None:
        session_type = "easy"
        distance_km = round((mean_dist or 5.0) * EASY_FRACTION, 1)
        evidence.append({"label": "Because", "value": "Steady week — bank an easy one"})

    if session_type == "rest":
        pace_band = None
        hr_cap = None
    else:
        pace = easy_pace_s or 360.0
        if session_type == "tempo":
            pace -= 40
        pace_band = [int(pace - PACE_BAND_HALF_WIDTH_S), int(pace + PACE_BAND_HALF_WIDTH_S)]
        if easy_hr is not None:
            hr_cap = int(round(easy_hr + HR_CAP_MARGIN))
        elif profile.get("max_hr"):
            hr_cap = int(round(profile["max_hr"] * HR_CAP_FRACTION))
        else:
            hr_cap = None

    if queries.history_days(df, today) < queries.MIN_HISTORY_DAYS:
        evidence.append({"label": "Note", "value": "Too little history to judge load yet"})
    elif session_type != "rest":
        evidence.append({"label": "Watch for", "value": "Drift in the last third"})

    return {
        "date": today.isoformat(),
        "week_n": today.isocalendar().week,
        "session_type": session_type,
        "distance_km": distance_km,
        "pace_band_s": pace_band,
        "hr_cap": hr_cap,
        "week": {"km_so_far": round(km_so_far, 1), "target_km": target_km},
        "evidence": evidence,
    }
