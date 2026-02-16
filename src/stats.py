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


def personal_records(df: pd.DataFrame) -> dict:
    """Find personal records across all activities."""
    records = {}

    if not df.empty:
        fastest = df.loc[df["pace_min_km"].idxmin()]
        records["fastest_pace"] = {
            "value": f"{int(fastest['pace_min_km'])}:{int((fastest['pace_min_km'] % 1) * 60):02d} min/km",
            "date": fastest["start_time"].strftime("%b %d, %Y"),
            "distance": f"{fastest['distance_km']:.1f} km",
        }

        longest = df.loc[df["distance_km"].idxmax()]
        records["longest_run"] = {
            "value": f"{longest['distance_km']:.2f} km",
            "date": longest["start_time"].strftime("%b %d, %Y"),
            "pace": f"{int(longest['pace_min_km'])}:{int((longest['pace_min_km'] % 1) * 60):02d} min/km",
        }

        elev = df.dropna(subset=["elevation_gain"])
        if not elev.empty:
            most_elev = elev.loc[elev["elevation_gain"].idxmax()]
            records["most_elevation"] = {
                "value": f"+{most_elev['elevation_gain']:.0f} m",
                "date": most_elev["start_time"].strftime("%b %d, %Y"),
                "distance": f"{most_elev['distance_km']:.1f} km",
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
    if "fastest_pace" in prs:
        pr = prs["fastest_pace"]
        print(f"  Fastest Pace:    {pr['value']}  ({pr['distance']} on {pr['date']})")
    if "longest_run" in prs:
        pr = prs["longest_run"]
        print(f"  Longest Run:     {pr['value']}  ({pr['pace']} on {pr['date']})")
    if "most_elevation" in prs:
        pr = prs["most_elevation"]
        print(f"  Most Elevation:  {pr['value']}  ({pr['distance']} on {pr['date']})")

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
