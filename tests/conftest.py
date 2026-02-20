"""Shared fixtures for the test suite."""

import sqlite3
from datetime import datetime, timedelta

import pandas as pd
import pytest


@pytest.fixture
def sample_activities_df():
    """DataFrame with 5 realistic running activities across different dates."""
    base = datetime(2025, 6, 1, 8, 0, 0)
    data = {
        "activity_id": [1001, 1002, 1003, 1004, 1005],
        "name": [
            "Morning Easy Run",
            "Tempo Run",
            "Long Run",
            "Recovery Jog",
            "Interval Session",
        ],
        "start_time": [
            base,
            base + timedelta(days=1),
            base + timedelta(days=3),
            base + timedelta(days=4),
            base + timedelta(days=6),
        ],
        "distance_m": [8000.0, 10000.0, 21000.0, 5000.0, 12000.0],
        "duration_s": [2400.0, 2700.0, 6300.0, 1800.0, 3600.0],
        "calories": [500.0, 650.0, 1300.0, 300.0, 800.0],
        "avg_hr": [145.0, 165.0, 155.0, 130.0, 170.0],
        "max_hr": [160.0, 180.0, 175.0, 145.0, 190.0],
        "avg_speed": [3.333, 3.704, 3.333, 2.778, 3.333],
        "elevation_gain": [50.0, 30.0, 150.0, 10.0, 40.0],
        "cadence": [170.0, 175.0, 168.0, 165.0, 180.0],
    }
    df = pd.DataFrame(data)
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["distance_km"] = df["distance_m"] / 1000
    df["duration_min"] = df["duration_s"] / 60
    df["pace_min_km"] = df["duration_min"] / df["distance_km"]
    return df


@pytest.fixture
def empty_df():
    """Empty DataFrame with the correct column structure."""
    cols = [
        "activity_id", "name", "start_time", "distance_m", "duration_s",
        "calories", "avg_hr", "max_hr", "avg_speed", "elevation_gain",
        "cadence", "distance_km", "duration_min", "pace_min_km",
    ]
    df = pd.DataFrame(columns=cols)
    df["start_time"] = pd.to_datetime(df["start_time"])
    return df


@pytest.fixture
def single_activity_df(sample_activities_df):
    """DataFrame with just one activity."""
    return sample_activities_df.iloc[:1].copy()


@pytest.fixture
def sample_activity_dicts():
    """Raw API-format activity dicts (as returned by Garmin Connect API)."""
    return [
        {
            "activityId": 2001,
            "activityName": "Morning Run",
            "startTimeLocal": "2025-07-01 07:30:00",
            "distance": 10000.0,
            "duration": 3000.0,
            "calories": 600.0,
            "averageHR": 150.0,
            "maxHR": 175.0,
            "averageSpeed": 3.333,
            "elevationGain": 45.0,
            "averageRunningCadenceInStepsPerMinute": 172.0,
        },
        {
            "activityId": 2002,
            "activityName": "Evening Tempo",
            "startTimeLocal": "2025-07-02 18:00:00",
            "distance": 8000.0,
            "duration": 2160.0,
            "calories": 500.0,
            "averageHR": 165.0,
            "maxHR": 185.0,
            "averageSpeed": 3.704,
            "elevationGain": 20.0,
            "averageRunningCadenceInStepsPerMinute": 178.0,
        },
    ]


@pytest.fixture
def sample_lap_dtos():
    """Raw lap DTOs as returned by Garmin's get_activity_splits()."""
    return [
        {
            "lapIndex": 0,
            "distance": 1000.0,
            "duration": 270.0,
            "averageSpeed": 3.704,
            "averageHR": 155.0,
            "maxHR": 165.0,
            "averageRunCadence": 174.0,
            "elevationGain": 5.0,
            "elevationLoss": 3.0,
            "calories": 80.0,
            "intensityType": "ACTIVE",
        },
        {
            "lapIndex": 1,
            "distance": 1000.0,
            "duration": 300.0,
            "averageSpeed": 3.333,
            "averageHR": 160.0,
            "maxHR": 170.0,
            "averageRunCadence": 172.0,
            "elevationGain": 8.0,
            "elevationLoss": 6.0,
            "calories": 90.0,
            "intensityType": "ACTIVE",
        },
        {
            "lapIndex": 2,
            "distance": 1000.0,
            "duration": 330.0,
            "averageSpeed": 3.030,
            "averageHR": 148.0,
            "maxHR": 155.0,
            "averageRunCadence": 168.0,
            "elevationGain": 3.0,
            "elevationLoss": 5.0,
            "calories": 75.0,
            "intensityType": "REST",
        },
    ]


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary SQLite database with the activity/laps schema."""
    from src.db import SCHEMA_ACTIVITIES, SCHEMA_LAPS

    db_path = tmp_path / "test_garmin.db"
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA_ACTIVITIES)
    conn.execute(SCHEMA_LAPS)
    conn.commit()
    conn.close()
    return db_path
