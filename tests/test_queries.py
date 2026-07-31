"""Tests for src.queries — windowed views used by the engines."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from src import queries


def _df(rows):
    """rows: list of (days_ago, km, minutes, hr)."""
    today = datetime(2026, 8, 3, 8, 0, 0)
    data = []
    for i, (days_ago, km, minutes, hr) in enumerate(rows):
        data.append({
            "activity_id": 1000 + i,
            "name": "Run",
            "start_time": today - timedelta(days=days_ago),
            "distance_km": km,
            "duration_min": minutes,
            "pace_min_km": minutes / km,
            "avg_hr": hr,
        })
    return pd.DataFrame(data)


TODAY = date(2026, 8, 3)


class TestWindows:
    def test_runs_in_window_excludes_older(self):
        df = _df([(1, 5, 30, 145), (10, 5, 30, 145)])
        assert len(queries.runs_in_window(df, TODAY, 7)) == 1

    def test_km_in_window_sums(self):
        df = _df([(1, 5, 30, 145), (3, 7, 42, 145)])
        assert queries.km_in_window(df, TODAY, 7) == pytest.approx(12.0)

    def test_empty_window_is_zero(self):
        assert queries.km_in_window(_df([]), TODAY, 7) == 0.0

    def test_km_since_includes_run_on_start_date(self):
        # km_since's lower bound is inclusive, unlike km_in_window's — a
        # calendar week must count the Monday it starts on.
        start = TODAY - timedelta(days=7)
        df = _df([(7, 5, 30, 145)])  # exactly on `start`
        assert queries.km_since(df, start, TODAY) == pytest.approx(5.0)


class TestAcwr:
    def test_none_when_history_too_short(self):
        df = _df([(1, 5, 30, 145), (3, 5, 30, 145)])
        assert queries.acwr(df, TODAY) is None

    def test_flat_load_is_about_one(self):
        rows = [(d, 5, 30, 145) for d in range(1, 29, 2)]
        assert queries.acwr(_df(rows), TODAY) == pytest.approx(1.0, abs=0.35)

    def test_spike_exceeds_one_four(self):
        rows = [(d, 3, 18, 145) for d in range(8, 29, 2)]
        rows += [(1, 15, 90, 150), (3, 15, 90, 150)]
        assert queries.acwr(_df(rows), TODAY) > 1.4


class TestPaceAndHr:
    def test_median_easy_pace_ignores_fast_efforts(self):
        rows = [(2, 6, 36, 140), (4, 6, 36, 140), (6, 6, 36, 140), (8, 5, 20, 178)]
        pace = queries.median_easy_pace_s(_df(rows), TODAY)
        assert pace == pytest.approx(360, abs=5)

    def test_none_without_data(self):
        assert queries.median_easy_pace_s(_df([]), TODAY) is None

    def test_median_easy_hr(self):
        rows = [(2, 6, 36, 140), (4, 6, 36, 144), (6, 6, 36, 142)]
        assert queries.median_easy_hr(_df(rows), TODAY) == pytest.approx(142, abs=2)

    def test_median_easy_hr_none_without_data(self):
        assert queries.median_easy_hr(_df([]), TODAY) is None


class TestStreaksAndGaps:
    def test_consecutive_run_days(self):
        df = _df([(1, 5, 30, 145), (2, 5, 30, 145), (3, 5, 30, 145), (9, 5, 30, 145)])
        assert queries.consecutive_run_days(df, TODAY) == 3

    def test_consecutive_zero_when_gap_yesterday(self):
        df = _df([(4, 5, 30, 145)])
        assert queries.consecutive_run_days(df, TODAY) == 0

    def test_days_since_last_run(self):
        assert queries.days_since_last_run(_df([(4, 5, 30, 145)]), TODAY) == 4

    def test_days_since_none_when_empty(self):
        assert queries.days_since_last_run(_df([]), TODAY) is None


class TestBase:
    def test_base_established(self):
        rows = []
        for week in range(3):
            rows += [(week * 7 + 1, 5, 30, 145), (week * 7 + 4, 5, 30, 145)]
        assert queries.weeks_with_min_runs(_df(rows), TODAY) is True

    def test_base_not_established_with_one_run_per_week(self):
        rows = [(1, 5, 30, 145), (8, 5, 30, 145), (15, 5, 30, 145)]
        assert queries.weeks_with_min_runs(_df(rows), TODAY) is False


class TestLaps:
    def test_laps_for_shapes_rows(self):
        laps = pd.DataFrame([
            {"activity_id": 1, "lap_index": 0, "distance_km": 1.0,
             "duration_min": 5.5, "pace_min_km": 5.5, "avg_hr": 150.0,
             "cadence": 172.0, "elevation_gain": 4.0},
        ])
        out = queries.laps_for(laps, 1)
        assert out == [{"km": 1.0, "pace_s": 330, "hr": 150, "cadence": 172, "elev": 4}]
