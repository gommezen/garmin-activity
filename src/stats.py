"""Summary statistics for running activities."""

import pandas as pd


MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def _fmt_pace(pace: float) -> str:
    """Format pace as M:SS min/km."""
    return f"{int(pace)}:{int((pace % 1) * 60):02d} min/km"


def get_available_years(df: pd.DataFrame) -> list[int]:
    """Get list of unique years with activity data, sorted descending."""
    if df.empty:
        return []
    return sorted(df["start_time"].dt.year.unique(), reverse=True)


def year_totals(df: pd.DataFrame) -> dict:
    """Calculate year-level totals."""
    return {
        "runs": len(df),
        "total_km": df["distance_km"].sum(),
        "total_hours": df["duration_min"].sum() / 60,
        "total_elevation": df["elevation_gain"].sum(),
        "total_calories": df["calories"].sum(),
    }


def year_highlights(df: pd.DataFrame) -> dict:
    """Calculate year highlights: best month, biggest week, fastest/longest run, streaks."""
    highlights = {}

    # Best month (most km)
    df_copy = df.copy()
    df_copy["month_num"] = df_copy["start_time"].dt.month
    month_stats = df_copy.groupby("month_num").agg(
        km=("distance_km", "sum"), runs=("activity_id", "count")
    )
    best_month_idx = month_stats["km"].idxmax()
    highlights["best_month"] = {
        "month": MONTH_NAMES[best_month_idx],
        "km": month_stats.loc[best_month_idx, "km"],
        "runs": int(month_stats.loc[best_month_idx, "runs"]),
    }

    # Biggest week (most km)
    df_copy["iso_week"] = (df_copy["start_time"].dt.isocalendar().year.astype(str)
                           + "-W" + df_copy["start_time"].dt.isocalendar().week.astype(str).str.zfill(2))
    week_stats = df_copy.groupby("iso_week").agg(
        km=("distance_km", "sum"), runs=("activity_id", "count")
    )
    best_week_idx = week_stats["km"].idxmax()
    highlights["biggest_week"] = {
        "week": best_week_idx,
        "km": week_stats.loc[best_week_idx, "km"],
        "runs": int(week_stats.loc[best_week_idx, "runs"]),
    }

    # Fastest run (min pace, >= 1km)
    fast_candidates = df[df["distance_km"] >= 1.0]
    if not fast_candidates.empty:
        fastest = fast_candidates.loc[fast_candidates["pace_min_km"].idxmin()]
        highlights["fastest_run"] = {
            "pace": _fmt_pace(fastest["pace_min_km"]),
            "date": fastest["start_time"].strftime("%b %d"),
            "distance": fastest["distance_km"],
            "name": fastest["name"],
        }

    # Longest run
    longest = df.loc[df["distance_km"].idxmax()]
    highlights["longest_run"] = {
        "km": longest["distance_km"],
        "date": longest["start_time"].strftime("%b %d"),
        "pace": _fmt_pace(longest["pace_min_km"]),
        "name": longest["name"],
    }

    # Longest streak (consecutive days)
    dates = sorted(df["start_time"].dt.date.unique())
    if len(dates) <= 1:
        highlights["longest_streak"] = len(dates)
    else:
        current_streak = 1
        max_streak = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        highlights["longest_streak"] = max_streak

    # Active days
    highlights["active_days"] = df["start_time"].dt.date.nunique()

    return highlights


def monthly_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """Get month-by-month stats for a specific year. Returns all 12 months."""
    df_copy = df.copy()
    df_copy["month_num"] = df_copy["start_time"].dt.month

    grouped = df_copy.groupby("month_num").agg(
        runs=("activity_id", "count"),
        total_km=("distance_km", "sum"),
        avg_pace=("pace_min_km", "mean"),
    ).round(1)

    # Ensure all 12 months present
    grouped = grouped.reindex(range(1, 13), fill_value=0)
    grouped["avg_pace"] = grouped["avg_pace"].replace(0, float("nan"))
    grouped["month_name"] = grouped.index.map(MONTH_NAMES)

    return grouped


def personal_records(df: pd.DataFrame) -> dict:
    """Find personal records across all activities.

    Returns fastest 1K, fastest 5K, and longest run.
    """
    records = {}
    if df.empty:
        return records

    # Fastest 1K — best average pace among runs >= 1 km
    candidates_1k = df[df["distance_km"] >= 1.0]
    if not candidates_1k.empty:
        best = candidates_1k.loc[candidates_1k["pace_min_km"].idxmin()]
        records["fastest_1k"] = {
            "value": _fmt_pace(best["pace_min_km"]),
            "date": best["start_time"].strftime("%b %d, %Y"),
            "detail": f"{best['distance_km']:.1f} km \u00b7 {best['name']}",
        }

    # Fastest 5K — best average pace among runs >= 5 km
    candidates_5k = df[df["distance_km"] >= 5.0]
    if not candidates_5k.empty:
        best = candidates_5k.loc[candidates_5k["pace_min_km"].idxmin()]
        records["fastest_5k"] = {
            "value": _fmt_pace(best["pace_min_km"]),
            "date": best["start_time"].strftime("%b %d, %Y"),
            "detail": f"{best['distance_km']:.1f} km \u00b7 {best['name']}",
        }

    # Longest run
    longest = df.loc[df["distance_km"].idxmax()]
    records["longest_run"] = {
        "value": f"{longest['distance_km']:.2f} km",
        "date": longest["start_time"].strftime("%b %d, %Y"),
        "detail": _fmt_pace(longest["pace_min_km"]),
    }

    return records


def print_summary_stats(df: pd.DataFrame):
    """Print year summary and personal records to console."""
    if df.empty:
        print("No activities in database.")
        return

    # Personal records
    prs = personal_records(df)
    print(f"\n{'='*60}")
    print(" Personal Records")
    print(f"{'='*60}")
    if "fastest_1k" in prs:
        pr = prs["fastest_1k"]
        print(f"  Fastest 1K:      {pr['value']}  ({pr['detail']} on {pr['date']})")
    if "fastest_5k" in prs:
        pr = prs["fastest_5k"]
        print(f"  Fastest 5K:      {pr['value']}  ({pr['detail']} on {pr['date']})")
    if "longest_run" in prs:
        pr = prs["longest_run"]
        print(f"  Longest Run:     {pr['value']}  ({pr['detail']} on {pr['date']})")

    # Year summary for latest year
    years = get_available_years(df)
    if years:
        year = years[0]
        year_df = df[df["start_time"].dt.year == year]
        totals = year_totals(year_df)
        print(f"\n{'='*60}")
        print(f" {year} Summary")
        print(f"{'='*60}")
        print(f"  Runs:       {totals['runs']}")
        print(f"  Distance:   {totals['total_km']:.0f} km")
        print(f"  Time:       {totals['total_hours']:.0f} hrs")
        print(f"  Elevation:  +{totals['total_elevation']:.0f} m")
        print(f"  Calories:   {totals['total_calories']:.0f} kcal")

    print()
