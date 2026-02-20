"""Tests for src.stats — pure function tests on summary statistics."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.stats import (
    _fmt_pace,
    get_available_years,
    monthly_breakdown,
    personal_records,
    year_highlights,
    year_totals,
)


# ── _fmt_pace ────────────────────────────────────────────


class TestFmtPace:
    def test_normal_pace(self):
        assert _fmt_pace(5.5) == "5:30 min/km"

    def test_sub_four(self):
        assert _fmt_pace(3.75) == "3:45 min/km"

    def test_exact_minute(self):
        assert _fmt_pace(5.0) == "5:00 min/km"

    def test_high_pace(self):
        assert _fmt_pace(7.25) == "7:15 min/km"


# ── get_available_years ──────────────────────────────────


class TestGetAvailableYears:
    def test_multiple_years(self, sample_activities_df):
        # Add activities from different years
        df = sample_activities_df.copy()
        df.loc[0, "start_time"] = datetime(2024, 3, 15)
        df.loc[1, "start_time"] = datetime(2023, 6, 20)
        result = get_available_years(df)
        assert 2025 in result
        assert 2024 in result
        assert 2023 in result
        # Sorted descending
        assert result == sorted(result, reverse=True)

    def test_single_year(self, sample_activities_df):
        result = get_available_years(sample_activities_df)
        assert result == [2025]

    def test_empty_df(self, empty_df):
        assert get_available_years(empty_df) == []


# ── year_totals ──────────────────────────────────────────


class TestYearTotals:
    def test_normal(self, sample_activities_df):
        totals = year_totals(sample_activities_df)
        assert totals["runs"] == 5
        assert totals["total_km"] == pytest.approx(56.0)  # 8+10+21+5+12
        expected_hours = (2400 + 2700 + 6300 + 1800 + 3600) / 60 / 60
        assert totals["total_hours"] == pytest.approx(expected_hours)
        assert totals["total_elevation"] == pytest.approx(280.0)
        assert totals["total_calories"] == pytest.approx(3550.0)

    def test_empty_df(self, empty_df):
        totals = year_totals(empty_df)
        assert totals["runs"] == 0
        assert totals["total_km"] == 0


# ── year_highlights ──────────────────────────────────────


class TestYearHighlights:
    def test_best_month(self, sample_activities_df):
        highlights = year_highlights(sample_activities_df)
        # All activities are in June, so best month is Jun
        assert highlights["best_month"]["month"] == "Jun"
        assert highlights["best_month"]["runs"] == 5

    def test_longest_streak(self, sample_activities_df):
        highlights = year_highlights(sample_activities_df)
        # Days: Jun 1, Jun 2 (streak=2), Jun 4, Jun 5 (streak=2), Jun 7
        assert highlights["longest_streak"] == 2

    def test_single_activity(self, single_activity_df):
        highlights = year_highlights(single_activity_df)
        assert highlights["longest_streak"] == 1
        assert highlights["longest_run"]["km"] == pytest.approx(8.0)

    def test_fastest_run(self, sample_activities_df):
        highlights = year_highlights(sample_activities_df)
        # Tempo Run has fastest pace: 2700s / (10km) = 4.5 min/km
        assert highlights["fastest_run"]["name"] == "Tempo Run"

    def test_longest_run(self, sample_activities_df):
        highlights = year_highlights(sample_activities_df)
        assert highlights["longest_run"]["km"] == pytest.approx(21.0)
        assert highlights["longest_run"]["name"] == "Long Run"


# ── monthly_breakdown ────────────────────────────────────


class TestMonthlyBreakdown:
    def test_all_twelve_months(self, sample_activities_df):
        result = monthly_breakdown(sample_activities_df)
        assert len(result) == 12
        assert list(result.index) == list(range(1, 13))

    def test_months_with_zero_runs(self, sample_activities_df):
        result = monthly_breakdown(sample_activities_df)
        # Only June has data; all other months should be 0
        assert result.loc[1, "runs"] == 0  # January
        assert result.loc[6, "runs"] == 5  # June
        assert result.loc[12, "runs"] == 0  # December

    def test_month_names(self, sample_activities_df):
        result = monthly_breakdown(sample_activities_df)
        assert result.loc[1, "month_name"] == "Jan"
        assert result.loc[6, "month_name"] == "Jun"
        assert result.loc[12, "month_name"] == "Dec"


# ── personal_records ─────────────────────────────────────


class TestPersonalRecords:
    def test_fastest_1k(self, sample_activities_df):
        prs = personal_records(sample_activities_df)
        assert "fastest_1k" in prs
        # Tempo Run has best pace (4.5 min/km)
        assert "Tempo Run" in prs["fastest_1k"]["detail"]

    def test_fastest_5k(self, sample_activities_df):
        prs = personal_records(sample_activities_df)
        assert "fastest_5k" in prs
        # Among runs >= 5km, Tempo Run is fastest
        assert "Tempo Run" in prs["fastest_5k"]["detail"]

    def test_longest_run(self, sample_activities_df):
        prs = personal_records(sample_activities_df)
        assert "longest_run" in prs
        assert "21.00" in prs["longest_run"]["value"]

    def test_no_qualifying_runs(self):
        """All runs under 1km — no 1K or 5K records."""
        df = pd.DataFrame({
            "activity_id": [1],
            "name": ["Short"],
            "start_time": [datetime(2025, 1, 1)],
            "distance_km": [0.5],
            "duration_min": [3.0],
            "pace_min_km": [6.0],
        })
        df["start_time"] = pd.to_datetime(df["start_time"])
        prs = personal_records(df)
        assert "fastest_1k" not in prs
        assert "fastest_5k" not in prs
        # Longest run is still tracked
        assert "longest_run" in prs

    def test_empty_df(self, empty_df):
        prs = personal_records(empty_df)
        assert prs == {}
