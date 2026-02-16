"""Garmin Connect authentication and activity fetching."""

import os
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
import time

from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectTooManyRequestsError

load_dotenv()

TOKEN_DIR = Path(__file__).parents[1] / "data" / ".garmin_tokens"

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
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    client.garth.dump(str(TOKEN_DIR))
    client.display_name = client.garth.profile["displayName"]
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


def pull_laps(client: Garmin, activity_id: int, max_retries: int = 5) -> list[dict]:
    """Fetch lap/split data for a single activity with rate-limit retry."""
    for attempt in range(max_retries):
        try:
            splits = client.get_activity_splits(str(activity_id))
            return splits.get("lapDTOs", [])
        except GarminConnectTooManyRequestsError:
            wait = 60 * (2 ** attempt)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)
    print(f"  Failed to fetch laps for {activity_id} after {max_retries} retries")
    return []
