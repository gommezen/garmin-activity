"""Tests for src.store — append-only prescription and debrief storage."""

import pytest

from src import db, store


@pytest.fixture(autouse=True)
def _patch_db_path(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")


class TestProfile:
    def test_defaults_when_no_row(self):
        p = store.get_profile()
        assert p["units"] == "km"
        assert p["goal_type"] == "return_to_running"
        assert p["days_available"] == ["Mon", "Wed", "Fri", "Sat"]


class TestPrescriptions:
    def test_save_and_get(self):
        pid = store.save_prescription(
            "2026-08-03", {"session_type": "easy"}, "Run slow.", "Slow is fast.",
            "claude-opus-5", "v1",
        )
        assert pid > 0
        got = store.get_prescription("2026-08-03")
        assert got["prescription"]["session_type"] == "easy"
        assert got["dialogue"] == "Run slow."
        assert got["word"] == "Slow is fast."

    def test_missing_date_returns_none(self):
        assert store.get_prescription("2026-01-01") is None

    def test_first_prescription_date(self):
        assert store.first_prescription_date() is None
        store.save_prescription("2026-08-05", {}, "a", "w", "m", "v")
        store.save_prescription("2026-08-03", {}, "b", "w", "m", "v")
        assert store.first_prescription_date() == "2026-08-03"

    def test_one_per_date(self):
        store.save_prescription("2026-08-03", {}, "a", "w", "m", "v")
        with pytest.raises(Exception):
            store.save_prescription("2026-08-03", {}, "b", "w", "m", "v")


class TestDebriefs:
    def test_save_and_fetch_by_activity(self):
        did = store.save_debrief(
            1001, None, {"assessment": "solid"}, "You held the pace.",
            "Rest tomorrow.", "claude-opus-5", "v1",
        )
        got = store.get_debrief_by_activity(1001)
        assert got["id"] == did
        assert got["verdict"]["assessment"] == "solid"
        assert got["instruction"] == "Rest tomorrow."

    def test_recent_instructions_newest_first(self):
        store.save_debrief(1, None, {}, "d", "first", "m", "v")
        store.save_debrief(2, None, {}, "d", "second", "m", "v")
        store.save_debrief(3, None, {}, "d", "third", "m", "v")
        assert store.recent_instructions(2) == ["third", "second"]

    def test_null_instruction_skipped_in_memory(self):
        store.save_debrief(1, None, {}, "d", None, "m", "v")
        store.save_debrief(2, None, {}, "d", "kept", "m", "v")
        assert store.recent_instructions() == ["kept"]


class TestGuardedFills:
    def test_feel_set_once(self):
        did = store.save_debrief(1, None, {}, "d", None, "m", "v")
        assert store.set_feel(did, "good") is True
        assert store.set_feel(did, "flat") is False
        assert store.get_debrief(did)["feel"] == "good"

    def test_followup_set_once(self):
        did = store.save_debrief(1, None, {}, "d", None, "m", "v")
        assert store.set_followup(did, "Why?", "Because.") is True
        assert store.set_followup(did, "Again?", "No.") is False
        got = store.get_debrief(did)
        assert got["followup_q"] == "Why?"
        assert got["followup_a"] == "Because."
