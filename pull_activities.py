"""
Garmin Connect Activity Puller
Pulls activities by sport type from your Garmin Connect account.
"""

import os
import json
import argparse
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin, GarminConnectAuthenticationError

load_dotenv()

TOKEN_DIR = Path(__file__).parent / ".garmin_tokens"

SPORT_TYPES = [
    "running", "cycling", "swimming", "walking", "hiking",
    "strength_training", "yoga", "cardio", "elliptical",
    "stair_climbing", "rowing", "skiing", "golf", "soccer",
    "basketball", "tennis", "multi_sport", "fitness_equipment",
]


def login() -> Garmin:
    """Authenticate with Garmin Connect, using saved tokens if available."""
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        print("Error: Set GARMIN_EMAIL and GARMIN_PASSWORD in your .env file.")
        raise SystemExit(1)

    client = Garmin(email=email, password=password, return_on_mfa=True)

    # Try to resume from saved tokens
    if TOKEN_DIR.exists():
        try:
            client.garth.load(str(TOKEN_DIR))
            client.display_name = client.garth.profile["displayName"]
            print(f"Logged in as {client.display_name} (from saved tokens)")
            return client
        except Exception:
            print("Saved tokens expired, logging in fresh...")

    # Fresh login
    result1, result2 = client.login()

    if result1 == "needs_mfa":
        mfa_code = input("Enter your MFA code: ")
        try:
            client.resume_login(result2, mfa_code)
        except GarminConnectAuthenticationError:
            print("Error: Invalid MFA code.")
            raise SystemExit(1)

    # Save tokens for next time
    TOKEN_DIR.mkdir(exist_ok=True)
    client.garth.dump(str(TOKEN_DIR))
    print(f"Logged in as {client.display_name}")
    return client


def pull_activities(client: Garmin, sport: str, days: int, limit: int) -> list[dict]:
    """Pull activities filtered by sport type and date range."""
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=days)).isoformat()

    print(f"\nFetching '{sport}' activities from {start_date} to {end_date}...")

    activities = client.get_activities_by_date(
        startdate=start_date,
        enddate=end_date,
        activitytype=sport,
    )

    if limit:
        activities = activities[:limit]

    return activities


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
        steps = act.get("steps", None)
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

        if steps:
            print(f"      Steps:    {steps:,}")

        print()


def save_to_json(activities: list[dict], sport: str):
    """Save raw activity data to a JSON file."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    filename = output_dir / f"{sport}_activities_{date.today().isoformat()}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(activities, f, indent=2, default=str)

    print(f"Raw data saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Pull Garmin Connect activities by sport type")
    parser.add_argument(
        "sport",
        help=f"Sport type to filter. Options: {', '.join(SPORT_TYPES)}",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of days to look back (default: 30)",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Max number of activities to return (default: all)",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save raw data to JSON file in output/ folder",
    )
    parser.add_argument(
        "--list-sports", action="store_true",
        help="List all supported sport types and exit",
    )

    args = parser.parse_args()

    if args.list_sports:
        print("Supported sport types:")
        for s in SPORT_TYPES:
            print(f"  - {s}")
        return

    client = login()
    activities = pull_activities(client, args.sport, args.days, args.limit)
    display_activities(activities, args.sport)

    if args.save:
        save_to_json(activities, args.sport)


if __name__ == "__main__":
    main()
