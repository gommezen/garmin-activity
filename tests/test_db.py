"""Tests for src.db — database operations with temporary SQLite databases."""

import sqlite3

import pandas as pd
import pytest

from src import db


@pytest.fixture(autouse=True)
def _patch_db_path(test_db, monkeypatch):
    """Override DB_PATH so all db functions use the temp database."""
    monkeypatch.setattr(db, "DB_PATH", test_db)


class TestSaveAndGetActivities:
    def test_insert_and_retrieve(self, sample_activity_dicts):
        db.save_activities(sample_activity_dicts)
        rows = db.get_activities()
        assert len(rows) == 2
        # Check first activity's ID
        assert rows[0][0] == 2001

    def test_duplicate_handling(self, sample_activity_dicts):
        """INSERT OR IGNORE should skip duplicates silently."""
        db.save_activities(sample_activity_dicts)
        db.save_activities(sample_activity_dicts)  # Insert same data again
        rows = db.get_activities()
        assert len(rows) == 2  # Still 2, not 4

    def test_get_activities_with_days_filter(self, sample_activity_dicts):
        db.save_activities(sample_activity_dicts)
        # Activities are from 2025-07 — with a 1-day filter from "now", none match
        rows = db.get_activities(days=1)
        assert len(rows) == 0

    def test_null_optional_fields(self):
        """Activities with missing optional fields should still save."""
        acts = [{
            "activityId": 3001,
            "activityName": "No HR Run",
            "startTimeLocal": "2025-08-01 10:00:00",
            "distance": 5000.0,
            "duration": 1500.0,
            "calories": 300.0,
            "averageHR": None,
            "maxHR": None,
            "averageSpeed": 3.333,
            "elevationGain": None,
            "averageRunningCadenceInStepsPerMinute": None,
        }]
        db.save_activities(acts)
        rows = db.get_activities()
        assert len(rows) == 1


class TestLoadDataframe:
    def test_derived_columns(self, sample_activity_dicts):
        db.save_activities(sample_activity_dicts)
        df = db.load_dataframe(raw=True)
        assert "distance_km" in df.columns
        assert "duration_min" in df.columns
        assert "pace_min_km" in df.columns
        # Check derived values: 10000m = 10km
        row = df[df["activity_id"] == 2001].iloc[0]
        assert row["distance_km"] == pytest.approx(10.0)

    def test_filtering(self, sample_activity_dicts):
        """Default filtering removes bad records."""
        # Add a bad activity (too short)
        bad_act = [{
            "activityId": 9999,
            "activityName": "GPS Glitch",
            "startTimeLocal": "2025-07-03 12:00:00",
            "distance": 100.0,  # 0.1 km — below 0.5 km threshold
            "duration": 30.0,
            "calories": 10.0,
            "averageHR": None,
            "maxHR": None,
            "averageSpeed": 3.333,
            "elevationGain": None,
            "averageRunningCadenceInStepsPerMinute": None,
        }]
        db.save_activities(sample_activity_dicts + bad_act)
        raw = db.load_dataframe(raw=True)
        clean = db.load_dataframe(raw=False)
        assert len(raw) == 3
        assert len(clean) < len(raw)

    def test_empty_database(self):
        df = db.load_dataframe()
        assert df.empty
        assert "distance_km" in df.columns


class TestSaveAndLoadLaps:
    def test_insert_and_retrieve(self, sample_activity_dicts, sample_lap_dtos):
        db.save_activities(sample_activity_dicts)
        db.save_laps(2001, sample_lap_dtos)
        laps_df = db.load_laps_dataframe()
        assert len(laps_df) == 3
        assert "distance_km" in laps_df.columns
        assert "pace_min_km" in laps_df.columns

    def test_duplicate_laps(self, sample_activity_dicts, sample_lap_dtos):
        db.save_activities(sample_activity_dicts)
        db.save_laps(2001, sample_lap_dtos)
        db.save_laps(2001, sample_lap_dtos)
        laps_df = db.load_laps_dataframe()
        assert len(laps_df) == 3

    def test_empty_laps(self):
        laps_df = db.load_laps_dataframe()
        assert laps_df.empty


class TestGetActivitiesWithoutLaps:
    def test_all_missing(self, sample_activity_dicts):
        db.save_activities(sample_activity_dicts)
        missing = db.get_activities_without_laps()
        assert len(missing) == 2

    def test_partial_laps(self, sample_activity_dicts, sample_lap_dtos):
        db.save_activities(sample_activity_dicts)
        db.save_laps(2001, sample_lap_dtos)  # Only first activity has laps
        missing = db.get_activities_without_laps()
        assert len(missing) == 1
        assert missing[0][0] == 2002  # Second activity still missing

    def test_all_have_laps(self, sample_activity_dicts, sample_lap_dtos):
        db.save_activities(sample_activity_dicts)
        db.save_laps(2001, sample_lap_dtos)
        db.save_laps(2002, sample_lap_dtos)
        missing = db.get_activities_without_laps()
        assert len(missing) == 0

    def test_empty_database(self):
        missing = db.get_activities_without_laps()
        assert len(missing) == 0
