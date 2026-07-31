"""Windowed views over activity data, shared by the prescriber and the judge.

Every function takes an explicit `today` so the engines stay testable.
"""

from datetime import date, timedelta

import pandas as pd

MIN_HISTORY_DAYS = 14


def _dates(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["start_time"]).dt.date


def runs_in_window(df: pd.DataFrame, today: date, days: int) -> pd.DataFrame:
    """Runs within the last `days` days, inclusive of today."""
    if df.empty:
        return df
    cutoff = today - timedelta(days=days)
    return df[(_dates(df) > cutoff) & (_dates(df) <= today)]


def km_in_window(df: pd.DataFrame, today: date, days: int) -> float:
    window = runs_in_window(df, today, days)
    return float(window["distance_km"].sum()) if not window.empty else 0.0


def km_since(df: pd.DataFrame, start: date, today: date) -> float:
    """Kilometres run in [start, today] — inclusive of both ends.

    Distinct from km_in_window, whose lower bound is exclusive: a calendar
    week must count the Monday it starts on.
    """
    if df.empty:
        return 0.0
    window = df[(_dates(df) >= start) & (_dates(df) <= today)]
    return float(window["distance_km"].sum()) if not window.empty else 0.0


def history_days(df: pd.DataFrame, today: date) -> int:
    if df.empty:
        return 0
    return (today - min(_dates(df))).days


def acwr(df: pd.DataFrame, today: date) -> float | None:
    """Acute:chronic workload ratio. None when history is too short to mean anything."""
    if history_days(df, today) < MIN_HISTORY_DAYS:
        return None
    chronic_weekly = km_in_window(df, today, 28) / 4.0
    if chronic_weekly == 0:
        return None
    return km_in_window(df, today, 7) / chronic_weekly


def mean_run_distance(df: pd.DataFrame, today: date, days: int = 28) -> float | None:
    window = runs_in_window(df, today, days)
    if window.empty:
        return None
    return float(window["distance_km"].mean())


def _easy_runs(df: pd.DataFrame, today: date, days: int) -> pd.DataFrame:
    """The slower 60% of the window — excludes tempo and interval efforts."""
    window = runs_in_window(df, today, days)
    if window.empty:
        return window
    window = window.dropna(subset=["pace_min_km"])
    if window.empty:
        return window
    threshold = window["pace_min_km"].quantile(0.40)
    return window[window["pace_min_km"] >= threshold]


def median_easy_pace_s(df: pd.DataFrame, today: date, days: int = 28) -> float | None:
    easy = _easy_runs(df, today, days)
    if easy.empty:
        return None
    return float(easy["pace_min_km"].median() * 60)


def median_easy_hr(df: pd.DataFrame, today: date, days: int = 28) -> float | None:
    easy = _easy_runs(df, today, days)
    if easy.empty:
        return None
    easy = easy.dropna(subset=["avg_hr"])
    if easy.empty:
        return None
    return float(easy["avg_hr"].median())


def longest_run_km(df: pd.DataFrame, today: date, days: int | None = None) -> float | None:
    window = df if days is None else runs_in_window(df, today, days)
    if window.empty:
        return None
    return float(window["distance_km"].max())


def consecutive_run_days(df: pd.DataFrame, today: date) -> int:
    """Run-days ending yesterday. Today is not counted — it hasn't happened yet."""
    if df.empty:
        return 0
    run_days = set(_dates(df))
    count, cursor = 0, today - timedelta(days=1)
    while cursor in run_days:
        count += 1
        cursor -= timedelta(days=1)
    return count


def days_since_last_run(df: pd.DataFrame, today: date) -> int | None:
    if df.empty:
        return None
    return (today - max(_dates(df))).days


def weeks_with_min_runs(df: pd.DataFrame, today: date, weeks: int = 3,
                        min_runs: int = 2) -> bool:
    """True when every one of the last `weeks` 7-day blocks had >= min_runs runs."""
    if df.empty:
        return False
    for w in range(weeks):
        end = today - timedelta(days=7 * w)
        start = end - timedelta(days=7)
        block = df[(_dates(df) > start) & (_dates(df) <= end)]
        if len(block) < min_runs:
            return False
    return True


def laps_for(laps_df: pd.DataFrame, activity_id: int) -> list[dict]:
    """Per-lap rows for one activity, shaped for the verdict JSON."""
    if laps_df.empty:
        return []
    rows = laps_df[laps_df["activity_id"] == activity_id].sort_values("lap_index")
    out = []
    for _, lap in rows.iterrows():
        out.append({
            "km": round(float(lap["distance_km"]), 2),
            "pace_s": int(round(float(lap["pace_min_km"]) * 60)),
            "hr": int(lap["avg_hr"]) if pd.notna(lap["avg_hr"]) else None,
            "cadence": int(lap["cadence"]) if pd.notna(lap["cadence"]) else None,
            "elev": int(lap["elevation_gain"]) if pd.notna(lap["elevation_gain"]) else None,
        })
    return out
