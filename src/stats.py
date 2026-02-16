"""Weekly and monthly summary statistics for running activities."""

import pandas as pd


def weekly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate running stats by ISO week."""
    df = df.copy()
    df["week"] = df["start_time"].dt.isocalendar().week.astype(int)
    df["year"] = df["start_time"].dt.isocalendar().year.astype(int)
    df["year_week"] = df["year"].astype(str) + "-W" + df["week"].astype(str).str.zfill(2)

    grouped = df.groupby("year_week").agg(
        runs=("activity_id", "count"),
        total_km=("distance_km", "sum"),
        total_min=("duration_min", "sum"),
        avg_pace=("pace_min_km", "mean"),
        avg_cadence=("cadence", "mean"),
        avg_hr=("avg_hr", "mean"),
        total_elevation=("elevation_gain", "sum"),
        total_calories=("calories", "sum"),
    ).round(1)

    return grouped


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate running stats by month."""
    df = df.copy()
    df["month"] = df["start_time"].dt.to_period("M").astype(str)

    grouped = df.groupby("month").agg(
        runs=("activity_id", "count"),
        total_km=("distance_km", "sum"),
        total_min=("duration_min", "sum"),
        avg_pace=("pace_min_km", "mean"),
        avg_cadence=("cadence", "mean"),
        avg_hr=("avg_hr", "mean"),
        total_elevation=("elevation_gain", "sum"),
        total_calories=("calories", "sum"),
    ).round(1)

    return grouped


def _fmt_pace(pace: float) -> str:
    """Format pace as M:SS min/km."""
    return f"{int(pace)}:{int((pace % 1) * 60):02d} min/km"


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
            "detail": f"{best['distance_km']:.1f} km · {best['name']}",
        }

    # Fastest 5K — best average pace among runs >= 5 km
    candidates_5k = df[df["distance_km"] >= 5.0]
    if not candidates_5k.empty:
        best = candidates_5k.loc[candidates_5k["pace_min_km"].idxmin()]
        records["fastest_5k"] = {
            "value": _fmt_pace(best["pace_min_km"]),
            "date": best["start_time"].strftime("%b %d, %Y"),
            "detail": f"{best['distance_km']:.1f} km · {best['name']}",
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
    """Print weekly and monthly summaries to console."""
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

    # Monthly summary
    monthly = monthly_summary(df)
    print(f"\n{'='*60}")
    print(" Monthly Summary")
    print(f"{'='*60}")
    print(f"  {'Month':<10} {'Runs':>5} {'Dist (km)':>10} {'Time (min)':>11} {'Avg Pace':>9}")
    print(f"  {'-'*10} {'-'*5} {'-'*10} {'-'*11} {'-'*9}")
    for month, row in monthly.iterrows():
        pace = row["avg_pace"]
        pace_str = f"{int(pace)}:{int((pace % 1) * 60):02d}" if pd.notna(pace) else "N/A"
        print(f"  {month:<10} {int(row['runs']):>5} {row['total_km']:>10.1f} {row['total_min']:>11.0f} {pace_str:>9}")

    # Weekly summary
    weekly = weekly_summary(df)
    print(f"\n{'='*60}")
    print(" Weekly Summary")
    print(f"{'='*60}")
    print(f"  {'Week':<10} {'Runs':>5} {'Dist (km)':>10} {'Time (min)':>11} {'Avg Pace':>9}")
    print(f"  {'-'*10} {'-'*5} {'-'*10} {'-'*11} {'-'*9}")
    for week, row in weekly.iterrows():
        pace = row["avg_pace"]
        pace_str = f"{int(pace)}:{int((pace % 1) * 60):02d}" if pd.notna(pace) else "N/A"
        print(f"  {week:<10} {int(row['runs']):>5} {row['total_km']:>10.1f} {row['total_min']:>11.0f} {pace_str:>9}")

    print()
