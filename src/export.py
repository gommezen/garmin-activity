"""Export activities to JSON and CSV."""

import csv
import json
from datetime import date
from pathlib import Path

OUTPUT_DIR = Path(__file__).parents[1] / "output"


def save_to_json(activities: list[dict], sport: str):
    """Save raw activity data to a JSON file."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = OUTPUT_DIR / f"{sport}_activities_{date.today().isoformat()}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(activities, f, indent=2, default=str)

    print(f"JSON saved to: {filename}")


def save_to_csv(activities: list[dict], sport: str):
    """Save activity data to a CSV file with human-readable columns."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = OUTPUT_DIR / f"{sport}_activities_{date.today().isoformat()}.csv"

    headers = [
        "date", "name", "distance_km", "duration_min", "pace_min_km",
        "calories", "avg_hr", "max_hr", "cadence_spm", "elevation_m",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for act in activities:
            distance_m = act.get("distance", 0) or 0
            duration_s = act.get("duration", 0) or 0
            distance_km = distance_m / 1000
            duration_min = duration_s / 60
            pace = duration_min / distance_km if distance_km > 0 else None

            writer.writerow([
                act.get("startTimeLocal", ""),
                act.get("activityName", ""),
                f"{distance_km:.2f}",
                f"{duration_min:.1f}",
                f"{pace:.2f}" if pace else "",
                act.get("calories", ""),
                act.get("averageHR", ""),
                act.get("maxHR", ""),
                act.get("averageRunningCadenceInStepsPerMinute", ""),
                act.get("elevationGain", ""),
            ])

    print(f"CSV saved to: {filename}")
