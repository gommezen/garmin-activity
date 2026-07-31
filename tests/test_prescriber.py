"""Tests for src.prescriber — the rule engine behind the brief."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from src import prescriber

BASE = datetime(2026, 8, 3, 8, 0, 0)       # a Monday
SAT_BASE = datetime(2026, 8, 8, 8, 0, 0)   # the Saturday of the same week
MONDAY = date(2026, 8, 3)
WEDNESDAY = date(2026, 8, 5)
SATURDAY = date(2026, 8, 8)


def _history(rows, anchor=BASE):
    """rows: list of (days_ago, km, minutes, hr), counted back from `anchor`.

    Tests that run on a day other than Monday anchor to that day, so a
    fixture meaning "two runs a week for four weeks" still lands relative
    to the `today` under test.
    """
    return pd.DataFrame([
        {"activity_id": 1000 + i, "name": "Run",
         "start_time": anchor - timedelta(days=days_ago),
         "distance_km": km, "duration_min": minutes,
         "pace_min_km": minutes / km, "avg_hr": hr}
        for i, (days_ago, km, minutes, hr) in enumerate(rows)
    ])


def _profile(**over):
    p = {"goal_type": "return_to_running", "goal_target": None,
         "days_available": ["Mon", "Wed", "Fri", "Sat"], "max_hr": 190.0}
    p.update(over)
    return p


# Two runs a week for four weeks — base established, steady load.
STEADY = []
for _w in range(4):
    STEADY += [(_w * 7 + 2, 6.0, 37.0, 148.0), (_w * 7 + 5, 6.0, 37.0, 148.0)]


class TestRestRule:
    def test_rest_when_day_not_available(self):
        p = prescriber.prescribe(_profile(days_available=["Tue"]),
                                 _history(STEADY), MONDAY, None)
        assert p["session_type"] == "rest"
        assert p["distance_km"] is None

    def test_rest_on_load_spike(self):
        rows = [(d, 3.0, 18.0, 145.0) for d in range(8, 29, 2)]
        rows += [(1, 15.0, 90.0, 150.0), (2, 15.0, 90.0, 150.0)]
        p = prescriber.prescribe(_profile(), _history(rows), MONDAY, None)
        assert p["session_type"] == "rest"
        assert any("load" in e["value"].lower() for e in p["evidence"])

    def test_rest_after_three_consecutive_days(self):
        rows = STEADY + [(1, 5.0, 31.0, 148.0), (2, 5.0, 31.0, 148.0),
                         (3, 5.0, 31.0, 148.0)]
        p = prescriber.prescribe(_profile(), _history(rows), MONDAY, None)
        assert p["session_type"] == "rest"

    def test_rest_when_wrecked(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, "wrecked")
        assert p["session_type"] == "rest"

    def test_good_feel_does_not_force_rest(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, "good")
        assert p["session_type"] != "rest"


class TestLongRule:
    def test_long_on_the_last_available_day(self):
        p = prescriber.prescribe(_profile(), _history(STEADY, anchor=SAT_BASE),
                                 SATURDAY, None)
        assert p["session_type"] == "long"
        assert p["distance_km"] > 6.0

    def test_no_long_without_base(self):
        p = prescriber.prescribe(_profile(), _history([(2, 5.0, 30.0, 148.0)]),
                                 SATURDAY, None)
        assert p["session_type"] == "easy"

    def test_long_capped_at_previous_longest_plus_ten_percent(self):
        # The 10 km sits 10 days back: inside the 28-day window that sets the
        # cap, outside the rolling 7 days that would count it as already done.
        rows = STEADY + [(10, 10.0, 62.0, 150.0)]
        p = prescriber.prescribe(_profile(), _history(rows, anchor=SAT_BASE),
                                 SATURDAY, None)
        assert p["session_type"] == "long"
        assert p["distance_km"] <= 11.0

    def test_no_second_long_within_seven_days(self):
        rows = STEADY + [(3, 10.0, 62.0, 150.0)]
        p = prescriber.prescribe(_profile(), _history(rows, anchor=SAT_BASE),
                                 SATURDAY, None)
        assert p["session_type"] != "long"


class TestTempoRule:
    def test_tempo_for_time_based_goal(self):
        p = prescriber.prescribe(_profile(goal_type="break_45"),
                                 _history(STEADY), MONDAY, None)
        assert p["session_type"] == "tempo"

    def test_no_tempo_for_distance_goal(self):
        p = prescriber.prescribe(_profile(goal_type="first_10k"),
                                 _history(STEADY), MONDAY, None)
        assert p["session_type"] == "easy"

    def test_no_second_tempo_within_seven_days(self):
        rows = STEADY + [(3, 6.0, 28.0, 172.0)]     # a hard effort three days ago
        p = prescriber.prescribe(_profile(goal_type="break_45"),
                                 _history(rows), WEDNESDAY, None)
        assert p["session_type"] == "easy"

    def test_hard_effort_yesterday_blocks_tempo_across_the_week_boundary(self):
        """Sunday's tempo must suppress Monday's — this is why the window rolls."""
        rows = STEADY + [(1, 6.0, 28.0, 172.0)]     # Sunday, the day before MONDAY
        p = prescriber.prescribe(_profile(goal_type="break_45"),
                                 _history(rows), MONDAY, None)
        assert p["session_type"] == "easy"


class TestEasyDefaults:
    def test_easy_distance_scales_from_recent_mean(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["session_type"] == "easy"
        assert 3.6 <= p["distance_km"] <= 4.8

    def test_pace_band_brackets_recent_easy_pace(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        lo, hi = p["pace_band_s"]
        assert lo < 370 < hi
        assert hi - lo == 20

    def test_hr_cap_from_observed_easy_hr(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["hr_cap"] == 153

    def test_hr_cap_falls_back_to_max_hr_fraction(self):
        p = prescriber.prescribe(_profile(), _history([]), MONDAY, None)
        assert p["hr_cap"] == 148


class TestEnvelope:
    def test_always_has_date_and_evidence(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["date"] == "2026-08-03"
        assert len(p["evidence"]) >= 1
        assert all({"label", "value"} == set(e) for e in p["evidence"])

    def test_short_history_says_so(self):
        p = prescriber.prescribe(_profile(), _history([(1, 5.0, 30.0, 145.0)]),
                                 MONDAY, None)
        assert any("history" in e["value"].lower() for e in p["evidence"])

    def test_week_target_grows_by_ten_percent(self):
        p = prescriber.prescribe(_profile(), _history(STEADY), MONDAY, None)
        assert p["week"]["target_km"] == pytest.approx(13.2, abs=0.1)
