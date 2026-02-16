"""Console display formatting for Garmin activities."""


def display_activities(activities: list[dict], sport: str):
    """Print a formatted summary of activities."""
    if not activities:
        print(f"No '{sport}' activities found in the given date range.")
        return

    print(f"\n{'='*60}")
    print(f" Found {len(activities)} '{sport}' activities")
    print(f"{'='*60}\n")

    for i, act in enumerate(activities, 1):
        name = act.get("activityName", "Unnamed")
        start_time = act.get("startTimeLocal", "N/A")
        distance_m = act.get("distance", 0) or 0
        duration_s = act.get("duration", 0) or 0
        calories = act.get("calories", 0) or 0
        avg_hr = act.get("averageHR", None)
        max_hr = act.get("maxHR", None)
        cadence = act.get("averageRunningCadenceInStepsPerMinute", None)
        elevation_gain = act.get("elevationGain", None)
        avg_speed = act.get("averageSpeed", None)

        print(f"  [{i}] {name}")
        print(f"      Date:     {start_time}")
        print(f"      Distance: {distance_m / 1000:.2f} km ({distance_m / 1609.34:.2f} mi)")
        print(f"      Duration: {int(duration_s // 3600)}h {int((duration_s % 3600) // 60)}m {int(duration_s % 60)}s")
        print(f"      Calories: {calories:.0f} kcal")

        if avg_hr:
            print(f"      Avg HR:   {avg_hr:.0f} bpm", end="")
            if max_hr:
                print(f"  |  Max HR: {max_hr:.0f} bpm")
            else:
                print()

        if avg_speed:
            pace_min_per_km = (1000 / avg_speed) / 60 if avg_speed > 0 else 0
            print(f"      Avg Pace: {int(pace_min_per_km)}:{int((pace_min_per_km % 1) * 60):02d} min/km")

        if elevation_gain:
            print(f"      Elevation: +{elevation_gain:.0f} m")

        if cadence:
            print(f"      Cadence:  {cadence:.0f} spm")

        print()
