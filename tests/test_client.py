"""Tests for src.client — mocked API interaction tests."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.client import pull_activities, pull_laps


@pytest.fixture
def mock_garmin():
    """A mocked Garmin client."""
    client = MagicMock()
    client.get_activities_by_date.return_value = [
        {"activityId": 101, "activityName": "Run 1", "distance": 10000},
        {"activityId": 102, "activityName": "Run 2", "distance": 8000},
        {"activityId": 103, "activityName": "Run 3", "distance": 5000},
    ]
    return client


class TestPullActivities:
    def test_date_range(self, mock_garmin):
        result = pull_activities(mock_garmin, "running", days=30, limit=0)
        mock_garmin.get_activities_by_date.assert_called_once()
        call_kwargs = mock_garmin.get_activities_by_date.call_args
        assert call_kwargs[1]["activitytype"] == "running"
        assert len(result) == 3

    def test_limit(self, mock_garmin):
        result = pull_activities(mock_garmin, "running", days=30, limit=2)
        assert len(result) == 2
        assert result[0]["activityId"] == 101
        assert result[1]["activityId"] == 102

    def test_empty_results(self, mock_garmin):
        mock_garmin.get_activities_by_date.return_value = []
        result = pull_activities(mock_garmin, "running", days=30, limit=0)
        assert result == []


class TestPullLaps:
    def test_normal_fetch(self):
        client = MagicMock()
        client.get_activity_splits.return_value = {
            "lapDTOs": [
                {"lapIndex": 0, "distance": 1000, "duration": 270},
                {"lapIndex": 1, "distance": 1000, "duration": 280},
            ]
        }
        laps = pull_laps(client, 101)
        assert len(laps) == 2
        client.get_activity_splits.assert_called_once_with("101")

    def test_retry_on_rate_limit(self):
        from garminconnect import GarminConnectTooManyRequestsError

        client = MagicMock()
        # Fail once with rate limit, then succeed
        client.get_activity_splits.side_effect = [
            GarminConnectTooManyRequestsError("rate limited"),
            {"lapDTOs": [{"lapIndex": 0, "distance": 1000}]},
        ]
        with patch("src.client.time.sleep"):  # Don't actually sleep in tests
            laps = pull_laps(client, 101, max_retries=3)
        assert len(laps) == 1
        assert client.get_activity_splits.call_count == 2

    def test_all_retries_exhausted(self):
        from garminconnect import GarminConnectTooManyRequestsError

        client = MagicMock()
        client.get_activity_splits.side_effect = GarminConnectTooManyRequestsError(
            "rate limited"
        )
        with patch("src.client.time.sleep"):
            laps = pull_laps(client, 101, max_retries=2)
        assert laps == []
        assert client.get_activity_splits.call_count == 2

    def test_empty_lap_response(self):
        client = MagicMock()
        client.get_activity_splits.return_value = {"lapDTOs": []}
        laps = pull_laps(client, 101)
        assert laps == []
