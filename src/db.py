"""SQLite storage for Garmin running activities."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parents[1] / "data" / "garmin_data.db"

SCHEMA_ACTIVITIES = """
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

SCHEMA_LAPS = """
CREATE TABLE IF NOT EXISTS laps (
    activity_id     INTEGER,
    lap_index       INTEGER,
    distance_m      REAL DEFAULT 0,
    duration_s      REAL DEFAULT 0,
    avg_speed       REAL,
    avg_hr          REAL,
    max_hr          REAL,
    cadence         REAL,
    elevation_gain  REAL,
    elevation_loss  REAL,
    calories        REAL,
    intensity       TEXT,
    PRIMARY KEY (activity_id, lap_index),
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id)
)
"""
SCHEMA_PROFILE = """
CREATE TABLE IF NOT EXISTS profile (
    id                INTEGER PRIMARY KEY CHECK (id = 1),
    display_name      TEXT,
    goal_type         TEXT,
    goal_target       TEXT,
    goal_date         TEXT,
    days_available    TEXT,
    level             TEXT,
    weekly_volume_lo  REAL,
    weekly_volume_hi  REAL,
    pb_json           TEXT,
    units             TEXT DEFAULT 'km',
    max_hr            REAL,
    created_at        TEXT,
    updated_at        TEXT
)
"""

SCHEMA_PRESCRIPTIONS = """
CREATE TABLE IF NOT EXISTS prescriptions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    date               TEXT NOT NULL UNIQUE,
    prescription_json  TEXT NOT NULL,
    brief_dialogue     TEXT,
    word               TEXT,
    model              TEXT NOT NULL,
    prompt_version     TEXT NOT NULL,
    created_at         TEXT NOT NULL
)
"""

SCHEMA_DEBRIEFS = """
CREATE TABLE IF NOT EXISTS debriefs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER,
    prescription_id INTEGER,
    verdict_json    TEXT NOT NULL,
    dialogue        TEXT NOT NULL,
    instruction     TEXT,
    feel            TEXT,
    followup_q      TEXT,
    followup_a      TEXT,
    model           TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id),
    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
)
"""


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA_ACTIVITIES)
    conn.execute(SCHEMA_LAPS)
    conn.execute(SCHEMA_PROFILE)
    conn.execute(SCHEMA_PRESCRIPTIONS)
    conn.execute(SCHEMA_DEBRIEFS)
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


# ── Lap data ─────────────────────────────────────────


def save_laps(activity_id: int, lap_dtos: list[dict]):
    """Insert laps for an activity, skipping duplicates."""
    conn = _connect()
    for lap in lap_dtos:
        conn.execute(
            """INSERT OR IGNORE INTO laps
               (activity_id, lap_index, distance_m, duration_s, avg_speed,
                avg_hr, max_hr, cadence, elevation_gain, elevation_loss,
                calories, intensity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                activity_id,
                lap.get("lapIndex", 0),
                lap.get("distance", 0) or 0,
                lap.get("duration", 0) or 0,
                lap.get("averageSpeed"),
                lap.get("averageHR"),
                lap.get("maxHR"),
                lap.get("averageRunCadence") or lap.get("averageCadence"),
                lap.get("elevationGain"),
                lap.get("elevationLoss"),
                lap.get("calories", 0) or 0,
                lap.get("intensityType"),
            ),
        )
    conn.commit()
    conn.close()


def get_activities_without_laps() -> list[tuple]:
    """Return (activity_id, name) pairs for activities missing lap data."""
    conn = _connect()
    rows = conn.execute(
        """SELECT a.activity_id, a.name FROM activities a
           LEFT JOIN laps l ON a.activity_id = l.activity_id
           WHERE l.activity_id IS NULL
           ORDER BY a.start_time"""
    ).fetchall()
    conn.close()
    return rows


def load_laps_dataframe():
    """Load laps into a DataFrame with derived columns, joined to activity info."""
    import pandas as pd

    conn = _connect()
    df = pd.read_sql(
        """SELECT l.*, a.name, a.start_time
           FROM laps l
           JOIN activities a ON l.activity_id = a.activity_id
           ORDER BY a.start_time, l.lap_index""",
        conn,
    )
    conn.close()

    if df.empty:
        return df

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["distance_km"] = df["distance_m"] / 1000
    df["duration_min"] = df["duration_s"] / 60
    df["pace_min_km"] = df["duration_min"] / df["distance_km"].replace(0, float("nan"))

    return df
