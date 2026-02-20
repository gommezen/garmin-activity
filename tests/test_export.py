"""Tests for src.export — JSON and CSV export format validation."""

import csv
import json

import pytest

from src.export import save_to_csv, save_to_json


@pytest.fixture
def sample_activities():
    """Two sample activities in raw API format."""
    return [
        {
            "activityId": 5001,
            "activityName": "Morning Run",
            "startTimeLocal": "2025-09-01 07:00:00",
            "distance": 10000.0,
            "duration": 3000.0,
            "calories": 600,
            "averageHR": 150,
            "maxHR": 175,
            "averageSpeed": 3.333,
            "elevationGain": 40,
            "averageRunningCadenceInStepsPerMinute": 172,
        },
        {
            "activityId": 5002,
            "activityName": "Hill Repeats",
            "startTimeLocal": "2025-09-02 17:30:00",
            "distance": 7500.0,
            "duration": 2400.0,
            "calories": 520,
            "averageHR": 168,
            "maxHR": 190,
            "averageSpeed": 3.125,
            "elevationGain": 120,
            "averageRunningCadenceInStepsPerMinute": 176,
        },
    ]


class TestSaveToJson:
    def test_valid_json(self, tmp_path, monkeypatch, sample_activities):
        monkeypatch.setattr("src.export.OUTPUT_DIR", tmp_path)
        save_to_json(sample_activities, "running")
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert len(data) == 2

    def test_correct_structure(self, tmp_path, monkeypatch, sample_activities):
        monkeypatch.setattr("src.export.OUTPUT_DIR", tmp_path)
        save_to_json(sample_activities, "running")
        files = list(tmp_path.glob("*.json"))
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data[0]["activityId"] == 5001
        assert data[0]["activityName"] == "Morning Run"

    def test_filename_contains_sport(self, tmp_path, monkeypatch, sample_activities):
        monkeypatch.setattr("src.export.OUTPUT_DIR", tmp_path)
        save_to_json(sample_activities, "running")
        files = list(tmp_path.glob("*.json"))
        assert "running" in files[0].name


class TestSaveToCsv:
    def test_correct_headers(self, tmp_path, monkeypatch, sample_activities):
        monkeypatch.setattr("src.export.OUTPUT_DIR", tmp_path)
        save_to_csv(sample_activities, "running")
        files = list(tmp_path.glob("*.csv"))
        assert len(files) == 1
        with open(files[0], encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
        expected = [
            "date", "name", "distance_km", "duration_min", "pace_min_km",
            "calories", "avg_hr", "max_hr", "cadence_spm", "elevation_m",
        ]
        assert headers == expected

    def test_formatted_values(self, tmp_path, monkeypatch, sample_activities):
        monkeypatch.setattr("src.export.OUTPUT_DIR", tmp_path)
        save_to_csv(sample_activities, "running")
        files = list(tmp_path.glob("*.csv"))
        with open(files[0], encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row = next(reader)
        # distance_km = 10000/1000 = 10.00
        assert row[2] == "10.00"
        # duration_min = 3000/60 = 50.0
        assert row[3] == "50.0"

    def test_zero_distance_no_division_error(self, tmp_path, monkeypatch):
        """Activity with zero distance should not crash."""
        acts = [{
            "activityId": 9001,
            "activityName": "Zero Distance",
            "startTimeLocal": "2025-09-03 12:00:00",
            "distance": 0,
            "duration": 60,
            "calories": 10,
            "averageHR": None,
            "maxHR": None,
            "averageSpeed": None,
            "elevationGain": None,
            "averageRunningCadenceInStepsPerMinute": None,
        }]
        monkeypatch.setattr("src.export.OUTPUT_DIR", tmp_path)
        save_to_csv(acts, "running")
        files = list(tmp_path.glob("*.csv"))
        with open(files[0], encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)
            row = next(reader)
        # Pace should be empty (no division by zero crash)
        assert row[4] == ""
