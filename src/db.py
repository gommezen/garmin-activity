"""SQLite storage for Garmin running activities."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "data" / "garmin_data.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    activity_id     INTEGER PRIMARY KEY,
    name            TEXT,
    start_time      TEXT,
    distance_m      REAL DEFAULT 0,
    duration_s      REAL DEFAULT 0,
    calories        REAL DEFAULT 0,
    avg_hr          REAL,
    max_hr          REAL,
    avg_speed       REAL,
    elevation_gain  REAL,
    cadence         REAL
)
"""


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def save_activities(activities: list[dict]):
    """Insert activities into the database, skipping duplicates."""
    conn = _connect()
    inserted = 0
    for act in activities:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO activities
                   (activity_id, name, start_time, distance_m, duration_s,
                    calories, avg_hr, max_hr, avg_speed, elevation_gain, cadence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    act.get("activityId"),
                    act.get("activityName"),
                    act.get("startTimeLocal"),
                    act.get("distance", 0) or 0,
                    act.get("duration", 0) or 0,
                    act.get("calories", 0) or 0,
                    act.get("averageHR"),
                    act.get("maxHR"),
                    act.get("averageSpeed"),
                    act.get("elevationGain"),
                    act.get("averageRunningCadenceInStepsPerMinute"),
                ),
            )
            inserted += conn.total_changes and 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    conn.close()
    print(f"Database: {inserted} new activities saved ({count} total in DB)")


def get_activities(days: int = None) -> list[tuple]:
    """Fetch activities from the database, optionally filtered by recent days."""
    conn = _connect()
    if days:
        rows = conn.execute(
            """SELECT * FROM activities
               WHERE date(start_time) >= date('now', ?)
               ORDER BY start_time""",
            (f"-{days} days",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM activities ORDER BY start_time"
        ).fetchall()
    conn.close()
    return rows


COLUMNS = [
    "activity_id", "name", "start_time", "distance_m", "duration_s",
    "calories", "avg_hr", "max_hr", "avg_speed", "elevation_gain", "cadence",
]


def load_dataframe(raw=False):
    """Load activities into a pandas DataFrame with derived columns.

    By default filters out bad data (GPS glitches, interval fragments, etc).
    Pass raw=True to get everything unfiltered.
    """
    import pandas as pd

    conn = _connect()
    df = pd.read_sql("SELECT * FROM activities ORDER BY start_time", conn)
    conn.close()

    df.columns = COLUMNS
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["distance_km"] = df["distance_m"] / 1000
    df["duration_min"] = df["duration_s"] / 60
    df["pace_min_km"] = df["duration_min"] / df["distance_km"].replace(0, float("nan"))

    if not raw:
        total = len(df)
        df = df[
            (df["distance_km"] >= 0.5)
            & (df["duration_s"] > 0)
            & (df["pace_min_km"] >= 2)
            & (df["pace_min_km"] <= 15)
        ]
        filtered = total - len(df)
        if filtered:
            print(f"Filtered {filtered} bad records ({len(df)} clean activities)")

    return df
