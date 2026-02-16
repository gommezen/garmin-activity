"""
Garmin Connect Activity Puller
CLI entry point for pulling activities by sport type.
"""

import sys
import argparse

# Ensure Unicode output works on Windows
sys.stdout.reconfigure(encoding="utf-8")

from src.client import login, pull_activities, SPORT_TYPES
from src.db import save_activities
from src.display import display_activities
from src.export import save_to_json, save_to_csv


def main():
    parser = argparse.ArgumentParser(description="Pull Garmin Connect activities by sport type")
    parser.add_argument(
        "sport",
        nargs="?",
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
        "--csv", action="store_true",
        help="Save data to CSV file in output/ folder",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show weekly and monthly summary stats",
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

    if not args.sport:
        parser.error("sport is required (use --list-sports to see options)")

    client = login()
    activities = pull_activities(client, args.sport, args.days, args.limit)
    display_activities(activities, args.sport)
    save_activities(activities)

    if args.save:
        save_to_json(activities, args.sport)

    if args.csv:
        save_to_csv(activities, args.sport)

    if args.stats:
        from src.stats import print_summary_stats
        from src.db import load_dataframe
        df = load_dataframe()
        print_summary_stats(df)


if __name__ == "__main__":
    main()
