"""Tests for src.verdict — the deterministic judge."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from src import verdict

TODAY = date(2026, 8, 3)
BASE = datetime(2026, 8, 3, 8, 0, 0)


def _history(rows):
    """rows: list of (days_ago, km, minutes, hr)."""
    return pd.DataFrame([
        {"activity_id": 1000 + i, "name": "Run",
         "start_time": BASE - timedelta(days=days_ago),
         "distance_km": km, "duration_min": minutes,
         "pace_min_km": minutes / km, "avg_hr": hr}
        for i, (days_ago, km, minutes, hr) in enumerate(rows)
    ])


def _run(km=6.0, minutes=37.0, hr=151.0, days_ago=0):
    return {"activity_id": 9001, "start_time": BASE - timedelta(days=days_ago),
            "distance_km": km, "duration_min": minutes,
            "pace_min_km": minutes / km, "avg_hr": hr}


STEADY = [(d, 6.0, 37.0, 150.0) for d in range(2, 29, 3)]
NO_LAPS = pd.DataFrame()


class TestShape:
    def test_core_fields_present(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["state"] == "new_run"
        assert v["run"]["km"] == 6.0
        assert v["run"]["pace_s"] == 370
        assert set(v) >= {"run", "vs_self", "flags", "assessment", "streak"}

    def test_memory_passed_through(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None,
                          ["Rest tomorrow."])
        assert v["last_instructions"] == ["Rest tomorrow."]


class TestAssessment:
    def test_solid_is_the_default(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "solid"

    def test_caution_on_load_spike(self):
        rows = [(d, 3.0, 18.0, 145.0) for d in range(8, 29, 2)]
        rows += [(1, 15.0, 90.0, 150.0), (3, 15.0, 90.0, 150.0)]
        v = verdict.judge(_run(), _history(rows), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "caution"
        assert "load_spike" in v["flags"]

    def test_caution_on_oversized_run(self):
        run = _run(km=12.0, minutes=74.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "caution"

    def test_excellent_when_faster_at_normal_hr(self):
        run = _run(km=6.0, minutes=34.0, hr=150.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "excellent"

    def test_easy_when_slower_at_low_hr(self):
        run = _run(km=6.0, minutes=41.0, hr=132.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["assessment"] == "easy"


class TestFlags:
    def test_negative_split(self):
        laps = pd.DataFrame([
            {"activity_id": 9001, "lap_index": 0, "distance_km": 1.0,
             "duration_min": 6.4, "pace_min_km": 6.4, "avg_hr": 148.0,
             "cadence": 170.0, "elevation_gain": 2.0},
            {"activity_id": 9001, "lap_index": 1, "distance_km": 1.0,
             "duration_min": 6.0, "pace_min_km": 6.0, "avg_hr": 152.0,
             "cadence": 172.0, "elevation_gain": 2.0},
        ])
        v = verdict.judge(_run(), _history(STEADY), laps, TODAY, None, [])
        assert "negative_split" in v["flags"]
        assert len(v["run"]["laps"]) == 2

    def test_long_gap(self):
        v = verdict.judge(_run(), _history([(20, 6.0, 37.0, 150.0)]),
                          NO_LAPS, TODAY, None, [])
        assert "long_gap" in v["flags"]

    def test_longest_run_4wk(self):
        run = _run(km=9.0, minutes=56.0)
        v = verdict.judge(run, _history(STEADY), NO_LAPS, TODAY, None, [])
        assert "longest_run_4wk" in v["flags"]


class TestVsPrescription:
    def test_none_without_prescription(self):
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, None, [])
        assert v["vs_prescription"] is None

    def test_in_band(self):
        p = {"distance_km": 6.0, "pace_band_s": [360, 380]}
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, p, [])
        assert v["vs_prescription"]["pace"] == "in_band"

    def test_above_band(self):
        p = {"distance_km": 6.0, "pace_band_s": [380, 400]}
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, p, [])
        assert v["vs_prescription"]["pace"] == "above_band"
        assert v["vs_prescription"]["distance_delta_km"] == pytest.approx(0.0)

    def test_rest_day_prescription_does_not_raise(self):
        # A prescribed rest day carries explicit Nones (not missing keys) —
        # ran anyway, and the judge should degrade gracefully rather than
        # raising on unpacking `pace_band_s`.
        p = {"session_type": "rest", "distance_km": None,
             "pace_band_s": None, "hr_cap": None}
        v = verdict.judge(_run(), _history(STEADY), NO_LAPS, TODAY, p, [])
        assert v["vs_prescription"]["pace"] is None
        assert v["vs_prescription"]["distance_delta_km"] == pytest.approx(
            v["run"]["km"])
